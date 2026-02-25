## Current State (Verified)
- This repository currently does **not** reference `engageub/InternetIncome` (no scripts/configs/invocations).
- Service orchestration today is a custom stack:
  - Docker Compose services: `honeygain`, `traffmonetizer`, `packetstream`, `packetshare`, `repocket`, `earnfm`, `grass`, `mysterium`, `pawns`, `proxyrack`, `bitping`.
  - Host-native systemd services: `wipter`, `uprock`.
- The dashboard stores secrets in `.env.enc` and generates a decrypted temporary env-file only at runtime.

## Key Compatibility Note
- The repository URL should be `https://github.com/XternA/income-generator` (without the trailing dot). The wiki pages you linked match that repo.
- IGM’s public application table (README/wiki) includes most of our Docker services and `WIPTER`, but **does not show `UPROCK`**. Plan keeps `uprock` as a native-managed service unless the cloned IGM repo proves otherwise.

## Migration Approach
- Keep the dashboard/UI and encrypted config model.
- Swap the orchestration backend from “our docker-compose.yml + systemd wrappers” to “IGM CLI/tool”, while preserving:
  - Per-service enable/disable, start/stop/restart.
  - Container/service status listing.
  - Logs viewing.
  - Watchdog recovery loop.
- Maintain `uprock` (and optionally `wipter`) as native services if IGM does not support them.

## Implementation Plan
### 1) Vendor/Pin IGM Into This Repo
- Add `third_party/income-generator/` (submodule or vendored copy) pinned to a specific commit/tag for deterministic behavior.
- Add configuration knob `MONEYTREE_IGM_ROOT` (default to the vendored path) so deployments can override to a preinstalled `~/.igm` if desired.

### 2) Create a Single Orchestration Wrapper (IGM Bridge)
- Add a new module (e.g., `app/igm_manager.py`) responsible for:
  - Validating IGM presence (`start.sh` / platform entrypoints exist).
  - Executing IGM commands with:
    - Strict timeouts.
    - Captured output capped to 5MB (matching current log policy).
    - Stable cwd/ENV handling.
  - Mapping “Money-tree service names” ↔ “IGM application identifiers”.

### 3) Config Mapping (Money-tree → IGM)
- After vendoring IGM, read its config schema (e.g., `.env` keys / app table definitions) and implement a definitive mapping:
  - `DEVICE_NAME` → IGM alias/device naming.
  - App credentials/tokens → the exact IGM env keys.
  - Enable flags → IGM enable/disable toggles.
  - Resource limits: map our existing defaults to IGM’s built-in “resource limit” feature.
- Preserve `.env.enc` as the source of truth; generate/update the IGM `.env` inside `MONEYTREE_IGM_ROOT` from decrypted config when applying changes.

### 4) Swap Dashboard Backend Calls
- Replace current Docker Compose calls in [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py) with IGM-backed operations:
  - `get_containers()` → `igm show` (or IGM’s structured status if present), normalized to the same JSON shape.
  - `control_container()` / `stop_all()` → IGM start/stop/redeploy equivalents.
  - `get_container_logs()` → IGM log retrieval (or docker logs via container names returned by IGM, if IGM doesn’t expose logs directly).
- Keep [native_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/native_manager.py) for `uprock` (and `wipter` if needed).

### 5) Update Watchdog Logic
- Replace “Docker container status” checks with IGM status checks.
- Preserve `mysterium` healthcheck behavior; on failure, restart via IGM (or docker restart if IGM doesn’t expose a restart verb).

### 6) Update Bootstrap/Setup
- Modify `setup.sh` to:
  - Install any prerequisites IGM requires on Linux (git, etc.).
  - Install/update the vendored/pinned IGM runtime path.
  - Ensure Docker + Compose plugin remain installed (IGM depends on container runtime).

### 7) Tests and Verification (No Regressions)
- Replace Compose inventory assertions with IGM inventory assertions:
  - Verify our supported-service list remains intact.
  - Verify our config sections still cover all required services.
  - Verify IGM app definitions include our required apps (except `uprock`, which remains native if unsupported).
- Keep encrypted-config tests unchanged.
- Add tests for:
  - IGM command runner timeout/output caps.
  - Stable mapping coverage (every enabled service has corresponding IGM mapping).

## Deliverables
- IGM vendored/pinned under `third_party/`.
- New `app/igm_manager.py` wrapper.
- Updated dashboard orchestration paths.
- Updated watchdog and service verification/tests.
- Updated documentation describing IGM-based operation and how `uprock` is handled.

## Acceptance Criteria
- All currently supported services remain present in the UI and controllable.
- Enabling/disabling services results in correct runtime state under IGM.
- Logs and status views work.
- Watchdog recovers stopped services.
- Test suite passes with the new backend.