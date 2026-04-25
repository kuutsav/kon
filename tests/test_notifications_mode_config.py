from pathlib import Path

from kon import get_config, reset_config, set_notifications_enabled
from kon.config import NOTIFICATION_MODES


def test_set_notifications_enabled_persists_and_updates_runtime_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_config()

    try:
        original_config = get_config()
        cfg = set_notifications_enabled(True)

        config_file = Path(tmp_path) / ".kon" / "config.toml"
        assert cfg is original_config
        assert cfg.notifications.enabled is True
        assert get_config().notifications.enabled is True
        assert "enabled = true" in config_file.read_text(encoding="utf-8")
    finally:
        reset_config()


def test_notification_modes_match_command_options():
    assert NOTIFICATION_MODES == ("on", "off")
