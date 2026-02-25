from fabric import Connection, Config

conn = Connection('192.168.1.18', user='orangepi', connect_kwargs={'password': 'orangepi'}, config=Config(overrides={'sudo': {'password': 'orangepi'}}))

cmds = [
    "curl -L -o /opt/moneytree/PINGPONG https://pingpong-build.s3.ap-southeast-1.amazonaws.com/linux/latest/PINGPONG",
    "chmod +x /opt/moneytree/PINGPONG",
]

print("Downloading binary...")
for cmd in cmds:
    print(f"Executing: {cmd}")
    res = conn.sudo(cmd, warn=True)
    if res.failed:
        print(f"Failed: {res.stderr}")

service_content = """[Unit]
Description=Pingpong Multi-Mining Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/moneytree
ExecStart=/opt/moneytree/venv/bin/python3 -m app.pingpong_wrapper
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=/opt/moneytree"

[Install]
WantedBy=multi-user.target
"""

print("Creating service file...")
conn.run(f"echo '{service_content}' > /tmp/pingpong.service")
conn.sudo("mv /tmp/pingpong.service /etc/systemd/system/pingpong.service")
conn.sudo("systemctl daemon-reload")

print("Restarting manager...")
conn.sudo("systemctl restart income-manager.service")

print("Done.")
conn.close()
