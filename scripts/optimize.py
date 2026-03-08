import os
import subprocess
import sys

ALLOWED_ZRAM_SIZES_MB = [512, 1024, 1536, 2048, 3072, 4096]

def run_command(command):
    try:
        if isinstance(command, str):
            command = command.split()
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Success: {' '.join(command)}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {' '.join(command)}: {e}")

def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _write_text(path: str, value: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)


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
        run_command(["swapoff", "/swapfile"])
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
        run_command(["fallocate", "-l", "1G", "/swapfile"])
        run_command(["chmod", "600", "/swapfile"])
        run_command(["mkswap", "/swapfile"])
        run_command(["swapon", "/swapfile"])
        
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
        run_command(["modprobe", "zram", "num_devices=1"])
        
        if os.path.exists('/sys/block/zram0'):
            alg_path = "/sys/block/zram0/comp_algorithm"
            if os.path.exists(alg_path):
                available = _read_text(alg_path)
                # Prefer zstd for better compression on low-RAM devices, then lz4
                if "zstd" in available:
                    _write_text(alg_path, "zstd")
                    print("Selected compression: zstd")
                elif "lz4" in available:
                    _write_text(alg_path, "lz4")
                    print("Selected compression: lz4")
            desired = _desired_zram_size_bytes()
            current = _zram_disksize_bytes()
            if _has_swap_device("zram") and current == desired:
                print("ZRAM swap already active at desired size.")
                cleanup_swapfile_if_present()
                return True
            if _has_swap_device("zram"):
                run_command(["swapoff", "/dev/zram0"])
            if os.path.exists("/sys/block/zram0/reset"):
                _write_text("/sys/block/zram0/reset", "1")
            _write_text("/sys/block/zram0/disksize", str(desired))
            run_command(["mkswap", "/dev/zram0"])
            run_command(["swapon", "-p", "100", "/dev/zram0"]) # Higher priority than disk swap
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
    run_command(["sysctl", f"vm.swappiness={target_swappiness}"])
    
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


def setup_armbian_optimizations():
    """Apply tuning specific to Armbian/ARM TV boxes (Amlogic, Rockchip, Allwinner)."""
    print("Checking for ARM/Armbian-specific optimizations...")

    try:
        from app.platform_info import get_platform_info, is_arm, is_armbian
        info = get_platform_info()
    except Exception:
        print("Could not load platform_info; skipping ARM optimizations.")
        return

    if not is_arm(info):
        print(f"Not an ARM platform ({info.arch}); skipping ARM optimizations.")
        return

    print(f"ARM platform detected: {info.machine} ({info.arch})")
    if is_armbian(info):
        print(f"Armbian detected: {info.os_name} {info.os_version}")

    # 1. eMMC/SD-friendly I/O tuning (reduce write amplification on flash storage)
    sysctl_path = "/etc/sysctl.d/99-moneytree.conf"
    sysctl_content = _read_text(sysctl_path)
    arm_tuning = {
        "vm.dirty_ratio": "10",
        "vm.dirty_background_ratio": "5",
        "vm.min_free_kbytes": "8192",
    }
    added = False
    for key, value in arm_tuning.items():
        setting = f"{key}={value}"
        if setting.replace(" ", "") not in sysctl_content.replace(" ", ""):
            try:
                with open(sysctl_path, "a", encoding="utf-8") as f:
                    f.write(f"{setting}\n")
                run_command(["sysctl", setting])
                print(f"Applied: {setting}")
                added = True
            except Exception as e:
                print(f"Failed to apply {setting}: {e}")
    if not added:
        print("ARM sysctl tuning already applied.")

    # 2. I/O scheduler: prefer mq-deadline for flash storage (eMMC/SD)
    for block_dev in ["mmcblk0", "mmcblk1", "mmcblk2"]:
        sched_path = f"/sys/block/{block_dev}/queue/scheduler"
        if os.path.exists(sched_path):
            available = _read_text(sched_path)
            if "mq-deadline" in available and "[mq-deadline]" not in available:
                try:
                    _write_text(sched_path, "mq-deadline")
                    print(f"Set I/O scheduler for {block_dev} to mq-deadline")
                except Exception as e:
                    print(f"Failed to set scheduler for {block_dev}: {e}")
            elif "[mq-deadline]" in available:
                print(f"I/O scheduler for {block_dev} already mq-deadline")

    # 3. CPU frequency governor: prefer schedutil for ARM SoCs
    policy_dir = "/sys/devices/system/cpu/cpufreq"
    if os.path.isdir(policy_dir):
        for entry in os.listdir(policy_dir):
            gov_path = os.path.join(policy_dir, entry, "scaling_governor")
            if os.path.exists(gov_path):
                current = _read_text(gov_path).strip()
                available_path = os.path.join(policy_dir, entry, "scaling_available_governors")
                available = _read_text(available_path)
                preferred = "schedutil" if "schedutil" in available else ("ondemand" if "ondemand" in available else "")
                if preferred and current != preferred:
                    try:
                        _write_text(gov_path, preferred)
                        print(f"Set CPU governor for {entry} to {preferred} (was {current})")
                    except Exception as e:
                        print(f"Failed to set governor for {entry}: {e}")
                elif current == preferred:
                    print(f"CPU governor for {entry} already {preferred}")

    print("ARM/Armbian optimizations complete.")


if __name__ == "__main__":
    if os.name != 'posix':
        print("This script is intended for Linux systems.")
    elif os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
    
    zram_active = setup_zram()
    setup_swap(zram_active)
    setup_swappiness()
    setup_armbian_optimizations()
    print("System optimization complete.")

