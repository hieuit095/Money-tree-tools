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
from cryptography.fernet import Fernet
from typing import Any, Dict, Iterable, Tuple

# Load Inventory
def load_inventory(file_path="inventory.yaml"):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def create_deploy_package(output_filename="deploy_package.tar.gz"):
    local_files = [
        "app",
        "scripts",
        "third_party/income-generator",
        "docker-compose.yml",
        "requirements.txt",
        "setup.sh",
        "income-manager.service",
    ]
    with tarfile.open(output_filename, "w:gz") as tar:
        for item in local_files:
            if os.path.exists(item):
                tar.add(item, arcname=item)
    return output_filename

def _to_env_var_name(key: str) -> str:
    key = key.strip()
    if not key:
        return key
    if all(c.isupper() or c.isdigit() or c == "_" for c in key) and "_" in key:
        return key
    return key.upper().replace("-", "_").replace(" ", "_")


def _iter_env_items(source: Dict[str, Any]) -> Iterable[Tuple[str, Any]]:
    for k, v in source.items():
        if v is None:
            continue
        yield _to_env_var_name(str(k)), v


def _resolve_profile(inventory: Dict[str, Any], device: Dict[str, Any]) -> Dict[str, Any]:
    profile = device.get("profile")
    if isinstance(profile, dict):
        return profile
    if isinstance(profile, str) and profile:
        profiles = inventory.get("profiles", {})
        if isinstance(profiles, dict):
            resolved = profiles.get(profile, {})
            if isinstance(resolved, dict):
                return resolved
    return {}

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
        conn = Connection(
            host=ip,
            user=user,
            connect_kwargs={
                "password": password,
                "banner_timeout": 60,
                "auth_timeout": 60,
                "timeout": 60,
            },
            config=config
        )
        
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

        # 3. System Optimization (Docker logging)
        print(f"[{box_id}] Configuring Docker logging limits...", flush=True)
        
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
        # conn.sudo("systemctl restart docker || true")
        print(f"[{box_id}] Docker config updated.", flush=True)

        # 4. Deploy Source Code
        print(f"[{box_id}] Deploying Codebase...", flush=True)
        remote_dir = "/opt/moneytree"
        
        # Clean Install: Stop containers and remove directory
        print(f"[{box_id}] Cleaning up old installation...", flush=True)
        conn.sudo("bash -c 'systemctl stop income-manager.service moneytree-zram.service docker-binfmt.service 2>/dev/null || true'", warn=True)
        conn.sudo("bash -c 'systemctl disable income-manager.service moneytree-zram.service docker-binfmt.service 2>/dev/null || true'", warn=True)
        conn.sudo("bash -c 'rm -f /etc/systemd/system/income-manager.service /etc/systemd/system/moneytree-zram.service /etc/systemd/system/docker-binfmt.service 2>/dev/null || true'", warn=True)
        conn.sudo("bash -c 'rm -rf /etc/moneytree 2>/dev/null || true'", warn=True)
        conn.sudo("bash -c 'systemctl daemon-reload 2>/dev/null || true'", warn=True)

        legacy_dirs = [
            remote_dir,
            f"/home/{user}/Money-tree-tools",
            f"/home/{user}/money-tree-tools",
            f"/home/{user}/moneytree-tools",
        ]
        for d in legacy_dirs:
            conn.sudo(f"bash -c 'if [ -d \"{d}\" ]; then cd \"{d}\" && docker compose down || true; fi'", warn=True)
            conn.sudo(f"rm -rf \"{d}\"", warn=True)
        
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

        # Configure environment (Always overwrite for clean install)
        print(f"[{box_id}] Configuring environment...", flush=True)
        
        # Base config
        env_content = f"DEVICE_NAME={box_id}\nWEB_USERNAME={user}\nWEB_PASSWORD={password}\n"
        
        inventory = load_inventory()

        exclude_keys = {"ip", "user", "pass", "box_id", "profile", "env"}
        resolved_profile = _resolve_profile(inventory, device)

        env_items: Dict[str, Any] = {}
        for k, v in _iter_env_items(resolved_profile):
            env_items[k] = v
        for item_key, value in device.items():
            if item_key not in exclude_keys:
                k = _to_env_var_name(str(item_key))
                env_items[k] = value
        explicit_env = device.get("env", {})
        if isinstance(explicit_env, dict):
            for k, v in _iter_env_items(explicit_env):
                env_items[k] = v

        for env_var, value in sorted(env_items.items()):
            env_content += f"{env_var}={value}\n"
        
        master_key = Fernet.generate_key()
        token = Fernet(master_key).encrypt(env_content.encode("utf-8")).decode("utf-8")
        master_key_str = master_key.decode("utf-8")

        conn.sudo("mkdir -p /etc/moneytree")
        conn.sudo("chmod 700 /etc/moneytree")
        conn.sudo(f"bash -c 'umask 077; printf %s\\\\n \"{master_key_str}\" > /etc/moneytree/master.key'")
        conn.run(f"bash -c 'umask 077; printf %s\\\\n \"{token}\" > {remote_dir}/.env.enc'")

        # 5. Activation
        print(f"[{box_id}] Installing Dependencies & Starting...", flush=True)
        conn.run(f"chmod +x {remote_dir}/setup.sh")
        
        # Execute setup.sh separately
        setup_cmd = f"cd {remote_dir} && ./setup.sh"
        print(f"[{box_id}] Running setup script...", flush=True)
        conn.sudo(f"bash -c '{setup_cmd}'", pty=True)
        
        # Execute docker compose separately
        compose_cmd = f"cd {remote_dir} && docker compose up -d"
        print(f"[{box_id}] Starting containers...", flush=True)
        conn.sudo(f"bash -c '{compose_cmd}'", pty=True)

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
    
    # Sequential Deployment for Debugging
    # for dev in devices:
    #     print(f"Deploying to {dev['box_id']}...", flush=True)
    #     try:
    #         res = deploy_device(dev)
    #         results.append(res)
    #     except Exception as e:
    #         import traceback
    #         traceback.print_exc()
    #         results.append({"box_id": dev['box_id'], "ip": dev['ip'], "status": "Failed", "msg": str(e)})

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
