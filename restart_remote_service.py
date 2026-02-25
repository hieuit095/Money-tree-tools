import paramiko
import time
import sys

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"

def restart_service():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    print("Starting service...", flush=True)
    stdin, stdout, stderr = ssh.exec_command(f"echo {PASS} | sudo -S systemctl start income-manager.service")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status != 0:
        print(f"Failed to start service. Exit code: {exit_status}", flush=True)
        print(stderr.read().decode())
    else:
        print("Service start command issued.", flush=True)

    print("Waiting 5 seconds...", flush=True)
    time.sleep(5)

    print("Checking status...", flush=True)
    stdin, stdout, stderr = ssh.exec_command("systemctl status income-manager.service")
    status_output = stdout.read().decode()
    print(status_output)

    if "Active: active (running)" in status_output:
        print("\nSUCCESS: Service is running.", flush=True)
    else:
        print("\nFAILURE: Service is not running. Checking logs...", flush=True)
        stdin, stdout, stderr = ssh.exec_command("journalctl -u income-manager.service -n 20 --no-pager")
        print(stdout.read().decode())

    ssh.close()

if __name__ == "__main__":
    restart_service()
