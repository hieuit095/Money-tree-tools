import argparse
import shlex

import paramiko


def run_sudo(ssh: paramiko.SSHClient, password: str, command: str) -> str:
    wrapped = "sudo -S -p '' bash -c " + shlex.quote(command)
    stdin, stdout, _ = ssh.exec_command(wrapped)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.close()
    stdout.channel.recv_exit_status()
    return stdout.read().decode(errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("password")
    args = parser.parse_args()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, username=args.user, password=args.password, timeout=20)

    output = run_sudo(
        ssh,
        args.password,
        r"""
set -euo pipefail
ps -eo pid,stat,etime,cmd | grep -E '[s]etup\.sh' || true
pids="$(pgrep -f "cd /opt/moneytree && ./setup\.sh" 2>/dev/null || true)"
pids="$pids $(pgrep -f "/bin/bash ./setup\.sh" 2>/dev/null || true)"
pids="$(echo "$pids" | tr ' ' '\n' | awk 'NF' | sort -u)"
for pid in $pids; do
  pkill -9 -P "$pid" 2>/dev/null || true
done
for pid in $pids; do
  kill -9 "$pid" 2>/dev/null || true
done
echo AFTER_KILL
ps -eo pid,stat,etime,cmd | grep -E '[s]etup\.sh' || true
pgrep -fa 'setup\.sh' 2>/dev/null || echo NO_SETUP_PROCESS
""".strip(),
    )
    with open("remote_force_kill_output.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(output)
    print(output.strip(), flush=True)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
