I will implement the P0 compliance hardening patch as requested.

### 1. Fix Config Persistence Gaps

**File:** `app/config_manager.py`

* Add `WIPTER_EMAIL`, `WIPTER_PASSWORD`, and `WIZARDGAIN_EMAIL` to the `get_required_fields()` list to ensure they are persisted to `.env.enc`.

### 2. Fix WizardGain Service Management

**File:** `app/docker_manager.py`

* Add `ENABLE_WIZARDGAIN` to `SERVICE_MAP` to ensure the WizardGain container is started/stopped correctly based on the config.

### 3. Fix Update/Restart Mechanism

**File:** `app/main.py`

* In `perform_update`, replace `sys.exit(0)` with `os._exit(0)` inside the background thread. This ensures the Python process actually terminates, allowing `systemd` to restart it.

### 4. Harden Security

**File:** `app/main.py`

* **Disable Debug Mode:** Change `app.run(host='0.0.0.0', port=5000, debug=True)` to `debug=False`.

### 5. Add Platform Gating

**Files:** `app/native_manager.py`, `app/zram_manager.py`

* **Native Manager:** Add a check for `sys.platform == 'linux'` in `is_systemd_unit_present`, `control_systemd_unit`, and other systemd-related functions. If not on Linux, return appropriate "not supported" statuses instead of attempting to run `systemctl`.

* **ZRAM Manager:** Add a check for `sys.platform == 'linux'` in `get_status` and `apply_size_mb`. Return safe default values (e.g., `swap_active=False`) or error messages on non-Linux platforms to prevent crashes when accessing `/sys` or `/proc`.

