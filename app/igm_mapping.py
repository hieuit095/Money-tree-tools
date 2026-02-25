import os
import platform
import re
import tempfile
from dataclasses import dataclass

import psutil

from app.config_manager import config_root


@dataclass(frozen=True)
class IGMServiceSpec:
    enable_key: str
    profile_var: str
    container_name: str


IGM_SERVICES: dict[str, IGMServiceSpec] = {
    "honeygain": IGMServiceSpec(enable_key="ENABLE_HONEYGAIN", profile_var="HONEYGAIN", container_name="honeygain"),
    "traffmonetizer": IGMServiceSpec(enable_key="ENABLE_TRAFFMONETIZER", profile_var="TRAFFMONETIZER", container_name="traffmonetizer"),
    "packetstream": IGMServiceSpec(enable_key="ENABLE_PACKETSTREAM", profile_var="PACKETSTREAM", container_name="packetstream"),
    "packetshare": IGMServiceSpec(enable_key="ENABLE_PACKETSHARE", profile_var="PACKETSHARE", container_name="packetshare"),
    "repocket": IGMServiceSpec(enable_key="ENABLE_REPOCKET", profile_var="REPOCKET", container_name="repocket"),
    "earnfm": IGMServiceSpec(enable_key="ENABLE_EARNFM", profile_var="EARNFM", container_name="earnfm"),
    "grass": IGMServiceSpec(enable_key="ENABLE_GRASS", profile_var="GRASS", container_name="grass"),
    "mysterium": IGMServiceSpec(enable_key="ENABLE_MYSTERIUM", profile_var="MYSTERIUM", container_name="mysterium"),
    "pawns": IGMServiceSpec(enable_key="ENABLE_PAWNS", profile_var="PAWNS", container_name="pawns"),
    "proxyrack": IGMServiceSpec(enable_key="ENABLE_PROXYRACK", profile_var="PROXYRACK", container_name="proxyrack"),
    "bitping": IGMServiceSpec(enable_key="ENABLE_BITPING", profile_var="BITPING", container_name="bitping"),
    "wipter": IGMServiceSpec(enable_key="ENABLE_WIPTER", profile_var="WIPTER", container_name="wipter"),
    "wizardgain": IGMServiceSpec(enable_key="ENABLE_WIZARDGAIN", profile_var="WIZARDGAIN", container_name="wizardgain"),
}


def _dotenv_escape(value: str) -> str:
    if value == "":
        return ""
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f"\"{escaped}\""


def _read_total_ram_mb() -> int:
    try:
        return int(psutil.virtual_memory().total // (1024 * 1024))
    except Exception:
        return 0


def calculate_igm_limits(limit_type: str) -> dict[str, str]:
    allowed = {"base", "min", "low", "mid", "max"}
    if limit_type not in allowed:
        raise ValueError("Invalid limit_type")

    cpu_cores = os.cpu_count() or 1
    total_ram_mb = _read_total_ram_mb()
    if total_ram_mb <= 0:
        raise RuntimeError("Unable to determine total system RAM")

    default_cpu_limit = 2
    min_cpu_limit = 0.5
    alt_min_cpu_limit = 0.8
    max_cpu_limit = max(1, cpu_cores // 2)

    default_ram_limit_mb = max(256, total_ram_mb // 4)
    bare_min_ram_limit_mb = max(256, total_ram_mb // 8)

    if limit_type == "base":
        cpu_limit_str = "0.2"
        ram_limit_mb = 350
        alt_min_cpu_limit_str = str(alt_min_cpu_limit)
    elif limit_type == "min":
        cpu_limit_str = str(min_cpu_limit)
        ram_limit_mb = bare_min_ram_limit_mb
        alt_min_cpu_limit_str = str(alt_min_cpu_limit)
    elif limit_type == "low":
        cpu_limit_str = f"{max(1, default_cpu_limit - 1)}.0"
        ram_limit_mb = bare_min_ram_limit_mb + (default_ram_limit_mb - bare_min_ram_limit_mb) // 2
        alt_min_cpu_limit_str = cpu_limit_str
    elif limit_type == "mid":
        cpu_limit_str = f"{default_cpu_limit}.0"
        ram_limit_mb = default_ram_limit_mb
        alt_min_cpu_limit_str = cpu_limit_str
    else:
        cpu_limit_str = f"{max_cpu_limit + 1}.0"
        ram_limit_mb = bare_min_ram_limit_mb + (default_ram_limit_mb + bare_min_ram_limit_mb) // 2
        alt_min_cpu_limit_str = cpu_limit_str

    ram_reserve_mb = max(128, ram_limit_mb // 2)
    return {
        "RESOURCE_LIMIT": limit_type,
        "CPU_LIMIT": cpu_limit_str,
        "RAM_LIMIT": f"{ram_limit_mb}m",
        "RAM_RESERVE": f"{ram_reserve_mb}m",
        "ALT_MIN_CPU_LIMIT": alt_min_cpu_limit_str,
    }


def build_igm_env(config: dict[str, str]) -> dict[str, str]:
    device = config.get("DEVICE_NAME", "").strip() or (platform.node() or "Server")

    grass_email = config.get("GRASS_EMAIL", "").strip()
    if not grass_email:
        grass_email = config.get("GRASS_USER", "").strip()
    grass_password = config.get("GRASS_PASSWORD", "").strip()
    if not grass_password:
        grass_password = config.get("GRASS_PASS", "").strip()

    repocket_platform = config.get("REPOCKET_PLATFORM", "").strip() or config.get("TARGET_PLATFORM", "").strip()
    packetstream_platform = config.get("PACKETSTREAM_PLATFORM", "").strip() or config.get("TARGET_PLATFORM", "").strip()

    limit_type = os.environ.get("MONEYTREE_IGM_LIMIT", "").strip().lower() or "low"
    limits = calculate_igm_limits(limit_type)

    env: dict[str, str] = {
        "DEVICE_ID": device,
        "HONEYGAIN_EMAIL": config.get("HONEYGAIN_EMAIL", "").strip(),
        "HONEYGAIN_PASSWORD": config.get("HONEYGAIN_PASSWORD", "").strip(),
        "TRAFFMONETIZER_TOKEN": config.get("TRAFFMONETIZER_TOKEN", "").strip(),
        "PACKETSTREAM_CID": config.get("PACKETSTREAM_CID", "").strip(),
        "PACKETSTREAM_PLATFORM": packetstream_platform,
        "PACKETSHARE_EMAIL": config.get("PACKETSHARE_EMAIL", "").strip(),
        "PACKETSHARE_PASSWORD": config.get("PACKETSHARE_PASSWORD", "").strip(),
        "REPOCKET_EMAIL": config.get("REPOCKET_EMAIL", "").strip(),
        "REPOCKET_API_KEY": config.get("REPOCKET_API_KEY", "").strip(),
        "REPOCKET_PLATFORM": repocket_platform,
        "EARNFM_TOKEN": config.get("EARNFM_TOKEN", "").strip(),
        "GRASS_EMAIL": grass_email,
        "GRASS_PASSWORD": grass_password,
        "PAWNS_EMAIL": config.get("PAWNS_EMAIL", "").strip(),
        "PAWNS_PASSWORD": config.get("PAWNS_PASSWORD", "").strip(),
        "PROXYRACK_UUID": config.get("PROXYRACK_UUID", "").strip(),
        "PROXYRACK_API_KEY": config.get("PROXYRACK_API_KEY", "").strip(),
        "BITPING_EMAIL": config.get("BITPING_EMAIL", "").strip(),
        "BITPING_PASSWORD": config.get("BITPING_PASSWORD", "").strip(),
        "BITPING_MFA": config.get("BITPING_MFA", "").strip(),
        "WIPTER_EMAIL": config.get("WIPTER_EMAIL", "").strip(),
        "WIPTER_PASSWORD": config.get("WIPTER_PASSWORD", "").strip(),
        "VNC_PASS": config.get("VNC_PASS", "").strip(),
        "WIZARDGAIN_EMAIL": config.get("WIZARDGAIN_EMAIL", "").strip(),
        "P2PROFIT_EMAIL": config.get("PEER2PROFIT_EMAIL", "").strip(),
    }

    for k, spec in IGM_SERVICES.items():
        enabled = config.get(spec.enable_key, "false").lower() == "true"
        env[spec.profile_var] = "ENABLED" if enabled else "DISABLED"

    env.update(limits)
    return env


def write_igm_temp_env_file(env: dict[str, str]) -> str:
    lines = [f"{k}={_dotenv_escape(v)}" for k, v in sorted(env.items(), key=lambda kv: kv[0])]
    env_text = "\n".join(lines) + "\n"
    fd, path = tempfile.mkstemp(prefix="moneytree.igm.", suffix=".env", dir=config_root())
    try:
        os.write(fd, env_text.encode("utf-8"))
    finally:
        os.close(fd)
    if os.name == "posix":
        os.chmod(path, 0o600)
    return path


def create_igm_temp_env_file(config: dict[str, str]) -> str:
    return write_igm_temp_env_file(build_igm_env(config))
