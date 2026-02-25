## What’s Already Optimized (Current State)
- **Auto-recovery**: `income-manager.service` is a systemd unit with `Restart=always` and `RestartSec=5` so the app comes back after crashes/reboots.
- **RAM pressure handling**: setup configures **ZRAM swap**, sets `vm.swappiness=100` and `vm.vfs_cache_pressure=50`, and skips swapfile provisioning when ZRAM is active.
- **Container resilience + resource caps**: Docker Compose services use `restart: always`, plus per-service CPU/RAM/pids limits; Docker logs are capped/rotated (and `/etc/docker/daemon.json` enforces defaults).
- **ARM/SBC compatibility**: ARM checks and optional `binfmt/qemu` setup exist for multi-arch container support.

## Improvements To Make It More “24/7/365”
1. **Document the 24/7 guarantees**
   - Add a short doc/README section that explains: restart behavior, ZRAM policy, memory limits, log rotation, and the recommended SBC settings (cgroups, governor, /dev/net/tun).
2. **Harden the systemd service for long uptime**
   - Extend `income-manager.service` with reliability-focused settings (e.g., `StartLimitIntervalSec/StartLimitBurst`, `TimeoutStopSec`, `KillMode`, `WatchdogSec` + a watchdog ping in-app, and optional `OOMScoreAdjust`).
3. **Add health checks for containers**
   - Add `healthcheck:` blocks to critical Docker services and align restart/depends-on behavior so unhealthy containers recover more deterministically.
4. **Reduce storage wear + prevent disk-fill outages**
   - Add a maintenance mechanism (systemd timer or cron) for safe periodic cleanup (e.g., Docker image pruning with guardrails) and log rotation for app logs.
5. **Make optimizations configurable per device**
   - Extend `inventory.yaml`/config to allow per-device profiles (e.g., ZRAM size, CPU/RAM caps, enable/disable binfmt, watchdog interval).

## Verification After Changes
- Confirm systemd unit is active/enabled and survives reboot.
- Confirm ZRAM active and swap behaves as expected.
- Confirm container health checks report healthy and services recover after forced failures.
- Confirm log growth stays bounded and disk usage is stable over time.

If you confirm, I’ll implement the changes (docs + unit hardening + healthchecks + maintenance) and validate them locally and against the target device.