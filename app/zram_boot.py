import os
import sys

from app.config_manager import load_config
from app.zram_manager import apply_size_mb, validate_zram_size_mb


def main() -> int:
    if sys.platform != "linux":
        return 0
    if getattr(os, "geteuid", lambda: 1)() != 0:
        return 0
    config = load_config()
    raw = (config.get("ZRAM_SIZE_MB") or "").strip()
    try:
        validated = validate_zram_size_mb(raw)
    except Exception:
        validated = None
    try:
        apply_size_mb(validated)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
