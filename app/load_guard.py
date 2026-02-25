import time
import threading
import logging
from typing import Any

from app.config_manager import load_config
from app.system_monitor import get_cpu_stats, get_memory_stats
from app.docker_manager import get_containers, control_container, SERVICE_MAP
from app.priority_manager import effective_priority_services
from app.native_manager import (
    control_uprock,
    control_wipter,
    get_uprock_details,
    get_wipter_details,
    is_systemd_unit_present,
    WIPTER_SYSTEMD_UNIT,
)
from app.runtime_state import load_load_guard_state, save_load_guard_state


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LoadGuard")


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    raw = str(value).strip().lower()
    if raw == "":
        return default
    return raw == "true"


def _to_int(value: Any, default: int) -> int:
    if value is None:
        return default
    raw = str(value).strip()
    if raw.isdigit():
        return int(raw)
    return default


def _load_guard_config(config: dict[str, str]) -> dict[str, int | bool]:
    temp_c = _to_int(config.get("LOAD_REDUCTION_TEMP_C"), 70)
    cpu_pct = _to_int(config.get("LOAD_REDUCTION_CPU_PCT"), 90)
    ram_pct = _to_int(config.get("LOAD_REDUCTION_RAM_PCT"), 90)

    recover_temp_c = _to_int(config.get("LOAD_REDUCTION_RECOVER_TEMP_C"), max(0, temp_c - 5))
    recover_cpu_pct = _to_int(config.get("LOAD_REDUCTION_RECOVER_CPU_PCT"), max(0, cpu_pct - 10))
    recover_ram_pct = _to_int(config.get("LOAD_REDUCTION_RECOVER_RAM_PCT"), max(0, ram_pct - 10))

    interval_sec = max(5, _to_int(config.get("LOAD_REDUCTION_INTERVAL_SEC"), 10))
    trigger_sec = max(5, _to_int(config.get("LOAD_REDUCTION_TRIGGER_SEC"), 30))
    recover_sec = max(5, _to_int(config.get("LOAD_REDUCTION_RECOVER_SEC"), 60))
    cooldown_sec = max(5, _to_int(config.get("LOAD_REDUCTION_COOLDOWN_SEC"), 30))

    enabled = _to_bool(config.get("ENABLE_LOAD_REDUCTION"), True)

    return {
        "enabled": enabled,
        "temp_c": temp_c,
        "cpu_pct": cpu_pct,
        "ram_pct": ram_pct,
        "recover_temp_c": recover_temp_c,
        "recover_cpu_pct": recover_cpu_pct,
        "recover_ram_pct": recover_ram_pct,
        "interval_sec": interval_sec,
        "trigger_sec": trigger_sec,
        "recover_sec": recover_sec,
        "cooldown_sec": cooldown_sec,
    }


def _should_service_be_enabled(config: dict[str, str], service_name: str) -> bool:
    if service_name == "uprock":
        return (config.get("ENABLE_UPROCK") or "false").lower() == "true"
    if service_name == "wipter" and is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
        return (config.get("ENABLE_WIPTER") or "false").lower() == "true"
    for enable_key, mapped in SERVICE_MAP.items():
        if mapped == service_name:
            return (config.get(enable_key) or "false").lower() == "true"
    return False


def _stop_service(service_name: str) -> tuple[bool, str]:
    if service_name == "uprock":
        return control_uprock("stop")
    if service_name == "wipter" and is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
        return control_wipter("stop")
    return control_container(service_name, "stop")


def _start_service(service_name: str) -> tuple[bool, str]:
    if service_name == "uprock":
        return control_uprock("start")
    if service_name == "wipter" and is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
        return control_wipter("start")
    return control_container(service_name, "start")


def _pick_shed_candidate(config: dict[str, str], paused: set[str], priority: set[str]) -> str | None:
    containers = get_containers()
    best_name: str | None = None
    best_mem = -1

    for c in containers:
        name = str(c.get("name") or "").strip().lower()
        if not name or name in paused or name in priority:
            continue
        status = str(c.get("status") or "").strip().lower()
        if status != "running":
            continue
        if not _should_service_be_enabled(config, name):
            continue
        mem = c.get("memory") or 0
        try:
            mem_val = int(mem)
        except Exception:
            mem_val = 0
        if mem_val > best_mem:
            best_mem = mem_val
            best_name = name

    uprock = get_uprock_details()
    if str(uprock.get("status") or "").lower() == "running":
        name = "uprock"
        if name not in paused and name not in priority and _should_service_be_enabled(config, name):
            mem = uprock.get("memory") or 0
            try:
                mem_val = int(mem)
            except Exception:
                mem_val = 0
            if mem_val > best_mem:
                best_mem = mem_val
                best_name = name

    if is_systemd_unit_present(WIPTER_SYSTEMD_UNIT):
        wipter = get_wipter_details()
        if str(wipter.get("status") or "").lower() == "running":
            name = "wipter"
            if name not in paused and name not in priority and _should_service_be_enabled(config, name):
                mem = wipter.get("memory") or 0
                try:
                    mem_val = int(mem)
                except Exception:
                    mem_val = 0
                if mem_val > best_mem:
                    best_mem = mem_val
                    best_name = name

    return best_name


def _normalize_paused(paused: list[Any]) -> list[str]:
    cleaned: list[str] = []
    for item in paused:
        if isinstance(item, str):
            name = item.strip().lower()
            if name:
                cleaned.append(name)
    return cleaned


def load_guard_snapshot() -> dict[str, Any]:
    config = load_config()
    settings = _load_guard_config(config)
    state = load_load_guard_state() or {}
    paused = _normalize_paused(state.get("paused") or [])
    return {
        "active": bool(state.get("active") is True),
        "paused": paused,
        "reason": state.get("reason") if isinstance(state.get("reason"), dict) else None,
        "settings": settings,
    }


def load_guard_loop() -> None:
    state = load_load_guard_state() or {}
    active = bool(state.get("active") is True)
    paused = set(_normalize_paused(state.get("paused") or []))
    last_action_ts = int(state.get("last_action_ts") or 0)

    over_for = 0
    safe_for = 0

    while True:
        config = load_config()
        settings = _load_guard_config(config)
        interval = int(settings["interval_sec"])

        if not bool(settings["enabled"]):
            if active or paused:
                active = False
                paused = set()
                last_action_ts = 0
                save_load_guard_state({"active": False, "paused": [], "reason": None, "last_action_ts": 0})
            time.sleep(interval)
            continue

        cpu = get_cpu_stats()
        mem = get_memory_stats()
        temp = cpu.get("temp")
        cpu_pct = cpu.get("usage")
        ram_pct = mem.get("percent")

        temp_ok = isinstance(temp, (int, float))
        cpu_ok = isinstance(cpu_pct, (int, float))
        ram_ok = isinstance(ram_pct, (int, float))

        trigger = False
        safe = False
        if temp_ok and cpu_ok and ram_ok:
            trigger = (
                temp >= int(settings["temp_c"])
                and (cpu_pct >= int(settings["cpu_pct"]) or ram_pct >= int(settings["ram_pct"]))
            )
            safe = (
                temp <= int(settings["recover_temp_c"])
                and cpu_pct <= int(settings["recover_cpu_pct"])
                and ram_pct <= int(settings["recover_ram_pct"])
            )

        if trigger:
            over_for += interval
            safe_for = 0
        elif safe:
            safe_for += interval
            over_for = 0
        else:
            over_for = 0
            safe_for = 0

        priority = effective_priority_services(config)

        if not active:
            if over_for >= int(settings["trigger_sec"]):
                active = True
                reason = {"temp": temp, "cpu": cpu_pct, "ram": ram_pct}
                save_load_guard_state({"active": True, "paused": sorted(paused), "reason": reason, "last_action_ts": last_action_ts})
                logger.warning(f"Load reduction activated: temp={temp} cpu={cpu_pct} ram={ram_pct}")
            time.sleep(interval)
            continue

        now = int(time.time())

        to_remove: set[str] = set()
        for name in paused:
            if not _should_service_be_enabled(config, name):
                to_remove.add(name)
        if to_remove:
            paused -= to_remove

        if safe_for >= int(settings["recover_sec"]):
            if paused:
                name = sorted(paused)[0]
                success, msg = _start_service(name)
                if success:
                    paused.remove(name)
                    logger.info(f"Recovered service '{name}' after stabilization.")
                else:
                    logger.warning(f"Failed to recover service '{name}': {msg}")
                save_load_guard_state({"active": True, "paused": sorted(paused), "reason": None, "last_action_ts": last_action_ts})
            else:
                active = False
                last_action_ts = 0
                save_load_guard_state({"active": False, "paused": [], "reason": None, "last_action_ts": 0})
                logger.info("Load reduction cleared: system stabilized.")
            time.sleep(interval)
            continue

        if now - last_action_ts >= int(settings["cooldown_sec"]):
            candidate = _pick_shed_candidate(config, paused=paused, priority=priority)
            if candidate:
                success, msg = _stop_service(candidate)
                last_action_ts = now
                if success:
                    paused.add(candidate)
                    logger.warning(f"Stopped service '{candidate}' to reduce load.")
                else:
                    logger.warning(f"Failed to stop service '{candidate}': {msg}")
                reason = {"temp": temp, "cpu": cpu_pct, "ram": ram_pct}
                save_load_guard_state({"active": True, "paused": sorted(paused), "reason": reason, "last_action_ts": last_action_ts})

        time.sleep(interval)


def start_load_guard() -> threading.Thread:
    thread = threading.Thread(target=load_guard_loop, daemon=True)
    thread.start()
    return thread
