from fabric import Connection, Config
import os

ip = "192.168.1.18"
user = "orangepi"
password = "orangepi"

config = Config(overrides={'sudo': {'password': password}})
conn = Connection(
    host=ip,
    user=user,
    connect_kwargs={"password": password},
    config=config
)

files_to_sync = [
    "app/config_manager.py",
    "app/pingpong_configurator.py",
    "app/pingpong_wrapper.py",
    "app/native_manager.py",
    "app/runtime_state.py",
    "setup.sh"
]

print("Uploading files...")
for f in files_to_sync:
    filename = os.path.basename(f)
    tmp_path = f"/tmp/{filename}"
    remote_path = f"/opt/moneytree/{f}"
    print(f"  {f} -> {tmp_path} -> {remote_path}")
    conn.put(f, tmp_path)
    conn.sudo(f"mv {tmp_path} {remote_path}")
    conn.sudo(f"chown root:root {remote_path}")

print("Restarting income-manager service to apply code changes...")
conn.sudo("systemctl daemon-reload", warn=True)
conn.sudo("systemctl restart income-manager.service")

print("Done.")
conn.close()
