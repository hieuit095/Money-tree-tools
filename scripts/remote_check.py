import argparse
import paramiko
import shlex


def run(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return exit_status, out, err


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

    try:
        ssh.connect(
            args.host,
            username=args.user,
            password=args.password,
            timeout=60,
            banner_timeout=60,
            auth_timeout=60,
            look_for_keys=False,
            allow_agent=False,
        )

        exit_status = 0

        _, out, err = run(ssh, "ls -ld /opt/moneytree || echo NO_OPT_MONEYTREE")
        _, svc_active, _ = run(ssh, "systemctl is-active income-manager.service 2>/dev/null || echo inactive")
        _, svc_show, _ = run_sudo(
            ssh,
            args.password,
            "systemctl show income-manager.service -p ActiveState -p SubState -p MainPID -p ExecMainStatus -p ExecMainCode -p ExecMainStartTimestamp -p ExecStart 2>/dev/null || echo NO_INCOME_MANAGER_SHOW",
        )
        _, svc_unit, _ = run_sudo(
            ssh,
            args.password,
            "systemctl cat income-manager.service 2>/dev/null || echo NO_INCOME_MANAGER_UNIT",
        )
        _, svc_journal, _ = run_sudo(
            ssh,
            args.password,
            "journalctl -u income-manager.service -n 120 --no-pager 2>/dev/null || echo NO_INCOME_MANAGER_JOURNAL",
        )
        _, port_listen, _ = run_sudo(
            ssh,
            args.password,
            "ss -ltnp 2>/dev/null | grep -E '(:5000\\b)' || echo NO_LISTENER_5000",
        )
        _, curl_local, _ = run_sudo(
            ssh,
            args.password,
            "curl -sS -m 3 -o /dev/null -w 'HTTP=%{http_code}\\n' http://127.0.0.1:5000/ 2>/dev/null || echo CURL_LOCAL_FAILED",
        )
        _, setup_tail, _ = run_sudo(
            ssh,
            args.password,
            "if [ -f /opt/moneytree/setup.log ]; then tail -n 50 /opt/moneytree/setup.log; else echo NO_SETUP_LOG; fi",
        )
        _, setup_meta, _ = run_sudo(
            ssh,
            args.password,
            "if [ -f /opt/moneytree/setup.log ]; then wc -l /opt/moneytree/setup.log && stat -c '%y' /opt/moneytree/setup.log; else echo NO_SETUP_LOG; fi",
        )
        _, setup_procs, _ = run(ssh, "pgrep -fa 'setup.sh' 2>/dev/null || echo NO_SETUP_PROCESS")
        _, setup_ps, _ = run(ssh, "ps -eo pid,etime,stat,cmd | grep -E '[s]etup\\.sh' || true")
        _, venv_status, _ = run_sudo(ssh, args.password, "ls -ld /opt/moneytree/venv 2>/dev/null || echo NO_VENV")
        _, pingpong_fields, _ = run_sudo(
            ssh,
            args.password,
            "cd /opt/moneytree && PYTHONPATH=/opt/moneytree python3 -c \"from app.config_manager import get_config_sections; s=[x for x in get_config_sections() if x.get('id')=='pingpong'][0]; print('PINGPONG_FIELDS=' + str(len(s.get('fields') or [])))\" 2>/dev/null || echo PINGPONG_FIELDS_CHECK_FAILED",
        )
        _, compose_ps, compose_ps_err = run_sudo(
            ssh,
            args.password,
            "cd /opt/moneytree && docker compose ps 2>/dev/null || echo DOCKER_COMPOSE_PS_FAILED",
        )
        _, compose_ps_all, _ = run_sudo(
            ssh,
            args.password,
            "cd /opt/moneytree && docker compose ps -a 2>/dev/null || echo DOCKER_COMPOSE_PS_ALL_FAILED",
        )
        _, compose_services, _ = run_sudo(
            ssh,
            args.password,
            "cd /opt/moneytree && docker compose config --services 2>/dev/null || echo DOCKER_COMPOSE_SERVICES_FAILED",
        )
    except Exception as exc:
        exit_status = 1
        out = ""
        err = f"{type(exc).__name__}: {exc}"
        svc_active = "unknown"
        svc_show = ""
        svc_unit = ""
        svc_journal = ""
        port_listen = ""
        curl_local = ""
        setup_tail = ""
        setup_meta = ""
        setup_procs = ""
        setup_ps = ""
        venv_status = ""
        pingpong_fields = ""
        compose_ps = ""
        compose_ps_all = ""
        compose_services = ""
        compose_ps_err = ""
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    rendered = []
    rendered.append("REMOTE_CHECK_BEGIN\n")
    rendered.append(out)
    rendered.append("SERVICE_ACTIVE_BEGIN\n")
    rendered.append(svc_active.strip() + "\n")
    rendered.append("SERVICE_SHOW_BEGIN\n")
    rendered.append(svc_show)
    if not svc_show.endswith("\n"):
        rendered.append("\n")
    rendered.append("SERVICE_UNIT_BEGIN\n")
    rendered.append(svc_unit)
    if not svc_unit.endswith("\n"):
        rendered.append("\n")
    rendered.append("SERVICE_JOURNAL_BEGIN\n")
    rendered.append(svc_journal)
    if not svc_journal.endswith("\n"):
        rendered.append("\n")
    rendered.append("PORT_5000_LISTENER_BEGIN\n")
    rendered.append(port_listen)
    if not port_listen.endswith("\n"):
        rendered.append("\n")
    rendered.append("CURL_LOCAL_BEGIN\n")
    rendered.append(curl_local)
    if not curl_local.endswith("\n"):
        rendered.append("\n")
    rendered.append("SETUP_LOG_TAIL_BEGIN\n")
    rendered.append(setup_tail)
    if not setup_tail.endswith("\n"):
        rendered.append("\n")
    rendered.append("SETUP_LOG_META_BEGIN\n")
    rendered.append(setup_meta)
    if not setup_meta.endswith("\n"):
        rendered.append("\n")
    rendered.append("SETUP_PROCESS_BEGIN\n")
    rendered.append(setup_procs)
    if not setup_procs.endswith("\n"):
        rendered.append("\n")
    rendered.append("SETUP_PROCESS_STATUS_BEGIN\n")
    rendered.append(setup_ps)
    if not setup_ps.endswith("\n"):
        rendered.append("\n")
    rendered.append("VENV_STATUS_BEGIN\n")
    rendered.append(venv_status)
    if not venv_status.endswith("\n"):
        rendered.append("\n")
    rendered.append("PINGPONG_FIELDS_BEGIN\n")
    rendered.append(pingpong_fields)
    if not pingpong_fields.endswith("\n"):
        rendered.append("\n")
    rendered.append("DOCKER_COMPOSE_PS_BEGIN\n")
    rendered.append(compose_ps)
    if not compose_ps.endswith("\n"):
        rendered.append("\n")
    rendered.append("DOCKER_COMPOSE_PS_ALL_BEGIN\n")
    rendered.append(compose_ps_all)
    if not compose_ps_all.endswith("\n"):
        rendered.append("\n")
    rendered.append("DOCKER_COMPOSE_SERVICES_BEGIN\n")
    rendered.append(compose_services)
    if not compose_services.endswith("\n"):
        rendered.append("\n")
    if compose_ps_err.strip():
        rendered.append(compose_ps_err)
        if not compose_ps_err.endswith("\n"):
            rendered.append("\n")
    if err.strip():
        rendered.append(err)
        if not err.endswith("\n"):
            rendered.append("\n")

    output_text = "".join(rendered)
    with open("remote_check_output.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(output_text)
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
