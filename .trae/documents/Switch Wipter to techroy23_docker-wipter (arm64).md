## Diagnosis
- The dashboard’s Wipter modal currently has **no credential fields** because the Wipter section defines `fields: []`. [config_manager.py:L441-L449](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L441-L449)
- The codebase also currently treats Wipter as a **native systemd service** (`wipter.service`) rather than the Docker container shipped by IGM. [native_manager.py:L75-L103](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/native_manager.py#L75-L103), [watchdog.py:L54-L63](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/watchdog.py#L54-L63)
- Meanwhile, the vendored IGM compose defines a Docker `wipter` service that expects `EMAIL`/`PASSWORD` (mapped from `WIPTER_EMAIL`/`WIPTER_PASSWORD`) and optional `VNC_PASS`. [compose.local.yml:L181-L207](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.local.yml#L181-L207)

## What I Will Change
### 1) Add missing Wipter config fields to the UI
- Update Wipter section in [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py) to include:
  - `WIPTER_EMAIL`
  - `WIPTER_PASSWORD`
  - `VNC_PASS` (optional but commonly required for the container)

### 2) Persist `VNC_PASS` in encrypted config
- Add `VNC_PASS` to `get_required_fields()` so it is saved to `.env.enc` and available to the IGM env file.

### 3) Make ENABLE_WIPTER actually start the Docker Wipter container when systemd isn’t installed
- Add `ENABLE_WIPTER -> wipter` into Docker service orchestration so enabling Wipter triggers `docker compose up -d wipter`.
- Keep compatibility with “native wipter.service” installs:
  - If `wipter.service` exists, prefer native control.
  - If it does not exist, manage Docker Wipter.

### 4) Wire env mapping for VNC_PASS
- Extend IGM env mapping so `VNC_PASS` is written into the generated env file used for docker compose.

## Verification
- Run unit tests (`pytest`) and the inventory check script.
- Smoke-check on `192.168.1.15`:
  - Wipter modal shows new fields.
  - After saving + enabling, Wipter appears in `/api/containers` and transitions to `running` (or shows a real error state + logs).

## Deployment
- Redeploy the updated code to `192.168.1.15` and restart the systemd dashboard service.