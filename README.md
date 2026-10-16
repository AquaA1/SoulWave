# 🎧 Soulwave

> A cute terminal music controller for Linux. A tiny pixel-art soul with headphones vibes along to whatever you're playing, and you control everything without ever opening the browser.

---

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

---

## ✨ Features

- **Any Linux Player**: Auto-detects and controls Spotify, Firefox, Chrome, Brave, MPV, VLC, Amberol, or any MPRIS-compatible player over D-Bus with zero setup.
- **The Grooving Mascot**: A chunky pixel-art ghost soul wearing glowing headphones rendered in truecolor with half-block characters (`▀ ▄`). It head-bobs, sways, reacts to track changes, seeks, volume adjustments, and takes gentle naps when paused.
- **"Feels Like It's Listening" Rhythm Engine**: Per-song tempos derived deterministically from song titles, subtle organic swing, and floating musical notes (`♪ ♫ ♬`) drifting into the air.
- **Dynamic Themes & Accents**: Curated themes (*Night, Sunset, Mint, Sakura, Cyberpunk, Mono*) combined with a dynamic accent color generated uniquely for each song.
- **Synced Lyrics Panel**: Automatic scrolling `.lrc` lyrics from LRCLIB, centering the active lyric line, with local caching and `[` / `]` manual timing offset controls (±100ms).
- **Smooth Local Interpolation**: Sub-second smooth progress timeline without spamming D-Bus, with full **mouse click-to-seek** support.
- **Mini Mode (`m`)**: Collapses the interface into a sleek, ultra-compact widget perfect for tmux splits, i3/sway/hyprland sidebars, or small terminal panes.
- **Built-in Demo Mode (`--demo`)**: Try out Soulwave immediately even without an active media player running!

---

## 🚀 Installation

### One-Liner Install (Recommended)

Install Soulwave with a single command — no virtual environment activation, alias creation, or PATH editing required:

```bash
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash
```

Once installed, simply type:

```bash
soulwave
```

#### Prefer to inspect the installer first?

```bash
curl -fsSL -o install.sh https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh
less install.sh
bash install.sh
```

---

### Fedora Linux (Native RPM)

On Fedora, CentOS Stream, RHEL, Rocky, and AlmaLinux, the curl installer automatically downloads and installs the native RPM package with isolated application runtime at `/usr/lib/soulwave` and standard launcher at `/usr/bin/soulwave`:

```bash
# Via curl installer (auto-detects Fedora and installs native RPM)
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash

# Or install manually from a downloaded release RPM:
sudo dnf install ./soulwave-*.noarch.rpm
```

### Other Linux Distributions (Ubuntu, Debian, Arch, openSUSE)

On non-RPM distributions, `install.sh` automatically configures a self-contained, PEP 668-compliant application runtime in `/opt/soulwave` with an executable launcher in `/usr/local/bin/soulwave` (or `~/.local/share/soulwave` with `~/.local/bin/soulwave` if installing as non-root without sudo).

### Optional Audio Tools

Soulwave runs out of the box with an internal mock player and audio fallback. To enable live MPRIS player synchronization and audio frequency spectrum visualization, install `playerctl` and `cava`:

- **Fedora / RHEL**: `sudo dnf install playerctl cava`
- **Ubuntu / Debian**: `sudo apt install playerctl cava`
- **Arch Linux**: `sudo pacman -S playerctl cava`

---

### Updating & Upgrading

To update Soulwave to the latest release:

```bash
# Re-run the installer anytime
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash

# On Fedora (if installed via RPM):
sudo dnf upgrade soulwave
```

---

### Uninstallation

To remove Soulwave cleanly from your system:

```bash
curl -fsSL https://raw.githubusercontent.com/AquaA1/SoulWave/main/install.sh | bash -s -- --uninstall

# Or on Fedora:
sudo dnf remove soulwave
```

---

## 🎮 Launching & Options

```bash
# Launch normal auto-detect mode (picks up your active media player)
soulwave

# Or launch demo mode to explore with built-in lo-fi / synthwave tracks & lyrics
soulwave --demo

# Launch directly in compact mini mode
soulwave --mini

# Specify your favorite theme or preferred player
soulwave --theme sunset --player spotify
```

---

## ⌨️ Keybindings

| Key | Action |
|:---:|:---|
| <kbd>Space</kbd> | Toggle Play / Pause |
| <kbd>n</kbd> / <kbd>p</kbd> | Next / Previous track |
| <kbd>→</kbd> / <kbd>←</kbd> | Seek forward / backward (±5s) |
| <kbd>↑</kbd> / <kbd>↓</kbd> or <kbd>+</kbd> / <kbd>-</kbd> | Volume up / down (±5%) |
| <kbd>s</kbd> | Toggle Shuffle mode |
| <kbd>r</kbd> | Cycle Loop mode (*None → Track → Playlist*) |
| <kbd>Tab</kbd> | Switch between active players (*Spotify, Browser, Demo*) |
| <kbd>l</kbd> | Toggle Synced Lyrics panel |
| <kbd>v</kbd> | Toggle Audio Visualizer spectrum |
| <kbd>t</kbd> | Cycle Theme (*Night, Sunset, Mint, Sakura, Cyberpunk, Mono*) |
| <kbd>m</kbd> | Toggle Mini Mode |
| <kbd>[</kbd> / <kbd>]</kbd> | Adjust lyric synchronization offset (±100ms) |
| <kbd>q</kbd> | Quit Soulwave |
| **Mouse Click** | Click anywhere along the timeline bar to seek directly! |

---

## 🎨 Themes

Cycle through themes on the fly by pressing <kbd>t</kbd>, or configure your favorite in `~/.config/soulwave/config.toml`:

- **Night**: Midnight navy, slate, violet, soft cyan.
- **Sunset**: Dusk violet, warm peach, coral, and golden hour amber.
- **Mint**: Matcha dark green, fresh forest, and cool mint.
- **Sakura**: Cherry blossom plum, soft lilac, and pastel blossom pink.
- **Cyberpunk**: Deep onyx, neon magenta, electric cyan, and laser yellow.
- **Mono**: Minimalist slate carbon and chalk white.

---

## ⚙️ Configuration

Soulwave automatically creates a configuration file at `~/.config/soulwave/config.toml` (or follows `$XDG_CONFIG_HOME`).

```toml
# ~/.config/soulwave/config.toml

[app]
theme = "night"
show_lyrics = true
show_visualizer = true
mini_mode = false
mascot_skin = "classic"
default_player = "spotify"
fps = 12

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
```

---

## 🧪 Running Tests

Soulwave comes with a comprehensive test suite including headless TUI integration tests:

```bash
pytest tests/ -v
```

---

## 📄 License

MIT License. Crafted with cozy vibes for terminal lovers everywhere.
