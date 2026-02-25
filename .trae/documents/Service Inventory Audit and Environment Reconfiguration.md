## Current Inventory (Post-Change)

* **Allowlisted Docker services present in compose:** Honeygain, TraffMonetizer, PacketStream, Repocket, EarnFM, Mysterium, Pawns, ProxyRack, Bitping.
* **Allowlisted native service integrated:** Wipter (systemd unit `wipter.service`).
* **Non-allowed services removed from repo:** EarnApp, Grass, Uprock, PacketShare.
* **Config hardening:** secrets are stored encrypted at rest in `.env.enc` (plaintext `.env` is migrated and removed if found).
* **Credential hygiene:** tracked inventory files were scrubbed of plaintext credentials.

## Phase 1 — Removal of Non-Allowed Services (Repo + Host)

1. **Codebase removal (deterministic, no runtime assumptions):**

   * Remove EarnApp/Grass/Uprock/PacketShare from:

     * Compose definitions (including commented sections) in [docker-compose.yml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/docker-compose.yml).

     * Env key inventory and config UI in [config\_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py).

     * Container enable map in [docker\_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py).

     * Runtime routes/status aggregation in [main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py) and watchdog logic in [watchdog.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/watchdog.py).

     * Dashboard UI service selector/labels in [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html).

   * Remove service-specific helper scripts that hardcode credentials and/or only exist to manage removed services: [fix\_env.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/fix_env.py), [verify\_grass.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/verify_grass.py), [debug\_check.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/debug_check.py), and Grass-specific remote workaround [remote\_fix.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/remote_fix.py).

   * Update [setup.sh](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/setup.sh) to stop installing EarnApp.

   * Update internal docs in [.trae/documents](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/.trae/documents) to remove EarnApp/Grass/Uprock/PacketShare mentions.
2. **Host/container removal workflow (implemented as safe, idempotent scripts + documented commands):**

   * Docker: stop/remove containers, remove associated images, and remove named volumes created for these services.

   * System services: detect and remove EarnApp systemd unit(s) and binaries installed by the Bright Data script.

   * Env/credentials: remove related keys from managed `.env.enc` and ensure they are not reintroduced.

   * Network rules/ports and DB artifacts: include explicit checks/cleanup steps in scripts, but they will only delete what is actually detected (repo scan found no rule automation; scripts will validate before deleting).

## Phase 2 — Add Missing Required Services (Full Integration)

For each missing required service, add a first-class integration that matches the project’s existing pattern (Compose + ENABLE\_\* flags + UI section + logs + watchdog recovery):

1. **Mysterium**

   * Use official Docker image `mysteriumnetwork/myst` (Docker Hub). Run `service --agreed-terms-and-conditions` and persist node data via a dedicated volume. Source: [mysteriumnetwork/myst](https://hub.docker.com/r/mysteriumnetwork/myst).

   * Add health check using TequilAPI `GET /healthcheck` on default port 4050 (documented). Source: [Mysterium docs healthcheck](https://docs.mysterium.network/for-developers/node-development) and [TequilAPI defaults](https://help.mystnodes.com/en/articles/4531943-tequilapi).

   * Security: do not expose TequilAPI beyond localhost by default; if exposed, require configured credentials.
2. **Pawns**

   * Use Docker image `iproyal/pawns-cli` and run with required flags (email/password/device identifiers) as documented. Sources: [Pawns official blog](https://pawns.app/blog/how-to-install-and-run-the-pawns-app-container-in-docker/) and [Docker Hub](https://hub.docker.com/r/iproyal/pawns-cli).
3. **ProxyRack**

   * Use Docker Hub image referenced by ProxyRack help guidance and require UUID (+ optional API key). Sources: [ProxyRack help](https://help.proxyrack.com/en/articles/8397256-how-do-i-install-the-peer-program-in-docker) and [proxyrack/pop](https://hub.docker.com/r/proxyrack/pop).
4. **Bitping**

   * Use official Docker image `bitping/bitpingd` and configure per official install instructions; persist `/root/.bitpingd` via a dedicated volume. Sources: [Bitping node install docs](https://bitping.com/help/nodes/installing-the-node) and [bitping/bitpingd](https://hub.docker.com/r/bitping/bitpingd).
5. **Wipter**

   * Wipter has an official website and claims Linux support, but no official Docker image was identified in sources found so far. Source: [wipter.com](https://wipter.com/en).

   * To satisfy your “official sources + verified checksums/signatures” requirement with zero ambiguity, implementation will proceed only if we can obtain an official, verifiable distribution channel (e.g., vendor-signed apt repo metadata, or published checksum + signature files). If Wipter does not publish verifiable signatures, the plan will explicitly stop and report non-compliance rather than silently weakening the requirement.

## Phase 3 — Supply-Chain Verification (No Tag Drift)

* For every Docker-based service, lock images by **digest pinning** (`image: repo@sha256:...`) after pulling the vendor’s “latest stable” reference.

* Where vendors provide signature verification for artifacts, implement it (GPG/cosign/Notation). If not provided, record that fact explicitly in the final report and rely on digest pinning as the integrity mechanism for images.

## Phase 4 — Secure Defaults, Logging, Monitoring, Health, Restart

* **Logging:** keep Docker `json-file` rotation at 5MB already present in compose; unify across all services.

* **Resource limits:** enforce CPU/RAM limits per service in a way that is actually honored by the deployed compose runtime (verified via `docker inspect` after deployment).

* **Health checks:**

  * Use vendor-documented HTTP health endpoints when available (e.g., Mysterium /healthcheck).

  * Otherwise, implement a deterministic process-level health probe (only if the service provides a documented CLI status command; no guessing).

* **Restart policies:** keep Docker restart policy + extend the existing watchdog to include the new services and exclude removed ones.

## Phase 5 — Tests (Real, Non-Mocked)

* Add a test suite that validates:

  * The “allowed service set” is the only one present in compose/config/UI.

  * All required services have full config fields, enable flags, and are wired into watchdog + logs.

  * Integration tests that exercise real Docker interactions (requires Docker available). Tests will fail fast with explicit prerequisites if Docker is unavailable, instead of using mocks.

## Phase 6 — Documentation + Audit Report Output

* Add/refresh documentation:

  * Minimal README (currently empty) describing how to configure and run exactly the ten services.

  * Provide safe examples (`.env.example`, `inventory.example.yaml`) and add ignore rules so real secrets are never committed.

* Generate a detailed report (checked into repo under a `reports/` directory) containing:

  * Before/after inventory (what was found vs what remains).

  * Removal actions (files deleted/updated, containers/images targeted, credential purge steps).

  * Installation sources + verification approach per service.

  * Operational verification results (container states, healthcheck outcomes, watchdog behavior).

  * Final attestation: only the specified ten services remain referenced in-repo.

## Execution/Verification Notes (After You Approve This Plan)

* I will run a repository-wide scan again after edits to prove there are zero residual references.

* I will validate that the compose runtime honors resource limits (no assumptions).

* I will not claim any host-level “uninstalled” state unless the uninstall scripts are executed and their outputs are captured into the report.
