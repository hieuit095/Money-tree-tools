## What’s Causing the Errors

* **`swapoff /dev/zram0 ... SIGKILL`** comes from Python raising `CalledProcessError` when `swapoff` is killed by the OS. On a 512MB device this usually happens when **zram swap is currently in use** and `swapoff` tries to move swapped pages back into RAM, triggering memory pressure/OOM, so the kernel kills `swapoff`.

* **“Network error applying ZRAM”** is consistent with the dashboard request to `POST /api/system/zram` not completing because the system becomes unstable (OOM / service restart / request timeout) while trying to apply ZRAM live.

## Immediate Workaround (No Code)

* Set ZRAM to **Auto (1/1 RAM)** (on 512MB this becomes 512MB minimum) and **reboot** the device. Applying at boot is safer because ZRAM is not heavily in use yet.

## Planned Code Changes

### 1) Make live ZRAM apply safe

* Update [zram\_manager.py](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/zram_manager.py) to read `/proc/swaps` and determine **zram0 used swap**.

* Change `apply_size_mb()` behavior:

  * If zram swap is active **and** used > 0 (or MemAvailable is very low), do **not** run `swapoff`.

  * Instead return a result like `{status: "pending_reboot", ...}` so the UI can tell the user to reboot.

  * If swap used is 0 (safe), proceed with current swapoff/reset/disksize/mkswap/swapon flow.

* Improve error reporting by catching `subprocess.CalledProcessError` and returning a clearer message (instead of a raw exception string).

### 2) Update dashboard messaging for ZRAM

* Update the ZRAM panel in [dashboard.html](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/app/templates/dashboard.html#L498-L583) so that when the backend returns `pending_reboot`, it shows “Saved; reboot required to apply safely.”

### 3) Update device IP in inventory

* Update [inventory.yaml](file:///c:/Users/USER/Documents/GitHub/Money-tree-tools/inventory.yaml) from `192.168.1.15` → `192.168.1.18` (credentials unchanged).

### 4) Roll the fix to the device while keeping config

* Redeploy to `192.168.1.18` using the preserve-config deploy path so `.env.enc` stays intact.

* Verify:

  * `income-manager.service` is active.

  * `/api/system/zram` GET works.

  * Applying ZRAM from the UI no longer hard-fails; when swap is in use it returns “pending reboot” instead of crashing.

## Outcome

* ZRAM changes will stop breaking the dashboard on low-RAM devices.

* Users will get a deterministic, safe flow: apply immediately only when safe; otherwise save + reboot.

* Repo inventory will match the device’s new IP.

