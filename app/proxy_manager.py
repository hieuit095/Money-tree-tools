import os
import re
import subprocess

import docker

from app.igm_paths import igm_root
from app.log_utils import truncate_utf8_text


_ALLOWED_PROXY_PROTOCOLS = {"http", "socks4", "socks5", "ss", "relay"}
_PROXY_LINE_RE = re.compile(
    r"^(?P<proto>[a-z0-9]+)://"
    r"(?:(?P<user>[^:@/]+):(?P<pw>[^@/]+)@)?"
    r"(?P<host>(?:\[[^\]]+\]|[^:/?#]+)):(?P<port>\d+)"
    r"(?:[/?#].*)?$",
    re.IGNORECASE,
)


def _normalize_proxy_entries_text(value: str) -> str:
    text = (value or "").replace("\\n", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip() + ("\n" if lines else "")


def _validate_proxy_entries(text: str) -> tuple[bool, str]:
    if not text.strip():
        return False, "No proxy entries configured"
    active = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        m = _PROXY_LINE_RE.match(line)
        if not m:
            return False, f"Invalid proxy entry: {line}"
        proto = (m.group("proto") or "").lower()
        if proto not in _ALLOWED_PROXY_PROTOCOLS:
            return False, f"Unsupported proxy protocol: {proto}"
        port = int(m.group("port"))
        if port < 1 or port > 65535:
            return False, f"Invalid proxy port: {port}"
        active += 1
    if active <= 0:
        return False, "No active proxy entries (all entries are commented out)"
    return True, "OK"


def _build_env_deploy_proxy_text(config: dict[str, str]) -> tuple[bool, str, str]:
    mapping = {
        "REPOCKET": config.get("ENABLE_PROXY_REPOCKET", "false").lower() == "true",
        "EARNFM": config.get("ENABLE_PROXY_EARNFM", "false").lower() == "true",
        "PACKETSHARE": config.get("ENABLE_PROXY_PACKETSHARE", "false").lower() == "true",
    }
    if not any(mapping.values()):
        return False, "No proxy applications selected", ""
    lines = [f"{name}={'ENABLED' if enabled else 'DISABLED'}" for name, enabled in sorted(mapping.items())]
    return True, "OK", "\n".join(lines) + "\n"


def _run_igm_proxy_cmd(subcommand: str, *, timeout_s: float) -> str:
    root = igm_root()
    if os.name == "nt":
        cmd = ["cmd", "/c", os.path.join(root, "start.bat"), "proxy", subcommand]
    else:
        cmd = ["sh", os.path.join(root, "start.sh"), "proxy", subcommand]
    result = subprocess.run(
        cmd,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        input="Y\n\n\n",
        timeout=timeout_s,
    )
    out = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    return truncate_utf8_text(out.strip(), max_bytes=5 * 1024 * 1024)


def _proxy_containers_exist() -> bool:
    try:
        client = docker.from_env()
        for c in client.containers.list(all=True):
            labels = getattr(c, "labels", {}) or {}
            if labels.get("project") == "proxy":
                return True
        return False
    except Exception:
        return False


def apply_proxy_configuration(config: dict[str, str]) -> tuple[bool, str]:
    enabled = config.get("ENABLE_MULTI_PROXY", "false").lower() == "true"
    root = igm_root()
    proxies_path = os.path.join(root, "proxies.txt")
    deploy_path = os.path.join(root, ".env.deploy.proxy")

    proxy_exists = _proxy_containers_exist()

    if not enabled:
        if proxy_exists:
            out = _run_igm_proxy_cmd("remove", timeout_s=1800.0)
            return True, out or "Proxy applications removed"
        return True, "Multi-Proxy disabled"

    normalized = _normalize_proxy_entries_text(config.get("PROXY_ENTRIES", ""))
    ok, msg = _validate_proxy_entries(normalized)
    if not ok:
        return False, msg

    apps_ok, apps_msg, deploy_text = _build_env_deploy_proxy_text(config)
    if not apps_ok:
        return False, apps_msg

    current_proxies = open(proxies_path, "r", encoding="utf-8").read() if os.path.exists(proxies_path) else ""
    current_deploy = open(deploy_path, "r", encoding="utf-8").read() if os.path.exists(deploy_path) else ""

    needs_redeploy = (current_proxies != normalized) or (current_deploy != deploy_text) or (not proxy_exists)

    if current_proxies != normalized:
        open(proxies_path, "w", encoding="utf-8", newline="\n").write(normalized)
    if current_deploy != deploy_text:
        open(deploy_path, "w", encoding="utf-8", newline="\n").write(deploy_text)

    if not needs_redeploy:
        return True, "Multi-Proxy already configured"

    if proxy_exists:
        _run_igm_proxy_cmd("remove", timeout_s=1800.0)

    out = _run_igm_proxy_cmd("install", timeout_s=3600.0)
    return True, out or "Proxy applications installed"
