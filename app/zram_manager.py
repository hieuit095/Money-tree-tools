import os
import sys
import subprocess


ALLOWED_ZRAM_SIZES_MB = [512, 1024, 1536, 2048, 3072, 4096]


def validate_zram_size_mb(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        size_mb = value
    else:
        raw = str(value).strip()
        if raw == "":
            return None
        size_mb = int(raw)
    mem_total_mb = int(_mem_total_bytes() / (1024 * 1024)) if sys.platform == "linux" and _mem_total_bytes() else None
    if size_mb not in allowed_sizes_mb(mem_total_mb):
        raise ValueError("invalid_zram_size_mb")
    return size_mb


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _write_text(path: str, value: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)


def _run(argv: list[str]) -> None:
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _mem_total_bytes() -> int:
    content = _read_text("/proc/meminfo")
    for line in content.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return 0


def _mem_available_bytes() -> int:
    content = _read_text("/proc/meminfo")
    for line in content.splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return 0


def _zram_disksize_bytes() -> int | None:
    raw = _read_text("/sys/block/zram0/disksize").strip()
    if raw.isdigit():
        return int(raw)
    return None


def _zram_reset() -> None:
    reset_path = "/sys/block/zram0/reset"
    if os.path.exists(reset_path):
        _write_text(reset_path, "1")


def _zram_is_swap_active() -> bool:
    swaps = _read_text("/proc/swaps")
    for line in swaps.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0].endswith("/zram0") or os.path.basename(parts[0]) == "zram0":
            return True
    return False


def _zram_swap_used_kib() -> int | None:
    swaps = _read_text("/proc/swaps")
    for line in swaps.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 5:
            continue
        if parts[0].endswith("/zram0") or os.path.basename(parts[0]) == "zram0":
            used = parts[3]
            if used.isdigit():
                return int(used)
            return None
    return 0


def ensure_zram_device() -> None:
    if os.path.exists("/sys/block/zram0"):
        return
    _run(["modprobe", "zram", "num_devices=1"])
    if not os.path.exists("/sys/block/zram0"):
        raise RuntimeError("zram_device_not_available")


def compute_auto_size_bytes() -> int:
    total = _mem_total_bytes()
    size = total // 2 if total else 0
    if size < 256 * 1024 * 1024:
        size = 256 * 1024 * 1024
    return size


def allowed_sizes_mb(mem_total_mb: int | None) -> list[int]:
    if not mem_total_mb:
        return ALLOWED_ZRAM_SIZES_MB
    return [s for s in ALLOWED_ZRAM_SIZES_MB if s <= mem_total_mb]


def get_status() -> dict:
    if sys.platform != "linux":
        return {
            "mem_total_mb": None,
            "zram_size_mb": None,
            "swap_active": False,
            "allowed_sizes_mb": ALLOWED_ZRAM_SIZES_MB,
            "status": "not_supported_on_platform"
        }
    ensure_zram_device()
    size_bytes = _zram_disksize_bytes()
    mem_total_bytes = _mem_total_bytes()
    mem_total_mb = int(mem_total_bytes / (1024 * 1024)) if mem_total_bytes else None
    return {
        "mem_total_mb": mem_total_mb,
        "zram_size_mb": int(size_bytes / (1024 * 1024)) if size_bytes else None,
        "swap_active": _zram_is_swap_active(),
        "allowed_sizes_mb": allowed_sizes_mb(mem_total_mb),
    }


def apply_size_mb(size_mb: int | None) -> dict:
    if sys.platform != "linux":
        return {"status": "error", "message": "not_supported_on_platform"}
    ensure_zram_device()
    desired_bytes = compute_auto_size_bytes() if size_mb is None else int(size_mb) * 1024 * 1024
    current_bytes = _zram_disksize_bytes()
    desired_mb = int(desired_bytes / (1024 * 1024))

    if current_bytes == desired_bytes and _zram_is_swap_active():
        return {"status": "noop", "size_mb": desired_mb}

    if _zram_is_swap_active():
        used_kib = _zram_swap_used_kib()
        available_bytes = _mem_available_bytes()
        should_require_reboot = (
            current_bytes is not None
            and current_bytes != desired_bytes
            and (
                (isinstance(used_kib, int) and used_kib > 0)
                or (available_bytes and available_bytes < 64 * 1024 * 1024)
            )
        )
        if should_require_reboot:
            return {
                "status": "pending_reboot",
                "size_mb": desired_mb,
                "swap_used_mb": int(used_kib / 1024) if isinstance(used_kib, int) else None,
            }
        try:
            _run(["swapoff", "/dev/zram0"])
        except subprocess.CalledProcessError as e:
            if e.returncode in {-9, 137}:
                return {"status": "pending_reboot", "size_mb": desired_mb, "swapoff_killed": True}
            raise RuntimeError(f"swapoff_failed: {e}") from e

    _zram_reset()
    _write_text("/sys/block/zram0/disksize", str(desired_bytes))
    try:
        _run(["mkswap", "/dev/zram0"])
        _run(["swapon", "-p", "100", "/dev/zram0"])
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"zram_apply_failed: {e}") from e

    return {"status": "applied", "size_mb": desired_mb}
