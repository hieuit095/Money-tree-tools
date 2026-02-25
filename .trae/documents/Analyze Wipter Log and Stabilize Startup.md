## Diagnosis
- “Last Apply Results” is rendered in [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L130-L147) as a plain list. When `last_apply.results` is long, it expands the page.
- The dashboard already uses Alpine.js (loaded via CDN) and Tailwind utilities, so we can implement collapse + scrolling without backend changes.

## UI Change (Dashboard)
- Update the “Last Apply Results” card in [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L130-L147) to:
  - Add a small “Hide/Show” toggle button in the header.
  - Persist the toggle state in `localStorage` so it stays collapsed across refreshes.
  - Wrap the results list in a container with a fixed max height and `overflow-y-auto` so long results scroll instead of creating a very long page.

## Preserve Configuration During Deployment
- Current remote deploy wipes `/opt/moneytree`, which can delete configuration because config is stored under the project root via `config_root()` (see [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L13-L29)).
- Implement a “preserve config” redeploy path that:
  - Backs up `/opt/moneytree/.env.enc` and `/opt/moneytree/last_apply.json` (if present) before wiping.
  - Deploys the new code.
  - Restores the backed-up files into the new `/opt/moneytree` with correct ownership.
  - Does not touch `/etc/moneytree/master.key` (used for encryption on Linux per [secret_store.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/secret_store.py#L18-L54)).
- This maintains current configuration + encrypted secrets while still doing a clean code redeploy.

## Rollout to Device
- Run the preserve-config redeploy against `192.168.1.15` (from [inventory.yaml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/inventory.yaml)).
- Verify on-device:
  - `income-manager.service` is active.
  - `ss -ltnp | grep :5000` shows the listener.
  - Dashboard is reachable and the “Last Apply Results” section is collapsible and scrollable.

## Verification (Local)
- Quick local checks:
  - Python compile for modified scripts.
  - Template renders without syntax errors.

If you confirm, I’ll implement the template changes and a preserve-config redeploy script/flag, then roll it to `192.168.1.15` without resetting your config.