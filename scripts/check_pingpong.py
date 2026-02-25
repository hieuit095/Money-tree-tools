import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.18", username="orangepi", password="orangepi", timeout=10)
    stdin, stdout, stderr = ssh.exec_command(
        "bash -lc 'cd /opt/moneytree && PYTHONPATH=/opt/moneytree python3 -c \"from app.config_manager import get_config_sections; s=[x for x in get_config_sections() if x.get(\\\"id\\\")==\\\"pingpong\\\"][0]; print(len(s.get(\\\"fields\\\") or []))\"'"
    )
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()
except Exception as e:
    print(e)
