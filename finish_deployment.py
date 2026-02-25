import paramiko
import sys
import time

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"
REMOTE_DIR = "/home/orangepi/Money-tree-tools"

def finish():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    print("Running setup.sh...", flush=True)
    # Ensure executable
    ssh.exec_command(f"chmod +x {REMOTE_DIR}/setup.sh")
    
    cmd = f"cd {REMOTE_DIR} && echo {PASS} | sudo -S ./setup.sh"
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            print(stdout.channel.recv(1024).decode(), end="", flush=True)
        else:
            time.sleep(0.1)
            
    if stdout.channel.recv_ready():
        print(stdout.channel.recv(1024).decode(), end="", flush=True)

    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("\nSetup successful!", flush=True)
    else:
        print(f"\nSetup failed with exit code {exit_status}", flush=True)

    ssh.close()

if __name__ == "__main__":
    finish()
