import os
import tempfile
import sys

import pytest

from app import runtime_state
from app.pingpong_configurator import apply_pingpong_configuration


def _dummy_config(**overrides: str) -> dict[str, str]:
    base: dict[str, str] = {
        "ENABLE_PINGPONG": "true",
        "PINGPONG_KEY": "device_key",
        "PINGPONG_0G_PRIVATE_KEY": "",
        "PINGPONG_AIOZ_PRIV_KEY": "",
        "PINGPONG_GRASS_ACCESS": "",
        "PINGPONG_GRASS_REFRESH": "",
        "PINGPONG_BLOCKMESH_EMAIL": "",
        "PINGPONG_BLOCKMESH_PASSWORD": "",
        "PINGPONG_DAWN_EMAIL": "",
        "PINGPONG_DAWN_PASSWORD": "",
        "PINGPONG_HEMI_KEY": "",
    }
    base.update(overrides)
    return base


@pytest.mark.skipif(sys.platform != "linux", reason="Pingpong configurator only runs on linux")
def test_pingpong_configurator_validates_pair_fields(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("MONEYTREE_CONFIG_DIR", tmp)
        runtime_state.save_pingpong_state({})
        open(os.path.join(tmp, "PINGPONG"), "wb").write(b"")

        res = apply_pingpong_configuration(_dummy_config(PINGPONG_GRASS_ACCESS="a"))
        assert any("grass requires both access and refresh" in r for r in res)

        res = apply_pingpong_configuration(_dummy_config(PINGPONG_BLOCKMESH_EMAIL="x@y.com"))
        assert any("blockmesh requires both email and password" in r for r in res)

        res = apply_pingpong_configuration(_dummy_config(PINGPONG_DAWN_EMAIL="x@y.com"))
        assert any("dawn requires both email and password" in r for r in res)


@pytest.mark.skipif(sys.platform != "linux", reason="Pingpong configurator only runs on linux")
def test_pingpong_configurator_applies_only_when_changed(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(args: list[str]):
        calls.append(list(args))
        return True, "ok"

    monkeypatch.setattr("app.pingpong_configurator._run_pingpong", fake_run)

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("MONEYTREE_CONFIG_DIR", tmp)
        open(os.path.join(tmp, "PINGPONG"), "wb").write(b"")

        first = apply_pingpong_configuration(
            _dummy_config(
                PINGPONG_0G_PRIVATE_KEY="k0g",
                PINGPONG_GRASS_ACCESS="ga",
                PINGPONG_GRASS_REFRESH="gr",
            )
        )
        assert any("config set -> OK" in r for r in first)
        assert any("start depins=0g -> OK" in r for r in first)
        assert any("start depins=grass -> OK" in r for r in first)

        calls.clear()
        second = apply_pingpong_configuration(
            _dummy_config(
                PINGPONG_0G_PRIVATE_KEY="k0g",
                PINGPONG_GRASS_ACCESS="ga",
                PINGPONG_GRASS_REFRESH="gr",
            )
        )
        assert second == ["pingpong: depin configuration unchanged"]
        assert calls == []

        calls.clear()
        third = apply_pingpong_configuration(
            _dummy_config(
                PINGPONG_0G_PRIVATE_KEY="k0g2",
                PINGPONG_GRASS_ACCESS="ga",
                PINGPONG_GRASS_REFRESH="gr",
            )
        )
        assert any("start depins=0g -> OK" in r for r in third)
        assert not any("start depins=grass -> OK" in r for r in third)
