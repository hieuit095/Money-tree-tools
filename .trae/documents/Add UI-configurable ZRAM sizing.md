## Current State
- ZRAM is only configured during install via [optimize.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/optimize.py) (auto size = ½ RAM, min 256MiB).
- The UI has no ZRAM control; “System Settings” currently only includes update actions and a raw env editor: [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html).

## Goal
- Add a UI control to set a ZRAM “level” with fixed increments: **512MB, 1GB, 1.5GB, 2GB, 3GB, 4GB**.
- Persist the selected value in encrypted config and apply it immediately on the host.

## Implementation Plan
### 1) Add Config Keys
- Add `ZRAM_SIZE_MB` to required config fields (stored in `.env.enc`) via [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py).
- Define allowed values (as integers): `512, 1024, 1536, 2048, 3072, 4096`.

### 2) Add a Safe ZRAM Controller Module
- Create a new module (e.g. `app/zram_manager.py`) that:
  - Reads current RAM and current `/sys/block/zram0/disksize`.
  - Applies a new size by performing: `swapoff /dev/zram0` (if active) → `echo 1 > /sys/block/zram0/reset` → write new `disksize` → `mkswap` → `swapon -p 100`.
  - Loads the module if missing (`modprobe zram num_devices=1`).
  - Validates the requested size is one of the allowed values.
  - Returns structured status + error messages for the UI.

### 3) Expose API Endpoints
- Add endpoints in [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py):
  - `GET /api/system/zram` → returns current ZRAM size, total RAM, and current configured `ZRAM_SIZE_MB`.
  - `POST /api/system/zram` with `{size_mb: 512|1024|1536|2048|3072|4096}` → saves `ZRAM_SIZE_MB` to encrypted config and applies ZRAM immediately.

### 4) Add UI Controls (Dropdown)
- Update [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html) “System Settings” view to include a ZRAM card with:
  - A dropdown showing exactly those increments.
  - An “Apply” button that calls the API and shows success/error feedback.
  - A small status line showing “current ZRAM size” from `GET /api/system/zram`.

### 5) Wire Install-Time Behavior
- Update [scripts/optimize.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/optimize.py) so that if `ZRAM_SIZE_MB` exists in environment at install time, it uses that size instead of ½ RAM.

### 6) Tests
- Add unit tests to ensure:
  - `ZRAM_SIZE_MB` is included in `get_required_fields()`.
  - Validation only accepts the allowed size list.
  - The dashboard config round-trip preserves `ZRAM_SIZE_MB`.

## Verification
- Run `python -m pytest`.
- (Optional on a Linux host) call `POST /api/system/zram` and confirm `swapon --show` and `/sys/block/zram0/disksize` reflect the selected value.

## Notes
- This feature changes host swap configuration and therefore requires the service to run with sufficient privileges (your current systemd unit runs as root). The endpoint remains protected by existing HTTP basic auth.