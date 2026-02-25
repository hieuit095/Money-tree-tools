from fabric import Connection, Config

conn = Connection('192.168.1.18', user='orangepi', connect_kwargs={'password': 'orangepi'}, config=Config(overrides={'sudo': {'password': 'orangepi'}}))

service_content = """[Unit]
Description=Passive Income Manager Dashboard
After=network.target docker.service
Requires=docker.service
StartLimitIntervalSec=60
StartLimitBurst=10

[Service]
Type=notify
NotifyAccess=main
User=root
WorkingDirectory=/opt/moneytree
ExecStart=/opt/moneytree/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
TimeoutStartSec=120
TimeoutStopSec=30
KillMode=mixed
WatchdogSec=60
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=/opt/moneytree"
Environment="MONEYTREE_IGM_ROOT=/opt/moneytree/third_party/income-generator"

[Install]
WantedBy=multi-user.target
"""

print("Restoring income-manager.service...")
conn.run(f"echo '{service_content}' > /tmp/income-manager.service")
conn.sudo("mv /tmp/income-manager.service /etc/systemd/system/income-manager.service")
conn.sudo("systemctl daemon-reload")
conn.sudo("systemctl enable income-manager.service")
conn.sudo("systemctl restart income-manager.service")

print("Checking status...")
print(conn.run("systemctl is-active income-manager.service", hide=True).stdout)
conn.close()
