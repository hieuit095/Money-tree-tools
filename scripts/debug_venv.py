from fabric import Connection, Config
import sys

conn = Connection('192.168.1.18', user='orangepi', connect_kwargs={'password': 'orangepi'}, config=Config(overrides={'sudo': {'password': 'orangepi'}}))

print("Creating venv manually...")
result = conn.sudo("bash -c 'cd /opt/moneytree && python3 -m venv venv'", warn=True)
if result.failed:
    print(f"Failed to create venv: {result.stderr}")
else:
    print("Venv created.")
    conn.sudo("bash -c 'cd /opt/moneytree && ./venv/bin/pip install -r requirements.txt'")

conn.close()
