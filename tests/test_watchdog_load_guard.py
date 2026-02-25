import app.watchdog as watchdog


def _config_with_enabled(service_enable_key: str) -> dict[str, str]:
    cfg = {"ENABLE_WIPTER": "false", "ENABLE_UPROCK": "false", "ENABLE_MYSTERIUM": "false"}
    for key in watchdog.SERVICE_MAP.keys():
        cfg[key] = "false"
    cfg[service_enable_key] = "true"
    return cfg


def test_watchdog_skips_start_for_paused_service(monkeypatch):
    monkeypatch.setattr(watchdog, "load_config", lambda: _config_with_enabled("ENABLE_GRASS"))
    monkeypatch.setattr(watchdog, "load_load_guard_state", lambda: {"paused": ["grass"]})
    monkeypatch.setattr(watchdog, "get_containers", lambda: [{"name": "grass", "status": "exited"}])
    monkeypatch.setattr(watchdog, "get_wipter_details", lambda: {"status": "not_installed"})
    monkeypatch.setattr(watchdog, "get_uprock_details", lambda: {"status": "not_installed"})
    monkeypatch.setattr(watchdog, "is_systemd_unit_present", lambda _: False)

    calls = []

    def fake_control_container(service, action):
        calls.append((service, action))
        return True, "Success"

    monkeypatch.setattr(watchdog, "control_container", fake_control_container)
    monkeypatch.setattr(watchdog, "control_wipter", lambda _: (True, "Success"))
    monkeypatch.setattr(watchdog, "control_uprock", lambda _: (True, "Success"))

    watchdog.check_and_recover()
    assert ("grass", "start") not in calls


def test_watchdog_stops_running_disabled_service(monkeypatch):
    monkeypatch.setattr(watchdog, "load_config", lambda: _config_with_enabled("ENABLE_HONEYGAIN"))
    cfg = _config_with_enabled("ENABLE_HONEYGAIN")
    cfg["ENABLE_HONEYGAIN"] = "false"
    monkeypatch.setattr(watchdog, "load_config", lambda: cfg)
    monkeypatch.setattr(watchdog, "load_load_guard_state", lambda: {"paused": []})
    monkeypatch.setattr(watchdog, "get_containers", lambda: [{"name": "honeygain", "status": "running"}])
    monkeypatch.setattr(watchdog, "get_wipter_details", lambda: {"status": "not_installed"})
    monkeypatch.setattr(watchdog, "get_uprock_details", lambda: {"status": "not_installed"})
    monkeypatch.setattr(watchdog, "is_systemd_unit_present", lambda _: False)

    calls = []

    def fake_control_container(service, action):
        calls.append((service, action))
        return True, "Success"

    monkeypatch.setattr(watchdog, "control_container", fake_control_container)
    monkeypatch.setattr(watchdog, "control_wipter", lambda _: (True, "Success"))
    monkeypatch.setattr(watchdog, "control_uprock", lambda _: (True, "Success"))

    watchdog.check_and_recover()
    assert ("honeygain", "stop") in calls

