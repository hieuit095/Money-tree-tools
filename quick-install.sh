#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Money-tree-tools: Quick Installer
# One-command setup for Armbian TV boxes and Debian/Ubuntu hosts
#
# Usage (on the target device):
#   curl -fsSL https://raw.githubusercontent.com/hieuit095/Money-tree-tools/main/quick-install.sh | bash
#
# Or if already cloned:
#   bash quick-install.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
  echo ""
  echo -e "${GREEN}${BOLD}"
  echo "  ╔═══════════════════════════════════════════╗"
  echo "  ║       💰 Money-tree-tools Installer       ║"
  echo "  ║    Passive Income Service Manager v1.0    ║"
  echo "  ╚═══════════════════════════════════════════╝"
  echo -e "${NC}"
}

info()  { echo -e "  ${CYAN}ℹ${NC}  $*"; }
ok()    { echo -e "  ${GREEN}✔${NC}  $*"; }
warn()  { echo -e "  ${YELLOW}⚠${NC}  $*"; }
fail()  { echo -e "  ${RED}✖${NC}  $*"; exit 1; }
step()  { echo -e "\n${BOLD}── $* ──${NC}"; }

# ── Pre-flight checks ──────────────────────────────────────
banner

[ "$(uname -s)" = "Linux" ] || fail "This installer supports Linux only. Current OS: $(uname -s)"
command -v systemctl >/dev/null 2>&1 || fail "systemctl not found. This project requires systemd."
command -v apt-get  >/dev/null 2>&1 || fail "apt-get not found. Debian/Ubuntu-based distributions only."

# ── Ensure root ─────────────────────────────────────────────
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    warn "Not running as root — relaunching with sudo..."
    exec sudo bash "$0" "$@"
  fi
  fail "Root privileges required (sudo not available)."
fi

# ── Detect architecture ─────────────────────────────────────
step "Detecting system"
ARCH="$(uname -m || true)"
IS_ARM="false"
case "${ARCH}" in
  aarch64|arm64)   IS_ARM="true"; TARGET_PLATFORM="linux/arm64"   ;;
  armv7l|armv7)    IS_ARM="true"; TARGET_PLATFORM="linux/arm/v7"  ;;
  armv6l|armv6)    IS_ARM="true"; TARGET_PLATFORM="linux/arm/v6"  ;;
  x86_64|amd64)    TARGET_PLATFORM="linux/amd64"                  ;;
  *)               TARGET_PLATFORM="linux/amd64"                  ;;
esac

TOTAL_RAM_MB=$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null || echo "0")
CPU_CORES=$(nproc 2>/dev/null || echo "?")
HOSTNAME_SHORT=$(hostname -s 2>/dev/null || echo "unknown")

info "Hostname    : ${HOSTNAME_SHORT}"
info "Architecture: ${ARCH} (${TARGET_PLATFORM})"
info "CPU cores   : ${CPU_CORES}"
info "Total RAM   : ${TOTAL_RAM_MB} MB"
info "ARM device  : ${IS_ARM}"

# Detect Armbian
IS_ARMBIAN="false"
if [ -f /etc/armbian-release ] || grep -qi armbian /etc/os-release 2>/dev/null; then
  IS_ARMBIAN="true"
  ok "Armbian detected — TV box optimizations will be applied."
fi

# ── Clone or locate the repository ──────────────────────────
step "Preparing repository"
INSTALL_DIR="/opt/moneytree"

# If this script is running from inside a cloned repo, use that
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd -P || true)"
if [ -f "${SCRIPT_DIR}/setup.sh" ] && [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
  INSTALL_DIR="${SCRIPT_DIR}"
  ok "Using existing repo at: ${INSTALL_DIR}"
elif [ -d "${INSTALL_DIR}/.git" ]; then
  ok "Existing installation found at: ${INSTALL_DIR}"
  info "Pulling latest changes..."
  cd "${INSTALL_DIR}"
  git pull --ff-only || warn "Git pull failed — continuing with current version."
else
  info "Cloning repository to ${INSTALL_DIR}..."
  apt-get install -y git >/dev/null 2>&1 || true
  git clone https://github.com/hieuit095/Money-tree-tools.git "${INSTALL_DIR}"
  ok "Repository cloned."
fi

cd "${INSTALL_DIR}"

# Initialize submodules
if [ -f ".gitmodules" ]; then
  info "Initializing git submodules..."
  git submodule update --init --recursive
  ok "Submodules ready."
fi

# ── Install system dependencies ─────────────────────────────
step "Installing system dependencies"
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq \
  python3-venv python3-pip \
  docker.io ca-certificates curl \
  apparmor apparmor-utils \
  git openssl >/dev/null 2>&1

apt-get install -y -qq docker-compose-plugin 2>/dev/null \
  || apt-get install -y -qq docker-compose-v2 2>/dev/null \
  || warn "docker-compose plugin not available from apt — will try later."

if [ "${IS_ARM}" = "true" ]; then
  info "Installing ARM/QEMU multi-arch support..."
  apt-get install -y -qq qemu-user-static binfmt-support >/dev/null 2>&1
  ok "qemu-user-static + binfmt-support installed."
fi

ok "System dependencies installed."

# ── Start Docker ────────────────────────────────────────────
step "Configuring Docker"
systemctl enable docker >/dev/null 2>&1
systemctl start docker 2>/dev/null || true

if ! systemctl is-active --quiet docker; then
  warn "Docker not running — restarting..."
  systemctl restart docker
  sleep 5
  systemctl is-active --quiet docker || fail "Docker failed to start!"
fi
ok "Docker is running."

# Docker log rotation (prevent disk fill on small eMMC/SD)
mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ] || ! grep -q "max-size" /etc/docker/daemon.json 2>/dev/null; then
  cat > /etc/docker/daemon.json <<'DAEMON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "5m",
    "max-file": "1"
  }
}
DAEMON
  systemctl restart docker
  ok "Docker log rotation configured (5 MB max)."
fi

# Binfmt for ARM hosts (run amd64 images under emulation)
if [ "${IS_ARM}" = "true" ]; then
  info "Installing binfmt handlers for multi-arch..."
  if timeout 60s docker run --privileged --rm tonistiigi/binfmt --install all >/dev/null 2>&1; then
    ok "Binfmt emulation handlers installed."
  else
    warn "Binfmt install failed (network?). amd64 images may not start."
  fi
fi

# ── Python environment ──────────────────────────────────────
step "Setting up Python environment"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
./venv/bin/pip install --quiet -r requirements.txt
ok "Python dependencies installed."

# ── System optimization ─────────────────────────────────────
step "Optimizing system"
./venv/bin/python3 scripts/optimize.py
ok "System optimized (ZRAM + VM tuning + ARM tweaks)."

# ── Systemd services ────────────────────────────────────────
step "Installing systemd services"
CURRENT_DIR="$(pwd)"

# 1. ZRAM boot service
cat > /etc/systemd/system/moneytree-zram.service <<EOF
[Unit]
Description=MoneyTree ZRAM configuration
After=local-fs.target

[Service]
Type=oneshot
User=root
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python3 -m app.zram_boot
Environment="PYTHONPATH=${CURRENT_DIR}"

[Install]
WantedBy=multi-user.target
EOF

# 2. Dashboard service
cat > /etc/systemd/system/income-manager.service <<EOF
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
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
TimeoutStartSec=120
TimeoutStopSec=30
KillMode=mixed
WatchdogSec=60
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=${CURRENT_DIR}"
Environment="MONEYTREE_IGM_ROOT=${CURRENT_DIR}/third_party/income-generator"

[Install]
WantedBy=multi-user.target
EOF

# 3. Pingpong service
cat > /etc/systemd/system/pingpong.service <<EOF
[Unit]
Description=Pingpong Multi-Mining Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python3 -m app.pingpong_wrapper
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONPATH=${CURRENT_DIR}"

[Install]
WantedBy=multi-user.target
EOF

# 4. Maintenance timer (Docker cleanup weekly)
cat > /etc/systemd/system/moneytree-maintenance.service <<EOF
[Unit]
Description=MoneyTree maintenance (Docker cleanup)
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker image prune -af --filter until=168h
ExecStart=/usr/bin/docker builder prune -af --filter until=168h
EOF

cat > /etc/systemd/system/moneytree-maintenance.timer <<EOF
[Unit]
Description=Run MoneyTree maintenance daily

[Timer]
OnCalendar=*-*-* 03:30:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Log rotation
cat > /etc/logrotate.d/moneytree <<EOF
${CURRENT_DIR}/*.log {
  weekly
  rotate 4
  missingok
  notifempty
  compress
  delaycompress
  copytruncate
}
EOF

# Enable and start
systemctl daemon-reload
systemctl enable moneytree-zram.service income-manager.service moneytree-maintenance.timer pingpong.service >/dev/null 2>&1
systemctl start moneytree-zram.service || true
systemctl start moneytree-maintenance.timer || true
systemctl start income-manager.service
ok "Systemd services installed and started."

# ── Pingpong binary ─────────────────────────────────────────
step "Setting up Pingpong"
PINGPONG_BIN="${CURRENT_DIR}/PINGPONG"
if [ ! -f "${PINGPONG_BIN}" ]; then
  info "Downloading Pingpong binary..."
  if curl -fsSL -o "${PINGPONG_BIN}" https://pingpong-build.s3.ap-southeast-1.amazonaws.com/linux/latest/PINGPONG; then
    chmod +x "${PINGPONG_BIN}"
    ok "Pingpong binary downloaded."
  else
    warn "Failed to download Pingpong (will retry on next run)."
  fi
else
  ok "Pingpong binary already present."
fi

# ── Smoke test ──────────────────────────────────────────────
step "Running post-install checks"
./venv/bin/python3 scripts/smoke_test.py || warn "Some smoke test checks failed (see above)."

# ── Done! ───────────────────────────────────────────────────
DEVICE_IP=$(hostname -I 2>/dev/null | cut -d' ' -f1 || echo "localhost")

echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║             ✅ Installation Complete!                 ║"
echo "  ╠═══════════════════════════════════════════════════════╣"
echo "  ║                                                       ║"
echo "  ║  Dashboard: http://${DEVICE_IP}:5000                  ║"
echo "  ║  Login    : admin / admin (change after first login)  ║"
echo "  ║                                                       ║"
echo "  ║  Next steps:                                          ║"
echo "  ║    1. Open the dashboard in your browser              ║"
echo "  ║    2. Set your service credentials & tokens           ║"
echo "  ║    3. Enable the services you want to run             ║"
echo "  ║    4. Click 'Apply' — services start automatically    ║"
echo "  ║                                                       ║"
echo "  ╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "  ${CYAN}Useful commands:${NC}"
echo "    systemctl status income-manager    # Dashboard status"
echo "    journalctl -u income-manager -f    # Live dashboard logs"
echo "    docker compose ps                  # Container status"
echo ""
