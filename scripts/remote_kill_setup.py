import argparse
import shlex

import paramiko


def run_sudo(ssh: paramiko.SSHClient, password: str, command: str) -> tuple[int, str, str]:
    wrapped = "sudo -S -p '' bash -c " + shlex.quote(command)
    stdin, stdout, stderr = ssh.exec_command(wrapped)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.close()
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return exit_status, out, err


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("password")
    args = parser.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, username=args.user, password=args.password, timeout=20)

    run_sudo(ssh, args.password, "pkill -9 -f \"cd /opt/moneytree && ./setup\\.sh\" 2>/dev/null || true")
    run_sudo(ssh, args.password, "pkill -9 -f \"/bin/bash ./setup\\.sh\" 2>/dev/null || true")
    run_sudo(ssh, args.password, "pkill -9 -f \"setup\\.sh\" 2>/dev/null || true")
    _, remaining, _ = run_sudo(ssh, args.password, "pgrep -fa 'setup\\.sh' 2>/dev/null || echo NO_SETUP_PROCESS")
    print(remaining.strip(), flush=True)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
