"""Mascot animation state machine and deterministic rhythm dance engine."""

from __future__ import annotations

import hashlib
import math
import time
from enum import Enum
from typing import List, Optional

from .frames import (
    ANIMATIONS,
    FrameLibrary,
    IDLE_F0,
    PLAY_BOB_DOWN,
    PLAY_SWAY_LEFT,
    PLAY_SWAY_RIGHT,
    PAUSED_F0,
    SLEEP_F0,
)
from .sprite import PixelSprite, RGBColor


class MascotState(str, Enum):
    PLAYING = "playing"
    TRACK_TRANSITION = "track_transition"
    PAUSED = "paused"
    IDLE = "idle"
    RESUMING = "resuming"
    SLEEPING = "sleeping"
    TRACK_CHANGE = "track_transition"
    SEEKING = "seeking"
    VOL_UP = "vol_up"
    VOL_DOWN = "vol_down"


class MascotAnimator:
    """Controls mascot animations with a deterministic, smooth dance cycle and calm track transitions."""

    CYCLE_DURATION = 2.2  # Repeating dance cycle duration in seconds (~2.0-2.5s)

    def __init__(self, base_fps: int = 12) -> None:
        self.base_fps = base_fps
        self.state = MascotState.IDLE
        self._target_state = MascotState.IDLE
        self._transient_end_time: float = 0.0

        self.bpm: float = 100.0
        self.current_song_key: str = ""
        self.accent_color: Optional[RGBColor] = None

        self._dance_clock: float = 0.0
        self._last_tick_time: float = time.monotonic()
        self.speed_factor: float = 0.0
        self.amplitude_factor: float = 0.0
        self.sway_x: int = 0
        self.bounce_y: int = 0

    def set_track(self, title: str, artist: str) -> None:
        """Derive consistent, per-song BPM without resetting or accelerating the dance."""
        key = f"{artist.strip().lower()} - {title.strip().lower()}"
        if key == self.current_song_key:
            return

        self.current_song_key = key
        clean = title.strip()
        if not clean:
            # Temporary empty metadata during transition: stay calm!
            return

        # Compute deterministic BPM
        h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)
        self.bpm = 88.0 + (h % 37)

    def begin_track_transition(self) -> None:
        """Called when a next/prev track transition begins.
        Smoothly reduces speed and amplitude to settle into a calm pose."""
        self.state = MascotState.TRACK_TRANSITION
        self._target_state = MascotState.TRACK_TRANSITION

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
            if self.state == MascotState.TRACK_TRANSITION:
                self._target_state = MascotState.RESUMING
            else:
                self._target_state = MascotState.PLAYING
        else:
            self._target_state = MascotState.PAUSED

        # If currently in a transient reaction, don't interrupt until it completes
        if time.monotonic() < self._transient_end_time:
            return

        if self.state == MascotState.TRACK_TRANSITION:
            # Stay in transition until confirmed playing with a valid track
            if is_playing and has_track:
                self.state = MascotState.RESUMING
        elif self.state == MascotState.RESUMING:
            if not is_playing:
                self.state = self._target_state
        else:
            self.state = self._target_state

    def trigger_reaction(self, reaction: MascotState, duration: float = 0.8) -> None:
        """Trigger an ephemeral reaction (e.g. volume change)."""
        if reaction in (MascotState.TRACK_CHANGE, MascotState.TRACK_TRANSITION):
            self.begin_track_transition()
            return
        self.state = reaction
        self._transient_end_time = time.monotonic() + duration

    def set_accent_color(self, color: RGBColor | None) -> None:
        self.accent_color = color

    def tick(self) -> PixelSprite:
        """Advance animation based on monotonic clock and return current sprite."""
        now = time.monotonic()
        dt = max(0.0, min(0.2, now - self._last_tick_time))
        self._last_tick_time = now

        # Handle transient reaction expiration
        if self._transient_end_time > 0 and now >= self._transient_end_time:
            self._transient_end_time = 0.0
            self.state = self._target_state

        # Target speed and amplitude for smooth easing
        if self.state in (MascotState.PLAYING, MascotState.RESUMING):
            target_speed = 1.0
            target_amp = 1.0
        else:
            target_speed = 0.0
            target_amp = 0.0

        # Smooth exponential easing
        ease_rate = 3.5
        self.speed_factor += (target_speed - self.speed_factor) * min(1.0, dt * ease_rate)
        self.amplitude_factor += (target_amp - self.amplitude_factor) * min(1.0, dt * ease_rate)

        # Transition completion checks
        if self.state == MascotState.RESUMING and self.speed_factor >= 0.85:
            self.state = MascotState.PLAYING

        # Advance monotonic dance clock only according to current speed
        self._dance_clock += dt * self.speed_factor

        # Fixed 2.2-second repeating cycle
        norm_phase = (self._dance_clock % self.CYCLE_DURATION) / self.CYCLE_DURATION

        # Calculate restrained sway (max 1 char horizontally) and bounce (max 1 line vertically)
        self.sway_x = int(round(math.sin(norm_phase * 2 * math.pi) * 1.0 * self.amplitude_factor))
        self.bounce_y = int(round(abs(math.sin(norm_phase * 2 * math.pi)) * 1.0 * self.amplitude_factor))

        # Select pose based on state and phase
        if self.state in (MascotState.PLAYING, MascotState.RESUMING):
            if norm_phase < 0.25:
                ascii_frame = PLAY_SWAY_LEFT
            elif norm_phase < 0.50:
                ascii_frame = PLAY_BOB_DOWN
            elif norm_phase < 0.75:
                ascii_frame = PLAY_SWAY_RIGHT
            else:
                ascii_frame = IDLE_F0
        elif self.state == MascotState.TRACK_TRANSITION:
            ascii_frame = IDLE_F0
        elif self.state == MascotState.PAUSED:
            ascii_frame = PAUSED_F0
        elif self.state in (MascotState.IDLE, MascotState.SLEEPING):
            ascii_frame = SLEEP_F0
        elif self.state.value in ANIMATIONS:
            frames = ANIMATIONS[self.state.value]
            ascii_frame = frames[0]
        else:
            ascii_frame = IDLE_F0

        return FrameLibrary.create_sprite(ascii_frame, self.accent_color)
