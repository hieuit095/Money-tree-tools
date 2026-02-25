#!/bin/bash
set -e

# Ensure root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Set non-interactive mode for apt-get
export DEBIAN_FRONTEND=noninteractive

echo "Installing System Dependencies..."
ARCH="$(uname -m || true)"
IS_ARM="false"
case "${ARCH}" in
  aarch64|arm64|armv7l|armv7|armv6l|armv6) IS_ARM="true" ;;
esac

apt-get update
apt-get install -y python3-venv python3-pip docker.io ca-certificates curl apparmor apparmor-utils git openssl
apt-get install -y docker-compose-plugin || apt-get install -y docker-compose-v2

if [ "${IS_ARM}" = "true" ]; then
  apt-get install -y qemu-user-static binfmt-support
fi

# Start and Enable Docker Service
echo "Starting Docker Service..."
systemctl enable docker
systemctl start docker || true

# Verify Docker is running
if ! systemctl is-active --quiet docker; then
    echo "Docker failed to start. Attempting to restart..."
    systemctl restart docker
    sleep 5
    if ! systemctl is-active --quiet docker; then
        echo "Docker service is not running!"
        exit 1
    fi
fi

if [ "${IS_ARM}" = "true" ]; then
    echo "Configuring binfmt emulation for ARM hosts..."
    if timeout 60s docker run --privileged --rm tonistiigi/binfmt --install all; then
        echo "Binfmt handlers installed."
    else
        echo "WARNING: Failed to install binfmt handlers (network issue?). Skipping..."
    fi

    cat > /etc/systemd/system/docker-binfmt.service <<EOL
[Unit]
Description=Install binfmt handlers for multi-arch containers
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/timeout 60s /usr/bin/docker run --privileged --rm tonistiigi/binfmt --install all

[Install]
WantedBy=multi-user.target
EOL

    systemctl daemon-reload
    systemctl enable docker-binfmt.service
    timeout 60s systemctl start docker-binfmt.service || echo "WARNING: Failed to start binfmt service"
fi

# Setup Python Env
echo "Setting up Python Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

if [ -d ".git" ] && [ -f ".gitmodules" ]; then
    git submodule update --init --recursive
fi

# Install requirements
./venv/bin/pip install -r requirements.txt

CURRENT_DIR=$(pwd)

# Run System Optimization
echo "Running System Optimization..."
./venv/bin/python3 scripts/optimize.py

# Configure persistent ZRAM apply at boot
echo "Configuring ZRAM systemd unit..."
ZRAM_SERVICE_FILE="moneytree-zram.service"
cat > $ZRAM_SERVICE_FILE <<EOL
[Unit]
Description=MoneyTree ZRAM configuration
After=local-fs.target

[Service]
Type=oneshot
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 -m app.zram_boot
Environment="PYTHONPATH=$CURRENT_DIR"

[Install]
WantedBy=multi-user.target
EOL
cp $ZRAM_SERVICE_FILE /etc/systemd/system/

# Setup Systemd Service
echo "Configuring Systemd Service..."
SERVICE_FILE="income-manager.service"

# Create service file with correct paths
cat > $SERVICE_FILE <<EOL
[Unit]
Description=Passive Income Manager Dashboard
After=network.target docker.service
Requires=docker.service
StartLimitIntervalSec=60
StartLimitBurst=10

[Service]
Type=notify
NotifyAccess=main
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
TimeoutStartSec=120
TimeoutStopSec=30
KillMode=mixed
WatchdogSec=60
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=$CURRENT_DIR"
Environment="MONEYTREE_IGM_ROOT=$CURRENT_DIR/third_party/income-generator"

[Install]
WantedBy=multi-user.target
EOL

# Install service
cp $SERVICE_FILE /etc/systemd/system/
systemctl daemon-reload
systemctl enable moneytree-zram.service
systemctl start moneytree-zram.service || true
systemctl enable income-manager.service
systemctl start income-manager.service

echo "Configuring maintenance jobs..."
cat > /etc/systemd/system/moneytree-maintenance.service <<EOL
[Unit]
Description=MoneyTree maintenance (Docker cleanup)
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker image prune -af --filter until=168h
ExecStart=/usr/bin/docker builder prune -af --filter until=168h
EOL

cat > /etc/systemd/system/moneytree-maintenance.timer <<EOL
[Unit]
Description=Run MoneyTree maintenance daily

[Timer]
OnCalendar=*-*-* 03:30:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOL

systemctl daemon-reload
systemctl enable moneytree-maintenance.timer
systemctl start moneytree-maintenance.timer || true

cat > /etc/logrotate.d/moneytree <<EOL
$CURRENT_DIR/*.log {
  weekly
  rotate 4
  missingok
  notifempty
  compress
  delaycompress
  copytruncate
}
EOL

# Setup Pingpong
echo "Setting up Pingpong..."
PINGPONG_BIN="$CURRENT_DIR/PINGPONG"
if [ ! -f "$PINGPONG_BIN" ]; then
    echo "Downloading Pingpong binary..."
    # Use -L to follow redirects if any, though S3 usually doesn't need it
    curl -L -o "$PINGPONG_BIN" https://pingpong-build.s3.ap-southeast-1.amazonaws.com/linux/latest/PINGPONG || echo "WARNING: Failed to download Pingpong"
    if [ -f "$PINGPONG_BIN" ]; then
        chmod +x "$PINGPONG_BIN"
    fi
fi

PINGPONG_SERVICE_FILE="pingpong.service"
cat > $PINGPONG_SERVICE_FILE <<EOL
[Unit]
Description=Pingpong Multi-Mining Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 -m app.pingpong_wrapper
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=$CURRENT_DIR"

[Install]
WantedBy=multi-user.target
EOL

cp $PINGPONG_SERVICE_FILE /etc/systemd/system/
systemctl daemon-reload
systemctl enable pingpong.service
# Service is managed by native_manager (started if enabled in config)

echo "Running post-install smoke test..."
./venv/bin/python3 scripts/smoke_test.py

echo "Setup Complete!"
echo "Dashboard available at http://$(hostname -I | cut -d' ' -f1):5000"
