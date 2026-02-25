## What’s Happening
- **Display 99 lock conflict**: the Wipter container starts an X server (likely Xvfb) on `:99`. If the container crashes/restarts without being recreated, `/tmp/.X99-lock` can persist inside the same container filesystem and the next start fails.
- **`nice: cannot set niceness`**: the container is trying to adjust process priority; Docker blocks that unless the container has `SYS_NICE` capability.

## Repo Findings
- Wipter is defined in [compose.local.yml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/third_party/income-generator/compose/compose.local.yml#L181-L207) as `image: ghcr.io/xterna/wipter`.
- Service start/recovery is driven by [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py) and watchdog recovery in [watchdog.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/watchdog.py).
- Current recovery path can call Docker SDK `container.start()` without recreating the container, which does **not** clear stale `/tmp/.X99-lock`.

## Planned Changes
### 1) Allow Wipter to change niceness
- Update the Wipter compose definition to add `cap_add: ["SYS_NICE"]`.
- (Optional) If we see additional needs later, we can extend capabilities, but we’ll start minimal.

### 2) Make Wipter recovery recreate the container when it’s not running
- Update [docker_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/docker_manager.py) so that when starting **wipter** and the container exists but is in a bad state (e.g. `exited`, `restarting`, `dead`), it **removes the container** and uses `docker compose up -d --force-recreate wipter`.
- This clears stale `/tmp/.X99-lock` because the container filesystem is replaced.

### 3) Verification
- Re-run the service start from the UI / watchdog path and verify:
  - Wipter container reaches `running`.
  - Logs no longer show `Server is already active for display 99`.
  - `nice: cannot set niceness` is gone (or reduced to non-fatal warnings).

## Rollback
- Revert the compose change (remove `cap_add`) and revert the `docker_manager.py` recreate-on-start logic.

If you confirm, I’ll implement the code/compose changes and run a quick local sanity check of the compose generation logic.