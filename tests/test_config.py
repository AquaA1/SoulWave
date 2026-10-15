"""Tests for configuration persistence and parsing."""

import tempfile
from pathlib import Path
from soulwave.config import Config


def test_config_defaults():
    cfg = Config()
    assert cfg.theme == "night"
    assert cfg.show_lyrics is True
    assert cfg.show_visualizer is True
    assert cfg.mini_mode is False
    assert cfg.fps == 12
    assert "space" in cfg.keybindings.values()


def test_config_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "config.toml"
        cfg = Config(theme="cyberpunk", fps=18, mini_mode=True)
        cfg.save(cfg_path)

        assert cfg_path.is_file()

        loaded = Config.load(cfg_path)
        assert loaded.theme == "cyberpunk"
        assert loaded.fps == 18
        assert loaded.mini_mode is True
