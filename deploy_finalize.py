import paramiko
import os
import sys
import time

HOST = "192.168.1.15"
USER = "orangepi"
PASS = "orangepi"
REMOTE_DIR = "/home/orangepi/Money-tree-tools"

def deploy_finalize():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...", flush=True)
    try:
        ssh.connect(HOST, username=USER, password=PASS)
    except Exception as e:
        print(f"Connection failed: {e}", flush=True)
        return

    print("Uploading finalize_setup.py...", flush=True)
    sftp = ssh.open_sftp()
    sftp.put("finalize_setup_remote.py", f"{REMOTE_DIR}/finalize_setup.py")
    sftp.close()

    print("Running finalize_setup.py...", flush=True)
    cmd = f"cd {REMOTE_DIR} && echo {PASS} | sudo -S python3 finalize_setup.py"
    
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
        print("\nFinalization successful!", flush=True)
    else:
        print(f"\nFinalization failed with exit code {exit_status}", flush=True)

    ssh.close()

if __name__ == "__main__":
    deploy_finalize()
