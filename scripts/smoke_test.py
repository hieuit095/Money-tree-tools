from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    title: str
    details: str = ""


def _run(cmd: Sequence[str], *, timeout_s: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=os.environ.copy(),
    )


def _fmt_cmd(cmd: Sequence[str]) -> str:
    return " ".join(cmd)


def _ok(title: str, details: str = "") -> CheckResult:
    return CheckResult(ok=True, title=title, details=details)


def _fail(title: str, details: str = "") -> CheckResult:
    return CheckResult(ok=False, title=title, details=details)


def check_paths(repo_root: Path) -> Iterable[CheckResult]:
    yield _ok("Repo root", str(repo_root))

    setup_sh = repo_root / "setup.sh"
    if not setup_sh.is_file():
        yield _fail("setup.sh present", f"Missing: {setup_sh}")
    else:
        yield _ok("setup.sh present")

    requirements = repo_root / "requirements.txt"
    if not requirements.is_file():
        yield _fail("requirements.txt present", f"Missing: {requirements}")
    else:
        yield _ok("requirements.txt present")

    igm_root = repo_root / "third_party" / "income-generator"
    if not igm_root.is_dir():
        yield _fail("Git submodule present", f"Missing directory: {igm_root}")
    else:
        children = [p for p in igm_root.iterdir() if p.name not in {".git"}]
        if not children:
            yield _fail("Git submodule initialized", f"Directory exists but appears empty: {igm_root}")
        else:
            yield _ok("Git submodule initialized", str(igm_root))


def check_python_imports() -> Iterable[CheckResult]:
    modules = [
        "flask",
        "docker",
        "psutil",
        "cryptography",
        "yaml",
        "dotenv",
    ]

    failures: list[str] = []
    for m in modules:
        try:
            __import__(m)
        except Exception as e:
            failures.append(f"{m}: {type(e).__name__}: {e}")

    if failures:
        yield _fail("Python dependencies importable", "\n".join(failures))
    else:
        yield _ok("Python dependencies importable")


def check_docker() -> Iterable[CheckResult]:
    try:
        import docker
    except Exception as e:
        yield _fail("Docker SDK importable", f"{type(e).__name__}: {e}")
        return

    try:
        client = docker.from_env()
        client.ping()
        yield _ok("Docker daemon reachable (SDK ping)")
    except Exception as e:
        yield _fail("Docker daemon reachable (SDK ping)", f"{type(e).__name__}: {e}")

    proc = _run(["docker", "compose", "version"], timeout_s=15)
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        yield _fail(
            "docker compose available",
            f"Command failed: {_fmt_cmd(['docker','compose','version'])}\nexit={proc.returncode}\nstdout={stdout}\nstderr={stderr}",
        )
    else:
        yield _ok("docker compose available", (proc.stdout or "").strip())


def check_systemd_units() -> Iterable[CheckResult]:
    if platform.system() != "Linux":
        yield _ok("systemd checks skipped", "Non-Linux host")
        return

    if not Path("/bin/systemctl").exists() and not Path("/usr/bin/systemctl").exists():
        yield _fail("systemctl present", "systemctl not found at /bin/systemctl or /usr/bin/systemctl")
        return

    units = [
        "income-manager.service",
        "moneytree-zram.service",
        "moneytree-maintenance.timer",
        "pingpong.service",
    ]

    for unit in units:
        show = _run(["systemctl", "show", unit, "--no-pager"], timeout_s=10)
        if show.returncode != 0:
            stderr = (show.stderr or "").strip()
            yield _fail(f"systemd unit present: {unit}", stderr or f"exit={show.returncode}")
            continue

        yield _ok(f"systemd unit present: {unit}")

        active = _run(["systemctl", "is-active", unit, "--quiet"], timeout_s=10)
        if active.returncode == 0:
            yield _ok(f"systemd unit active: {unit}")
        else:
            yield _ok(f"systemd unit not active: {unit}", "Not necessarily an error (depends on config)")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    checks: list[CheckResult] = []
    checks.extend(list(check_paths(repo_root)))
    checks.extend(list(check_python_imports()))
    checks.extend(list(check_docker()))
    checks.extend(list(check_systemd_units()))

    failures = [c for c in checks if not c.ok]

    for c in checks:
        status = "OK" if c.ok else "FAIL"
        line = f"[{status}] {c.title}"
        print(line)
        if c.details:
            print(c.details.rstrip())

    if failures:
        print(f"\nSmoke test failed: {len(failures)} checks failed.", file=sys.stderr)
        return 1

    print("\nSmoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
