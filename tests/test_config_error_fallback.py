from pathlib import Path

from kon.config import Config, consume_config_warnings, get_config, reset_config


def test_invalid_toml_falls_back_to_defaults_and_records_warning(tmp_path, monkeypatch):
    home = tmp_path / "home"
    config_dir = home / ".kon"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("[bad", encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: home)

    reset_config()

    cfg = get_config()

    assert isinstance(cfg, Config)
    assert cfg.llm.default_provider == "openai-codex"
    assert cfg.llm.default_model == "gpt-5.4"

    warnings = consume_config_warnings()
    assert len(warnings) == 1
    assert "Invalid config" in warnings[0]
    assert str(config_file) in warnings[0]

    assert consume_config_warnings() == []
