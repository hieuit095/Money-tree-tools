## Goal
Modify the existing "one-button update" feature to fully comply with IGM's update guidelines:
1. Sync the project repository (`git pull`).
2. Sync the vendored `income-generator` submodule (`git submodule update --init --recursive`).
3. Explicitly restart the application (send success response → `sys.exit(0)` → systemd restart) to ensure all changes and config updates are applied.

## Changes
### 1. Backend (`app/main.py`)
- Add imports: `sys`, `threading`, `time`.
- Update `perform_update()` endpoint:
  - Keep the existing `git pull`.
  - Add `git submodule update --init --recursive` to ensure the backend library stays in sync.
  - Implement a "delayed exit" mechanism: spawn a background thread that sleeps for 1 second (to allow the JSON response to flush) and then calls `sys.exit(0)`.

### 2. Frontend (`app/templates/dashboard.html`)
- Update the success handler for the update button.
- Add a 5-second timeout after a successful update to reload the page (`window.location.reload()`), confirming the service has restarted and is back online.

## Verification
- Code review to ensure commands match the plan.
- Since we cannot push updates to the remote during this session, verification will rely on checking the implementation logic (commands + restart flow).
