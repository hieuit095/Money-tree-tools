#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[94m",
        "OK": "\033[92m",
        "WARN": "\033[93m",
        "FAIL": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}[{status}] {message}{colors['RESET']}")

def check_tun_module():
    """Check if the TUN module is available for Mysterium."""
    if os.path.exists("/dev/net/tun"):
        print_status("TUN device found.", "OK")
        return True
    
    # Try to load it
    try:
        subprocess.run(["modprobe", "tun"], check=True, stderr=subprocess.DEVNULL)
        if os.path.exists("/dev/net/tun"):
            print_status("TUN module loaded successfully.", "OK")
            return True
    except subprocess.CalledProcessError:
        pass
        
    print_status("TUN module missing! Mysterium will not work.", "FAIL")
    print_status("  Try: sudo modprobe tun", "INFO")
    return False

def check_cpufreq_governor():
    """Check CPU governor settings."""
    try:
        # Check cpu0 governor
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "r") as f:
            gov = f.read().strip()
            
        if gov == "performance":
            print_status(f"CPU governor is '{gov}'. Watch out for overheating on passive Amlogic boxes!", "WARN")
            print_status("  Consider using 'schedutil' or 'ondemand' via 'cpufreq-set'.", "INFO")
        elif gov in ["schedutil", "ondemand", "conservative"]:
            print_status(f"CPU governor is '{gov}'. Good for passive cooling.", "OK")
        else:
            print_status(f"CPU governor is '{gov}'.", "INFO")
            
    except FileNotFoundError:
        print_status("CPU frequency scaling not available or accessible.", "INFO")

def check_zram_status():
    """Check if ZRAM is active and swappiness is optimized."""
    # Check swappiness
    try:
        with open("/proc/sys/vm/swappiness", "r") as f:
            swappiness = int(f.read().strip())
        
        if swappiness < 60:
            print_status(f"vm.swappiness is {swappiness}. For ZRAM, 60-100 is recommended.", "WARN")
        else:
            print_status(f"vm.swappiness is {swappiness}. Good.", "OK")
    except:
        pass

    # Check ZRAM device
    zram_active = False
    with open("/proc/swaps", "r") as f:
        for line in f:
            if "zram" in line:
                zram_active = True
                print_status(f"ZRAM swap detected: {line.split()[0]}", "OK")
                
                # Check compression algo if possible
                try:
                    with open("/sys/block/zram0/comp_algorithm", "r") as alg:
                        content = alg.read().strip()
                        # content usually like: [lz4] lzo zstd
                        selected = [x for x in content.split() if x.startswith("[")][0].strip("[]")
                        print_status(f"ZRAM compression: {selected}", "INFO")
                        if selected == "lz4" and "zstd" in content:
                            print_status("  'zstd' is available but not used. It saves more RAM.", "WARN")
                except:
                    pass
                break
    
    if not zram_active:
        print_status("No ZRAM swap detected. Highly recommended for 2GB devices.", "WARN")

def check_docker_memory_limit_support():
    """Check if kernel supports cgroup memory limits."""
    # This is rough; usually if /sys/fs/cgroup/memory exists it's good
    if os.path.exists("/sys/fs/cgroup/memory"):
        print_status("Cgroup memory controller detected.", "OK")
    else:
        # cgroup v2
        if os.path.exists("/sys/fs/cgroup/cgroup.controllers"):
            with open("/sys/fs/cgroup/cgroup.controllers", "r") as f:
                if "memory" in f.read():
                    print_status("Cgroup v2 memory controller detected.", "OK")
                    return
        print_status("Cgroup memory controller NOT detected. Docker RAM limits might not work!", "WARN")
        print_status("  Add 'cgroup_enable=memory cgroup_memory=1' to kernel boot args (e.g., /boot/uEnv.txt or /boot/cmdline.txt)", "INFO")

def main():
    print("=== ARM/Amlogic Optimization Check ===")
    
    if os.geteuid() != 0:
        print_status("Not running as root. Some checks might fail.", "WARN")
    
    check_tun_module()
    check_cpufreq_governor()
    check_zram_status()
    check_docker_memory_limit_support()
    
    print("\nDone. Run 'python3 scripts/optimize.py' to apply ZRAM/Swappiness fixes.")

if __name__ == "__main__":
    main()
