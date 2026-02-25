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
    print("Running setup.sh manually...")
    # Using pty=True to see interactive output if any
    conn.sudo("bash -c 'cd /opt/moneytree && ./setup.sh'", pty=True)
    print("Setup complete. Starting containers...")
    conn.sudo("bash -c 'cd /opt/moneytree && docker compose up -d'", pty=True)
    print("Deployment complete.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
