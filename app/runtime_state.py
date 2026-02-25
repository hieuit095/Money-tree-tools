import json
import os
import time
from typing import Any

from app.config_manager import config_root


_LAST_APPLY_FILE = "last_apply.json"
_LOAD_GUARD_FILE = "load_guard.json"
_PINGPONG_FILE = "pingpong.json"


def _state_path(filename: str) -> str:
    return os.path.join(config_root(), filename)


def save_last_apply(results: list[str]) -> None:
    payload = {
        "ts": int(time.time()),
        "results": list(results),
    }
    path = _state_path(_LAST_APPLY_FILE)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    if os.name == "posix":
        os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def load_last_apply() -> dict[str, Any] | None:
    path = _state_path(_LAST_APPLY_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        ts = data.get("ts")
        results = data.get("results")
        if not isinstance(ts, int) or not isinstance(results, list):
            return None
        cleaned: list[str] = []
        for item in results:
            if isinstance(item, str):
                cleaned.append(item)
        return {"ts": ts, "results": cleaned}
    except Exception:
        return None


def save_load_guard_state(state: dict[str, Any]) -> None:
    payload = dict(state)
    payload["ts"] = int(time.time())
    path = _state_path(_LOAD_GUARD_FILE)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    if os.name == "posix":
        os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def load_load_guard_state() -> dict[str, Any] | None:
    path = _state_path(_LOAD_GUARD_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_pingpong_state(state: dict[str, Any]) -> None:
    payload = dict(state)
    payload["ts"] = int(time.time())
    path = _state_path(_PINGPONG_FILE)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    if os.name == "posix":
        os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, path)


def load_pingpong_state() -> dict[str, Any] | None:
    path = _state_path(_PINGPONG_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None
