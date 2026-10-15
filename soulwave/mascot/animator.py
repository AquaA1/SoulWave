"""Mascot animation state machine and dynamic tempo rhythm engine."""

from __future__ import annotations

import hashlib
import random
import time
from enum import Enum
from typing import List, Optional

from .frames import ANIMATIONS, FrameLibrary
from .sprite import PixelSprite, RGBColor


class MascotState(str, Enum):
    IDLE = "idle"
    SLEEPING = "sleeping"
    PLAYING = "playing"
    PAUSED = "paused"
    TRACK_CHANGE = "track_change"
    SEEKING = "seeking"
    VOL_UP = "vol_up"
    VOL_DOWN = "vol_down"


class MascotAnimator:
    """Controls mascot animations, tempo calculation, and reactive behavior."""

    def __init__(self, base_fps: int = 12) -> None:
        self.base_fps = base_fps
        self.state = MascotState.IDLE
        self._target_state = MascotState.IDLE
        self._transient_end_time: float = 0.0

        self.bpm: float = 100.0
        self.current_song_key: str = ""
        self.accent_color: Optional[RGBColor] = None

        self._frame_index: int = 0
        self._last_frame_tick: float = time.monotonic()
        self._last_beat_time: float = time.monotonic()
        self._jitter_offset: float = 0.0

    def set_track(self, title: str, artist: str) -> None:
        """Derive consistent, per-song BPM from hash of track title and artist."""
        key = f"{artist.strip().lower()} - {title.strip().lower()}"
        if key == self.current_song_key:
            return

        self.current_song_key = key
        # Compute deterministic hash
        h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)
        # Map to a comfortable grooving tempo range: 88 to 124 BPM
        self.bpm = 88.0 + (h % 37)
        self.trigger_reaction(MascotState.TRACK_CHANGE, duration=0.9)

    def trigger_reaction(self, reaction: MascotState, duration: float = 0.8) -> None:
        """Trigger an ephemeral reaction (e.g. volume change, seek, track change)."""
        self.state = reaction
        self._transient_end_time = time.monotonic() + duration
        self._frame_index = 0

    def update_playback_state(
        self,
        is_playing: bool,
        is_connected: bool,
        has_track: bool = True,
    ) -> None:
        """Update base state according to playback status."""
        if not is_connected or not has_track:
            self._target_state = MascotState.SLEEPING
        elif is_playing:
            self._target_state = MascotState.PLAYING
        else:
            self._target_state = MascotState.PAUSED

        # If not currently playing a transient reaction, update state
        if time.monotonic() >= self._transient_end_time:
            self.state = self._target_state

    def set_accent_color(self, color: RGBColor | None) -> None:
        self.accent_color = color

    def tick(self) -> PixelSprite:
        """Advance animation based on tempo or idle timer and return current sprite."""
        now = time.monotonic()

        # Handle transient reaction expiration
        if self._transient_end_time > 0 and now >= self._transient_end_time:
            self._transient_end_time = 0.0
            self.state = self._target_state
            self._frame_index = 0

        frames = ANIMATIONS.get(self.state.value, ANIMATIONS["idle"])

        # Determine frame interval
        if self.state == MascotState.PLAYING:
            # Beat duration in seconds: 60 / BPM
            beat_sec = 60.0 / max(60.0, self.bpm)
            # 6 frames per beat cycle (down, sway-l, down, sway-r, hop, center)
            frame_interval = (beat_sec / len(frames)) + self._jitter_offset
        elif self.state in (MascotState.TRACK_CHANGE, MascotState.SEEKING, MascotState.VOL_UP):
            frame_interval = 0.12  # Snappy reactions
        elif self.state == MascotState.PAUSED:
            frame_interval = 0.65  # Very slow, sleepy breathing
        elif self.state == MascotState.SLEEPING:
            frame_interval = 1.2   # Dreamy slow zzz drift
        else:
            frame_interval = 0.35  # Relaxed idle float

        if now - self._last_frame_tick >= frame_interval:
            self._last_frame_tick = now
            self._frame_index = (self._frame_index + 1) % len(frames)

            # Introduce small natural variations when playing (imperfections/sway)
            if self.state == MascotState.PLAYING and self._frame_index == 0:
                # 10% chance of a micro-pause or double-bounce
                if random.random() < 0.15:
                    self._jitter_offset = random.uniform(-0.02, 0.03)
                else:
                    self._jitter_offset = 0.0

        current_ascii = frames[self._frame_index % len(frames)]
        return FrameLibrary.create_sprite(current_ascii, self.accent_color)
