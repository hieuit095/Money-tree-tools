from fabric import Connection, Config


def main() -> None:
    ip = "192.168.1.18"
    user = "orangepi"
    password = "orangepi"

    conn = Connection(
        host=ip,
        user=user,
        connect_kwargs={"password": password},
        config=Config(overrides={"sudo": {"password": password}}),
    )

    result = conn.sudo(
        "bash -lc \"cd /opt/moneytree && PYTHONPATH=/opt/moneytree /opt/moneytree/venv/bin/python3 -c \\\"from app.pingpong_configurator import apply_pingpong_configuration; print(apply_pingpong_configuration({'ENABLE_PINGPONG':'true'}))\\\"\"",
        hide=True,
        warn=True,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    print(out or err or "(no output)")
    conn.close()


if __name__ == "__main__":
    main()
