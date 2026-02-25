I will add the Peer2Profit service to the project by updating the configuration, Docker management, and IGM mapping files.

### 1. Update `app/config_manager.py`
*   Add `PEER2PROFIT_EMAIL` and `ENABLE_PEER2PROFIT` to the `get_required_fields()` list.
*   Add a new configuration section for "Peer2Profit" in `get_config_sections()`, including:
    *   Title: "Peer2Profit"
    *   Enable key: `ENABLE_PEER2PROFIT`
    *   Field: `PEER2PROFIT_EMAIL` (Label: Email, Sensitive: False)

### 2. Update `app/docker_manager.py`
*   Add `"ENABLE_PEER2PROFIT": "peer2profit"` to the `SERVICE_MAP` dictionary. This ensures the dashboard can start/stop the container.

### 3. Update `app/igm_mapping.py`
*   Add `peer2profit` to `IGM_SERVICES` with:
    *   `enable_key="ENABLE_PEER2PROFIT"`
    *   `profile_var="PEER2PROFIT"`
    *   `container_name="peer2profit"`
*   Update `build_igm_env` to map the application config `PEER2PROFIT_EMAIL` to the IGM environment variable `P2PROFIT_EMAIL`, which the compose file expects.
