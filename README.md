# Money-tree-tools

Passive-income service manager with a web dashboard and watchdog for the following supported services:

- Honeygain
- TraffMonetizer
- Mysterium
- Pawns
- PacketStream
- PacketShare
- Repocket
- EarnFM
- Grass
- ProxyRack
- Bitping
- Wipter
- Uprock

## Security Model

- Secrets are stored encrypted at rest in `.env.enc`.
- The encryption key is stored at `MONEYTREE_SECRET_DIR/master.key` (defaults to `/etc/moneytree/master.key` on Linux).
- Docker service images are pinned by immutable sha256 digests in `docker-compose.yml`.
- Docker logs are rotated (5MB max, 1 file).

## Configuration

- Start the dashboard service.
- Open the dashboard and set all required credentials/tokens.
- The dashboard writes an encrypted config at `.env.enc` and never persists a plaintext `.env`.

Environment roots:

- `MONEYTREE_CONFIG_DIR` (optional): override where `.env.enc` is stored (default: project root).
- `MONEYTREE_SECRET_DIR` (optional): override where `master.key` is stored (default: `/etc/moneytree` on Linux).

## Running

On Debian/Ubuntu hosts with systemd, run the installer from the repo root:

```bash
bash install.sh
```

On Windows hosts, you can run the same installer via WSL2 (Ubuntu recommended):

```powershell
.\install.ps1
```

After install, open the dashboard and set all required credentials/tokens. The dashboard writes an encrypted config at `.env.enc` and never persists a plaintext `.env`.

Docker services are controlled via `docker compose` using a decrypted temporary env-file generated at runtime.

Wipter and Uprock are managed as host-native systemd units (`wipter.service`, `uprock.service`) and are controlled from the dashboard when installed.

## 24/7/365 Operation

The project is optimized for always-on devices:

- systemd-managed dashboard with automatic restart
- ZRAM + VM tuning for low-memory stability
- per-service Docker CPU/RAM/pid limits
- capped/rotated Docker logs to prevent disk-fill outages

See [docs/24-7.md](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/docs/24-7.md) for operational guidance and SBC recommendations.

## Armbian / ARM (Amlogic, Rockchip, etc.)

- `setup.sh` detects ARM and installs binfmt/qemu support so amd64-only images can still run under emulation.
- Prefer running services natively by setting `TARGET_PLATFORM` to match your board:
  - `linux/arm64` (most modern Armbian SBCs)
  - `linux/arm/v7` (32-bit armv7)
- You can override any single service by setting its `*_PLATFORM` variable (for example, `HONEYGAIN_PLATFORM=linux/amd64`).
- To generate a compatibility report for your target platform:

```bash
TARGET_PLATFORM=linux/arm64 python scripts/check_image_platforms.py
```

## Updating Image Digests

To refresh pinned digests and update `reports/image-digests.json`:

```bash
python scripts/resolve_dockerhub_digests.py
```

## Tests

```bash
python -m pytest
```

The test suite enforces the allowed-service inventory, digest pinning, resource limits, and encrypted-config behavior.
