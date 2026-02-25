## Findings (Current vs Official)
- The official Bitping Docker guidance uses image `bitping/bitpingd:latest`, mounts the credentials directory to `/root/.bitpingd`, and supports login via env vars including `BITPING_MFA` (optional). 
- Your bundled IGM compose already uses `bitping/bitpingd` and mounts a named volume at `/root/.bitpingd`, which is aligned. [compose.hosting.yml:L133-L158](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.hosting.yml#L133-L158)
- However, your stack currently **does not pass `BITPING_MFA` into the container**, and your generated IGM env file also **does not export `BITPING_MFA`**, even though the dashboard has a `BITPING_MFA` field. [igm_mapping.py:L117-L143](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/igm_mapping.py#L117-L143), [config_manager.py:L409-L440](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L409-L440)

## Changes To Make
### 1) Pass MFA env var through end-to-end
- Add `BITPING_MFA` to the generated IGM env mapping so Docker Compose can see it. [igm_mapping.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/igm_mapping.py)
- Update the Bitping service in the bundled compose to include `BITPING_MFA: ${BITPING_MFA:-}` in the container environment. [compose.hosting.yml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.hosting.yml)

### 2) Make the image reference explicit (doc conformity)
- Change `image: bitping/bitpingd` to `image: bitping/bitpingd:latest` (functionally equivalent, but matches the official docs).

### 3) Improve UX guidance in the Bitping config panel
- Update the Bitping instructions to reflect the official guidance:
  - “Don’t run multiple Bitping instances pointing to the same credentials directory/volume.”
  - Clarify that `BITPING_MFA` is a current 2FA code (optional; only needed when the account uses 2FA).

## Verification
- Run unit tests.
- Smoke-check on `192.168.1.15`:
  - Confirm `BITPING_MFA` appears in the generated env file and is passed to the container.
  - Start Bitping and confirm it runs (or at minimum, errors are surfaced clearly in the UI/logs).

## Deployment
- Redeploy to `192.168.1.15` and restart the dashboard service.