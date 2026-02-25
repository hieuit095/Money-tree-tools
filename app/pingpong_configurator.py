import hashlib
import json
import os
import subprocess
import sys
from typing import Any

from app import runtime_state
from app.config_manager import config_root
from app.log_utils import truncate_utf8_text


def _pingpong_binary_path() -> str:
    return os.path.join(config_root(), "PINGPONG")


def _hash_payload(payload: Any) -> str:
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _run_pingpong(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
        combined = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        combined = truncate_utf8_text(combined, max_bytes=128 * 1024)
        if result.returncode == 0:
            return True, combined
        msg = combined or f"Exited with status {result.returncode}"
        return False, msg
    except Exception as e:
        return False, str(e)


def _build_depin_config(config: dict[str, str]) -> tuple[dict[str, dict[str, str]], list[str]]:
    errors: list[str] = []
    depins: dict[str, dict[str, str]] = {}

    key_0g = config.get("PINGPONG_0G_PRIVATE_KEY", "").strip()
    if key_0g:
        depins["0g"] = {"--0g": key_0g}

    aioz = config.get("PINGPONG_AIOZ_PRIV_KEY", "").strip()
    if aioz:
        depins["aioz"] = {"--aioz": aioz}

    grass_access = config.get("PINGPONG_GRASS_ACCESS", "").strip()
    grass_refresh = config.get("PINGPONG_GRASS_REFRESH", "").strip()
    if grass_access or grass_refresh:
        if not grass_access or not grass_refresh:
            errors.append("pingpong: grass requires both access and refresh tokens")
        else:
            depins["grass"] = {"--grass.access": grass_access, "--grass.refresh": grass_refresh}

    bm_email = config.get("PINGPONG_BLOCKMESH_EMAIL", "").strip()
    bm_pwd = config.get("PINGPONG_BLOCKMESH_PASSWORD", "").strip()
    if bm_email or bm_pwd:
        if not bm_email or not bm_pwd:
            errors.append("pingpong: blockmesh requires both email and password")
        else:
            depins["blockmesh"] = {"--blockmesh.email": bm_email, "--blockmesh.pwd": bm_pwd}

    dawn_email = config.get("PINGPONG_DAWN_EMAIL", "").strip()
    dawn_pwd = config.get("PINGPONG_DAWN_PASSWORD", "").strip()
    if dawn_email or dawn_pwd:
        if not dawn_email or not dawn_pwd:
            errors.append("pingpong: dawn requires both email and password")
        else:
            depins["dawn"] = {"--dawn.email": dawn_email, "--dawn.pwd": dawn_pwd}

    hemi_key = config.get("PINGPONG_HEMI_KEY", "").strip()
    if hemi_key:
        depins["hemi"] = {"--hemi": hemi_key}

    return depins, errors


def apply_pingpong_configuration(config: dict[str, str]) -> list[str]:
    if sys.platform != "linux":
        return ["pingpong: skipped (not supported on this platform)"]

    if config.get("ENABLE_PINGPONG", "false").lower() != "true":
        return []

    binary = _pingpong_binary_path()
    if not os.path.exists(binary):
        return [f"pingpong: missing binary at {binary}"]

    depins, errors = _build_depin_config(config)
    if errors:
        return errors
    if not depins:
        return ["pingpong: no depin configuration set"]

    desired_hashes = {name: _hash_payload(fields) for name, fields in depins.items()}
    state = runtime_state.load_pingpong_state() or {}
    previous = state.get("depins") if isinstance(state.get("depins"), dict) else {}
    previous_hashes = {k: v for k, v in previous.items() if isinstance(k, str) and isinstance(v, str)}

    changed = sorted([name for name, h in desired_hashes.items() if previous_hashes.get(name) != h])
    if not changed:
        return ["pingpong: depin configuration unchanged"]

    config_args: list[str] = [binary, "config", "set"]
    for depin, fields in sorted(depins.items()):
        for flag, value in sorted(fields.items()):
            config_args.append(f"{flag}={value}")

    ok, msg = _run_pingpong(config_args)
    if not ok:
        return [f"pingpong: config set failed: {msg}"]

    results: list[str] = []
    results.append(f"pingpong: config set -> OK ({', '.join(changed)})")

    for depin in changed:
        ok_stop, stop_msg = _run_pingpong([binary, "stop", f"--depins={depin}"])
        if not ok_stop:
            results.append(f"pingpong: stop depins={depin} -> {stop_msg}")
            continue
        ok_start, start_msg = _run_pingpong([binary, "start", f"--depins={depin}"])
        if ok_start:
            results.append(f"pingpong: start depins={depin} -> OK")
        else:
            results.append(f"pingpong: start depins={depin} -> {start_msg}")

    merged = runtime_state.load_pingpong_state() or {}
    if not isinstance(merged, dict):
        merged = {}
    merged["depins"] = desired_hashes
    runtime_state.save_pingpong_state(merged)
    return results
