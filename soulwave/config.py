"""Configuration management for Soulwave."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


@dataclass
class Config:
    """Soulwave user settings."""
    theme: str = "night"
    show_lyrics: bool = True
    show_visualizer: bool = True
    mini_mode: bool = False
    mascot_skin: str = "classic"
    default_player: str = ""
    fps: int = 12
    seek_step_seconds: float = 5.0
    volume_step_percent: float = 0.05
    lyrics_cache_dir: str = field(
        default_factory=lambda: str(Path.home() / ".cache" / "soulwave" / "lyrics")
    )
    keybindings: Dict[str, str] = field(
        default_factory=lambda: {
            "play_pause": "space",
            "next": "n",
            "previous": "p",
            "seek_forward": "right",
            "seek_backward": "left",
            "volume_up": "up",
            "volume_down": "down",
            "shuffle": "s",
            "loop": "r",
            "switch_player": "tab",
            "toggle_lyrics": "l",
            "toggle_visualizer": "v",
            "cycle_theme": "t",
            "toggle_mini": "m",
            "lyrics_offset_earlier": "[",
            "lyrics_offset_later": "]",
            "quit": "q",
        }
    )

    @classmethod
    def get_config_path(cls) -> Path:
        """Returns the default configuration file path."""
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"
        return base / "soulwave" / "config.toml"

    @classmethod
    def load(cls, custom_path: Path | None = None) -> "Config":
        """Load configuration from disk, falling back to defaults."""
        path = custom_path or cls.get_config_path()
        if not path.is_file() or tomllib is None:
            return cls()

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            
            app_cfg = data.get("app", {})
            keybinds = data.get("keybindings", {})

            cfg = cls()
            if "theme" in app_cfg:
                cfg.theme = str(app_cfg["theme"])
            if "show_lyrics" in app_cfg:
                cfg.show_lyrics = bool(app_cfg["show_lyrics"])
            if "show_visualizer" in app_cfg:
                cfg.show_visualizer = bool(app_cfg["show_visualizer"])
            if "mini_mode" in app_cfg:
                cfg.mini_mode = bool(app_cfg["mini_mode"])
            if "mascot_skin" in app_cfg:
                cfg.mascot_skin = str(app_cfg["mascot_skin"])
            if "default_player" in app_cfg:
                cfg.default_player = str(app_cfg["default_player"])
            if "fps" in app_cfg:
                cfg.fps = int(app_cfg["fps"])

            if keybinds:
                cfg.keybindings.update(keybinds)

            return cfg
        except Exception:
            return cls()

    def save(self, custom_path: Path | None = None) -> None:
        """Save configuration to disk in TOML format."""
        path = custom_path or self.get_config_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            lines = [
                "# Soulwave Configuration",
                "[app]",
                f'theme = "{self.theme}"',
                f'show_lyrics = {str(self.show_lyrics).lower()}',
                f'show_visualizer = {str(self.show_visualizer).lower()}',
                f'mini_mode = {str(self.mini_mode).lower()}',
                f'mascot_skin = "{self.mascot_skin}"',
                f'default_player = "{self.default_player}"',
                f'fps = {self.fps}',
                "",
                "[keybindings]",
            ]
            for action, key in self.keybindings.items():
                lines.append(f'{action} = "{key}"')
            lines.append("")

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass
