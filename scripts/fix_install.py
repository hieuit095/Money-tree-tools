from fabric import Connection, Config
import sys

conn = Connection('192.168.1.18', user='orangepi', connect_kwargs={'password': 'orangepi'}, config=Config(overrides={'sudo': {'password': 'orangepi'}}))

print("Running setup.sh...")
# Ensure it is executable
conn.sudo("chmod +x /opt/moneytree/setup.sh")
# Run it
result = conn.sudo("bash -c 'cd /opt/moneytree && ./setup.sh'", pty=True, warn=True)
if result.failed:
    print(f"Setup failed: {result.stdout}")
else:
    print("Setup succeeded.")
conn.close()
