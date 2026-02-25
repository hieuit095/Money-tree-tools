import paramiko
import sys

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"

def diagnose():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    print("\n--- Service Status ---", flush=True)
    stdin, stdout, stderr = ssh.exec_command("systemctl status income-manager.service")
    print(stdout.read().decode())
    
    print("\n--- Recent Logs ---", flush=True)
    stdin, stdout, stderr = ssh.exec_command("journalctl -u income-manager.service -n 50 --no-pager")
    print(stdout.read().decode())

    print("\n--- Manual Start Attempt ---", flush=True)
    # Try running the command manually to see if it throws python errors
    stdin, stdout, stderr = ssh.exec_command("cd /home/orangepi/Money-tree-tools && ./venv/bin/python3 -m app.main")
    
    # Read stdout/stderr for a bit
    import time
    time.sleep(2) 
    if stdout.channel.recv_ready():
        print("STDOUT:", stdout.channel.recv(4096).decode())
    if stderr.channel.recv_ready():
        print("STDERR:", stderr.channel.recv(4096).decode())

    ssh.close()

if __name__ == "__main__":
    diagnose()
