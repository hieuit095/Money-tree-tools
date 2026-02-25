from fabric import Connection, Config
import sys

ip = "192.168.1.18"
user = "orangepi"
password = "orangepi"

config = Config(overrides={'sudo': {'password': password}})
conn = Connection(
    host=ip,
    user=user,
    connect_kwargs={
        "password": password,
        "banner_timeout": 60,
        "auth_timeout": 60,
        "timeout": 60,
    },
    config=config
)

print(f"Connecting to {ip}...")
try:
    # 1. Stop and Clean
    print("Stopping services and cleaning secrets...")
    conn.sudo("bash -c 'systemctl stop income-manager.service moneytree-zram.service wipter.service uprock.service 2>/dev/null || true'")
    conn.sudo("bash -c 'rm -rf /etc/moneytree /opt/moneytree /var/log/moneytree* 2>/dev/null || true'")
    
    # 2. Cleanup Docker
    print("Cleaning up Docker resources...")
    conn.sudo("docker rm -f $(docker ps -aq --filter label=project=standard) 2>/dev/null || true")
    conn.sudo("docker rm -f $(docker ps -aq --filter label=project=proxy) 2>/dev/null || true")
    conn.sudo("docker rm -f $(docker ps -aq --filter label=com.docker.compose.project=moneytree-igm) 2>/dev/null || true")
    
    print("Wipe complete.")
except Exception as e:
    print(f"Error during wipe: {e}")
finally:
    conn.close()
