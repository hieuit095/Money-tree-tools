import os
import subprocess
import sys

# Assume we are in /home/orangepi/Money-tree-tools

def run(cmd):
    print(f"Running: {cmd}", flush=True)
    subprocess.check_call(cmd, shell=True)

def main():
    print("Starting fast setup...", flush=True)
    
    # 1. Setup Python Env
    if os.path.exists("venv"):
        print("Removing existing venv...", flush=True)
        run("rm -rf venv")
        
    print("Creating venv...", flush=True)
    try:
        run("python3 -m venv venv")
    except subprocess.CalledProcessError:
        print("Standard venv creation failed. Trying with --without-pip and ensurepip...", flush=True)
        run("python3 -m venv venv --without-pip")
        run("curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py")
        run("./venv/bin/python3 get-pip.py")
    
    # 2. Install requirements
    print("Installing requirements...", flush=True)
    run("./venv/bin/pip install -r requirements.txt")
    
    # 3. Setup Systemd Service
    print("Configuring Systemd Service...", flush=True)
    cwd = os.getcwd()
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
WorkingDirectory={cwd}
ExecStart={cwd}/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
TimeoutStartSec=120
TimeoutStopSec=30
KillMode=mixed
WatchdogSec=60
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH={cwd}"
Environment="MONEYTREE_IGM_ROOT={cwd}/third_party/income-generator"

[Install]
WantedBy=multi-user.target
"""
    with open("income-manager.service", "w") as f:
        f.write(service_content)
        
    run("cp income-manager.service /etc/systemd/system/")
    run("systemctl daemon-reload")
    run("systemctl enable income-manager.service")
    run("systemctl restart income-manager.service")
    
    print("Setup Complete!", flush=True)

if __name__ == "__main__":
    main()
