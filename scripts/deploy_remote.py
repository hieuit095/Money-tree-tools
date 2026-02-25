import argparse
import os
import paramiko
import sys
import shlex
import time
import traceback
from stat import S_ISDIR

IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "venv", "__pycache__", "node_modules", 
    "reports", "htmlcov", ".pytest_cache"
}
IGNORED_FILES = {
    ".DS_Store", "master.key", ".env"
}

def run_cmd(
    ssh: paramiko.SSHClient,
    command: str,
    *,
    sudo: bool,
    password: str,
    allow_failure: bool,
) -> tuple[int, str, str]:
    if sudo:
        wrapped = f"sudo -S -p '' bash -c {shlex.quote(command)}"
        stdin, stdout, stderr = ssh.exec_command(wrapped)
        stdin.write(password + "\n")
        stdin.flush()
        stdin.close()
    else:
        stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if exit_status != 0 and not allow_failure:
        raise RuntimeError(f"remote_command_failed: exit={exit_status}, stderr={err.strip()}")
    return exit_status, out, err

def put_dir(sftp, local_dir, remote_dir, log):
    try:
        sftp.stat(remote_dir)
    except IOError:
        log(f"Creating remote directory: {remote_dir}")
        sftp.mkdir(remote_dir)

    for item in os.listdir(local_dir):
        if item in IGNORED_FILES or item in IGNORED_DIRS:
            continue
            
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"

        if os.path.isfile(local_path):
            sftp.put(local_path, remote_path)
        elif os.path.isdir(local_path):
            put_dir(sftp, local_path, remote_path, log)

def deploy(host, user, password, local_path, *, preserve_config: bool):
    log_path = "deploy_remote_output.txt"
    def log(line: str) -> None:
        print(line, flush=True)
        with open(log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    open(log_path, "w", encoding="utf-8", newline="\n").write("")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        log(f"Connecting to {user}@{host}...")
        last_exc: Exception | None = None
        for attempt in range(1, 6):
            try:
                if attempt > 1:
                    try:
                        ssh.close()
                    except Exception:
                        pass
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    host,
                    username=user,
                    password=password,
                    timeout=60,
                    banner_timeout=60,
                    auth_timeout=60,
                    look_for_keys=False,
                    allow_agent=False,
                )
                last_exc = None
                break
            except paramiko.ssh_exception.SSHException as e:
                last_exc = e
                log(f"SSH connect failed (attempt {attempt}/5): {e}")
                time.sleep(min(10, 1 + attempt * 2))
        if last_exc is not None:
            raise last_exc
        log("Connected.")

        remote_stage = f"/home/{user}/money-tree-tools-stage-{int(time.time())}"
        remote_target = "/opt/moneytree"
        legacy_dirs = [
            remote_target,
            f"/home/{user}/Money-tree-tools",
            f"/home/{user}/money-tree-tools",
            f"/home/{user}/moneytree-tools",
        ]

        log("Opening SFTP...")
        sftp = ssh.open_sftp()
        log("SFTP ready.")

        log(f"Deploying code to staging directory {remote_stage}...")
        try:
            sftp.stat(remote_stage)
            run_cmd(ssh, f'rm -rf "{remote_stage}"', sudo=False, password=password, allow_failure=True)
        except IOError:
            pass
        put_dir(sftp, local_path, remote_stage, log)
        sftp.close()

        log("Code transfer complete. Performing clean reinstall into /opt/moneytree...")

        log("Stopping services...")
        run_cmd(ssh, "systemctl stop income-manager.service moneytree-zram.service docker-binfmt.service wipter.service uprock.service 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "systemctl disable income-manager.service moneytree-zram.service docker-binfmt.service wipter.service uprock.service 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "rm -f /etc/systemd/system/income-manager.service /etc/systemd/system/moneytree-zram.service /etc/systemd/system/docker-binfmt.service 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "systemctl daemon-reload 2>/dev/null || true", sudo=True, password=password, allow_failure=True)

        log("Stopping any in-progress setup processes...")
        run_cmd(ssh, "pkill -f '/opt/moneytree/.*setup\\.sh' 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "pkill -f 'setup\\.sh' 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "pkill -f 'Xvfb\\s*:99' 2>/dev/null || true", sudo=True, password=password, allow_failure=True)

        preserve_dir = f"/tmp/moneytree-preserve-{int(time.time())}"
        if preserve_config:
            log("Preserving existing configuration...")
            run_cmd(ssh, f'mkdir -p "{preserve_dir}"', sudo=True, password=password, allow_failure=False)
            run_cmd(
                ssh,
                f'if [ -f "{remote_target}/.env.enc" ]; then cp -a "{remote_target}/.env.enc" "{preserve_dir}/.env.enc"; fi',
                sudo=True,
                password=password,
                allow_failure=True,
            )
            run_cmd(
                ssh,
                f'if [ -f "/etc/moneytree/master.key" ]; then cp -a "/etc/moneytree/master.key" "{preserve_dir}/master.key"; fi',
                sudo=True,
                password=password,
                allow_failure=True,
            )
            run_cmd(
                ssh,
                f'if [ -f "{remote_target}/last_apply.json" ]; then cp -a "{remote_target}/last_apply.json" "{preserve_dir}/last_apply.json"; fi',
                sudo=True,
                password=password,
                allow_failure=True,
            )

        log("Removing Moneytree Docker resources (containers/volumes/networks)...")
        run_cmd(ssh, "docker rm -f $(docker ps -aq --filter label=com.docker.compose.project=moneytree-igm) 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "docker rm -f $(docker ps -aq --filter label=project=standard) 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "docker rm -f $(docker ps -aq --filter label=project=proxy) 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "docker volume rm $(docker volume ls -q | grep -E '^moneytree-igm_' || true) 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "docker network rm $(docker network ls -q --filter name='^moneytree-igm_' || true) 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "docker image prune -f >/dev/null 2>&1 || true", sudo=True, password=password, allow_failure=True)

        log("Removing old Moneytree logs and secrets...")
        run_cmd(ssh, "rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "rm -rf /var/log/moneytree* /var/log/income-manager* 2>/dev/null || true", sudo=True, password=password, allow_failure=True)
        run_cmd(ssh, "rm -rf /etc/moneytree 2>/dev/null || true", sudo=True, password=password, allow_failure=True)

        log("Removing old installation directories...")
        for d in legacy_dirs:
            run_cmd(ssh, f'if [ -d \"{d}\" ]; then cd \"{d}\" && docker compose down || true; fi', sudo=True, password=password, allow_failure=True)
            run_cmd(ssh, f'rm -rf \"{d}\"', sudo=True, password=password, allow_failure=True)

        run_cmd(ssh, f'mkdir -p \"{remote_target}\"', sudo=True, password=password, allow_failure=False)
        run_cmd(ssh, f'cp -a \"{remote_stage}/.\" \"{remote_target}/\"', sudo=True, password=password, allow_failure=False)
        run_cmd(ssh, f'rm -rf \"{remote_stage}\"', sudo=True, password=password, allow_failure=False)
        run_cmd(ssh, f'chown -R root:root \"{remote_target}\"', sudo=True, password=password, allow_failure=False)

        if preserve_config:
            log("Restoring preserved configuration...")
            run_cmd(
                ssh,
                f'if [ -f "{preserve_dir}/.env.enc" ]; then cp -a "{preserve_dir}/.env.enc" "{remote_target}/.env.enc"; fi',
                sudo=True,
                password=password,
                allow_failure=True,
            )
            run_cmd(
                ssh,
                f'if [ -f "{preserve_dir}/master.key" ]; then mkdir -p /etc/moneytree && cp -a "{preserve_dir}/master.key" "/etc/moneytree/master.key"; fi',
                sudo=True,
                password=password,
                allow_failure=True,
            )
            run_cmd(
                ssh,
                f'if [ -f "{preserve_dir}/last_apply.json" ]; then cp -a "{preserve_dir}/last_apply.json" "{remote_target}/last_apply.json"; fi',
                sudo=True,
                password=password,
                allow_failure=True,
            )
            run_cmd(ssh, f'rm -rf \"{preserve_dir}\"', sudo=True, password=password, allow_failure=True)

        log("Running setup.sh in /opt/moneytree (this can take a while)...")
        run_cmd(ssh, f'cd \"{remote_target}\" && sed -i \'s/\\r$//\' setup.sh && chmod +x setup.sh', sudo=True, password=password, allow_failure=False)
        exit_status, _, _ = run_cmd(ssh, f'cd \"{remote_target}\" && ./setup.sh > setup.log 2>&1', sudo=True, password=password, allow_failure=False)
        log(f"Setup exited with status {exit_status}")

        log("Fetching setup.log...")
        _, log_out, log_err = run_cmd(ssh, f'cat \"{remote_target}/setup.log\"', sudo=True, password=password, allow_failure=False)
        if log_out:
            log(log_out.rstrip("\n"))
        if log_err:
            log(log_err.rstrip("\n"))
    except Exception:
        log("DEPLOY_ERROR_BEGIN")
        log(traceback.format_exc().rstrip("\n"))
        log("DEPLOY_ERROR_END")
        raise
    finally:
        try:
            ssh.close()
        except Exception:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preserve-config", action="store_true")
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("password")
    
    args = parser.parse_args()
    deploy(args.host, args.user, args.password, os.getcwd(), preserve_config=args.preserve_config)
