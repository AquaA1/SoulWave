"""Real-time CAVA audio spectrum reader for Soulwave.

Spawns CAVA in raw/ASCII mode with a per-process config file pointing at the
default PulseAudio / PipeWire monitor source.  Reads bar heights line-by-line
in a daemon thread, exposes the latest frame as a list[float] in [0.0, 1.0].

If CAVA is not installed, or fails to start, the reader silently stays idle
so the visualizer falls back to the synthetic wave pattern.
"""

from __future__ import annotations

import configparser
import io
import os
import shutil
import subprocess
import tempfile
import threading
from typing import List, Optional


_NUM_BARS = 36          # must match VisualizerView num_bars
_ASCII_MAX = 1000       # must match cava config ascii_max_range
_CAVA_BIN = shutil.which("cava")


class CavaReader:
    """Runs CAVA and exposes the latest bar-height frame."""

    def __init__(self, num_bars: int = _NUM_BARS) -> None:
        self.num_bars = num_bars
        self._bars: List[float] = [0.0] * num_bars
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None  # type: ignore[type-arg]
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._config_path: Optional[str] = None

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self) -> bool:
        """Start CAVA subprocess.  Returns True if successfully launched."""
        if not _CAVA_BIN:
            return False
        if self._running:
            return True

        self._config_path = self._write_config()
        try:
            self._proc = subprocess.Popen(
                [_CAVA_BIN, "-p", self._config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except OSError:
            return False

        self._running = True
        self._thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="cava-reader",
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stop CAVA subprocess and clean up."""
        self._running = False
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        if self._config_path and os.path.exists(self._config_path):
            try:
                os.unlink(self._config_path)
            except OSError:
                pass
        self._config_path = None

    @property
    def bars(self) -> List[float]:
        """Return latest bar heights normalised to [0.0, 1.0]."""
        with self._lock:
            return list(self._bars)

    @property
    def is_running(self) -> bool:
        return self._running and self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _write_config(self) -> str:
        """Write a minimal CAVA config to a temp file and return its path."""
        cfg_lines = [
            "[general]",
            f"bars = {self.num_bars}",
            "framerate = 60",
            "noise_reduction = 55",
            "",
            "[input]",
            "method = pulse",
            "source = auto",
            "",
            "[output]",
            "method = raw",
            "raw_target = /dev/stdout",
            "data_format = ascii",
            f"ascii_max_range = {_ASCII_MAX}",
            "bar_delimiter = 59",   # ';'
            "frame_delimiter = 10",  # newline
        ]
        fd, path = tempfile.mkstemp(prefix="soulwave_cava_", suffix=".cfg")
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(cfg_lines) + "\n")
        return path

    def _reader_loop(self) -> None:
        """Read CAVA stdout line-by-line; parse ';'-separated ASCII integers."""
        assert self._proc is not None
        assert self._proc.stdout is not None

        reader = io.TextIOWrapper(self._proc.stdout, encoding="ascii", errors="replace")
        try:
            while self._running:
                line = reader.readline()
                if not line:
                    break  # CAVA exited
                line = line.strip()
                if not line:
                    continue
                try:
                    values = [int(x) for x in line.split(";") if x]
                except ValueError:
                    continue
                if len(values) != self.num_bars:
                    continue
                normalised = [min(1.0, v / _ASCII_MAX) for v in values]
                with self._lock:
                    self._bars = normalised
        except Exception:
            pass
        finally:
            self._running = False
