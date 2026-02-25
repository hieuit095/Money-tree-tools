from fabric import Connection, Config

conn = Connection(
    '192.168.1.18', 
    user='orangepi', 
    connect_kwargs={'password': 'orangepi'}, 
    config=Config(overrides={'sudo': {'password': 'orangepi'}})
)

commands = [
    "cp /opt/moneytree/income-manager.service /etc/systemd/system/",
    "systemctl daemon-reload",
    "systemctl enable income-manager.service",
    "systemctl start income-manager.service"
]

for cmd in commands:
    print(f"Running: {cmd}")
    result = conn.sudo(cmd, warn=True)
    if result.failed:
        print(f"Command failed: {result.stderr}")

print("Checking status...")
print(conn.run("systemctl is-active income-manager.service", hide=True).stdout)
conn.close()
