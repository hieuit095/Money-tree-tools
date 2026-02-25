import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting...")
    ssh.connect("192.168.1.18", username="orangepi", password="orangepi", timeout=30)
    print("Connected. Running ls...")
    stdin, stdout, stderr = ssh.exec_command("ls -d /opt/moneytree /etc/moneytree /var/log/moneytree* /home/orangepi/Money-tree-tools 2>&1")
    output = stdout.read().decode()
    if not output.strip():
        print("No output (dirs likely gone).")
    else:
        print(f"Output:\n{output}")
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
