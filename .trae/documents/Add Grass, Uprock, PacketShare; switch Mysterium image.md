## Requirements (From Your Request)
- Add **Grass** using `mrcolorrain/grass` (Docker Hub).
- Add **Uprock** and **PacketShare** following `engageub/InternetIncome` run instructions.
- Ensure **Mysterium** uses `mysteriumnetwork/myst` (Docker Hub).

## Research Notes (What We Know Now)
- Grass image expects `GRASS_USER` and `GRASS_PASS` env vars and can run as a standard long-running container.
- InternetIncome runs PacketShare as `packetshare/packetshare` with flags `-accept-tos -email=$PACKETSHARE_EMAIL -password=$PACKETSHARE_PASSWORD`.
- Mysterium’s official Docker instructions run `mysteriumnetwork/myst service --agreed-terms-and-conditions` with `NET_ADMIN` and `--net host`; the current repo compose already matches this image family and pattern.

## Implementation Plan
### 1) Compose Services
- Update [docker-compose.yml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/docker-compose.yml):
  - Add `grass` service using `mrcolorrain/grass`.
    - Set `container_name: grass`, `hostname: ${DEVICE_NAME:-Server}`.
    - Pass env vars `GRASS_USER` / `GRASS_PASS`.
    - Apply existing project hardening pattern (log rotation + cpus/mem_limit/pids_limit).
    - Pin by digest (use the existing digest resolver workflow).
  - Add `packetshare` service using `packetshare/packetshare`.
    - Set command `-accept-tos -email=${PACKETSHARE_EMAIL} -password=${PACKETSHARE_PASSWORD}`.
    - Apply same hardening and digest pinning.
  - Add `uprock` service:
    - First, extract the exact image + command/env pattern from `engageub/InternetIncome` (their `internetIncome.sh` / `properties.conf`).
    - Implement that same container invocation in compose, then pin by digest.
    - If the upstream image is not on Docker Hub (e.g., GHCR), extend `scripts/resolve_dockerhub_digests.py` (or add a sibling script) to support that registry and still produce pinned refs + report.
  - Mysterium:
    - Confirm `mysteriumnetwork/myst` is used (already true) and optionally refresh the pinned digest via the digest resolver.

### 2) Dashboard + Config Storage
- Update [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py):
  - Add required credential keys:
    - Grass: `GRASS_USER`, `GRASS_PASS`.
    - PacketShare: `PACKETSHARE_EMAIL`, `PACKETSHARE_PASSWORD`.
    - Uprock: add exactly the fields required by InternetIncome’s run method (discovered in step 1).
  - Add enable flags: `ENABLE_GRASS`, `ENABLE_PACKETSHARE`, `ENABLE_UPROCK`.
  - Add UI sections in `get_config_sections()` for these services (matching the existing pattern: title/subtitle/instructions/enable_key/fields).

### 3) Service Control & Watchdog
- Update [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py):
  - Extend `SERVICE_MAP` with the 3 new enable flags → service names (`grass`, `packetshare`, `uprock`).
- Update [watchdog.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/watchdog.py):
  - Ensure watchdog restarts these services if enabled but not running.
  - Keep Mysterium healthcheck logic intact.

### 4) Digest Pinning & Reports
- Update pinned image inventory:
  - Run and/or extend [resolve_dockerhub_digests.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/resolve_dockerhub_digests.py) so new Docker Hub images get pinned, and non–Docker Hub registries (if Uprock uses one) are also supported.
  - Update `reports/image-digests.json` accordingly.

### 5) Tests + Docs
- Update/extend [tests/test_service_inventory.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/tests/test_service_inventory.py) to assert:
  - `docker-compose.yml` includes the newly supported services.
  - All compose images are digest-pinned.
  - `get_config_sections()` includes the new service sections.
- Update docs/examples:
  - [README.md](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/README.md)
  - [.env.example](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/.env.example)

## Verification
- Run `python -m pytest`.
- Run `python scripts/resolve_dockerhub_digests.py` (and the GHCR resolver if added) to ensure all images are pinned and the digest report is consistent.
- Run `python scripts/verify_required_services.py` to regenerate `reports/service-verification.json`.

## Open Point (Handled Automatically)
- Uprock’s exact container image/args aren’t visible in the snippets we have; after you confirm this plan, I will pull the exact Uprock run pattern from the InternetIncome repo and implement it verbatim in this project.