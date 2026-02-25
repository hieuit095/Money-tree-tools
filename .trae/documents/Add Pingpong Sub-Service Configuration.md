## Goal
Add first-class configuration for Pingpong sub-services (0G, AIOZ, Grass, BlockMesh, DAWN, Hemi) and apply them by running the documented CLI commands (`PINGPONG config set …` then `PINGPONG stop/start --depins=…`).

## Current State (What Exists)
- Pingpong is already a native systemd-managed service (`pingpong.service`) controlled via [native_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/native_manager.py#L131-L202).
- The dashboard exposes Pingpong in config UI and APIs via [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L639-L658) and [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L120-L229).
- The wrapper currently only launches the binary with the device key: [pingpong_wrapper.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/pingpong_wrapper.py).

## 1) Config UI + Encrypted Fields
Update [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py) to add encrypted config keys and UI fields for:
- **0G**: `PINGPONG_0G_PRIVATE_KEY` (maps to `./PINGPONG config set --0g=***`).
- **AIOZ**: `PINGPONG_AIOZ_PRIV_KEY` (maps to `./PINGPONG config set --aioz=***`).
- **Grass**: `PINGPONG_GRASS_ACCESS`, `PINGPONG_GRASS_REFRESH` (maps to `./PINGPONG config set --grass.access=*** --grass.refresh=***`).
- **BlockMesh**: `PINGPONG_BLOCKMESH_EMAIL`, `PINGPONG_BLOCKMESH_PASSWORD` (maps to `./PINGPONG config set --blockmesh.email=*** --blockmesh.pwd=***`).
- **DAWN**: `PINGPONG_DAWN_EMAIL`, `PINGPONG_DAWN_PASSWORD` (maps to `./PINGPONG config set --dawn.email=*** --dawn.pwd=***`).
- **Hemi**: add a `PINGPONG_HEMI_KEY` field and wire it to a `./PINGPONG config set --hemi=***` command (and adjust naming/flag if the doc’s Hemi CLI flag differs).

All new secrets are marked `sensitive: True` so they stay encrypted in `.env.enc`.

## 2) Add a Pingpong “Configurator” (Safe CLI Runner)
Create a new module (e.g. `app/pingpong_configurator.py`) that:
- Builds the correct `PINGPONG config set …` arguments based on which fields are present.
- Runs the CLI commands using `subprocess.run(..., capture_output=True)` and returns sanitized status messages (never logs secret values).
- Implements the documented apply sequence per depin when its config changes:
  - `./PINGPONG stop --depins=<depin>`
  - `./PINGPONG start --depins=<depin>`
- Stores a hash of last-applied Pingpong sub-service configuration in a small state file under `config_root()` (add helpers to [runtime_state.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/runtime_state.py)) so we only stop/start depins when the relevant config changed.

## 3) Integrate into Apply Flow
Update [native_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/native_manager.py#L161-L202) so that when `ENABLE_PINGPONG=true`:
- Apply Pingpong depin configuration first (via the new configurator).
- Then ensure `pingpong.service` is started.
- If the **device key** changes while Pingpong is enabled and running, restart `pingpong.service` (wrapper reads keys at startup).

This keeps behavior consistent with other services: “Save config” → apply → services converge.

## 4) Installer Wiring
Update [setup.sh](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/setup.sh#L196-L231) to:
- Continue downloading `/opt/moneytree/PINGPONG`.
- Install **and enable** `pingpong.service` (safe because the wrapper exits immediately when `ENABLE_PINGPONG=false`).

## 5) Tests
- Update [test_service_inventory.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/tests/test_service_inventory.py#L60-L80) to include `pingpong` in the “required service sections” set.
- Add a new test module for the configurator to verify:
  - Correct command-line flags are produced for each depin.
  - Hashing/state prevents unnecessary stop/start.
  - Errors are returned without leaking secrets.

## 6) Verification (Local + Remote)
- Run the existing test suite.
- On `192.168.1.18`, set sample sub-service config values (test-only), trigger apply, and verify:
  - `PINGPONG config set …` ran successfully.
  - Only changed depins were restarted.
  - `pingpong.service` remains running and logs do not expose secrets.
