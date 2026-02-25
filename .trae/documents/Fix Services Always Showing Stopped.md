## What’s Happening
The dashboard currently shows **Running** only when `status === "running"`; everything else is displayed as **Stopped**. So if a container is `exited`, `restarting`, `created`, or if startup fails (image pull failure, wrong arch, missing env/token, docker/compose error), you’ll see **Stopped** with no explanation.

Relevant code:
- UI badge logic: [dashboard.html:L770-L833](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L770-L833)
- Container status source: [docker_manager.py:L60-L93](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py#L60-L93)
- Enable flow starts/stops services but discards results: [main.py:L121-L139](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L121-L139)

## Fix Strategy
### 1) Surface real startup failures immediately
- Change `/save-config` to capture and display `apply_docker_configuration()` and `apply_native_configuration()` results on the dashboard page (success + error messages).
- Ensure docker/compose errors are included (stderr/stdout) so users see why a service didn’t start.

### 2) Improve status reporting (stop hiding important states)
- Return richer status data from `/api/containers`:
  - keep `status` but also include `status_raw` / `detail` (e.g., `exited`, `restarting`, `created`).
  - include `enabled` (from config) so the UI can show “Enabled but not running”.
- Update the UI to show:
  - **Running** (green) when running
  - **Starting / Restarting / Exited** (distinct badges)
  - a quick “View Logs” action for non-running services.

### 3) Make control/start more reliable
- Enhance `control_container()` to locate the correct container either by exact name or by Compose labels (so start/stop works even if Docker Compose names differ).

## Validation
- Deploy the updated code to `192.168.1.15`.
- Verify on-device:
  - enabling a service shows a clear “start OK” or “start failed: …” message
  - `/api/containers` returns correct states
  - the dashboard shows non-running states accurately and logs are accessible
