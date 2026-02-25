## Why You Still Only See “Device Key”
- The UI renders Pingpong fields directly from `get_config_sections()` and `section.fields` in the server-rendered template ([main.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/main.py#L69-L76), [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L628-L739)).
- In the current repo, Pingpong’s section already includes the new depin fields (0G/AIOZ/Grass/BlockMesh/DAWN/Hemi) in [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L131-L180) and [config_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/config_manager.py#L639-L657).
- If your dashboard at `192.168.1.18:5000` still shows only “Device Key”, that device is almost certainly running an older build (or hasn’t restarted to load updated Python/template code).

## What I Will Do Next (After You Confirm)
1. Update the remote device’s code to the latest version (either via the dashboard’s update endpoints or the existing deploy script).
2. Restart `income-manager.service` so Flask reloads `config_manager.py` and the updated [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html).
3. Verify in the browser (hard refresh) that the Pingpong modal now shows the new fields.
4. Trigger an apply once with sample non-secret placeholders removed, ensuring the apply path is still healthy.

## Notes
- No frontend “cache-busting” is required for the modal content because it’s rendered server-side; a service restart is what matters most.
- The new fields are persisted encrypted in `.env.enc` because they’re part of `get_required_fields()` (same mechanism used by other secrets).
