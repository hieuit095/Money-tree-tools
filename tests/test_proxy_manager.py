import os

import pytest

from app import proxy_manager


def test_validate_proxy_entries_accepts_supported_schemas():
    ok, msg = proxy_manager._validate_proxy_entries(
        "socks5://user:pass@1.2.3.4:1080\nhttp://5.6.7.8:8080\n#socks4://9.9.9.9:1080\n"
    )
    assert ok is True
    assert msg == "OK"


@pytest.mark.parametrize(
    "line",
    [
        "ftp://1.2.3.4:21",
        "socks5://1.2.3.4",
        "http://1.2.3.4:99999",
        "not-a-url",
    ],
)
def test_validate_proxy_entries_rejects_invalid(line: str):
    ok, msg = proxy_manager._validate_proxy_entries(line + "\n")
    assert ok is False
    assert msg


def test_build_env_deploy_proxy_text_requires_selection():
    ok, msg, text = proxy_manager._build_env_deploy_proxy_text(
        {
            "ENABLE_PROXY_REPOCKET": "false",
            "ENABLE_PROXY_EARNFM": "false",
            "ENABLE_PROXY_PACKETSHARE": "false",
        }
    )
    assert ok is False
    assert text == ""
    assert msg


def test_apply_proxy_configuration_disable_noop(monkeypatch, tmp_path):
    monkeypatch.setenv("MONEYTREE_IGM_ROOT", str(tmp_path))
    monkeypatch.setattr(proxy_manager, "_proxy_containers_exist", lambda: False)
    ok, msg = proxy_manager.apply_proxy_configuration({"ENABLE_MULTI_PROXY": "false"})
    assert ok is True
    assert "disabled" in msg.lower()


def test_apply_proxy_configuration_enable_writes_files_and_runs_install(monkeypatch, tmp_path):
    monkeypatch.setenv("MONEYTREE_IGM_ROOT", str(tmp_path))
    calls: list[str] = []

    def fake_run(subcommand: str, *, timeout_s: float) -> str:
        calls.append(subcommand)
        return f"ran:{subcommand}"

    monkeypatch.setattr(proxy_manager, "_run_igm_proxy_cmd", fake_run)
    monkeypatch.setattr(proxy_manager, "_proxy_containers_exist", lambda: False)

    ok, msg = proxy_manager.apply_proxy_configuration(
        {
            "ENABLE_MULTI_PROXY": "true",
            "PROXY_ENTRIES": "socks5://user:pass@1.2.3.4:1080\\nhttp://5.6.7.8:8080",
            "ENABLE_PROXY_REPOCKET": "true",
            "ENABLE_PROXY_EARNFM": "false",
            "ENABLE_PROXY_PACKETSHARE": "true",
        }
    )
    assert ok is True
    assert "ran:install" in msg
    assert calls == ["install"]

    proxies_txt = (tmp_path / "proxies.txt").read_text(encoding="utf-8")
    deploy_txt = (tmp_path / ".env.deploy.proxy").read_text(encoding="utf-8")
    assert "socks5://user:pass@1.2.3.4:1080" in proxies_txt
    assert "http://5.6.7.8:8080" in proxies_txt
    assert "REPOCKET=ENABLED" in deploy_txt
    assert "PACKETSHARE=ENABLED" in deploy_txt


def test_apply_proxy_configuration_enable_redeploys_when_changed(monkeypatch, tmp_path):
    monkeypatch.setenv("MONEYTREE_IGM_ROOT", str(tmp_path))
    (tmp_path / "proxies.txt").write_text("http://1.1.1.1:8080\n", encoding="utf-8")
    (tmp_path / ".env.deploy.proxy").write_text("REPOCKET=ENABLED\nEARNFM=DISABLED\nPACKETSHARE=DISABLED\n", encoding="utf-8")

    calls: list[str] = []

    def fake_run(subcommand: str, *, timeout_s: float) -> str:
        calls.append(subcommand)
        return f"ran:{subcommand}"

    monkeypatch.setattr(proxy_manager, "_run_igm_proxy_cmd", fake_run)
    monkeypatch.setattr(proxy_manager, "_proxy_containers_exist", lambda: True)

    ok, msg = proxy_manager.apply_proxy_configuration(
        {
            "ENABLE_MULTI_PROXY": "true",
            "PROXY_ENTRIES": "http://2.2.2.2:8080",
            "ENABLE_PROXY_REPOCKET": "true",
            "ENABLE_PROXY_EARNFM": "false",
            "ENABLE_PROXY_PACKETSHARE": "false",
        }
    )
    assert ok is True
    assert calls == ["remove", "install"]
    assert "ran:install" in msg
