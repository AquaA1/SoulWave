# 🎧 Soulwave

<p align="center">
  <img src="https://raw.githubusercontent.com/AquaA1/SoulWave/main/soulwave/mascot/preview.png" alt="Soulwave Banner" width="480" onerror="this.style.display='none'"/>
</p>

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
        ╭──────────────────╮
```

> **A retro-futuristic terminal music controller with grooving pixel-art soul companions, synchronized scrolling lyrics, real-time audio spectrum visualization, and universal MPRIS integration.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://kernel.org)
[![Packaging: Native RPM](https://img.shields.io/badge/RPM-Fedora%20%7C%20RHEL-informational.svg)](packaging/rpm/)
[![Release Pipeline](https://github.com/AquaA1/SoulWave/actions/workflows/release.yml/badge.svg)](https://github.com/AquaA1/SoulWave/actions/workflows/release.yml)

---

## Table of Contents

- [✨ Features](#-features)
- [🚀 Quick Installation](#-quick-installation)
  - [One-Liner Install (Recommended)](#one-liner-install-recommended)
  - [Fedora Linux & RPM Distributions](#fedora-linux--rpm-distributions)
  - [Ubuntu, Debian, Arch & Other Distributions](#ubuntu-debian-arch--other-distributions)
  - [Inspection Before Installing](#inspection-before-installing)
  - [Upgrading & Uninstallation](#upgrading--uninstallation)
- [🎮 Getting Started](#-getting-started)
- [⌨️ Complete Keybindings](#️-complete-keybindings)
- [👾 The Mascot & Companions Family](#-the-mascot--companions-family)
- [🎵 Lyrics Synchronization Engine](#-lyrics-synchronization-engine)
- [📊 Audio Spectrum Visualizer (CAVA)](#-audio-spectrum-visualizer-cava)
- [🎨 Dynamic Themes & Colors](#-dynamic-themes--colors)
- [🖥️ Mini Mode for Tiling WMs & Tmux](#️-mini-mode-for-tiling-wms--tmux)
- [⚙️ Full Configuration Guide](#️-full-configuration-guide)
- [🎧 Player Setup & Permissions Guide](#-player-setup--permissions-guide)
- [❓ Troubleshooting & FAQ](#-troubleshooting--faq)
- [🛠️ Packaging & Release Pipeline](#️-packaging--release-pipeline)
- [🧪 Running the Test Suite](#-running-the-test-suite)
- [📄 License & Credits](#-license--credits)

---

## ✨ Features

- **Universal MPRIS Media Player Control**: Seamlessly detects and controls Spotify, Firefox, Chrome, Brave, MPV, VLC, Cider, Amberol, Rhythmbox, or any MPRIS-compatible Linux media player over D-Bus with zero manual configuration.
- **The Grooving Soul Mascot**: An enlarged pixel-art soul wearing glowing headphones, animated with a smooth, deterministic 2.2-second dance cycle derived from a monotonic clock.
- **Three Unified Companion Mascots**:
  - 🌿 **Pip (The gentle soul)**: Subtle vertical bobs with a delicate swaying sprout leaf.
  - ⭐ **Nova (The energetic soul)**: Playful double-hop bounces crowned with a glowing star halo.
  - 🎧 **Mochi (The sleepy soul)**: Cozy side-to-side rocking with custom headphone earcups.
- **Graceful Track Transitions**: Mascots ease down smoothly when switching songs (<kbd>n</kbd>/<kbd>p</kbd>) or when metadata loads, eliminating erratic jumps or sudden acceleration.
- **Synchronized Scrolling Lyrics**: Real-time `.lrc` lyrics from LRCLIB with auto-scrolling, active line centering, local persistent caching, and on-the-fly timing offset adjustments (<kbd>[</kbd> / <kbd>]</kbd> ±100ms).
- **No-Lyrics Dance Fallback**: When synchronized lyrics are unavailable, Soulwave displays a calm countdown and transitions into an enlarged center-stage groove so your terminal never looks blank.
- **Local Timeline Interpolation & Click-to-Seek**: Sub-second progress timeline without D-Bus spam, complete with full mouse click-to-seek and track-epoch safeguards against stale zero-position anomalies.
- **Live CAVA Audio Spectrum**: Direct FIFO audio spectrum visualizer with smooth frequency scaling and graceful decay when paused.
- **Curated Dynamic Themes**: Six built-in aesthetic palettes (*Night, Sunset, Mint, Sakura, Cyberpunk, Mono*) combined with a deterministic dynamic accent color calculated uniquely for each track.
- **Compact Mini Mode (`m`)**: Collapses Soulwave into an ultra-slim single-widget bar perfect for tmux panes, i3/sway bars, or narrow sidebars.
- **Zero-Dependency Demo Mode (`--demo`)**: Try out Soulwave immediately even when no media player is playing!

---

## 🚀 Quick Installation

### One-Liner Install (Recommended)

Run the official installer directly from your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash
```

Once installed, simply type:

```bash
soulwave
```

> **Zero hassle**: The installer automatically chooses the best installation method for your distribution, verifies SHA-256 cryptographic checksums, configures the executable launcher in your standard `$PATH`, and requires **no virtualenv activation**, **no aliases**, and **no manual shell configuration**.

---

### Fedora Linux & RPM Distributions

On Fedora Linux, CentOS Stream, RHEL, Rocky Linux, and AlmaLinux, the installer automatically downloads and installs the native Fedora RPM package:

```bash
# Automated via installer
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash

# Or install manually from a downloaded release RPM:
sudo dnf install ./soulwave-*.noarch.rpm
```

- **Standard Binary**: Installed to `/usr/bin/soulwave` (always on `$PATH`).
- **Isolated Runtime**: Pure-Python runtime located in `/usr/lib/soulwave/vendor` conforming strictly to Fedora packaging guidelines and PEP 668 (zero pollution of system Python).
- **Clean Package Management**: Fully integrated with `dnf` for clean updates and removals.

---

### Ubuntu, Debian, Arch & Other Distributions

On non-RPM distributions, `install.sh` automatically creates an isolated application runtime:
- **System-wide** (with `sudo`): Installs to `/opt/soulwave` with launcher in `/usr/local/bin/soulwave`.
- **User-only** (without root / with `--user`): Installs to `~/.local/share/soulwave` with launcher in `~/.local/bin/soulwave`.

---

### Inspection Before Installing

If you prefer to inspect scripts before executing them:

```bash
# Download and view the installer script
curl -fsSL -o install.sh https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh
less install.sh

# Run locally with optional flags
bash install.sh
```

#### Installer Flags & Options

```
OPTIONS:
    --version, -v <tag>  Install specific release tag (e.g. v0.1.0)
    --file, -f <path>    Install from a local .rpm or .whl file without network
    --user               Force user directory install (~/.local/share/soulwave)
    --system             Force system directory install (/opt/soulwave or RPM)
    --wheel              Force wheel install even on RPM distributions
    --uninstall          Uninstall Soulwave cleanly from the system
    --help, -h           Show help and usage message
```

---

### Recommended Audio Utilities

Soulwave functions immediately out of the box with an internal mock player and audio fallback. To enable active MPRIS player tracking and real-time audio spectrum visualization:

```bash
# Fedora / RHEL / CentOS
sudo dnf install playerctl cava

# Ubuntu / Debian / Linux Mint
sudo apt update && sudo apt install playerctl cava

# Arch Linux / Manjaro
sudo pacman -S playerctl cava

# openSUSE
sudo zypper install playerctl cava
```

---

### Upgrading & Uninstallation

```bash
# Upgrade to the latest release anytime
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash

# Or on Fedora via DNF:
sudo dnf upgrade soulwave

# Clean uninstallation:
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --uninstall

# Or on Fedora:
sudo dnf remove soulwave
```

---

## 🎮 Getting Started

Launch Soulwave in your preferred terminal emulator (Kitty, Alacritty, Ghostty, WezTerm, Foot, GNOME Terminal, etc.):

```bash
# 1. Normal Mode: Automatically connects to your currently active music player
soulwave

# 2. Demo Mode: Explore animations and synced lyrics with built-in lo-fi tracks
soulwave --demo

# 3. Mini Mode: Start directly in compact widget mode
soulwave --mini

# 4. Custom Theme: Launch with a specific theme palette
soulwave --theme sunset

# 5. Lock Player: Focus on a specific player instance
soulwave --player spotify
```

---

## ⌨️ Complete Keybindings

| Key | Function | Description |
|:---:|:---|:---|
| <kbd>Space</kbd> | **Play / Pause** | Toggle playback on the active media player |
| <kbd>n</kbd> | **Next Track** | Skip to next track with smooth transition easing |
| <kbd>p</kbd> | **Previous Track** | Return to previous track |
| <kbd>→</kbd> | **Seek Forward** | Jump forward by 5 seconds |
| <kbd>←</kbd> | **Seek Backward** | Jump backward by 5 seconds |
| <kbd>↑</kbd> or <kbd>+</kbd> | **Volume Up** | Increase player volume by 5% |
| <kbd>↓</kbd> or <kbd>-</kbd> | **Volume Down** | Decrease player volume by 5% |
| <kbd>s</kbd> | **Shuffle** | Toggle player shuffle mode |
| <kbd>r</kbd> | **Repeat / Loop** | Cycle repeat mode (*Off → Track → Playlist*) |
| <kbd>Tab</kbd> | **Switch Player** | Cycle through active players (*Spotify, Firefox, Chrome, Demo*) |
| <kbd>l</kbd> | **Toggle Lyrics** | Show / hide the synchronized scrolling lyrics panel |
| <kbd>v</kbd> | **Toggle Visualizer** | Show / hide the CAVA audio frequency spectrum |
| <kbd>t</kbd> | **Cycle Theme** | Cycle themes (*Night → Sunset → Mint → Sakura → Cyberpunk → Mono*) |
| <kbd>m</kbd> | **Mini Mode** | Toggle between full dashboard and ultra-compact widget |
| <kbd>[</kbd> | **Lyrics Offset -** | Nudge lyrics 100ms earlier (persisted per song) |
| <kbd>]</kbd> | **Lyrics Offset +** | Nudge lyrics 100ms later (persisted per song) |
| <kbd>q</kbd> | **Quit** | Exit Soulwave |
| **Mouse Click** | **Direct Timeline Seek** | Click anywhere along the timeline bar to seek immediately! |

---

## 👾 The Mascot & Companions Family

Soulwave's visual center is a cozy animated scene featuring a large grooving soul mascot and three charming companion souls rendered in truecolor ANSI half-blocks (`▀`, `▄`).

```
   [Pip 🌿]           [Soul 🎧]           [Nova ⭐]      [Mochi 🎧]
  Gentle Bob         Groovy Dance        Energetic Hop    Sleepy Rock
```

### Deterministic Dance Cycle
- Derived from a strict monotonic clock (`time.monotonic()`), completely decoupled from UI render ticks or audio jitter.
- Cycles through a 4-beat sequence over 2.2 seconds:
  1. **Beat 1**: Smooth horizontal lean to the left.
  2. **Beat 2**: Rhythmic vertical bounce downward.
  3. **Beat 3**: Smooth horizontal lean to the right.
  4. **Beat 4**: Upright center rebound.
- Floating musical notes (`♪`, `♫`, `♬`) rise organically into the air as the music plays.

### Transition Easing
When changing tracks or waiting for stream metadata, the mascot never speeds up or stutters. The animation engine enters a `TRACK_TRANSITION` state that smoothly dampens motion down to a calm resting pose, resuming the dance only when the new song confirms active playback.

---

## 🎵 Lyrics Synchronization Engine

Soulwave features a production-grade lyrics engine:

1. **LRCLIB Integration**: Automatically queries synchronized `.lrc` timestamps using song title, artist, and duration.
2. **Plain-Text Fallback**: If synchronized lyrics are not available, plain lyrics are progressively scrolled based on the song's playback progress.
3. **No-Lyrics Fallback**: If no lyrics exist, Soulwave gracefully switches into a full-width mascot dance showcase with ambient audio groove.
4. **Local Disk Caching**: Lyrics are stored locally in `~/.cache/soulwave/lyrics/` to prevent duplicate API requests and enable instant loading on replays.
5. **Manual Offset Memory**: Fine-tune lyric timing using <kbd>[</kbd> and <kbd>]</kbd> (±100ms per press). Offsets are remembered across sessions for that specific track.

---

## 📊 Audio Spectrum Visualizer (CAVA)

Soulwave embeds a real-time 16-bar frequency spectrum powered by [CAVA](https://github.com/karlstav/cava):

- Connects automatically via a private FIFO pipe in `/tmp/soulwave-cava-*.fifo`.
- Auto-detects audio output devices through PulseAudio, PipeWire, or ALSA.
- Features smooth peak smoothing and a graceful decay animation when playback pauses.
- If CAVA is not installed, Soulwave displays a subtle rhythm-based ambient visualizer so the interface remains cohesive.

---

## 🎨 Dynamic Themes & Colors

Soulwave comes with 6 handcrafted color palettes:

- **Night** *(Default)*: Midnight deep navy, slate gray, electric violet, and soft cyan.
- **Sunset**: Dusk purple, warm peach, vibrant coral, and golden hour amber.
- **Mint**: Matcha dark teal, fresh forest green, and crisp cool mint.
- **Sakura**: Cherry blossom plum, soft lilac, and pastel blossom pink.
- **Cyberpunk**: Deep onyx, neon magenta, electric cyan, and laser yellow.
- **Mono**: Minimalist high-contrast carbon slate and chalk white.

Press <kbd>t</kbd> to cycle themes at any time. Soulwave also generates an **algorithmic dynamic accent color** for every unique song title and artist, subtly tinting progress bars and mascots.

---

## 🖥️ Mini Mode for Tiling WMs & Tmux

Press <kbd>m</kbd> or launch with `soulwave --mini` to switch to Mini Mode:

```
▶  Cyberpunk 2077 OST - I Really Want to Stay At Your House   02:14 / 04:06 ━━━━●──────── [Spotify]
```

- Collapses the multi-panel layout into an ultra-compact single widget.
- Perfect for narrow tmux panes, i3/sway/hyprland sidebars, or floating terminal scratchpads.
- Retains all playback keybindings (<kbd>Space</kbd>, <kbd>n</kbd>, <kbd>p</kbd>, seeks, volume).

---

## ⚙️ Full Configuration Guide

Soulwave automatically creates a default configuration file at `~/.config/soulwave/config.toml` (respecting `$XDG_CONFIG_HOME`):

```toml
# ~/.config/soulwave/config.toml

[app]
theme = "night"              # night, sunset, mint, sakura, cyberpunk, mono
show_lyrics = true          # Show lyrics panel on startup
show_visualizer = true      # Show audio spectrum visualizer
mini_mode = false           # Start in compact mini mode
default_player = "spotify"  # Preferred player when multiple are active
fps = 12                    # Mascot animation & UI refresh framerate (10-30)

[keybindings]
play_pause = "space"
next = "n"
previous = "p"
seek_forward = "right"
seek_backward = "left"
volume_up = "up"
volume_down = "down"
shuffle = "s"
loop = "r"
switch_player = "tab"
toggle_lyrics = "l"
toggle_visualizer = "v"
cycle_theme = "t"
toggle_mini = "m"
lyrics_offset_earlier = "["
lyrics_offset_later = "]"
quit = "q"

[visualizer]
bars = 16                   # Number of frequency bars
sensitivity = 100           # CAVA audio sensitivity percentage

[lyrics]
cache_enabled = true        # Cache downloaded lyrics to disk
auto_scroll = true          # Automatically center active lyric line
```

---

## 🎧 Player Setup & Permissions Guide

Soulwave uses the standard Linux MPRIS D-Bus interface. Most modern Linux media players work out of the box with zero setup:

### Spotify
- **Native / Deb / RPM**: Works automatically.
- **Flatpak Spotify**: Grant D-Bus permission if not already enabled:
  ```bash
  flatpak override --user --talk-name=org.mpris.MediaPlayer2.spotify com.spotify.Client
  ```

### Web Browsers (YouTube, SoundCloud, Web Spotify, Bandcamp)
- **Firefox**: Ensure media keys are enabled in `about:config`:
  - `media.hardwaremediakeys.enabled` → `true`
- **Chromium / Google Chrome / Brave**:
  - Visit `chrome://flags/#hardware-media-key-handling` and set to **Enabled**.

### MPV
- Install the `mpv-mpris` plugin:
  ```bash
  # Fedora: sudo dnf install mpv-mpris
  # Ubuntu/Debian: sudo apt install mpv-mpris
  # Arch: sudo pacman -S mpv-mpris
  ```

---

## ❓ Troubleshooting & FAQ

### Soulwave shows "No Player Connected"
1. Start playing music in your browser or desktop player.
2. Run `playerctl status` in a terminal. If `playerctl` sees the player, Soulwave will connect instantly.
3. If using Firefox, make sure an audio or video tab is actively playing.

### Total time displays `--:--`
- Some web streams (live radio or podcasts) do not provide an end duration over MPRIS. Soulwave safely protects timeline position and displays live elapsed time without crashing.

### Lyrics timing is slightly ahead or behind
- Press <kbd>[</kbd> to shift lyrics 100ms earlier or <kbd>]</kbd> to shift lyrics 100ms later. Soulwave remembers your offset for that track.

### CAVA visualizer is flat
- Verify CAVA works independently: run `cava` in a terminal.
- If using PipeWire or PulseAudio, ensure your default audio sink is unmuted.

---

## 🛠️ Packaging & Release Pipeline

Soulwave features an automated, production-ready release pipeline:

- **Fedora RPM Specification**: [`packaging/rpm/soulwave.spec`](packaging/rpm/soulwave.spec)
  - Isolated `/usr/lib/soulwave/vendor` runtime.
  - Native `/usr/bin/soulwave` launcher.
  - Spec validation tested via `rpmspec` and `rpmbuild`.
- **Local RPM Builder**: [`packaging/rpm/build_rpm.sh`](packaging/rpm/build_rpm.sh)
- **GitHub Actions Workflow**: [`.github/workflows/release.yml`](.github/workflows/release.yml)
  - Multi-version Python test matrix (3.10 - 3.13).
  - Python wheel and sdist packaging.
  - Native Fedora 41 container RPM build.
  - Automated SHA-256 `checksums.txt` generation.
  - Automated GitHub Releases publication on version tag pushes (`v*`).

---

## 🧪 Running the Test Suite

Soulwave includes an extensive automated test suite covering unit tests, D-Bus integration, headless UI acceptance tests, animation timing, and packaging validation:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all 97 tests
pytest tests/ -v
```

---

## 📄 License & Credits

- **License**: [MIT License](LICENSE).
- **Crafted with cozy vibes** for terminal enthusiasts, tiling window manager lovers, and music vibers everywhere.
- Powered by [Textual](https://github.com/Textualize/textual), [Rich](https://github.com/Textualize/rich), [LRCLIB](https://lrclib.net), and [CAVA](https://github.com/karlstav/cava).
