import os
import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    os_id: str
    os_like: str
    os_name: str
    os_version: str
    machine: str
    arch: str


def _read_os_release() -> dict[str, str]:
    paths = ["/etc/os-release", "/usr/lib/os-release"]
    data: dict[str, str] = {}
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f.read().splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    data[k.strip()] = v
            if data:
                return data
        except OSError:
            continue
    return data


def normalize_arch(machine: str | None = None) -> str:
    m = (machine or platform.machine() or "").lower()
    if m in {"x86_64", "amd64"}:
        return "amd64"
    if m in {"aarch64", "arm64"}:
        return "arm64"
    if m in {"armv7l", "armv7"}:
        return "armv7"
    if m in {"armv6l", "armv6"}:
        return "armv6"
    return m or "unknown"


def get_platform_info() -> PlatformInfo:
    osr = _read_os_release()
    os_id = (osr.get("ID") or "").lower()
    os_like = (osr.get("ID_LIKE") or "").lower()
    name = osr.get("NAME") or platform.system()
    version = osr.get("VERSION_ID") or platform.release()
    machine = platform.machine() or ""
    arch = normalize_arch(machine)
    return PlatformInfo(
        os_id=os_id,
        os_like=os_like,
        os_name=name,
        os_version=version,
        machine=machine,
        arch=arch,
    )


def is_linux() -> bool:
    return os.name == "posix" and platform.system().lower() == "linux"


def is_armbian(info: PlatformInfo | None = None) -> bool:
    i = info or get_platform_info()
    hay = " ".join([i.os_id, i.os_like, i.os_name]).lower()
    return "armbian" in hay


def is_arm(info: PlatformInfo | None = None) -> bool:
    i = info or get_platform_info()
    return i.arch in {"arm64", "armv7", "armv6"}
