from fabric import Connection, Config
import sys

conn = Connection('192.168.1.18', user='orangepi', connect_kwargs={'password': 'orangepi'}, config=Config(overrides={'sudo': {'password': 'orangepi'}}))

print("Installing venv package...")
conn.sudo("apt-get update --allow-releaseinfo-change", warn=True)
conn.sudo("apt-get install -y python3-venv python3-pip", warn=True)

print("Creating venv...")
conn.sudo("rm -rf /opt/moneytree/venv")
res = conn.sudo("python3 -m venv /opt/moneytree/venv", warn=True)
if res.failed:
    print(f"Venv creation failed: {res.stderr}")
    sys.exit(1)

print("Installing requirements...")
res = conn.sudo("/opt/moneytree/venv/bin/pip install -r /opt/moneytree/requirements.txt", warn=True)
if res.failed:
    print(f"Pip install failed: {res.stderr}")

print("Restarting service...")
conn.sudo("systemctl restart income-manager.service")

print("Done.")
conn.close()
