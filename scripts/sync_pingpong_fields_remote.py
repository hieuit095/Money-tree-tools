from fabric import Connection, Config
import os


def main() -> None:
    print("START", flush=True)
    ip = "192.168.1.18"
    user = "orangepi"
    password = "orangepi"

    conn = Connection(
        host=ip,
        user=user,
        connect_kwargs={"password": password},
        config=Config(overrides={"sudo": {"password": password}}),
    )

    files_to_sync = [
        "app/config_manager.py",
        "app/pingpong_configurator.py",
        "app/pingpong_wrapper.py",
        "app/runtime_state.py",
        "app/native_manager.py",
    ]

    for f in files_to_sync:
        filename = os.path.basename(f)
        tmp_path = f"/tmp/{filename}"
        remote_path = f"/opt/moneytree/{f}"
        conn.put(f, tmp_path)
        conn.sudo(f"install -m 0644 -o root -g root {tmp_path} {remote_path}")
        conn.sudo(f"rm -f {tmp_path}")

    grep_out = conn.sudo(
        "bash -lc \"grep -n PINGPONG_0G_PRIVATE_KEY /opt/moneytree/app/config_manager.py | head -n 1 || echo NO_MATCH\"",
        hide=True,
        warn=True,
    ).stdout.strip()

    fields_out = conn.sudo(
        "bash -lc \"cd /opt/moneytree && PYTHONPATH=/opt/moneytree python3 -c \\\"from app.config_manager import get_config_sections; s=[x for x in get_config_sections() if x.get('id')=='pingpong'][0]; print(len(s.get('fields') or []))\\\"\"",
        hide=True,
        warn=True,
    ).stdout.strip()

    apply_stub_out = conn.sudo(
        "bash -lc \"cd /opt/moneytree && PYTHONPATH=/opt/moneytree python3 -c \\\"from app.pingpong_configurator import apply_pingpong_configuration; print(apply_pingpong_configuration({'ENABLE_PINGPONG':'true'}))\\\"\"",
        hide=True,
        warn=True,
    ).stdout.strip()

    conn.sudo("systemctl restart income-manager.service", warn=True)
    status = conn.sudo("systemctl is-active income-manager.service", hide=True, warn=True).stdout.strip()

    print(f"REMOTE_GREP={grep_out}")
    print(f"PINGPONG_FIELDS={fields_out}")
    print(f"PINGPONG_APPLY_STUB={apply_stub_out}")
    print(f"INCOME_MANAGER={status}")
    with open("_sync_pingpong_fields_remote_result.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(f"REMOTE_GREP={grep_out}\n")
        f.write(f"PINGPONG_FIELDS={fields_out}\n")
        f.write(f"PINGPONG_APPLY_STUB={apply_stub_out}\n")
        f.write(f"INCOME_MANAGER={status}\n")

    conn.close()


if __name__ == "__main__":
    main()
