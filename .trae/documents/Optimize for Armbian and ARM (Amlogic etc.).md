## Key Compatibility Risks on Armbian/ARM
- **Container architecture mismatch**: some service images may be amd64-only; on ARM this requires **binfmt/qemu emulation** or an **arm64-native image**.
- **Digest pinning + multi-arch**: pinning must remain stable, but we should also verify the pinned digest supports the target platform.
- **Armbian defaults**: Armbian often ships with **zram/zswap**, specific kernel modules, and different sysctl defaults; our `scripts/optimize.py` can conflict.
- **Docker on ARM SBCs**: cgroups/memory accounting and overlayfs can vary with kernels used on Amlogic boards.

## What I Will Change (High Level)
### 1) Add ARM/Armbian Platform Detection
- Add a small utility module (e.g., `app/platform_info.py`) to detect:
  - OS family (Debian/Armbian)
  - CPU arch (arm64/armv7/amd64)
  - whether systemd is available
- Use it to drive safe defaults (no hard-coded assumptions).

### 2) Make Installation Scripts Armbian-Safe
- Update [setup.sh](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/setup.sh):
  - Detect ARM (`uname -m`) and install `qemu-user-static` + `binfmt-support`.
  - Add a systemd unit that runs `tonistiigi/binfmt --install all` on boot (so emulation survives reboot).
  - Make docker-compose installation resilient (`docker-compose-v2` vs `docker-compose-plugin`).
  - Add checks for cgroup/memory accounting (warn + doc link output if unavailable).

### 3) Make System Optimization Script Armbian-Aware
- Update [scripts/optimize.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/optimize.py):
  - If Armbian already has zram enabled (detect via `/proc/swaps`), **do not override**.
  - Prefer writing to `/etc/sysctl.d/99-moneytree.conf` instead of appending to `/etc/sysctl.conf`.
  - Make zram algorithm/size configuration conditional on what the kernel exposes.

### 4) Add Platform Verification for Pinned Images
- Extend [scripts/resolve_dockerhub_digests.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/resolve_dockerhub_digests.py) and/or add a new script `scripts/check_image_platforms.py` to:
  - For each compose image, query the registry manifest list and record **supported platforms**.
  - Generate `reports/image-platforms.json`.
  - Fail loudly if an image lacks `linux/arm64` unless the user explicitly opts into `linux/amd64` emulation.

### 5) Allow Explicit Platform Overrides Per Service
- Update `docker-compose.yml` to support optional `platform:` per service via env vars, e.g.:
  - `HONEYGAIN_PLATFORM=linux/amd64` (forces emulation)
  - default empty (let Docker choose native arch)
- Keep digest pinning, but add a documented workflow:
  - Prefer native arm64
  - Fallback to amd64+binfmt only when required

### 6) Tests and Documentation
- Update tests to validate:
  - platform report generation exists and matches compose inventory
  - compose supports `platform` overrides without breaking
- Update docs (README) with an **Armbian/Amlogic** section:
  - Docker prerequisites
  - emulation notes
  - troubleshooting (cgroups, kernel modules, zram)

## Verification
- Run `python -m pytest`.
- Run `python scripts/resolve_dockerhub_digests.py` and `python scripts/check_image_platforms.py`.
- Confirm `setup.sh` is non-interactive and completes on Armbian.

## Outcome
- The repo will install cleanly on Armbian and ARM SBCs.
- Containers will run on ARM either natively (preferred) or via managed emulation.
- Optimization will not fight Armbian’s built-in zram/swap configuration.