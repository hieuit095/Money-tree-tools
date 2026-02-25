import threading
import time
from typing import Any

from app.docker_manager import apply_docker_configuration
from app.native_manager import apply_native_configuration
from app.runtime_state import load_last_apply, save_last_apply

_lock = threading.Lock()
_state: dict[str, Any] = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "message": None,
}


def get_apply_status() -> dict[str, Any]:
    with _lock:
        state = dict(_state)
    state["last_apply"] = load_last_apply()
    return state


def start_apply() -> bool:
    with _lock:
        if _state.get("running"):
            return False
        _state["running"] = True
        _state["started_at"] = int(time.time())
        _state["finished_at"] = None
        _state["message"] = "running"

    def _runner() -> None:
        results: list[str] = []
        try:
            try:
                results.extend(apply_docker_configuration())
            except Exception as e:
                results.append(f"docker: ERROR -> {str(e)}")
            try:
                results.extend(apply_native_configuration())
            except Exception as e:
                results.append(f"native: ERROR -> {str(e)}")
            try:
                save_last_apply(results)
            except Exception:
                pass
        finally:
            with _lock:
                _state["running"] = False
                _state["finished_at"] = int(time.time())
                _state["message"] = "done"

    threading.Thread(target=_runner, daemon=True).start()
    return True
