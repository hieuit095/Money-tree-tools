from fabric import Connection, Config

conn = Connection(
    '192.168.1.18', 
    user='orangepi', 
    connect_kwargs={'password': 'orangepi'}, 
    config=Config(overrides={'sudo': {'password': 'orangepi'}})
)

print("Checking requirements.txt on remote...")
conn.run("cat /opt/moneytree/requirements.txt")

print("\nInstalling requirements...")
conn.sudo("bash -c '/opt/moneytree/venv/bin/pip install -r /opt/moneytree/requirements.txt'", pty=True)

print("\nRestarting service...")
conn.sudo("systemctl restart income-manager.service")

print("\nChecking status...")
result = conn.run("systemctl is-active income-manager.service", hide=True)
print(f"Status: {result.stdout.strip()}")

conn.close()
