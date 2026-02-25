## 1) Power-Loss Autostart: Detailed Analysis
- **What reliably autostarts today**
  - `docker.service` is enabled in setup, so Docker comes back after a reboot/power loss.
  - `income-manager.service` (the dashboard) is enabled and uses `Restart=always` + systemd watchdog pings, so it restarts automatically.
  - `moneytree-zram.service` is enabled (oneshot) and reapplies ZRAM at boot.
- **How income services resume**
  - Docker containers defined by the IGM compose stack generally have `restart: always`, so once created, Docker will restart them when Docker comes up.
  - The dashboard’s internal watchdog periodically “reconciles” enabled services and will run `docker compose up -d ...` to recreate/start missing containers.
- **Important gaps found (where autostart may be “incorrect”)**
  - If a service is **disabled in config but its container exists with `restart: always`**, Docker can bring it back after reboot; the current watchdog explicitly does not stop services that “shouldn’t be running”.
  - Native/systemd-managed apps like **wipter/uprock** are only autostarted if their own systemd units are installed/enabled externally; repo doesn’t install/enable them.
  - Config persistence depends on `.env.enc` + underlying filesystem integrity; sudden power loss can corrupt storage on low-end devices.

## 2) Load Reduction Feature (Thermal + CPU/RAM pressure)
### Behavior
- Add a background “load guard” loop that monitors:
  - CPU temperature (°C)
  - CPU usage (%)
  - RAM usage (%)
  - (optionally) Swap usage (%) as an early-warning
- If **temp ≥ 70°C** AND (**CPU ≥ 90%** OR **RAM ≥ 90%**) for a short sustained window, enter **load-reduction mode**.
- In load-reduction mode:
  - Stop non-priority running services (one-by-one with cooldown) until the device stabilizes.
  - Record which services were stopped by the load guard.
- When stabilized (hysteresis to avoid flapping, e.g. temp ≤ 65°C and CPU/RAM below thresholds for N seconds):
  - Restart previously-stopped services that are enabled and non-priority (gradually).

### Implementation Approach
- Extend the existing monitoring primitives in `app/system_monitor.py` (already provides CPU temp/CPU/RAM).
- Extend/augment `app/watchdog.py` so that:
  - It does **not** restart services currently paused by load reduction.
  - It can optionally stop “disabled-but-running” services at boot to make power-loss recovery consistent with config.
- Add a small runtime state file (similar to `last_apply.json`) to persist:
  - whether load-reduction mode is active
  - which services were stopped by the guard
  - last trigger reason and timestamps

### Shedding Policy (what to stop)
- Default: stop the **highest memory usage** container among non-priority services first (uses existing per-container memory readings).
- Also support native services (wipter/uprock) via their existing start/stop control paths.

## 3) Priority Services (“Star”)
### Behavior
- Users can star services in the UI.
- Starred services are **never stopped** by the load-reduction guard.
- Defaults (if user hasn’t customized): **Grass, Wipter, Repocket, Honeygain**.

### Data Model
- Store in encrypted config as a single field, e.g. `PRIORITY_SERVICES=grass,wipter,repocket,honeygain`.
- Treat empty/missing as default list above.

### UI/Endpoints
- Add a star icon column to the “My Services” table:
  - Click toggles priority for that service via a new API endpoint.
  - Service rows visually indicate priority.
- Add an optional “Load Reduction” settings section to Configuration:
  - enable/disable
  - temp/CPU/RAM thresholds
  - recovery thresholds / cooldowns

## Verification
- Unit tests for:
  - priority parsing and defaults
  - threshold evaluation + hysteresis logic
  - watchdog not restarting paused services
- Local lint/compile/tests.
- Deploy to `192.168.1.18` and confirm:
  - after reboot, config-disabled services are not left running
  - load reduction triggers under forced conditions and recovers
  - priority-starred services remain running during shedding

