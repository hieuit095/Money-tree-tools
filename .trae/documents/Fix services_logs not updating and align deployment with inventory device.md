## Root Causes
- Configuration save crashes because [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L75-L84) calls `apply_docker_configuration()` without importing it, so containers never start/stop and “My Services” stays empty.
- Logs endpoint crashes because [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L69-L74) calls `get_container_logs()` without importing it, so the UI’s Logs view always errors.
- Update-check endpoints reference `os`/`subprocess` but [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py) doesn’t import them, which will break update features when used.

## Code Changes
- Update [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py):
  - Import `apply_docker_configuration` and `get_container_logs` from [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py#L93-L128).
  - Add missing standard imports: `os`, `subprocess`.
- Update [deployer.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/deployer.py#L174-L183) to preconfigure the deployed device using values from [inventory.yaml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/inventory.yaml):
  - When creating a new encrypted config, set `WEB_USERNAME`/`WEB_PASSWORD` from the inventory’s `user`/`pass` for that device.
  - Preserve existing `.env.enc` if already present.

## Verification
- Start the app and exercise the UI:
  - Saving configuration no longer throws `NameError` and containers start/stop via `docker compose`.
  - “My Services” populates from `/api/containers`.
  - Logs view returns content from `/api/logs/<service>`.
  - CPU/Memory/Network stats update (they should also visibly change once services actually run).
- Run a quick Python import/compile sanity check to ensure no NameErrors remain.

## Notes
- This matches the InternetIncome-style flow (configure credentials → enable services → containers run). The current blocker is simply the missing imports, not the docker-compose definitions.
