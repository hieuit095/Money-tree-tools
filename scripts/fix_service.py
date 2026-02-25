from fabric import Connection, Config

conn = Connection(
    '192.168.1.18', 
    user='orangepi', 
    connect_kwargs={'password': 'orangepi'}, 
    config=Config(overrides={'sudo': {'password': 'orangepi'}})
)

remote_dir = "/opt/moneytree"

service_content = f"""[Unit]
Description=Passive Income Manager Dashboard
After=network.target docker.service
Requires=docker.service
StartLimitIntervalSec=60
StartLimitBurst=10

[Service]
Type=notify
NotifyAccess=main
User=root
WorkingDirectory={remote_dir}
ExecStart={remote_dir}/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
TimeoutStartSec=120
TimeoutStopSec=30
KillMode=mixed
WatchdogSec=60
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH={remote_dir}"
Environment="MONEYTREE_IGM_ROOT={remote_dir}/third_party/income-generator"

[Install]
WantedBy=multi-user.target
"""

print("Updating service file on remote...")
conn.run(f"echo '{service_content}' > /tmp/income-manager.service")
conn.sudo(f"mv /tmp/income-manager.service /etc/systemd/system/income-manager.service")
conn.sudo("systemctl daemon-reload")
print("Starting service...")
conn.sudo("systemctl restart income-manager.service")

print("Checking status...")
result = conn.run("systemctl is-active income-manager.service", hide=True)
print(f"Status: {result.stdout.strip()}")

conn.close()
