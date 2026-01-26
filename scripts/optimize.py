import os
import subprocess
import sys

def run_command(command):
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Success: {command}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {command}: {e}")

def setup_swap():
    print("Configuring Swap...")
    if os.path.exists('/swapfile'):
        print("Swap file already exists.")
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

def setup_zram():
    print("Configuring ZRAM...")
    # Check if zram is active
    try:
        # Try to load module if not present
        run_command("modprobe zram num_devices=1")
        
        # Simple manual configuration
        # Note: robust implementation would check if /dev/zram0 is already mounted
        if os.path.exists('/sys/block/zram0'):
            run_command("echo lz4 > /sys/block/zram0/comp_algorithm")
            # Set size to 512M or 1G? User has 2GB RAM. 
            # ZRAM usually takes 50% of RAM. Let's try to set 1G.
            run_command("echo 1G > /sys/block/zram0/disksize")
            run_command("mkswap /dev/zram0")
            run_command("swapon -p 100 /dev/zram0") # Higher priority than disk swap
            print("ZRAM configured on /dev/zram0")
        else:
            print("Could not find /sys/block/zram0")
    except Exception as e:
        print(f"ZRAM setup note: {e}")

def setup_swappiness():
    print("Configuring Swappiness...")
    run_command("sysctl vm.swappiness=10")
    
    # Persist in sysctl.conf
    conf_path = '/etc/sysctl.conf'
    needs_update = True
    if os.path.exists(conf_path):
        try:
            with open(conf_path, 'r') as f:
                content = f.read()
                if 'vm.swappiness=10' in content.replace(' ', ''):
                    needs_update = False
        except Exception:
            pass
    
    if needs_update:
        try:
            with open(conf_path, 'a') as f:
                f.write('\nvm.swappiness=10\n')
            print("Swappiness saved to /etc/sysctl.conf")
        except Exception as e:
            print(f"Failed to write to {conf_path}: {e}")
    else:
        print("Swappiness already configured in /etc/sysctl.conf")

if __name__ == "__main__":
    if os.name != 'posix':
        print("This script is intended for Linux systems.")
    elif os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
    
    setup_swap()
    setup_zram()
    setup_swappiness()
    print("System optimization complete.")
