import json
import os
import tempfile

import yaml

from app import config_manager


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _igm_root() -> str:
    return os.path.join(_repo_root(), "third_party", "income-generator")


def _igm_compose_services() -> dict[str, dict]:
    compose_dir = os.path.join(_igm_root(), "compose")
    services: dict[str, dict] = {}
    for name in [
        "compose.yml",
        "compose.unlimited.yml",
        "compose.hosting.yml",
        "compose.local.yml",
        "compose.single.yml",
        "compose.service.yml",
    ]:
        path = os.path.join(compose_dir, name)
        compose = yaml.safe_load(open(path, "r", encoding="utf-8"))
        for svc_name, svc in (compose.get("services") or {}).items():
            services[svc_name] = svc
    return services


def test_igm_compose_contains_required_services():
    services = _igm_compose_services()
    required = {
        "honeygain",
        "traffmonetizer",
        "packetstream",
        "packetshare",
        "repocket",
        "earnfm",
        "grass",
        "mysterium",
        "pawns",
        "proxyrack",
        "bitping",
    }
    assert required.issubset(set(services.keys()))

    for svc_name in required:
        svc = services[svc_name]
        labels = svc.get("labels") or []
        assert isinstance(labels, list)
        assert "project=standard" in labels


def test_config_sections_cover_required_services():
    sections = config_manager.get_config_sections()
    ids = [s["id"] for s in sections]
    required_service_sections = {
        "honeygain",
        "traffmonetizer",
        "packetstream",
        "packetshare",
        "repocket",
        "earnfm",
        "grass",
        "mysterium",
        "pawns",
        "proxyrack",
        "bitping",
        "wipter",
        "uprock",
        "pingpong",
    }
    assert "dashboard-access" in ids
    assert required_service_sections.issubset(set(ids))


def test_encrypted_config_round_trip_without_plaintext_env_file():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MONEYTREE_CONFIG_DIR"] = tmp
        os.environ["MONEYTREE_SECRET_DIR"] = os.path.join(tmp, "secrets")

        config_manager.save_config(
            {
                "WEB_USERNAME": "user",
                "WEB_PASSWORD": "pass",
                "DEVICE_NAME": "device",
                "ENABLE_HONEYGAIN": "false",
                "ENABLE_MYSTERIUM": "false",
                "ENABLE_PAWNS": "false",
                "ENABLE_PROXYRACK": "false",
                "ENABLE_BITPING": "false",
                "ENABLE_WIPTER": "false",
            }
        )

        assert os.path.exists(os.path.join(tmp, ".env.enc"))
        assert not os.path.exists(os.path.join(tmp, ".env"))
        assert os.path.exists(os.path.join(tmp, "secrets", "master.key"))

        loaded = config_manager.load_config()
        assert loaded["WEB_USERNAME"] == "user"
        assert loaded["WEB_PASSWORD"] == "pass"
        assert loaded["DEVICE_NAME"] == "device"


def test_igm_apps_json_covers_required_services():
    apps_path = os.path.join(_igm_root(), "apps.json")
    apps = json.loads(open(apps_path, "r", encoding="utf-8").read())
    names = {str(a.get("name", "")).upper() for a in apps}
    required = {
        "HONEYGAIN",
        "TRAFFMONETIZER",
        "PACKETSTREAM",
        "PACKETSHARE",
        "REPOCKET",
        "EARNFM",
        "GRASS",
        "MYSTERIUM",
        "PAWNS",
        "PROXYRACK",
        "BITPING",
        "WIPTER",
    }
    assert required.issubset(names)
