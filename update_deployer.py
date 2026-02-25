import os
import sys
import io
import yaml
import time
from fabric import Connection

# Force UTF-8 encoding for stdout/stderr
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
        from fabric import Config
        config = Config(overrides={'sudo': {'password': password}})
        conn = Connection(host=ip, user=user, connect_kwargs={"password": password}, config=config)
        
        # 1. Check Disk Space (Optional for update, but good safety)
        # Skipped for speed in update
        
        # 2. Hostname & Avahi (Skipped, assume already set)
        
        # 3. System Optimization (Skipped, assume already set)

        # 4. Deploy Source Code (Update Only)
        print(f"[{box_id}] Updating Codebase...", flush=True)
        remote_dir = "/opt/moneytree"
        
        # Ensure directory exists (just in case)
        conn.sudo(f"mkdir -p {remote_dir}")
        conn.sudo(f"chown -R {user}:{user} {remote_dir}")
        
        if os.path.exists("deploy_package.tar.gz"):
             conn.put("deploy_package.tar.gz", remote_dir)
             # Extract (Overwrites code files, leaves others like .env.enc alone)
             conn.run(f"tar -xzf {remote_dir}/deploy_package.tar.gz -C {remote_dir}")
             # Cleanup remote
             conn.run(f"rm {remote_dir}/deploy_package.tar.gz")
        else:
             print(f"[{box_id}] Warning: deploy_package.tar.gz not found!")
             return {"box_id": box_id, "ip": ip, "status": "Failed", "msg": "Package not found"}

        # SKIP config generation to preserve existing encrypted config
        print(f"[{box_id}] Preserving existing configuration (.env.enc)...", flush=True)

        # 5. Activation
        print(f"[{box_id}] Updating Dependencies & Restarting Services...", flush=True)
        conn.run(f"chmod +x {remote_dir}/setup.sh")
        
        # Execute setup.sh separately (Updates venv)
        setup_cmd = f"cd {remote_dir} && ./setup.sh"
        print(f"[{box_id}] Running setup script...", flush=True)
        conn.sudo(f"bash -c '{setup_cmd}'", pty=True)
        
        # Execute docker compose (Recreates containers if changed)
        # Note: We do NOT run 'down' here to avoid downtime if possible, 
        # but 'up -d' will recreate changed containers when definitions/images change.
        compose_cmd = f"cd {remote_dir} && docker compose up -d"
        print(f"[{box_id}] Updating containers...", flush=True)
        conn.sudo(f"bash -c '{compose_cmd}'", pty=True)
        
        # Restart the management service to pick up any python code changes
        print(f"[{box_id}] Restarting income-manager...", flush=True)
        conn.sudo("systemctl restart income-manager")

        return {"box_id": box_id, "ip": ip, "status": "Success", "url": "Updated"}

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
    print("UPDATE REPORT", flush=True)
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
        
    print(tabulate(table_data, headers=["Box ID", "IP", "Status", "Info"], tablefmt="grid"), flush=True)

if __name__ == "__main__":
    main()
