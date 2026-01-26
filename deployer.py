import os
import sys
import io
import yaml
import time
from fabric import Connection

# Force UTF-8 encoding for stdout/stderr to prevent UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from concurrent.futures import ThreadPoolExecutor
from tabulate import tabulate

import tarfile

# Load Inventory
def load_inventory(file_path="inventory.yaml"):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def create_deploy_package(output_filename="deploy_package.tar.gz"):
    local_files = ["app", "scripts", "docker-compose.yml", "requirements.txt", "setup.sh", "income-manager.service"]
    with tarfile.open(output_filename, "w:gz") as tar:
        for item in local_files:
            if os.path.exists(item):
                tar.add(item, arcname=item)
    return output_filename

# Deployment Task for a Single Device
def deploy_device(device):
    ip = device['ip']
    user = device['user']
    password = device['pass']
    box_id = device['box_id']
    
    print(f"[{box_id}] Connecting to {ip}...", flush=True)
    
    try:
        # Create Connection
        # Explicitly set sudo password in config to ensure escalation works
        from fabric import Config
        config = Config(overrides={'sudo': {'password': password}})
        conn = Connection(host=ip, user=user, connect_kwargs={"password": password}, config=config)
        
        # 1. Check Disk Space (Require > 1GB)
        print(f"[{box_id}] Checking disk space...", flush=True)
        # Ensure we can run commands. Using sudo to check root partition if needed, though df usually works as user.
        # Note: df -h / works for user.
        result = conn.run("df -h / | tail -1 | awk '{print $4}'", hide=True)
        free_space = result.stdout.strip()
        # Basic check: if 'G' in string, usually > 1GB. If 'M', check amount.
        if 'M' in free_space or ('G' in free_space and float(free_space.replace('G', '')) < 1.0):
             res_bytes = conn.run("df / | tail -1 | awk '{print $4}'", hide=True)
             free_kb = int(res_bytes.stdout.strip())
             if free_kb < 1000000: # Less than 1GB (approx)
                 return {"box_id": box_id, "ip": ip, "status": "Failed", "msg": "Insufficient Disk Space (<1GB)"}

        # 2. Hostname & Avahi
        print(f"[{box_id}] Configuring Hostname & Avahi...", flush=True)
        # Set hostname to box_id.moneytree to attempt box_id.moneytree.local resolution via mDNS
        # Standard Avahi uses hostname.local. If hostname has dots, behavior varies. 
        # But user requested [box_id].moneytree.local
        hostname = f"{box_id}.moneytree"
        conn.sudo(f"hostnamectl set-hostname {hostname}")
        
        # Update hosts file to prevent sudo warnings
        # Using separate command for sed with sudo explicitly on the sed command if the complex chain fails
        # The issue "sed: couldn't open temporary file /etc/sedehpQkz: Permission denied" means sed itself wasn't running as root effectively in the pipe/chain or context.
        # But we used conn.sudo(...) which wraps the whole string.
        # "grep || sed" -> sudo (grep || sed). 
        # If grep fails (returns 1), sed runs.
        # The error suggests sed didn't have write perm to /etc. 
        # Sometimes || operators in sudo strings are tricky with shell parsing.
        # Let's break it down.
        try:
             conn.sudo(f"grep -q '127.0.1.1 {hostname}' /etc/hosts")
        except Exception:
             # If grep failed (not found), then run sed
             conn.sudo(f"sed -i '1i 127.0.1.1 {hostname}' /etc/hosts")

        conn.sudo("DEBIAN_FRONTEND=noninteractive apt-get update -qq")
        conn.sudo("DEBIAN_FRONTEND=noninteractive apt-get install -y avahi-daemon -qq")
        
        # Create custom avahi service
        avahi_service = f"""
<?xml version="1.0" standalone='no'?><!--*-nxml-*-->
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h</name>
  <service>
    <type>_http._tcp</type>
    <port>5000</port>
  </service>
</service-group>
"""
        conn.run(f"echo '{avahi_service}' > /tmp/moneytree.service")
        conn.sudo("mv /tmp/moneytree.service /etc/avahi/services/moneytree.service")
        conn.sudo("systemctl restart avahi-daemon")

        # 3. System Optimization
        print(f"[{box_id}] Optimizing System (Swap/ZRAM)...", flush=True)
        # Check swap
        swap_check = conn.run("swapon --show", hide=True)
        if "/swapfile" not in swap_check.stdout:
            conn.sudo("fallocate -l 1G /swapfile")
            conn.sudo("chmod 600 /swapfile")
            conn.sudo("mkswap /swapfile")
            conn.sudo("swapon /swapfile")
            try:
                conn.sudo("grep -q '/swapfile' /etc/fstab")
            except:
                conn.sudo("bash -c \"echo '/swapfile none swap sw 0 0' >> /etc/fstab\"")
        
        # ZRAM (simple method)
        conn.sudo("DEBIAN_FRONTEND=noninteractive apt-get install -y zram-config -qq || true")
        
        # Swappiness
        conn.sudo("sysctl vm.swappiness=10")
        try:
            conn.sudo("grep -q 'vm.swappiness=10' /etc/sysctl.conf")
        except:
            conn.sudo("bash -c \"echo 'vm.swappiness=10' >> /etc/sysctl.conf\"")
        
        # Docker Log Limit (Global Daemon Config)
        daemon_json = """
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "5m",
    "max-file": "1"
  }
}
"""
        conn.run(f"echo '{daemon_json}' > /tmp/daemon.json")
        conn.sudo("mkdir -p /etc/docker")
        conn.sudo("mv /tmp/daemon.json /etc/docker/daemon.json")
        # Restart docker to apply logging config (if installed, else next step installs it)
        conn.sudo("systemctl restart docker || true")

        # 4. Deploy Source Code
        print(f"[{box_id}] Deploying Codebase...", flush=True)
        remote_dir = "/opt/moneytree"
        conn.sudo(f"mkdir -p {remote_dir}")
        conn.sudo(f"chown -R {user}:{user} {remote_dir}")
        
        if os.path.exists("deploy_package.tar.gz"):
             conn.put("deploy_package.tar.gz", remote_dir)
             # Extract
             conn.run(f"tar -xzf {remote_dir}/deploy_package.tar.gz -C {remote_dir}")
             # Cleanup remote
             conn.run(f"rm {remote_dir}/deploy_package.tar.gz")
        else:
             print(f"[{box_id}] Warning: deploy_package.tar.gz not found!")

        # Create .env file only if it doesn't exist to preserve configuration
        print(f"[{box_id}] Configuring environment...", flush=True)
        try:
            conn.run(f"test -f {remote_dir}/.env")
            print(f"[{box_id}] Existing .env found, preserving configuration.", flush=True)
        except:
            print(f"[{box_id}] No .env found, creating with defaults.", flush=True)
            env_content = f"DEVICE_NAME={box_id}\nWEB_USERNAME=admin\nWEB_PASSWORD=admin\n"
            conn.run(f"echo '{env_content}' > {remote_dir}/.env")

        # 5. Activation
        print(f"[{box_id}] Installing Dependencies & Starting...", flush=True)
        conn.run(f"chmod +x {remote_dir}/setup.sh")
        
        # Correctly change directory then run as sudo
        # Using bash -c to handle cd and execution in one go under sudo
        # conn.sudo("cd ...") fails because cd is a shell builtin.
        # Fabric's context manager `with conn.cd(...)` works for `run` but `sudo` might reset environment depending on config.
        # Safest way: sudo bash -c "cd /path && ./script"
        
        start_cmd = f"cd {remote_dir} && ./setup.sh && docker compose up -d"
        conn.sudo(f"bash -c '{start_cmd}'", pty=True)

        return {"box_id": box_id, "ip": ip, "status": "Success", "url": f"http://{hostname}.local:5000"}

    except Exception as e:
        return {"box_id": box_id, "ip": ip, "status": "Failed", "msg": str(e)}

# Main Execution
def main():
    print("Loading inventory...")
    data = load_inventory()
    devices = data.get('devices', [])
    
    if not devices:
        print("No devices found in inventory.yaml")
        return

    # Create package once
    print("Creating deployment package...")
    pkg_path = create_deploy_package()
    print(f"Package created: {pkg_path}")

    results = []
    
    # Parallel Deployment
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(deploy_device, dev): dev for dev in devices}
        
        for future in futures:
            results.append(future.result())

    # Print Report
    print("\n" + "="*60, flush=True)
    print("DEPLOYMENT REPORT", flush=True)
    print("="*60, flush=True)
    
    # Clean up local package
    if os.path.exists("deploy_package.tar.gz"):
        os.remove("deploy_package.tar.gz")
    
    table_data = []
    for r in results:
        status_color = r['status']
        if r['status'] == 'Success':
            info = r['url']
        else:
            info = r.get('msg', 'Unknown Error')
        
        table_data.append([r['box_id'], r['ip'], r['status'], info])
        
    print(tabulate(table_data, headers=["Box ID", "IP", "Status", "URL/Error"], tablefmt="grid"), flush=True)

if __name__ == "__main__":
    main()
