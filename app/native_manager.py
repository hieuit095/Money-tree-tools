import subprocess
import os
import sys
import hashlib
from dataclasses import dataclass

from app.config_manager import load_config
from app.log_utils import truncate_utf8_text
from app import runtime_state
from app.pingpong_configurator import apply_pingpong_configuration


@dataclass(frozen=True)
class NativeServiceDetails:
    installed: bool
    name: str
    status: str
    memory: int


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def is_systemd_unit_present(unit_name: str) -> bool:
    if sys.platform != "linux":
        return False
    result = _run(["systemctl", "status", unit_name])
    return result.returncode in (0, 3)


def get_systemd_unit_status(unit_name: str) -> str:
    if not is_systemd_unit_present(unit_name):
        return "not_installed"
    result = _run(["systemctl", "is-active", unit_name])
    if result.returncode == 0:
        return "running"
    return "stopped"


def get_systemd_unit_memory_current(unit_name: str) -> int:
    if not is_systemd_unit_present(unit_name):
        return 0
    result = _run(["systemctl", "show", unit_name, "-p", "MemoryCurrent", "--value"])
    if result.returncode != 0:
        return 0
    value = (result.stdout or "").strip()
    try:
        return int(value)
    except ValueError:
        return 0


def control_systemd_unit(unit_name: str, action: str) -> tuple[bool, str]:
    if action not in {"start", "stop", "restart"}:
        return False, "Invalid action"
    if not is_systemd_unit_present(unit_name):
        return False, f"Service '{unit_name}' is not installed"

    cmd = ["systemctl", action, unit_name] if getattr(os, "geteuid", lambda: 1)() == 0 else ["sudo", "systemctl", action, unit_name]
    result = _run(cmd)
    if result.returncode == 0:
        return True, "Success"
    msg = (result.stderr or result.stdout or "").strip()
    return False, msg or f"Failed to {action} {unit_name}"


def get_systemd_unit_logs(unit_name: str, tail: int = 200) -> str:
    if not is_systemd_unit_present(unit_name):
        return f"Service '{unit_name}' is not installed"
    result = _run(["journalctl", "-u", unit_name, "-n", str(tail), "--no-pager"])
    if result.returncode == 0:
        return truncate_utf8_text(result.stdout, max_bytes=5 * 1024 * 1024)
    msg = (result.stderr or result.stdout or "").strip()
    return truncate_utf8_text(msg or f"Failed to read logs for {unit_name}", max_bytes=5 * 1024 * 1024)


WIPTER_SYSTEMD_UNIT = "wipter.service"
UPROCK_SYSTEMD_UNIT = "uprock.service"


def get_wipter_details() -> dict:
    installed = is_systemd_unit_present(WIPTER_SYSTEMD_UNIT)
    status = get_systemd_unit_status(WIPTER_SYSTEMD_UNIT)
    memory = get_systemd_unit_memory_current(WIPTER_SYSTEMD_UNIT)
    details = NativeServiceDetails(
        installed=installed,
        name="wipter",
        status=status,
        memory=memory,
    )
    return {
        "installed": details.installed,
        "name": details.name,
        "status": details.status,
        "memory": details.memory,
    }


def control_wipter(action: str) -> tuple[bool, str]:
    return control_systemd_unit(WIPTER_SYSTEMD_UNIT, action)


def get_wipter_logs(tail: int = 200) -> str:
    return get_systemd_unit_logs(WIPTER_SYSTEMD_UNIT, tail=tail)


def get_uprock_details() -> dict:
    installed = is_systemd_unit_present(UPROCK_SYSTEMD_UNIT)
    status = get_systemd_unit_status(UPROCK_SYSTEMD_UNIT)
    memory = get_systemd_unit_memory_current(UPROCK_SYSTEMD_UNIT)
    details = NativeServiceDetails(
        installed=installed,
        name="uprock",
        status=status,
        memory=memory,
    )
    return {
        "installed": details.installed,
        "name": details.name,
        "status": details.status,
        "memory": details.memory,
    }


def control_uprock(action: str) -> tuple[bool, str]:
    return control_systemd_unit(UPROCK_SYSTEMD_UNIT, action)


def get_uprock_logs(tail: int = 200) -> str:
    return get_systemd_unit_logs(UPROCK_SYSTEMD_UNIT, tail=tail)


PINGPONG_SYSTEMD_UNIT = "pingpong.service"


def get_pingpong_details() -> dict:
    installed = is_systemd_unit_present(PINGPONG_SYSTEMD_UNIT)
    status = get_systemd_unit_status(PINGPONG_SYSTEMD_UNIT)
    memory = get_systemd_unit_memory_current(PINGPONG_SYSTEMD_UNIT)
    details = NativeServiceDetails(
        installed=installed,
        name="pingpong",
        status=status,
        memory=memory,
    )
    return {
        "installed": details.installed,
        "name": details.name,
        "status": details.status,
        "memory": details.memory,
    }


def control_pingpong(action: str) -> tuple[bool, str]:
    return control_systemd_unit(PINGPONG_SYSTEMD_UNIT, action)


def get_pingpong_logs(tail: int = 200) -> str:
    return get_systemd_unit_logs(PINGPONG_SYSTEMD_UNIT, tail=tail)


def apply_native_configuration() -> list[str]:
    config = load_config()
    results: list[str] = []
    should_enable = config.get("ENABLE_WIPTER", "false").lower() == "true"
    status = get_systemd_unit_status(WIPTER_SYSTEMD_UNIT)
    if should_enable and status != "running":
        success, msg = control_systemd_unit(WIPTER_SYSTEMD_UNIT, "start")
        results.append(f"wipter: start -> {'OK' if success else msg}")
    if not should_enable and status == "running":
        success, msg = control_systemd_unit(WIPTER_SYSTEMD_UNIT, "stop")
        results.append(f"wipter: stop -> {'OK' if success else msg}")
    if should_enable and status == "running":
        results.append("wipter: start -> OK")
    if not should_enable and status != "running":
        results.append("wipter: stop -> OK")

    should_enable = config.get("ENABLE_UPROCK", "false").lower() == "true"
    status = get_systemd_unit_status(UPROCK_SYSTEMD_UNIT)
    if should_enable and status != "running":
        success, msg = control_systemd_unit(UPROCK_SYSTEMD_UNIT, "start")
        results.append(f"uprock: start -> {'OK' if success else msg}")
    if not should_enable and status == "running":
        success, msg = control_systemd_unit(UPROCK_SYSTEMD_UNIT, "stop")
        results.append(f"uprock: stop -> {'OK' if success else msg}")
    if should_enable and status == "running":
        results.append("uprock: start -> OK")
    if not should_enable and status != "running":
        results.append("uprock: stop -> OK")

    should_enable = config.get("ENABLE_PINGPONG", "false").lower() == "true"
    status = get_systemd_unit_status(PINGPONG_SYSTEMD_UNIT)
    key = config.get("PINGPONG_KEY", "").strip()
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest() if key else ""
    pp_state = runtime_state.load_pingpong_state() or {}
    prev_key_hash = pp_state.get("device_key_hash") if isinstance(pp_state.get("device_key_hash"), str) else ""
    should_restart = bool(key_hash) and key_hash != prev_key_hash
    if should_enable:
        results.extend(apply_pingpong_configuration(config))
    if should_enable and status != "running":
        success, msg = control_systemd_unit(PINGPONG_SYSTEMD_UNIT, "start")
        results.append(f"pingpong: start -> {'OK' if success else msg}")
    if not should_enable and status == "running":
        success, msg = control_systemd_unit(PINGPONG_SYSTEMD_UNIT, "stop")
        results.append(f"pingpong: stop -> {'OK' if success else msg}")
    if should_enable and status == "running" and should_restart:
        success, msg = control_systemd_unit(PINGPONG_SYSTEMD_UNIT, "restart")
        results.append(f"pingpong: restart -> {'OK' if success else msg}")
    if should_enable and status == "running":
        results.append("pingpong: start -> OK")
    if not should_enable and status != "running":
        results.append("pingpong: stop -> OK")
    if should_enable and key_hash:
        merged = dict(pp_state) if isinstance(pp_state, dict) else {}
        merged["device_key_hash"] = key_hash
        runtime_state.save_pingpong_state(merged)

    return results
