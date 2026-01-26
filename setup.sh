#!/bin/bash

# Ensure root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Installing System Dependencies..."
apt-get update
apt-get install -y python3-venv python3-pip docker.io docker-compose-v2

# Setup Python Env
echo "Setting up Python Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Install requirements
./venv/bin/pip install -r requirements.txt

# Run System Optimization
echo "Running System Optimization..."
./venv/bin/python3 scripts/optimize.py

# Setup Systemd Service
echo "Configuring Systemd Service..."
SERVICE_FILE="income-manager.service"
CURRENT_DIR=$(pwd)

# Create service file with correct paths
cat > $SERVICE_FILE <<EOL
[Unit]
Description=Passive Income Manager Dashboard
After=network.target docker.service
Requires=docker.service

[Service]
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
Environment="PYTHONPATH=$CURRENT_DIR"

[Install]
WantedBy=multi-user.target
EOL

# Install service
cp $SERVICE_FILE /etc/systemd/system/
systemctl daemon-reload
systemctl enable income-manager.service
systemctl start income-manager.service

echo "Setup Complete!"
echo "Dashboard available at http://$(hostname -I | cut -d' ' -f1):5000"
