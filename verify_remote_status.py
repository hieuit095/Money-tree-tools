import paramiko
import time

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"
REMOTE_DIR = "/home/orangepi/Money-tree-tools"

def verify():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    print("Checking remote files...", flush=True)
    stdin, stdout, stderr = ssh.exec_command(f"ls -F {REMOTE_DIR}/scripts/")
    files = stdout.read().decode().split()
    if "check_arm_requirements.py" in files:
        print("SUCCESS: check_arm_requirements.py found.", flush=True)
    else:
        print("FAILURE: check_arm_requirements.py NOT found.", flush=True)
        print(f"Files found: {files}", flush=True)

    print("Checking optimize.py content...", flush=True)
    stdin, stdout, stderr = ssh.exec_command(f"grep 'swappiness=100' {REMOTE_DIR}/scripts/optimize.py")
    if stdout.channel.recv_exit_status() == 0:
        print("SUCCESS: optimize.py has swappiness=100.", flush=True)
    else:
        print("FAILURE: optimize.py does NOT have swappiness=100.", flush=True)

    print("Checking service status...", flush=True)
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active income-manager.service")
    status = stdout.read().decode().strip()
    print(f"Service status: {status}", flush=True)

    ssh.close()

if __name__ == "__main__":
    verify()
