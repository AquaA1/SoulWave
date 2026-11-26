# Changelog

All notable changes to **SoulWave** are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2026-11-27

### Added
- **Persistent Group Dance Lyrics Fallback**:
  - Immediate group dance animation on track change while lyrics are searching.
  - Centered `SEARCHING FOR LYRICS...` status indicator that keeps the companion animation running smoothly without hiding or interrupting Pip, Nova, and Mochi.
  - Graceful `LYRICS NOT FOUND` banner on missing or failed lyrics requests that auto-hides after ~2.5 seconds while continuing the dance indefinitely.
  - Slower or out-of-order background requests are cancelled on track transitions, preventing stale track metadata from overwriting active UI.
  - Seamless animated transition to synchronized or plain lyrics whenever lyrics become available.
- **Interactive Linux Setup Assistant (`install.sh`)**:
  - Pre-flight system diagnostics table displayed prior to package installation.
  - 4-way interactive dependency resolution: `[1] Auto-install via sudo`, `[2] Manual instructions`, `[3] Skip dependency`, `[4] Exit`.
  - Distribution-accurate package manager mapping across `apt` (Debian/Ubuntu/Mint), `dnf` (Fedora/RHEL), `pacman` (Arch/Manjaro), and `zypper` (openSUSE).
  - New `--repair` flag for safely reinstalling and repairing binaries without overwriting user configs.
  - Edge-case hardening: validation of `--version` and `--file` arguments, local package format verification, and uninstallation cleaning system artifacts while preserving `~/.config/soulwave` and `~/.cache/soulwave`.
- **Comprehensive Diagnostic Command (`soulwave --doctor`)**:
  - Full system, environment, and runtime diagnostic audit command.
  - Checks Python architecture, core dependencies (`textual`, `rich`, `requests`, `syncedlyrics`), stylesheet resource integrity (`styles.tcss`), D-Bus session bus connectivity, `playerctl` CLI presence, active MPRIS players, `cava` visualizer, and audio server (PipeWire/PulseAudio).
- **Showcase Visuals & Architecture Documentation**:
  - Added hero multi-window desktop setup and close-up companion/lyrics screenshots to `README.md`.
  - Added system architecture diagram and comprehensive package-by-package guide for developers.

### Improved
- **MPRIS D-Bus Signal Handling**:
  - Implemented dynamic D-Bus `org.freedesktop.DBus.NameOwnerChanged` signal monitoring.
  - Instant discovery cache invalidation when players appear or disappear.
- **Position Interpolator**:
  - Precision sub-second wall-clock interpolation with drift compensation.
  - Smoother timeline updates during seek operations and track transitions.
- **Background Polling & Command Queue**:
  - Replaced blocking playerctl poll loops with asynchronous thread-safe queues.
  - Resolved UI freeze hazards during rapid track skips.

### Fixed
- **Startup Phantom Progress Bar**:
  - Resolved phantom progress advancement when track is PLAYING but position and duration are still 0.0 or unconfirmed.
- **Playerctl Unit Synchronization**:
  - Converted playerctl microsecond timestamp outputs to floating-point seconds.
  - Fixed status string normalization and duplicate timer synchronization conflicts.
- **Player Disconnection Lifecycle**:
  - Immediate transition to clean DISCONNECTED state when browser tabs or media players close.
  - Prevented PlayerManager reconnection loops and ghost player discovery.

### Changed
- Project version bumped to `0.2.0`.

### Known Issues
- Flatpak media players (e.g. Spotify installed via Flatpak) require standard D-Bus talk permissions:
  `flatpak override --user --talk-name=org.mpris.MediaPlayer2.spotify com.spotify.Client`

---

## [0.1.9] - 2026-11-22

### Fixed
- Playerctl progress bar tracking, seeking syntax, and prefix handling.
- Background polling thread shutdown race conditions.

---

## [0.1.8] - 2026-10-25

### Added
- Interactive audio utilities installer for `cava` and `playerctl`.
- In-app helpful notifications and hints for missing audio utilities.

---

## [0.1.7] - 2026-10-20

### Improved
- Universal standalone binary compatibility across Linux distributions.
- Robust rootless installer script with checksum verification.

---

## [0.1.6] - 2026-10-18

### Fixed
- Entrypoint relative import resolution in PyInstaller frozen bundles.

---

## [0.1.5] - 2026-10-17

### Added
- Standalone multi-architecture binaries (`x86_64` and `aarch64`).
- Single-command installer (`install.sh`).

---

## [0.1.0] - 2026-10-16

### Added
- Initial release of SoulWave: retro-futuristic terminal music controller with pixel-art soul companions, CAVA spectrum visualizer, synchronized lyrics, and universal MPRIS2 support.
