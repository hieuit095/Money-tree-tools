## Goal
- Keep default ZRAM behavior at 50% of detected RAM.
- Limit selectable/valid ZRAM sizes to a maximum of 100% of detected RAM (e.g., 1GB RAM → max 1024MB option; 512MB RAM → max 512MB option).

## Current Behavior (What We’ll Change)
- Dashboard UI hardcodes sizes up to 4GB and shows Auto (½ RAM).
- Backend validation allows only the static list `[512, 1024, 1536, 2048, 3072, 4096]` regardless of device RAM.
- Install-time optimize script uses a different default (60% for ≤2GB).

## Backend Changes
- Update [zram_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/zram_manager.py):
  - Keep the existing base list as `ALLOWED_ZRAM_SIZES_MB` for “known-good” sizes.
  - Compute `allowed_sizes_mb` dynamically as `sizes <= mem_total_mb`.
  - Update `validate_zram_size_mb()` to reject sizes that exceed `mem_total_mb` (in addition to not being in the base list).
  - Ensure `compute_auto_size_bytes()` stays at 50% of RAM (already is).

## Dashboard UI Changes
- Update the ZRAM dropdown in [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L498-L583):
  - Replace hardcoded size options with a dynamic list based on `status.allowed_sizes_mb`.
  - Rename Auto label to “Auto (50% RAM)” to match the intended default.

## Install-Time Optimization Alignment
- Update [scripts/optimize.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/scripts/optimize.py):
  - Change its default ZRAM sizing to 50% of RAM (remove the ≤2GB → 60% special-case).
  - Ensure any explicit `ZRAM_SIZE_MB` env override is also capped at ≤ 100% of detected RAM.

## Tests / Validation
- Update any unit tests that reference `ALLOWED_ZRAM_SIZES_MB` only if required by refactors.
- Run python compile + existing tests locally.

## Rollout
- Redeploy to the device at `192.168.1.18` using the preserve-config deploy path.
- Verify on device:
  - `GET /api/system/zram` reports `allowed_sizes_mb` capped at RAM.
  - UI only shows sizes up to 100% RAM.
  - Auto applies as 50% RAM.