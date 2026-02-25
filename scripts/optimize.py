import os
import subprocess
import sys

ALLOWED_ZRAM_SIZES_MB = [512, 1024, 1536, 2048, 3072, 4096]

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Success: {command}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {command}: {e}")

def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _has_swap_device(prefix: str) -> bool:
    swaps = _read_text("/proc/swaps")
    for line in swaps.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        if os.path.basename(parts[0]).startswith(prefix):
            return True
    return False


def _has_swap_path(path: str) -> bool:
    swaps = _read_text("/proc/swaps")
    for line in swaps.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == path:
            return True
    return False


def _remove_swapfile_from_fstab() -> None:
    fstab = "/etc/fstab"
    content = _read_text(fstab)
    if not content:
        return
    lines = content.splitlines(True)
    kept: list[str] = []
    changed = False
    for line in lines:
        if "/swapfile" in line and " swap " in f" {line} ":
            changed = True
            continue
        kept.append(line)
    if changed:
        with open(fstab, "w", encoding="utf-8") as f:
            f.write("".join(kept))


def cleanup_swapfile_if_present() -> None:
    if _has_swap_path("/swapfile"):
        run_command("swapoff /swapfile")
    if os.path.exists("/swapfile"):
        try:
            os.remove("/swapfile")
        except OSError:
            pass
    _remove_swapfile_from_fstab()


def _mem_total_bytes() -> int:
    content = _read_text("/proc/meminfo")
    for line in content.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return 0


def _zram_disksize_bytes() -> int | None:
    raw = _read_text("/sys/block/zram0/disksize").strip()
    if raw.isdigit():
        return int(raw)
    return None


def _desired_zram_size_bytes() -> int:
    raw = os.environ.get("ZRAM_SIZE_MB", "").strip()
    if raw.isdigit():
        size_mb = int(raw)
        total_mb = int(_mem_total_bytes() / (1024 * 1024)) if _mem_total_bytes() else None
        if size_mb in ALLOWED_ZRAM_SIZES_MB and (not total_mb or size_mb <= total_mb):
            return size_mb * 1024 * 1024
    total = _mem_total_bytes()
    size = total // 2 if total else 0
    
    if size < 256 * 1024 * 1024:
        size = 256 * 1024 * 1024
    return size


def setup_swap(zram_active: bool):
    print("Configuring Swap...")
    if zram_active or _has_swap_device("zram"):
        print("ZRAM swap detected; skipping swapfile provisioning.")
        cleanup_swapfile_if_present()
        return False
    if os.path.exists('/swapfile'):
        print("Swap file already exists.")
        return True
    else:
        run_command("fallocate -l 1G /swapfile")
        run_command("chmod 600 /swapfile")
        run_command("mkswap /swapfile")
        run_command("swapon /swapfile")
        
        # Add to fstab
        try:
            with open('/etc/fstab', 'a') as f:
                f.write('\n/swapfile none swap sw 0 0\n')
            print("Swap added to /etc/fstab")
        except Exception as e:
            print(f"Failed to write to /etc/fstab: {e}")
    return True

def setup_zram():
    print("Configuring ZRAM...")
    try:
        run_command("modprobe zram num_devices=1")
        
        if os.path.exists('/sys/block/zram0'):
            alg_path = "/sys/block/zram0/comp_algorithm"
            if os.path.exists(alg_path):
                available = _read_text(alg_path)
                # Prefer zstd for better compression on low-RAM devices, then lz4
                if "zstd" in available:
                    run_command("echo zstd > /sys/block/zram0/comp_algorithm")
                    print("Selected compression: zstd")
                elif "lz4" in available:
                    run_command("echo lz4 > /sys/block/zram0/comp_algorithm")
                    print("Selected compression: lz4")
            desired = _desired_zram_size_bytes()
            current = _zram_disksize_bytes()
            if _has_swap_device("zram") and current == desired:
                print("ZRAM swap already active at desired size.")
                cleanup_swapfile_if_present()
                return True
            if _has_swap_device("zram"):
                run_command("swapoff /dev/zram0")
            if os.path.exists("/sys/block/zram0/reset"):
                run_command("echo 1 > /sys/block/zram0/reset")
            run_command(f"echo {desired} > /sys/block/zram0/disksize")
            run_command("mkswap /dev/zram0")
            run_command("swapon -p 100 /dev/zram0") # Higher priority than disk swap
            print(f"ZRAM configured on /dev/zram0 ({int(desired/1024/1024)} MB)")
            cleanup_swapfile_if_present()
            return True
        else:
            print("Could not find /sys/block/zram0")
    except Exception as e:
        print(f"ZRAM setup note: {e}")
    return False

def setup_swappiness():
    print("Configuring Swappiness...")
    # For ZRAM, high swappiness (60-100) is preferred to aggressively use the compressed RAM
    # This frees up actual RAM for application caches and heap
    target_swappiness = 100
    run_command(f"sysctl vm.swappiness={target_swappiness}")
    
    conf_path = "/etc/sysctl.d/99-moneytree.conf"
    content = _read_text(conf_path)
    if f"vm.swappiness={target_swappiness}" in content.replace(" ", ""):
        print("Swappiness already configured.")
        return
    try:
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(f"vm.swappiness={target_swappiness}\n")
            # Also improve cache pressure to prefer keeping directory/inode caches
            f.write("vm.vfs_cache_pressure=50\n")
        print(f"Swappiness saved to {conf_path}")
    except Exception as e:
        print(f"Failed to write to {conf_path}: {e}")

if __name__ == "__main__":
    if os.name != 'posix':
        print("This script is intended for Linux systems.")
    elif os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
    
    zram_active = setup_zram()
    setup_swap(zram_active)
    setup_swappiness()
    print("System optimization complete.")
