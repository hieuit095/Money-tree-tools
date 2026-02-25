import json
import os
import socket
import subprocess
import time
import urllib.request

import yaml


REQUIRED_SERVICES = [
    "honeygain",
    "traffmonetizer",
    "mysterium",
    "pawns",
    "packetstream",
    "packetshare",
    "repocket",
    "earnfm",
    "grass",
    "proxyrack",
    "bitping",
    "wizardgain",
    "wipter",
    "uprock",
]


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def _systemd_status(unit: str) -> dict:
    if not shutil_which("systemctl"):
        return {"installed": False, "status": "systemctl_unavailable"}
    status = _run(["systemctl", "is-active", unit])
    if status.returncode == 0:
        return {"installed": True, "status": "running"}
    present = _run(["systemctl", "status", unit])
    if present.returncode in (0, 3):
        return {"installed": True, "status": "stopped"}
    return {"installed": False, "status": "not_installed"}


def shutil_which(cmd: str) -> str | None:
    try:
        import shutil

        return shutil.which(cmd)
    except Exception:
        return None


def check_mysterium_health() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:4050/healthcheck", timeout=5) as resp:
            return {"ok": getattr(resp, "status", 200) == 200}
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def main() -> int:
    igm_root = os.path.join(_repo_root(), "third_party", "income-generator")
    compose_dir = os.path.join(igm_root, "compose")
    compose_services: set[str] = set()
    for name in [
        "compose.yml",
        "compose.unlimited.yml",
        "compose.hosting.yml",
        "compose.local.yml",
        "compose.single.yml",
        "compose.service.yml",
    ]:
        compose = yaml.safe_load(open(os.path.join(compose_dir, name), "r", encoding="utf-8"))
        compose_services.update(set((compose.get("services") or {}).keys()))

    expected_compose = set(REQUIRED_SERVICES) - {"wipter", "uprock"}
    inventory_ok = expected_compose.issubset(compose_services)

    try:
        apps = json.loads(open(os.path.join(igm_root, "apps.json"), "r", encoding="utf-8").read())
        app_names = {str(a.get("name", "")).upper() for a in apps}
        igm_apps_ok = {
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
            "WIZARDGAIN",
            "WIPTER",
        }.issubset(app_names)
    except Exception as exc:
        igm_apps_ok = False
        app_names = set()

    report: dict = {
        "timestamp": time.time(),
        "inventory_ok": inventory_ok,
        "compose_services": sorted(compose_services),
        "expected_compose_services": sorted(expected_compose),
        "igm_apps_ok": igm_apps_ok,
        "igm_app_names": sorted(app_names),
        "docker": {"available": False},
        "native": {"wipter": _systemd_status("wipter.service"), "uprock": _systemd_status("uprock.service")},
        "mysterium_health": check_mysterium_health(),
        "host": {"hostname": socket.gethostname()},
    }

    try:
        import docker

        client = docker.from_env()
        report["docker"]["available"] = True
        containers = []
        for c in client.containers.list(all=True):
            containers.append({"name": c.name, "status": c.status})
        report["docker"]["containers"] = containers
    except Exception as exc:
        report["docker"]["error"] = repr(exc)

    reports_dir = os.path.join(_repo_root(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    out_path = os.path.join(reports_dir, "service-verification.json")
    open(out_path, "w", encoding="utf-8", newline="\n").write(json.dumps(report, indent=2, sort_keys=True))
    return 0 if (inventory_ok and igm_apps_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
