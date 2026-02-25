## Goal
Add **WizardGain** to the supported services list, as requested and verified to be present in the IGM compose file.

## Changes
### 1. IGM Mapping (`app/igm_mapping.py`)
- Add `wizardgain` to `IGM_SERVICES` mapping:
  - `enable_key`: `ENABLE_WIZARDGAIN`
  - `profile_var`: `WIZARDGAIN`
  - `container_name`: `wizardgain`
- Update `build_igm_env` to include `WIZARDGAIN_EMAIL`.

### 2. Config Schema (`app/config_manager.py`)
- Add `ENABLE_WIZARDGAIN` to the list of required fields.
- Add a new section for WizardGain:
  - ID: `wizardgain`
  - Title: "WizardGain"
  - Instructions: "Requires an email address."
  - Field: `WIZARDGAIN_EMAIL` (Email).

### 3. Verification
- Manual verification via code review (new service added to mapping and config schema).
- No new native manager code needed as it's an IGM container service.

## Note
- The compose file shows `WIZARDGAIN_EMAIL` as the required environment variable.
