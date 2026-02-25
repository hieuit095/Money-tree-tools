import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from app.igm_paths import igm_root


class IGMError(RuntimeError):
    pass


class IGMTimeoutError(IGMError):
    pass


@dataclass(frozen=True)
class IGMResult:
    returncode: int
    output: str


_OUTPUT_LIMIT_BYTES = 5 * 1024 * 1024


def _decode_output(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return repr(data)


def _run_capped_output(
    cmd: Sequence[str],
    *,
    cwd: str,
    env: Mapping[str, str],
    timeout_s: float,
    output_limit_bytes: int = _OUTPUT_LIMIT_BYTES,
) -> IGMResult:
    proc = subprocess.Popen(
        list(cmd),
        cwd=cwd,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert proc.stdout is not None

    buf = bytearray()
    lock = threading.Lock()

    def reader() -> None:
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            with lock:
                remaining = output_limit_bytes - len(buf)
                if remaining > 0:
                    buf.extend(chunk[:remaining])

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        finally:
            raise IGMTimeoutError(f"Command timed out after {timeout_s}s: {cmd}")
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        t.join(timeout=2)

    with lock:
        out = bytes(buf)

    return IGMResult(returncode=proc.returncode or 0, output=_decode_output(out))


def _igm_entrypoint() -> list[str]:
    root = Path(igm_root())
    if os.name == "nt":
        start_bat = root / "start.bat"
        return ["cmd", "/c", str(start_bat)]
    start_sh = root / "start.sh"
    return ["sh", str(start_sh)]


def ensure_igm_present() -> None:
    root = Path(igm_root())
    if not root.exists():
        raise IGMError(f"IGM root not found: {root}")
    if os.name == "nt":
        if not (root / "start.bat").exists():
            raise IGMError(f"IGM entrypoint not found: {root / 'start.bat'}")
        return
    if not (root / "start.sh").exists():
        raise IGMError(f"IGM entrypoint not found: {root / 'start.sh'}")


def run_igm(args: Sequence[str], *, timeout_s: float = 180.0) -> IGMResult:
    ensure_igm_present()
    root = igm_root()
    cmd = _igm_entrypoint() + list(args)

    env = os.environ.copy()
    start = time.time()
    result = _run_capped_output(cmd, cwd=root, env=env, timeout_s=timeout_s)
    duration = time.time() - start
    if result.returncode != 0:
        raise IGMError(f"IGM command failed rc={result.returncode} in {duration:.2f}s: {result.output}")
    return result


def igm_version() -> str:
    return run_igm(["version"], timeout_s=30.0).output.strip()


def igm_show(group: str | None = None) -> str:
    args: list[str] = ["show"]
    if group:
        args.append(group)
    return run_igm(args, timeout_s=60.0).output


def igm_logs(name: str) -> str:
    return run_igm(["logs", name], timeout_s=60.0).output


def igm_start(names: Sequence[str] | None = None) -> None:
    args: list[str] = ["start"]
    if names:
        args.extend(list(names))
    run_igm(args, timeout_s=300.0)


def igm_stop(names: Sequence[str] | None = None) -> None:
    args: list[str] = ["stop"]
    if names:
        args.extend(list(names))
    run_igm(args, timeout_s=300.0)


def igm_restart(name: str) -> None:
    run_igm(["restart", name], timeout_s=300.0)


def igm_remove(names: Sequence[str] | None = None) -> None:
    args: list[str] = ["remove"]
    if names:
        args.extend(list(names))
    run_igm(args, timeout_s=300.0)
