import argparse
import os
import shlex
import time

import paramiko


def run(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return exit_status, out, err


def run_sudo(ssh: paramiko.SSHClient, password: str, command: str, *, allow_failure: bool) -> tuple[int, str, str]:
    wrapped = "sudo -S -p '' bash -c " + shlex.quote(command)
    stdin, stdout, stderr = ssh.exec_command(wrapped)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.close()
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if exit_status != 0 and not allow_failure:
        raise RuntimeError(f"remote_command_failed: exit={exit_status}, stderr={err.strip()}")
    return exit_status, out, err


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("password")
    args = parser.parse_args()

    output_path = "remote_recover_output.txt"
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("")

    def log(line: str) -> None:
        print(line, flush=True)
        with open(output_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    log(f"Connecting to {args.user}@{args.host}...")
    ssh.connect(args.host, username=args.user, password=args.password, timeout=20)

    log("Stopping any in-progress setup.sh processes...")
    run_sudo(ssh, args.password, "pkill -f 'setup\\.sh' 2>/dev/null || true", allow_failure=True)
    time.sleep(1)

    log("Running setup.sh with logging...")
    run_sudo(
        ssh,
        args.password,
        "cd /opt/moneytree && sed -i 's/\\r$//' setup.sh && chmod +x setup.sh",
        allow_failure=False,
    )
    run_sudo(
        ssh,
        args.password,
        "cd /opt/moneytree && ./setup.sh > setup.log 2>&1",
        allow_failure=False,
    )

    log("Starting containers (best effort)...")
    run_sudo(
        ssh,
        args.password,
        "cd /opt/moneytree && docker compose up -d > compose_up.log 2>&1 || true",
        allow_failure=True,
    )

    _, svc_active, _ = run(ssh, "systemctl is-active income-manager.service 2>/dev/null || echo inactive")
    log(f"income-manager.service: {svc_active.strip()}")

    _, setup_tail, _ = run_sudo(
        ssh,
        args.password,
        "if [ -f /opt/moneytree/setup.log ]; then tail -n 80 /opt/moneytree/setup.log; else echo NO_SETUP_LOG; fi",
        allow_failure=True,
    )
    log("setup.log tail:")
    log(setup_tail.rstrip("\n"))

    _, compose_tail, _ = run_sudo(
        ssh,
        args.password,
        "if [ -f /opt/moneytree/compose_up.log ]; then tail -n 80 /opt/moneytree/compose_up.log; else echo NO_COMPOSE_LOG; fi",
        allow_failure=True,
    )
    log("compose_up.log tail:")
    log(compose_tail.rstrip("\n"))

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

