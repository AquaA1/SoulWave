"""Base abstractions and data models for media players."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PlaybackStatus(str, Enum):
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    DISCONNECTED = "Disconnected"


class LoopStatus(str, Enum):
    NONE = "None"
    TRACK = "Track"
    PLAYLIST = "Playlist"


class ShuffleStatus(str, Enum):
    OFF = "Off"
    ON = "On"


@dataclass
class TrackMetadata:
    """Track information returned by the player."""
    title: str = "No Track Playing"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration_seconds: float = 0.0
    art_url: Optional[str] = None
    track_id: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return self.title == "No Track Playing" or not self.title


@dataclass
class PlayerState:
    """Snapshot of player state at a given moment."""
    player_name: str = "None"
    status: PlaybackStatus = PlaybackStatus.DISCONNECTED
    metadata: TrackMetadata = field(default_factory=TrackMetadata)
    position_seconds: float = 0.0
    volume: float = 1.0  # 0.0 to 1.0
    loop: LoopStatus = LoopStatus.NONE
    shuffle: ShuffleStatus = ShuffleStatus.OFF
    can_control: bool = False
    can_seek: bool = False
    can_go_next: bool = False
    can_go_previous: bool = False


class BasePlayer(ABC):
    """Abstract interface for audio player controllers."""

    @abstractmethod
    def get_state(self) -> PlayerState:
        """Fetch current player state."""
        pass

    @abstractmethod
    def play_pause(self) -> None:
        """Toggle playback."""
        pass

    @abstractmethod
    def play(self) -> None:
        """Resume playback."""
        pass

    @abstractmethod
    def pause(self) -> None:
        """Pause playback."""
        pass

    @abstractmethod
    def next_track(self) -> None:
        """Skip to next track."""
        pass

    @abstractmethod
    def previous_track(self) -> None:
        """Skip to previous track."""
        pass

    @abstractmethod
    def seek(self, offset_seconds: float) -> None:
        """Seek relative to current position."""
        pass

    @abstractmethod
    def set_position(self, target_seconds: float) -> None:
        """Set absolute position in seconds."""
        pass

    @abstractmethod
    def set_volume(self, target_volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        pass

    @abstractmethod
    def cycle_loop(self) -> None:
        """Cycle loop status (None -> Track -> Playlist -> None)."""
        pass

    @abstractmethod
    def toggle_shuffle(self) -> None:
        """Toggle shuffle on/off."""
        pass

    def get_interpolated_position(self) -> float:
        """Returns smoothed playback or optimistic seek position."""
        return self.get_state().position_seconds

    def get_confirmed_position(self) -> float:
        """Returns the authoritative position confirmed by the player."""
        return self.get_state().position_seconds

    def close(self) -> None:
        """Release any persistent connections or background threads."""
        pass
