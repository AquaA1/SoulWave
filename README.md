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

> **A retro-futuristic terminal music controller with grooving pixel-art soul companions, synchronized scrolling lyrics, real-time audio spectrum visualization, and universal MPRIS integration.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://kernel.org)
[![Packaging: Native RPM](https://img.shields.io/badge/RPM-Fedora%20%7C%20RHEL-informational.svg)](packaging/rpm/)
[![Release Pipeline](https://github.com/AquaA1/SoulWave/actions/workflows/release.yml/badge.svg)](https://github.com/AquaA1/SoulWave/actions/workflows/release.yml)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [One-Liner Install](#one-liner-install-recommended)
  - [Fedora & RPM Distributions](#fedora--rpm-distributions)
  - [Ubuntu, Debian, Arch & Other Distributions](#ubuntu-debian-arch--other-distributions)
  - [Installation Options](#installation-options)
  - [Recommended Audio Utilities](#recommended-audio-utilities)
  - [Upgrading & Uninstallation](#upgrading--uninstallation)
- [Verification & Health Check](#verification--health-check)
- [Getting Started](#getting-started)
- [Keybindings](#keybindings)
- [The Mascot & Companions](#the-mascot--companions)
- [Lyrics Synchronization](#lyrics-synchronization)
- [Audio Spectrum Visualizer](#audio-spectrum-visualizer)
- [Themes & Colors](#themes--colors)
- [Mini Mode](#mini-mode)
- [Configuration Guide](#configuration-guide)
- [Player Setup & Permissions](#player-setup--permissions)
- [Troubleshooting & FAQ](#troubleshooting--faq)
- [Packaging & Releases](#packaging--releases)
- [Running Tests](#running-tests)
- [License](#license)

---

## Features

- **Universal MPRIS Control**: Automatically connects to Spotify, Firefox, Chrome, Brave, MPV, VLC, Cider, Amberol, Rhythmbox, or any MPRIS-compatible Linux media player over D-Bus with zero manual configuration.
- **The Grooving Soul Mascot**: An enlarged pixel-art soul wearing headphones, animated with a smooth, deterministic 2.2-second dance cycle derived from a monotonic clock.
- **Three Unified Companion Mascots**:
  - **Pip (The gentle soul)**: Subtle vertical bobs with a delicate swaying sprout leaf.
  - **Nova (The energetic soul)**: Playful double-hop bounces crowned with a star halo.
  - **Mochi (The sleepy soul)**: Cozy side-to-side rocking with custom headphone earcups.
- **Graceful Track Transitions**: Mascots ease down smoothly when switching songs (<kbd>n</kbd>/<kbd>p</kbd>) or when metadata loads, eliminating erratic jumps or sudden acceleration.
- **Synchronized Scrolling Lyrics**: Real-time `.lrc` lyrics from LRCLIB with auto-scrolling, active line centering, local persistent caching, and on-the-fly timing offset adjustments (<kbd>[</kbd> / <kbd>]</kbd> ±100ms).
- **No-Lyrics Fallback**: When synchronized lyrics are unavailable, Soulwave transitions into a full center-stage mascot groove so your terminal always feels alive.
- **Timeline Interpolation & Click-to-Seek**: Sub-second progress timeline without D-Bus spam, complete with full mouse click-to-seek and safeguards against stale zero-position anomalies.
- **Live CAVA Audio Spectrum**: Direct FIFO audio spectrum visualizer with smooth frequency scaling and graceful decay when paused.
- **Curated Dynamic Themes**: Six built-in aesthetic palettes (*Night, Sunset, Mint, Sakura, Cyberpunk, Mono*) combined with an algorithmic dynamic accent color calculated uniquely for each track.
- **Compact Mini Mode (<kbd>m</kbd>)**: Collapses Soulwave into an ultra-slim single-line widget ideal for tmux panes, tiling window manager bars, or narrow sidebars.
- **Zero-Dependency Demo Mode (`--demo`)**: Try out Soulwave immediately even when no media player is active.

---

## Installation

### One-Liner Install (Recommended)

Run the official installer directly in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash
```

Once installed, launch Soulwave:

```bash
soulwave
```

The installer automatically selects the best method for your distribution, verifies SHA-256 cryptographic checksums, configures the launcher in your standard `$PATH`, and runs an automated health check to confirm runtime dependencies and UI assets.

---

### Fedora & RPM Distributions

On Fedora, CentOS Stream, RHEL, Rocky Linux, and AlmaLinux, the installer automatically installs the native standalone RPM:

```bash
# Automated via installer
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash

# Or manually from a downloaded release RPM:
sudo dnf install ./soulwave-*.rpm
```

- **Executable Launcher**: `/usr/bin/soulwave` (on default `$PATH`).
- **Isolated Vendor Runtime**: Pure-Python runtime in `/usr/lib/soulwave/vendor` conforming strictly to Fedora packaging guidelines and PEP 668.
- **Clean Package Management**: Managed directly through `dnf` for clean updates and removals.

---

### Ubuntu, Debian, Arch & Other Distributions

On non-RPM distributions, `install.sh` creates an isolated application environment:
- **System-wide** (with `sudo`): Installs to `/opt/soulwave` with launcher in `/usr/local/bin/soulwave`.
- **User-only** (without root / with `--user`): Installs to `~/.local/share/soulwave` with launcher in `~/.local/bin/soulwave`.

---

### Installation Options

You can download and inspect the installer script before running it:

```bash
curl -fsSL -o install.sh https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh
less install.sh
bash install.sh [OPTIONS]
```

#### Available Flags

```text
OPTIONS:
    --version, -v <tag>  Install specific release tag (e.g. v0.1.1 or 0.1.1)
    --file, -f <path>    Install from a local .rpm or .whl file without network
    --user               Force user directory install (~/.local/share/soulwave)
    --system             Force system directory install (/opt/soulwave or RPM)
    --wheel              Force wheel install even on RPM distributions
    --uninstall          Uninstall Soulwave cleanly from the system
    --help, -h           Show help and usage message
```

---

### Recommended Audio Utilities

Soulwave functions out of the box with an internal mock player and audio fallback. To enable active MPRIS player tracking and real-time audio spectrum visualization:

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
# Upgrade to the latest release:
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash

# For manual RPM installs:
sudo dnf upgrade ./soulwave-*.rpm

# Clean uninstallation:
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --uninstall

# Or on Fedora (if installed via RPM):
sudo dnf remove soulwave
```

---

## Verification & Health Check

Soulwave provides a built-in health check flag to verify runtime imports, stylesheet package data, and headless UI mounting:

```bash
soulwave --check
```

On a healthy installation, this outputs:
```text
Checking Soulwave installation...
✓ Soulwave v0.1.1 health check passed (all runtime dependencies and UI stylesheets verified).
```

---

## Getting Started

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

## Keybindings

| Key | Function | Description |
|:---:|:---|:---|
| <kbd>Space</kbd> | **Play / Pause** | Toggle playback on the active media player |
| <kbd>n</kbd> | **Next Track** | Skip to next track with smooth transition easing |
| <kbd>p</kbd> | **Previous Track** | Return to previous track |
| <kbd>→</kbd> | **Seek Forward** | Jump forward by 5 seconds |
| <kbd>←</kbd> | **Seek Backward** | Jump backward by 5 seconds |
| <kbd>↑</kbd> / <kbd>+</kbd> | **Volume Up** | Increase player volume by 5% |
| <kbd>↓</kbd> / <kbd>-</kbd> | **Volume Down** | Decrease player volume by 5% |
| <kbd>s</kbd> | **Shuffle** | Toggle player shuffle mode |
| <kbd>r</kbd> | **Repeat / Loop** | Cycle repeat mode (*Off → Track → Playlist*) |
| <kbd>Tab</kbd> | **Switch Player** | Cycle through active players (*Spotify, Firefox, Chrome, Demo*) |
| <kbd>l</kbd> | **Toggle Lyrics** | Show / hide the synchronized scrolling lyrics panel |
| <kbd>v</kbd> | **Toggle Visualizer** | Show / hide the CAVA audio frequency spectrum |
| <kbd>t</kbd> | **Cycle Theme** | Cycle themes (*Night → Sunset → Mint → Sakura → Cyberpunk → Mono*) |
| <kbd>m</kbd> | **Mini Mode** | Toggle between full dashboard and ultra-compact widget |
| <kbd>[</kbd> | **Lyrics Offset -** | Shift lyrics 100ms earlier (saved per song) |
| <kbd>]</kbd> | **Lyrics Offset +** | Shift lyrics 100ms later (saved per song) |
| <kbd>q</kbd> | **Quit** | Exit Soulwave |
| **Mouse Click** | **Direct Timeline Seek** | Click anywhere along the timeline bar to seek immediately |

---

## The Mascot & Companions

Soulwave features an animated retro scene with a grooving main soul mascot and three soul companions rendered in truecolor ANSI half-blocks (`▀`, `▄`).

```text
   [Pip]              [Soul]              [Nova]         [Mochi]
 Gentle Bob        Groovy Dance       Energetic Hop    Sleepy Rock
```

### Deterministic Dance Cycle
- Derived from a strict monotonic clock (`time.monotonic()`), completely decoupled from UI render ticks or audio jitter.
- Cycles through a 4-beat sequence over 2.2 seconds:
  1. **Beat 1**: Smooth horizontal lean to the left.
  2. **Beat 2**: Rhythmic vertical bounce downward.
  3. **Beat 3**: Smooth horizontal lean to the right.
  4. **Beat 4**: Upright center rebound.
- Floating musical notes rise organically as the music plays.

### Transition Easing
When changing tracks or waiting for stream metadata, the mascot enters a `TRACK_TRANSITION` state that smoothly dampens motion down to a calm resting pose, resuming the dance only when the new song confirms active playback.

---

## Lyrics Synchronization

1. **LRCLIB Integration**: Automatically queries synchronized `.lrc` timestamps using song title, artist, and duration.
2. **Plain-Text Fallback**: If synchronized timestamps are unavailable, plain lyrics are progressively scrolled based on track progress.
3. **No-Lyrics Fallback**: If no lyrics exist, Soulwave switches into an ambient mascot groove showcase.
4. **Local Disk Caching**: Lyrics are stored locally in `~/.cache/soulwave/lyrics/` to prevent duplicate API requests.
5. **Manual Offset Memory**: Fine-tune lyric timing using <kbd>[</kbd> and <kbd>]</kbd> (±100ms per press). Offsets are remembered across sessions for each track.

---

## Audio Spectrum Visualizer

Soulwave embeds a real-time 16-bar frequency spectrum powered by [CAVA](https://github.com/karlstav/cava):

- Connects automatically via a private FIFO pipe in `/tmp/soulwave-cava-*.fifo`.
- Auto-detects audio output devices through PulseAudio, PipeWire, or ALSA.
- Features peak smoothing and graceful decay animation when playback pauses.
- If CAVA is not installed, Soulwave displays a subtle rhythm-based ambient visualizer so the interface remains cohesive.

---

## Themes & Colors

Soulwave includes 6 handcrafted color palettes:

- **Night** *(Default)*: Midnight deep navy, slate gray, electric violet, and soft cyan.
- **Sunset**: Dusk purple, warm peach, vibrant coral, and golden hour amber.
- **Mint**: Matcha dark teal, fresh forest green, and crisp cool mint.
- **Sakura**: Cherry blossom plum, soft lilac, and pastel blossom pink.
- **Cyberpunk**: Deep onyx, neon magenta, electric cyan, and laser yellow.
- **Mono**: Minimalist high-contrast carbon slate and chalk white.

Press <kbd>t</kbd> to cycle themes at any time. Soulwave also generates an algorithmic dynamic accent color for every unique song title and artist, subtly tinting progress bars and mascots.

---

## Mini Mode

Press <kbd>m</kbd> or launch with `soulwave --mini` to switch to Mini Mode:

```text
▶  Cyberpunk 2077 OST - I Really Want to Stay At Your House   02:14 / 04:06 ━━━━●──────── [Spotify]
```

- Collapses the multi-panel layout into an ultra-compact single widget.
- Perfect for narrow tmux panes, i3/sway/hyprland bars, or floating terminal scratchpads.
- Retains all playback keybindings (<kbd>Space</kbd>, <kbd>n</kbd>, <kbd>p</kbd>, seeks, volume).

---

## Configuration Guide

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

## Player Setup & Permissions

Soulwave uses the standard Linux MPRIS D-Bus interface. Most media players work out of the box:

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

## Troubleshooting & FAQ

### Soulwave shows "No Player Connected"
1. Start playback in your browser or desktop music player.
2. Run `playerctl status` in a terminal. If `playerctl` sees the player, Soulwave connects instantly.
3. If using Firefox, ensure an audio or video tab is actively playing.

### Total time displays `--:--`
- Some live streams (radio, podcasts) do not report total track duration over MPRIS. Soulwave safely protects timeline position and displays live elapsed time without crashing.

### Lyrics timing is slightly ahead or behind
- Press <kbd>[</kbd> to shift lyrics 100ms earlier or <kbd>]</kbd> to shift lyrics 100ms later. Soulwave saves your offset for that track.

### CAVA visualizer is flat
- Verify CAVA works independently by running `cava` in a terminal.
- If using PipeWire or PulseAudio, ensure your default audio sink is unmuted.

### Verify Installation Health
- Run `soulwave --check` to verify that all Python dependencies and stylesheet package assets are installed properly.

---

## Packaging & Releases

Soulwave features an automated, production-ready release pipeline:

- **Fedora RPM Specification**: [`packaging/rpm/soulwave.spec`](packaging/rpm/soulwave.spec)
  - Isolated `/usr/lib/soulwave/vendor` runtime.
  - Native `/usr/bin/soulwave` launcher.
- **Local RPM Builder**: [`packaging/rpm/build_rpm.sh`](packaging/rpm/build_rpm.sh)
- **GitHub Actions Workflow**: [`.github/workflows/release.yml`](.github/workflows/release.yml)
  - Multi-version Python test matrix (3.10 - 3.13).
  - Wheel and sdist distribution builds with verified package data.
  - Native Fedora container RPM build.
  - Automated SHA-256 `checksums.txt` generation.
  - Automated GitHub Releases publication on version tag pushes (`v*`).

---

## Running Tests

Soulwave includes an automated test suite covering unit tests, D-Bus integration, headless UI acceptance tests, animation timing, and packaging validation:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all 111 tests
pytest tests/ -v
```

---

## License

- **License**: [MIT License](LICENSE).
- Powered by [Textual](https://github.com/Textualize/textual), [Rich](https://github.com/Textualize/rich), [LRCLIB](https://lrclib.net), and [CAVA](https://github.com/karlstav/cava).
