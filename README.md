# Soulwave

```
             ✧                        
                   ✦                
             ▄▄▀▀▀▀▀▀▄▄             
           ▄▀ ▄▀▀▀▀▀▀▄ ▀▄           
           ▀  ▀ ▀  ▀ ▀  ▀           
            ▀ ▀▄▀▄ ▀▄▀ ▀            
              ▀▀▀▀▀▀▀▀            ✧ 
  ✧           ▀▀▀▀▀▀▀▀              
        ˚     ▄▀ ▀  ▀▄              
       ♬                            
```

> **A retro-futuristic terminal music controller featuring grooving pixel-art soul companions, synchronized scrolling lyrics, real-time CAVA spectrum visualization, and universal MPRIS support.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://kernel.org)
[![Binary: x86_64 | aarch64](https://img.shields.io/badge/Binary-x86__64%20%7C%20aarch64-blueviolet.svg)](https://github.com/AquaA1/SoulWave/releases)
[![Packaging: Native RPM](https://img.shields.io/badge/RPM-Fedora%20%7C%20RHEL-informational.svg)](packaging/rpm/)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Release Pipeline](https://github.com/AquaA1/SoulWave/actions/workflows/release.yml/badge.svg)](https://github.com/AquaA1/SoulWave/actions/workflows/release.yml)

---

## Features

- **Universal Standalone Binaries**: Single-file executables for `x86_64` and `aarch64` that run out of the box on Ubuntu, Debian, Mint, Fedora, Arch, openSUSE, Pop!_OS without Python or venv configuration.
- **Universal MPRIS Control**: Automatically connects to Spotify, Firefox, Chrome, Brave, MPV, VLC, or any MPRIS-compatible player over D-Bus.
- **Grooving Soul Companions**: Smooth pixel-art mascots (Pip, Nova, Mochi) dancing rhythmically with transition easing.
- **Synchronized Lyrics**: Real-time `.lrc` scrolling lyrics via LRCLIB with auto-centering, local caching, and offset tuning (<kbd>[</kbd>/<kbd>]</kbd>).
- **CAVA Audio Visualizer**: 16-bar real-time audio spectrum with smooth frequency response and pause decay.
- **Timeline & Seek**: Sub-second progress interpolation and full mouse click-to-seek support.
- **Themes & Mini Mode**: 6 built-in palettes (*Night, Sunset, Mint, Sakura, Cyberpunk, Mono*), dynamic song accent colors, and an ultra-compact single-line widget (<kbd>m</kbd>).

---

## Installation

### One-Liner Install (Universal Standalone Binary)

Install Soulwave on **Ubuntu, Debian, Fedora, Arch Linux, Linux Mint, Pop!_OS, openSUSE**, or other compatible Linux distributions with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash
```

- **Zero Python Configuration**: Downloads a verified, self-contained executable directly into `~/.local/bin/soulwave`. No virtual environments, `python3-venv`, or `pip` needed.
- **Rootless & Secure**: Does not require `sudo`. All downloads are verified against SHA-256 release checksums (fail-closed).
- **Supported Architectures**: `x86_64` (amd64) and `aarch64` (arm64).

> [!TIP]
> If `~/.local/bin` is not yet in your `$PATH`, add it by running:
> ```bash
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
> ```

### Alternative Installation Options

- **Fedora / RHEL (Native RPM)**:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --rpm
  # Or install a downloaded RPM package directly:
  sudo dnf install ./soulwave-*.rpm
  ```

- **Python Wheel (Virtual Environment)**:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --wheel
  ```

- **System-Wide Install** (Installs to `/usr/local/bin`):
  ```bash
  curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --system
  ```

- **Uninstall Soulwave**:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --uninstall
  ```

### Audio Utilities (Recommended for CAVA visualizer & playerctl)

Soulwave runs out-of-the-box in demo mode, but installing `playerctl` and `cava` enables live desktop media tracking (Spotify, Firefox, etc.) and real-time audio visualization:

- **Fedora / RHEL / CentOS**:
  ```bash
  sudo dnf install playerctl cava
  ```
- **Ubuntu / Debian / Linux Mint / Pop!_OS**:
  ```bash
  sudo apt update && sudo apt install playerctl cava
  ```
- **Arch Linux / Manjaro**:
  ```bash
  sudo pacman -S playerctl cava
  ```
- **openSUSE**:
  ```bash
  sudo zypper install playerctl cava
  ```

---

## Usage

Start Soulwave:
```bash
soulwave
```

Demo Mode (explore with built-in lo-fi tracks, no player needed):
```bash
soulwave --demo
```

Mini Mode (compact single-line bar widget):
```bash
soulwave --mini
```

Custom Theme:
```bash
soulwave --theme sunset
```

Lock to a specific player:
```bash
soulwave --player spotify
```

Run installation health check:
```bash
soulwave --check
```

---

## Keybindings

| Key | Action |
|:---:|:---|
| <kbd>Space</kbd> | Toggle Play / Pause |
| <kbd>n</kbd> / <kbd>p</kbd> | Next / Previous track |
| <kbd>→</kbd> / <kbd>←</kbd> | Seek forward / backward (5s) |
| <kbd>↑</kbd> / <kbd>↓</kbd> or <kbd>+</kbd> / <kbd>-</kbd> | Volume up / down (5%) |
| <kbd>s</kbd> | Toggle shuffle |
| <kbd>r</kbd> | Cycle repeat mode (*Off → Track → Playlist*) |
| <kbd>Tab</kbd> | Switch active player (*Spotify, Firefox, Chrome, Demo*) |
| <kbd>l</kbd> | Toggle synchronized lyrics panel |
| <kbd>v</kbd> | Toggle CAVA audio spectrum visualizer |
| <kbd>t</kbd> | Cycle color theme |
| <kbd>m</kbd> | Toggle ultra-compact Mini mode |
| <kbd>[</kbd> / <kbd>]</kbd> | Adjust lyric synchronization offset (±100ms) |
| <kbd>q</kbd> | Quit Soulwave |
| **Mouse Click** | Click anywhere along the timeline bar to seek directly |

---

## Configuration

Soulwave generates its default configuration at `~/.config/soulwave/config.toml`:

```toml
[app]
theme = "night"              # night, sunset, mint, sakura, cyberpunk, mono
show_lyrics = true          # Show lyrics panel on startup
show_visualizer = true      # Show audio visualizer
mini_mode = false           # Start in compact widget mode
default_player = "spotify"  # Preferred player
fps = 12                    # Mascot animation & UI refresh rate

[visualizer]
bars = 16                   # Number of frequency bars
sensitivity = 100           # CAVA audio sensitivity percentage

[lyrics]
cache_enabled = true        # Cache downloaded lyrics locally
auto_scroll = true          # Automatically scroll and center active line
```

---

## Troubleshooting & Quick Tips

Verify player detection with `playerctl`:
```bash
playerctl status
```

Grant Spotify Flatpak D-Bus permissions:
```bash
flatpak override --user --talk-name=org.mpris.MediaPlayer2.spotify com.spotify.Client
```

Run automated test suite:
```bash
pytest tests/ -v
```

Uninstall Soulwave:
```bash
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --uninstall
```

---

## Credits & Inspirations

- **[CAVA](https://github.com/karlstav/cava)** – Console-based Audio Visualizer by Karl Stavestrand, for inspiring and powering our real-time audio spectrum visualization.
- **[Textual](https://github.com/Textualize/textual)** & **[Rich](https://github.com/Textualize/rich)** – Terminal UI application framework and styled text engine.
- **[LRCLIB](https://lrclib.net)** – Open community API for real-time synchronized lyrics.
- **[playerctl](https://github.com/altdesktop/playerctl)** – MPRIS command-line interface and media player discovery.

---

## License

This project is licensed under the [MIT License](LICENSE). Built and debugged with AI assistance.
