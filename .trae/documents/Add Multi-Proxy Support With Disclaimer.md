## Goal
- Add multi-proxy deployment support (IGM-style) and show a clear disclaimer whenever users enable it.

## Requirements From IGM Docs
- Proxy entries are a newline-separated list using schemas:
  - `protocol://ip:port`
  - `protocol://user:password@ip:port`
- Supported protocol types include HTTP / Socks4 / Socks5 / Shadowsocks / Relay.
- Proxy deployments are managed separately from non-proxy deployments.
- Proxy scaling can trigger account bans; recommended to keep device count reasonable and respect each service’s ToS.

## UI Changes
- Add a new “Multi-Proxy” configuration section with:
  - Enable toggle (e.g. `ENABLE_MULTI_PROXY`).
  - Textarea for proxy entries (stored encrypted alongside other config).
  - Checklist for which apps to deploy via proxy (at minimum: Repocket, EarnFM, PacketShare; optionally extend later).
  - A prominent disclaimer that most services prohibit proxies, plus best-practice guidance.
- When the enable toggle is turned on, show an additional inline warning panel (and a confirmation dialog) before saving.

## Backend Changes
- Extend config schema:
  - Add required fields for `ENABLE_MULTI_PROXY`, `PROXY_ENTRIES`, and `ENABLE_PROXY_<APP>` flags.
- Implement proxy apply/remove logic (new module, e.g. `app/proxy_manager.py`):
  - On enable + save:
    - Validate proxy entry format (basic parsing, ignore comment lines starting with `#`).
    - Write `third_party/income-generator/proxies.txt` from the encrypted config value.
    - Generate `third_party/income-generator/.env.deploy.proxy` enabling only the selected proxy apps.
    - Trigger proxy install using IGM’s existing proxy engine (`start.sh proxy install`) in non-interactive mode by pre-supplying stdin and adding a long timeout.
  - On disable + save:
    - Trigger proxy removal (`start.sh proxy remove`) non-interactively.
- Update container inventory endpoints so proxy containers can be displayed and logged:
  - Include containers with label `project=proxy` in `/api/containers`.
  - Logs already work for arbitrary container names (e.g. `repocket-1`), so the existing Logs page will automatically support proxy containers once they appear in the container list.

## Disclaimer Content
- Displayed whenever multi-proxy is enabled:
  - “Most services prohibit proxy use; using proxies can lead to account termination and/or IP bans. Use private residential proxies and respect each service’s Terms of Service.”
  - Mention that scaling too aggressively (e.g., 50–100+) increases ban risk.

## Tests
- Add unit tests for:
  - Proxy entry parsing/validation and comment stripping.
  - `.env.deploy.proxy` generation for selected apps.
  - Ensuring disabling triggers the expected removal path (mocking subprocess runner).

## Verification
- Run the full test suite.
- Manual smoke test:
  - Enable multi-proxy with 1–2 proxy lines.
  - Verify proxy containers appear (names with `-1`, `-2`, etc.).
  - Verify Logs page shows proxy container logs via `docker logs <name>` behavior.
