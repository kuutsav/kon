from pathlib import Path

import pytest

from kon import get_config, reset_config, set_permission_mode
from kon.config import PERMISSION_MODES


def test_set_permission_mode_persists_and_updates_runtime_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_config()

    try:
        original_config = get_config()
        cfg = set_permission_mode("auto")

        config_file = Path(tmp_path) / ".kon" / "config.toml"
        assert cfg is original_config
        assert cfg.permissions.mode == "auto"
        assert get_config().permissions.mode == "auto"
        assert 'mode = "auto"' in config_file.read_text(encoding="utf-8")
    finally:
        reset_config()


def test_set_permission_mode_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unknown permission mode"):
        set_permission_mode("invalid")  # type: ignore[arg-type]


def test_permission_modes_match_config_schema_options():
    assert PERMISSION_MODES == ("prompt", "auto")
