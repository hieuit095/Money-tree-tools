import paramiko
import sys

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"

def check():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    print("Checking service status...", flush=True)
    stdin, stdout, stderr = ssh.exec_command("systemctl status income-manager.service")
    print(stdout.read().decode())
    
    print("Checking directory...", flush=True)
    stdin, stdout, stderr = ssh.exec_command("ls -l /home/orangepi/Money-tree-tools")
    print(stdout.read().decode())

    ssh.close()

if __name__ == "__main__":
    check()
