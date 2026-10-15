"""Mock player for demo mode and headless unit testing."""

from __future__ import annotations

import time
from typing import List
from .base import (
    BasePlayer,
    PlayerState,
    PlaybackStatus,
    LoopStatus,
    ShuffleStatus,
    TrackMetadata,
)
from .interpolator import PositionInterpolator


DEMO_TRACKS = [
    {
        "title": "Midnight Coffee",
        "artist": "Soulwave Chill",
        "album": "Lo-Fi Dreams Vol. 1",
        "duration": 174.0,
        "lyrics": """[00:05.20] Soft glow on the window pane
[00:12.40] Raindrops falling like a calm refrain
[00:20.10] Headphones on, world fades away
[00:28.50] Floating in a cozy shade of grey
[00:36.00] (Instrumental beat grooving)
[00:48.30] Pixel dreams and tape decay
[00:56.80] Warm mug in my hand today
[01:05.10] Neon stars are drifting light
[01:13.40] We're vibing through the peaceful night
[01:25.00] Little soul is humming low
[01:33.20] Watching all the shadows go
[01:42.00] Take a breath and let it be
[01:50.50] Coffee, beats, and poetry
[02:02.00] (Gentle fading chords)
[02:20.00] Goodnight terminal
""",
    },
    {
        "title": "Synthwave Sunset",
        "artist": "Neon Phantom",
        "album": "Cyber Highway '84",
        "duration": 210.0,
        "lyrics": """[00:08.00] Driving down the grid tonight
[00:15.50] Chrome horizon burning bright
[00:24.00] Analog feelings, digital heart
[00:32.00] Never thought we'd drift apart
[00:42.00] Retro pulse in eighty-four
[00:50.00] Can you hear the engines roar?
[01:02.00] Neon sunset, violet skies
[01:12.00] Reflections dancing in your eyes
""",
    },
    {
        "title": "Starlight Lullaby",
        "artist": "Cosmic Sprout",
        "album": "Galactic Garden",
        "duration": 145.0,
        "lyrics": """[00:06.00] Quiet little galaxy
[00:14.00] Sleeping under velvet trees
[00:22.00] Floating softly in the breeze
[00:30.00] Whispers from the seven seas
[00:42.00] Count the stars until you smile
[00:50.00] Rest your headphones for a while
""",
    },
]


class MockPlayer(BasePlayer):
    """Simulated media player with real-time progression for demo and tests."""

    def __init__(self, tracks: List[dict] | None = None) -> None:
        self.tracks = tracks or DEMO_TRACKS
        self.track_index = 0
        self.status = PlaybackStatus.PLAYING
        self.volume = 0.85
        self.loop = LoopStatus.PLAYLIST
        self.shuffle = ShuffleStatus.OFF
        self.interpolator = PositionInterpolator()
        self._current_pos = 0.0
        self._last_time = time.monotonic()
        self._sync_interpolator()

    @property
    def current_track_dict(self) -> dict:
        return self.tracks[self.track_index % len(self.tracks)]

    def _sync_interpolator(self) -> None:
        duration = self.current_track_dict["duration"]
        self.interpolator.sync(self._current_pos, self.status, duration)

    def _update_position(self) -> None:
        now = time.monotonic()
        if self.status == PlaybackStatus.PLAYING:
            delta = now - self._last_time
            self._current_pos += delta
            duration = self.current_track_dict["duration"]
            if self._current_pos >= duration:
                if self.loop == LoopStatus.TRACK:
                    self._current_pos = 0.0
                else:
                    self.next_track()
                    return
        self._last_time = now

    def get_state(self) -> PlayerState:
        self._update_position()
        t = self.current_track_dict
        meta = TrackMetadata(
            title=t["title"],
            artist=t["artist"],
            album=t["album"],
            duration_seconds=t["duration"],
            track_id=f"demo:{self.track_index}",
        )
        self.interpolator.sync(self._current_pos, self.status, t["duration"])
        return PlayerState(
            player_name="Soulwave Demo",
            status=self.status,
            metadata=meta,
            position_seconds=self._current_pos,
            volume=self.volume,
            loop=self.loop,
            shuffle=self.shuffle,
            can_control=True,
            can_seek=True,
            can_go_next=True,
            can_go_previous=True,
        )

    def get_interpolated_position(self) -> float:
        return self.interpolator.get_position()

    def get_current_lyrics(self) -> str:
        return self.current_track_dict.get("lyrics", "")

    def play_pause(self) -> None:
        self._update_position()
        if self.status == PlaybackStatus.PLAYING:
            self.status = PlaybackStatus.PAUSED
        else:
            self.status = PlaybackStatus.PLAYING
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def play(self) -> None:
        self.status = PlaybackStatus.PLAYING
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def pause(self) -> None:
        self._update_position()
        self.status = PlaybackStatus.PAUSED
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def next_track(self) -> None:
        self.track_index = (self.track_index + 1) % len(self.tracks)
        self._current_pos = 0.0
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def previous_track(self) -> None:
        if self._current_pos > 3.0:
            self._current_pos = 0.0
        else:
            self.track_index = (self.track_index - 1) % len(self.tracks)
            self._current_pos = 0.0
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def seek(self, offset_seconds: float) -> None:
        self._update_position()
        duration = self.current_track_dict["duration"]
        self._current_pos = max(0.0, min(self._current_pos + offset_seconds, duration))
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def set_position(self, target_seconds: float) -> None:
        duration = self.current_track_dict["duration"]
        self._current_pos = max(0.0, min(target_seconds, duration))
        self._last_time = time.monotonic()
        self._sync_interpolator()

    def set_volume(self, target_volume: float) -> None:
        self.volume = max(0.0, min(1.0, target_volume))

    def cycle_loop(self) -> None:
        order = [LoopStatus.NONE, LoopStatus.TRACK, LoopStatus.PLAYLIST]
        idx = order.index(self.loop)
        self.loop = order[(idx + 1) % len(order)]

    def toggle_shuffle(self) -> None:
        self.shuffle = ShuffleStatus.ON if self.shuffle == ShuffleStatus.OFF else ShuffleStatus.OFF
