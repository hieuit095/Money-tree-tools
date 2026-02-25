import paramiko
import os
import zipfile
import sys
import time

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"
REMOTE_DIR = "/home/orangepi/Money-tree-tools"
ZIP_NAME = "deploy_package.zip"

def create_zip():
    print(f"Zipping project to {ZIP_NAME}...", flush=True)
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("."):
            # Exclude pattern
            if 'venv' in root or '.git' in root or '__pycache__' in root or 'deploy_remote.py' in root:
                continue
            for file in files:
                if file == ZIP_NAME or file.endswith('.pyc') or file.endswith('.zip'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, ".")
                zipf.write(file_path, arcname)

def deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    # Helper to run sudo command
    def run_sudo(command, desc):
        print(f"{desc}...", flush=True)
        stdin, stdout, stderr = ssh.exec_command(f"echo {PASS} | sudo -S {command}", get_pty=True)
        # Wait for command to finish
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"Error executing {desc}:", flush=True)
            print(stdout.read().decode(), flush=True)
        return exit_status

    # 1. Stop service if exists
    run_sudo("systemctl stop income-manager.service", "Stopping existing service")

    # 2. Clean old directory
    print(f"Cleaning {REMOTE_DIR}...", flush=True)
    ssh.exec_command(f"rm -rf {REMOTE_DIR}")
    ssh.exec_command(f"mkdir -p {REMOTE_DIR}")

    # 3. Upload zip
    print("Uploading zip...", flush=True)
    sftp = ssh.open_sftp()
    sftp.put(ZIP_NAME, f"{REMOTE_DIR}/{ZIP_NAME}")
    sftp.close()

    # 4. Unzip
    print("Unzipping...", flush=True)
    # Ensure unzip is installed
    run_sudo("apt-get update && apt-get install -y unzip", "Installing unzip")
    
    print("Extracting files...", flush=True)
    stdin, stdout, stderr = ssh.exec_command(f"cd {REMOTE_DIR} && unzip -o {ZIP_NAME} && rm {ZIP_NAME}")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        print(f"Unzip failed: {stderr.read().decode()}", flush=True)
        return

    # 5. Run setup
    print("Running setup.sh (this may take a while)...", flush=True)
    cmd = f"cd {REMOTE_DIR} && chmod +x setup.sh && echo {PASS} | sudo -S ./setup.sh"
    
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    
    # Stream output
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            data = stdout.channel.recv(1024)
            print(data.decode(), end="", flush=True)
        else:
            time.sleep(0.1)
    
    # Print remaining
    if stdout.channel.recv_ready():
        print(stdout.channel.recv(1024).decode(), end="", flush=True)
        
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("\nDeployment successful!", flush=True)
    else:
        print(f"\nDeployment failed with exit code {exit_status}", flush=True)

    ssh.close()

if __name__ == "__main__":
    try:
        create_zip()
        deploy()
    finally:
        if os.path.exists(ZIP_NAME):
            os.remove(ZIP_NAME)
