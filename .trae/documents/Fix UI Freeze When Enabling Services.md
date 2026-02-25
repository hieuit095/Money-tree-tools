## Root Cause
- Saving config (`/save-config`) currently runs **container apply synchronously** inside the HTTP request:
  - `apply_docker_configuration()` can call Docker/Compose many times (start/stop for every service), which may include image pulls and can block for a while.
  - During this time the browser is waiting on the POST/redirect, so the UI appears to freeze. [main.py:L165-L194](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L165-L194)

## Fix Strategy
### 1) Make “Apply Config” asynchronous
- Introduce an in-process background worker (thread) that performs:
  - `apply_docker_configuration()`
  - `apply_native_configuration()`
  - `save_last_apply(results)`
- Modify `/save-config` to:
  - save the config
  - enqueue/start the apply job
  - immediately redirect back to the dashboard (no waiting)

### 2) Expose apply progress to the UI
- Add endpoints:
  - `GET /api/apply/status` → `{running, started_at, finished_at, last_results, message}`
  - (optional) `POST /api/apply/start` → start apply if not already running
- Update the dashboard UI so the user sees:
  - “Applying changes…” while the background job is running
  - final results from `last_apply.json` once completed

### 3) Reduce apply work to avoid unnecessary Docker/Compose calls
- Optimize `apply_docker_configuration()` so it only touches services that actually need action:
  - Pre-fetch current container states once (`get_containers()`)
  - If `ENABLE_X=false` and the service is not running/present → **skip** (don’t call compose stop)
  - If `ENABLE_X=true` and already running → **skip**
  - Keep current fallback behavior to `docker compose up/stop` when containers aren’t found.

### 4) Add safety timeouts
- Add a reasonable timeout to `docker compose` subprocess calls so an apply cannot hang forever.

## Files Expected to Change
- [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py) (make `/save-config` async; add status endpoints)
- New: `app/apply_manager.py` (background apply worker + shared state)
- [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py) (optimize apply + compose timeouts)
- [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html) (show “applying” indicator + poll status)

## Verification
- Local: run `pytest`.
- Remote (192.168.1.15):
  - Enable a service that previously caused a long wait.
  - Confirm the UI returns immediately and shows an “Applying…” indicator.
  - Confirm apply completes and last results update.
  - Confirm containers end up in expected state.
