# Armbian TV Box Installation Guide

Guide for installing Money-tree-tools on ARM-based TV boxes running Armbian (Amlogic S905/S912/S922, Rockchip RK3328/RK3399, Allwinner H6 etc.).

## Prerequisites

- **Armbian image**: Use the latest stable Armbian with Debian or Ubuntu base for your board.
  - [Armbian Downloads](https://www.armbian.com/download/)
  - For TV boxes without official support, look for community images on the [Armbian forum](https://forum.armbian.com/).
- **Storage**: 8GB+ eMMC or SD card (eMMC strongly recommended for reliability under 24/7 operation).
- **RAM**: 1GB minimum, 2GB+ recommended. Services are memory-constrained but running many simultaneously requires headroom.
- **Network**: Ethernet (Wi-Fi is supported but Ethernet is far more reliable for traffic-based services).
- **Cooling**: Passive heatsink at minimum. TV box SoCs (especially Amlogic S912) throttle aggressively without cooling.

## Quick Install (Recommended)

SSH into your Armbian TV box and run this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/hieuit095/Money-tree-tools/main/quick-install.sh | bash
```

This will automatically:
- Clone the repository to `/opt/moneytree`
- Detect ARM architecture and install `qemu-user-static` + `binfmt-support`
- Install Docker, Python, and all dependencies
- Set up ZRAM swap (compressed RAM swap, critical for low-memory devices)
- Apply ARM-specific optimizations (I/O scheduler, CPU governor, VM tuning)
- Create and enable all systemd services
- Launch the web dashboard

## Manual Install (Alternative)

If you prefer to clone manually:

1. **Flash Armbian** to your TV box and complete initial setup (root password, create user).

2. **Clone and install:**
   ```bash
   cd /opt
   git clone https://github.com/hieuit095/Money-tree-tools.git moneytree
   cd moneytree
   bash install.sh
   ```

3. **Access the dashboard** at `http://<device-ip>:5000` (default login: `admin`/`admin`).

4. **Configure services** via the dashboard — set credentials and enable the services you want to run.

## Recommended ZRAM Sizes

| Device RAM | ZRAM Size | Recommended Max Services |
|------------|-----------|--------------------------|
| 1 GB       | 512 MB    | 3–4 services             |
| 2 GB       | 1024 MB   | 6–8 services             |
| 4 GB       | 2048 MB   | 10+ services             |

Configure via the dashboard under ZRAM settings, or set `ZRAM_SIZE_MB` in your config.

## Platform Configuration

The installer auto-detects your ARM architecture and sets `TARGET_PLATFORM` accordingly:

| Architecture | Platform Value     |
|-------------|--------------------|
| aarch64     | `linux/arm64`      |
| armv7l      | `linux/arm/v7`     |

If a service image doesn't support your native architecture, the system automatically falls back to amd64 emulation via QEMU (slower but functional).

To check which images support your platform natively:
```bash
TARGET_PLATFORM=linux/arm64 python scripts/check_image_platforms.py
```

## Known ARM-Compatible Services

| Service        | arm64 Native | amd64 Emulation |
|---------------|:------------:|:----------------:|
| Honeygain     | ❌           | ✅               |
| TraffMonetizer| ❌           | ✅               |
| Mysterium     | ✅           | ✅               |
| Grass         | ❌           | ✅               |
| PacketStream  | ❌           | ✅               |
| Repocket      | ❌           | ✅               |
| EarnFM        | ❌           | ✅               |
| Pawns         | ✅           | ✅               |
| Bitping       | ✅           | ✅               |
| Pingpong      | ✅           | N/A              |

> **Note**: Services running under emulation use ~2-3x more CPU. On 1-2GB RAM devices, limit emulated services to 2-3 max.

## Cooling and Thermal Management

The system includes automatic **Load Reduction** that monitors CPU temperature and usage:

- When temperature exceeds the threshold (default 70°C) AND CPU/RAM are high, non-priority services are automatically stopped.
- Once the device stabilizes (default recovery at 65°C), services restart gradually.
- Configure thresholds via the dashboard under "Load Reduction" settings.

**Recommendations:**
- Attach a heatsink to the SoC (often requires opening the TV box case).
- Place the device in a ventilated area.
- For SoCs like the Amlogic S912, consider an active fan — they run very hot.
- Set ZRAM to use `zstd` compression (done automatically) for better memory efficiency with slightly more CPU.

## Troubleshooting

- **Docker services fail to start**: Check `docker compose logs <service>` for errors. Some services may need amd64 emulation — ensure `binfmt-support` and `qemu-user-static` are installed.
- **High CPU/thermal throttling**: Reduce the number of running services, prioritize native ARM images, and check cooling.
- **Dashboard not accessible**: Verify with `systemctl status income-manager.service` and check journal logs with `journalctl -u income-manager.service -n 50`.
- **ZRAM not active**: Check with `swapon --show`. If not listed, run `python -m app.zram_boot` as root.
