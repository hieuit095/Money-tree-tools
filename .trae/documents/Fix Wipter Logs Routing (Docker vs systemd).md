## Why This Happens

* The dashboard’s Logs endpoint treats `wipter` specially and always fetches **systemd journal logs** via `wipter.service`:

  * `GET /api/logs/wipter` → `get_wipter_logs()` → `journalctl -u wipter.service`

  * If the host does not have a native `wipter.service`, it returns: `Service 'wipter.service' is not installed`. [native\_manager.py:L65-L102](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/native_manager.py#L65-L102), [main.py:L150-L163](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L150-L163)

* But in your setup, Wipter is running as a **Docker container** (`ghcr.io/xterna/wipter`), so its logs should be fetched with `docker logs wipter` (per the IGM docs). That’s why other Docker services work and Wipter doesn’t: they use container logs, Wipter currently doesn’t.

## Fix

### 1) Route Wipter logs to the correct backend

* Update `/api/logs/<service>`:

  * If `wipter.service` exists → keep using systemd (`journalctl`).

  * Otherwise → use Docker logs (`get_container_logs('wipter')`).

### 2) (Optional) Improve message clarity

* If neither systemd nor Docker container exists, return a clear “not installed” message for Wipter.

## Verification

* Local: run `pytest`.

* Remote (`192.168.1.15`):

  * Confirm `GET /api/logs/wipter` returns Docker logs when Wipter is running in Docker.

  * Confirm native hosts still return journal logs.

## Files to Change

* [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py) (log routing logic)

