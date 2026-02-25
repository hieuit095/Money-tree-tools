import argparse
import paramiko
import shlex
import sys

def run_cmd(ssh, command, password):
    wrapped = f"sudo -S -p '' bash -c {shlex.quote(command)}"
    stdin, stdout, stderr = ssh.exec_command(wrapped)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.close()
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return exit_status, out, err

def wipe(host, user, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host}...")
    ssh.connect(host, username=user, password=password, timeout=30)
    
    commands = [
        "systemctl stop income-manager.service moneytree-zram.service wipter.service uprock.service 2>/dev/null || true",
        "systemctl disable income-manager.service moneytree-zram.service wipter.service uprock.service 2>/dev/null || true",
        "rm -f /etc/systemd/system/income-manager.service /etc/systemd/system/moneytree-zram.service /etc/systemd/system/docker-binfmt.service 2>/dev/null || true",
        "systemctl daemon-reload",
        "pkill -f 'setup\\.sh' 2>/dev/null || true",
        "docker rm -f $(docker ps -aq --filter label=project=standard) 2>/dev/null || true",
        "docker rm -f $(docker ps -aq --filter label=project=proxy) 2>/dev/null || true",
        "docker rm -f $(docker ps -aq --filter label=com.docker.compose.project=moneytree-igm) 2>/dev/null || true",
        "rm -rf /opt/moneytree",
        "rm -rf /etc/moneytree",
        "rm -rf /var/log/moneytree*",
        "rm -rf /var/log/income-manager*",
        "rm -rf /home/orangepi/Money-tree-tools",
        "rm -rf /home/orangepi/money-tree-tools",
        "rm -rf /home/orangepi/moneytree-tools",
        "rm -rf /home/orangepi/.env.enc"
    ]
    
    for cmd in commands:
        print(f"Executing: {cmd}")
        status, out, err = run_cmd(ssh, cmd, password)
        if status != 0 and "true" not in cmd:
            print(f"Warning: Command failed with status {status}")
            if err: print(f"Error: {err.strip()}")
            
    print("Wipe complete.")
    ssh.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("password")
    args = parser.parse_args()
    wipe(args.host, args.user, args.password)
