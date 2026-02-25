## Goal
Update Wipter configuration and environment mapping to include the required Email and Password fields, as specified in the IGM documentation.

## Changes
### 1. Config Schema (`app/config_manager.py`)
- Locate the "wipter" service definition in `CONFIG_SECTIONS`.
- Add `WIPTER_EMAIL` and `WIPTER_PASSWORD` to its `fields` list.
- Mark the password field as `sensitive: True`.

### 2. IGM Mapping (`app/igm_mapping.py`)
- Update `build_igm_env()` to read `WIPTER_EMAIL` and `WIPTER_PASSWORD` from the loaded config.
- Map these values to the corresponding IGM environment variables (likely `WIPTER_EMAIL` and `WIPTER_PASSWORD`, matching the pattern of other services).

### 3. Verification
- Manual verification via code review (fields added, mapping implemented).
- Since we can't run the IGM tool interactively to verify the exact env var names it expects, we follow the established convention (e.g., `HONEYGAIN_EMAIL`, `PAWNS_EMAIL`) which matches IGM's typical `APPNAME_FIELD` pattern.

## Notes
- Wipter is currently treated as a native service in `native_manager.py` but the user is asking to configure it via the main IGM-style config (or at least provide the creds so IGM *could* run it if we switched, or just to store them).
- Wait, the user says "According to the instructions in... IGM... Wipter requires...".
- Our `igm_mapping.py` treats Wipter as an IGM service (`IGMServiceSpec` exists for it), but `native_manager.py` also exists.
- The IGM mapping `build_igm_env` currently *misses* Wipter creds.
- I will add them to `build_igm_env` so if/when IGM manages it (or if the native manager needs to read them from config), they are available.
- **Crucially**: The user specifically pointed out Wipter has "no configuration options" in the UI. Adding them to `config_manager.py` fixes the UI. Adding them to `igm_mapping.py` fixes the backend env generation.

## Plan Steps
1.  Modify `app/config_manager.py`: Add fields to `wipter` section.
2.  Modify `app/igm_mapping.py`: Add `WIPTER_EMAIL` and `WIPTER_PASSWORD` to the returned env dict.
3.  (Implicit) The `native_manager.py` might need to read these if it were launching the process itself with creds, but currently `native_manager` just starts/stops a systemd unit. The user's request is about *providing* the info (likely for IGM or just to have it stored). I will focus on the UI and IGM mapping as requested.
