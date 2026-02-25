## Diagnosis
- The “DISABLED” label shown next to the service name is derived from `c.enabled` (your saved config: `ENABLE_*`).
- The “Running” status badge is derived from the actual Docker container state (`c.status`).
- When containers are running even though the config is disabled (or vice‑versa), the UI currently shows both values without explaining that they represent **different concepts**, which looks inconsistent.

Code path:
- UI badge logic: [dashboard.html:L807-L863](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L807-L863)
- `enabled` is computed from config keys in `/api/containers`: [main.py:L81-L112](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L81-L112)

## Changes I Will Make
### 1) Make the label explicit and mismatch-aware
- Replace the current `ENABLED/DISABLED` badge with a **config/desire** badge:
  - If `enabled=true`: show “Enabled” (green)
  - If `enabled=false` and `status=running`: show “Config Disabled” (amber) to highlight a mismatch
  - If `enabled=true` and `status!=running` (and not `not_installed`): show “Enabled (Stopped)” (amber)
  - If `enabled=false` and not running: show “Disabled” (slate)

This keeps the UI **accurate** (it doesn’t lie about config) while making it **consistent** (it’s clear what the label means and flags mismatches).

### 2) Add a short mismatch detail line (optional but recommended)
- When a mismatch is detected, append a small gray line under the service name like:
  - “configured disabled but running”
  - “configured enabled but stopped”

This avoids confusion without adding new columns.

### 3) Verify
- Smoke-check that a running-but-disabled container now displays “Config Disabled” (amber) rather than plain “DISABLED”.
- Confirm enabled-but-stopped services display “Enabled (Stopped)”.

## Files To Change
- Update the `enabledBadge` construction inside [dashboard.html:L807-L863](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L807-L863)

After you confirm, I’ll implement the UI changes and redeploy to `192.168.1.15` for verification.