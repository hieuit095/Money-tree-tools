# 💰 Money-tree-tools

Passive-income service manager with a web dashboard, watchdog, and automatic load control — optimized for **24/7 operation on Armbian TV boxes** and other low-power devices.

## ✨ Supported Services

| Service | Docker | Native | ARM Native |
|---------|:------:|:------:|:----------:|
| Honeygain | ✅ | | |
| TraffMonetizer | ✅ | | |
| Mysterium | ✅ | | ✅ |
| Pawns | ✅ | | ✅ |
| PacketStream | ✅ | | |
| PacketShare | ✅ | | |
| Repocket | ✅ | | |
| EarnFM | ✅ | | |
| Grass | ✅ | | |
| ProxyRack | ✅ | | |
| Bitping | ✅ | | ✅ |
| Wipter | | ✅ | |
| Uprock | | ✅ | |
| Pingpong | | ✅ | ✅ |

## 🚀 Quick Start

### One-Command Install (Armbian / Debian / Ubuntu)

SSH into your device and run:

```bash
curl -fsSL https://raw.githubusercontent.com/hieuit095/Money-tree-tools/main/quick-install.sh | bash
```

This single command will:
1. Clone the repository to `/opt/moneytree`
2. Install all system dependencies (Docker, Python, QEMU for ARM)
3. Configure ZRAM swap and system tuning
4. Apply Armbian/ARM optimizations (I/O scheduler, CPU governor)
5. Create and start systemd services
6. Launch the web dashboard

### Manual Install (from cloned repo)

```bash
git clone https://github.com/hieuit095/Money-tree-tools.git
cd Money-tree-tools
bash install.sh
```

### Windows (via WSL2)

```powershell
.\install.ps1
```

### After Installation

1. Open the dashboard at **`http://<device-ip>:5000`**
2. Login with default credentials: `admin` / `admin`
3. Configure your service credentials and tokens
4. Enable the services you want to run
5. Click **Apply** — services start automatically

## 🖥️ Dashboard

The web dashboard provides:
- **Service control** — Start, stop, restart any service with one click
- **Live status** — Real-time container health, CPU, RAM, and temperature
- **Configuration** — Set all credentials and tokens from the browser
- **ZRAM management** — Adjust compressed swap size without rebooting
- **Load reduction** — Automatic thermal protection with configurable thresholds
- **Logs** — View live container and service logs

## 🔒 Security Model

- Secrets are stored **encrypted at rest** in `.env.enc` (Fernet/AES-128-CBC)
- Encryption key stored at `/etc/moneytree/master.key` (mode `0600`)
- Docker images **pinned by sha256 digest** in `docker-compose.yml`
- Docker logs rotated (5 MB max) to prevent disk exhaustion
- No plaintext `.env` file is ever persisted

## ⚡ 24/7 Operation

Designed to run continuously on low-power devices:

- **systemd-managed** dashboard with automatic restart and watchdog
- **ZRAM** compressed swap for low-memory stability (auto-sized)
- **Load guard** — monitors temperature/CPU/RAM and stops services before overheating
- **Watchdog** — auto-recovers crashed services every 5 minutes
- **Docker limits** — per-service CPU/RAM/PID caps prevent runaway containers
- **Log rotation** — capped Docker + application logs prevent disk-fill
- **Daily maintenance** — automatic Docker image/cache prune

See [docs/24-7.md](docs/24-7.md) for operational details.

## 🔧 Armbian / ARM TV Boxes

The installer **auto-detects ARM architecture** and:
- Installs `qemu-user-static` + `binfmt-support` for amd64 image emulation
- Sets `TARGET_PLATFORM` to match your board (`linux/arm64` or `linux/arm/v7`)
- Applies ARM-specific kernel tuning (I/O scheduler, CPU governor, VM dirty ratios)
- Configures ZRAM with `zstd` compression (better ratio on low-RAM devices)

Override per-service platforms if needed:
```bash
HONEYGAIN_PLATFORM=linux/amd64  # force specific image
```

Check image compatibility:
```bash
TARGET_PLATFORM=linux/arm64 python scripts/check_image_platforms.py
```

See [docs/armbian_setup.md](docs/armbian_setup.md) for the full TV box installation guide.

## 📡 Multi-Device Deployment

Deploy to multiple devices at once using `deployer.py`:

```bash
# Edit inventory.yaml with your devices
python deployer.py
```

Define per-device profiles in `inventory.yaml`:
```yaml
profiles:
  sbc_low:
    ZRAM_SIZE_MB: 1024
    WATCHDOG_INTERVAL_SEC: 300

devices:
  - ip: "192.168.1.15"
    user: "orangepi"
    pass: "orangepi"
    box_id: "op-living-room"
    profile: "sbc_low"
    env:
      TARGET_PLATFORM: "linux/arm64"
```

## 🔄 Updating

From the dashboard, click **Update** or run manually:

```bash
cd /opt/moneytree
git pull
bash install.sh
```

## 📋 Configuration

All settings are managed through the dashboard. Key environment variables:

| Variable | Description |
|----------|-------------|
| `MONEYTREE_CONFIG_DIR` | Override config directory (default: project root) |
| `MONEYTREE_SECRET_DIR` | Override key directory (default: `/etc/moneytree`) |
| `TARGET_PLATFORM` | Docker platform override (e.g., `linux/arm64`) |
| `ZRAM_SIZE_MB` | ZRAM swap size in megabytes |

See [`.env.example`](.env.example) for all available variables.

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

## 📖 Useful Commands

```bash
# Dashboard
systemctl status income-manager     # Check status
journalctl -u income-manager -f     # Live logs

# Docker services
docker compose ps                   # Container status
docker compose logs -f honeygain    # Service logs

# System
swapon --show                       # Check ZRAM swap
cat /sys/block/zram0/comp_algorithm # Compression algo
```

## 📄 License

See [LICENSE](LICENSE) for details.

---
*Generated by ContribAI Farm-Agent v2.5.0 - Live Fire Crucible Test*
