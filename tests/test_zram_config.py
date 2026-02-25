import os
import tempfile

from app import config_manager
from app import zram_manager


def test_required_fields_include_zram_size():
    assert "ZRAM_SIZE_MB" in config_manager.get_required_fields()


def test_zram_size_validation_accepts_allowed_values():
    for v in zram_manager.ALLOWED_ZRAM_SIZES_MB:
        assert zram_manager.validate_zram_size_mb(v) == v
        assert zram_manager.validate_zram_size_mb(str(v)) == v


def test_zram_size_validation_rejects_other_values():
    for v in ["0", "256", "513", "4097", "1g", "auto"]:
        try:
            zram_manager.validate_zram_size_mb(v)
            assert False, f"expected failure for {v}"
        except ValueError:
            pass


def test_encrypted_config_round_trip_preserves_zram_size():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MONEYTREE_CONFIG_DIR"] = tmp
        os.environ["MONEYTREE_SECRET_DIR"] = os.path.join(tmp, "secrets")

        config_manager.save_config(
            {
                "WEB_USERNAME": "user",
                "WEB_PASSWORD": "pass",
                "DEVICE_NAME": "device",
                "ZRAM_SIZE_MB": "1024",
                "ENABLE_HONEYGAIN": "false",
            }
        )
        loaded = config_manager.load_config()
        assert loaded.get("ZRAM_SIZE_MB") == "1024"

