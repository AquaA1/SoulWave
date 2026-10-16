"""Smooth local position interpolator for responsive playback timelines."""

from __future__ import annotations

import time
from typing import Optional
from .base import PlaybackStatus


class PositionInterpolator:
    """Interpolates audio playback position locally between MPRIS sync events.

    Maintains clean separation between confirmed playback position and desired
    seek/scrub position, preventing stale polling/transient drops from overwriting
    optimistic UI state.
    """

    SEEK_SETTLE_WINDOW: float = 1.5  # Seconds during which seeks are protected from stale reads

    def __init__(self) -> None:
        self._confirmed_position: float = 0.0
        self._last_sync_time: float = time.monotonic()
        self._status: PlaybackStatus = PlaybackStatus.STOPPED
        self._duration: float = 0.0

        # Optimistic seeking state
        self._desired_position: Optional[float] = None
        self._seek_time: float = 0.0
        self._seek_seq: int = 0

        # Stale-zero safeguard and diagnostics
        self._track_epoch: int = 0
        self._stale_zero_count: int = 0
        self._last_accepted_pos: float = 0.0
        self._last_reported_pos: float = 0.0
        self._last_accepted_time: float = time.monotonic()
        self._is_uncertain: bool = False

    @property
    def is_uncertain(self) -> bool:
        """True if position reports have been continuously rejected as stale/buffering."""
        return self._is_uncertain

    @property
    def diagnostics(self) -> dict:
        """Diagnostic state for telemetry and verification."""
        return {
            "epoch": self._track_epoch,
            "confirmed_position": self._confirmed_position,
            "estimated_position": self.get_position(),
            "last_reported_pos": self._last_reported_pos,
            "last_accepted_pos": self._last_accepted_pos,
            "stale_zero_count": self._stale_zero_count,
            "is_uncertain": self._is_uncertain,
        }

    @property
    def _last_position(self) -> float:
        """Backwards compatibility alias for _confirmed_position."""
        return self._confirmed_position

    @_last_position.setter
    def _last_position(self, val: float) -> None:
        self._confirmed_position = max(0.0, val)

    def sync(
        self,
        position_seconds: float,
        status: PlaybackStatus,
        duration_seconds: float,
        timestamp: float | None = None,
        is_authoritative: bool = False,
        epoch: int | None = None,
    ) -> None:
        """Sync with position reported by the media player.

        Rejects stale/transitional reports and out-of-order samples from previous epochs.
        """
        # If epoch is specified and does not match active epoch, discard sample completely
        if epoch is not None and epoch != self._track_epoch:
            return

        now = timestamp if timestamp is not None else time.monotonic()
        pos = max(0.0, position_seconds)
        self._status = status
        self._last_reported_pos = pos

        if duration_seconds > 0.0:
            self._duration = duration_seconds

        if is_authoritative:
            self._confirmed_position = pos
            self._last_sync_time = now
            self._desired_position = None
            self._last_accepted_pos = pos
            self._last_accepted_time = now
            self._stale_zero_count = 0
            self._is_uncertain = False
            return

        if self._desired_position is not None:
            elapsed = now - self._seek_time
            if elapsed < self.SEEK_SETTLE_WINDOW:
                # If player reports within 2.0s of desired target, player has caught up
                if abs(pos - self._desired_position) <= 2.0:
                    self._confirmed_position = pos
                    self._last_sync_time = now
                    self._desired_position = None
                    self._last_accepted_pos = pos
                    self._last_accepted_time = now
                    self._stale_zero_count = 0
                    self._is_uncertain = False
                else:
                    # Player is returning transitional/stale data (e.g. 0.0 on YouTube buffer).
                    # Reject overwriting the desired position.
                    pass
            else:
                # Settle window expired without catch-up, accept player's confirmed position
                self._confirmed_position = pos
                self._last_sync_time = now
                self._desired_position = None
                self._last_accepted_pos = pos
                self._last_accepted_time = now
                self._stale_zero_count = 0
                self._is_uncertain = False
        else:
            # When playing, handle transient buffering drops and coarse player polling jitter
            if self._status == PlaybackStatus.PLAYING:
                estimated = self.get_position(now)

                # Track-aware stale-zero safeguard:
                # If playback is active and the timeline has already advanced legitimately past 0.5s,
                # a repeated near-zero sample (pos <= 0.2s) while _confirmed_position is still near zero
                # indicates the browser's media element has not yet flushed its position pipeline.
                if pos <= 0.2 and estimated > 0.5:
                    self._stale_zero_count += 1
                    # If stale zero reports persist for more than 15 consecutive samples (~12 seconds),
                    # mark uncertainty and cap drift to avoid unbounded timeline deviation
                    if self._stale_zero_count > 15:
                        self._is_uncertain = True
                    return

                # Calculate lag/lead between local estimation and player report
                jitter_behind = estimated - pos

                # Detect if the player seeked backward in its own UI (pos jumped backward)
                is_backward_seek = (pos < self._last_accepted_pos - 0.5 and self._last_accepted_pos > 0.5)
                if is_backward_seek:
                    # User seeked backward directly in media player: snap to new position immediately!
                    self._confirmed_position = pos
                    self._last_sync_time = now
                    self._last_accepted_pos = pos
                    self._last_accepted_time = now
                    self._stale_zero_count = 0
                    self._is_uncertain = False
                    return

                # Firefox/Chromium often update D-Bus Position only once every ~1.5-2.0s.
                # If incoming position is within [0.0, 2.5s] behind our currently interpolated position,
                # do NOT snap backwards and rubberband. Let smooth interpolation continue.
                if 0.0 <= jitter_behind < 2.5:
                    if pos > 0.2:
                        self._stale_zero_count = 0
                        self._is_uncertain = False
                        self._last_accepted_pos = pos
                        self._last_accepted_time = now
                    return

            self._confirmed_position = pos
            self._last_sync_time = now
            self._last_accepted_pos = pos
            self._last_accepted_time = now
            self._stale_zero_count = 0
            self._is_uncertain = False

    def get_position(self, now: float | None = None) -> float:
        """Calculate the estimated current position with high sub-second precision.

        Returns desired position if user is seeking/scrubbing, otherwise smooth
        interpolated position from the confirmed player position.
        """
        current_time = now if now is not None else time.monotonic()

        if self._desired_position is not None:
            if self._status == PlaybackStatus.PLAYING:
                elapsed = max(0.0, current_time - self._seek_time)
                interpolated = self._desired_position + elapsed
                if self._duration > 0.0:
                    return min(interpolated, self._duration)
                return interpolated
            return self._desired_position

        if self._status != PlaybackStatus.PLAYING:
            return self._confirmed_position

        elapsed = current_time - self._last_sync_time
        interpolated = self._confirmed_position + max(0.0, elapsed)

        if self._duration > 0.0:
            return min(interpolated, self._duration)
        return interpolated

    def get_confirmed_position(self, now: float | None = None) -> float:
        """Authoritative confirmed position without optimistic seek override."""
        if self._status != PlaybackStatus.PLAYING:
            return self._confirmed_position

        current_time = now if now is not None else time.monotonic()
        elapsed = current_time - self._last_sync_time
        interpolated = self._confirmed_position + max(0.0, elapsed)
        if self._duration > 0.0:
            return min(interpolated, self._duration)
        return interpolated

    def start_seek(self, target_seconds: float, timestamp: float | None = None) -> float:
        """Initiate an absolute seek. Returns clamped desired position."""
        if self._duration > 0.0:
            target = max(0.0, min(target_seconds, self._duration))
        else:
            target = max(0.0, target_seconds)

        self._desired_position = target
        self._seek_time = timestamp if timestamp is not None else time.monotonic()
        self._seek_seq += 1
        return target

    def step_relative_seek(self, offset_seconds: float, timestamp: float | None = None) -> float:
        """Apply an ordered relative seek offset. Preserves rapid keypress accumulation."""
        now = timestamp if timestamp is not None else time.monotonic()
        base = self.get_position(now) if self._desired_position is None else self._desired_position
        target = base + offset_seconds
        if self._duration > 0.0:
            target = max(0.0, min(target, self._duration))
        else:
            target = max(0.0, target)

        self._desired_position = target
        self._seek_time = now
        self._seek_seq += 1
        return target

    def confirm_seek(self, confirmed_seconds: float, timestamp: float | None = None) -> None:
        """Mark seek as confirmed by player (e.g. via Seeked signal)."""
        self._confirmed_position = max(0.0, confirmed_seconds)
        self._last_sync_time = timestamp if timestamp is not None else time.monotonic()
        self._desired_position = None

    def cancel_seek(self) -> None:
        """Cancel pending seek and revert to confirmed position."""
        self._desired_position = None

    def clear_seek(self) -> None:
        """Clear desired position."""
        self._desired_position = None

    def reset_for_new_track(
        self,
        initial_position: float = 0.0,
        duration: float = 0.0,
        timestamp: float | None = None,
        epoch: int | None = None,
    ) -> None:
        """Reset interpolator state when track changes, avoiding stale previous track position."""
        if epoch is not None:
            self._track_epoch = epoch
        else:
            self._track_epoch += 1

        now = timestamp if timestamp is not None else time.monotonic()
        self._confirmed_position = max(0.0, initial_position)
        self._last_sync_time = now
        self._desired_position = None
        self._duration = max(0.0, duration)
        self._stale_zero_count = 0
        self._last_accepted_pos = self._confirmed_position
        self._last_accepted_time = now
        self._is_uncertain = False

    def is_seeking(self) -> bool:
        """True if an optimistic seek/scrub is pending."""
        return self._desired_position is not None

    def get_seek_seq(self) -> int:
        """Current seek sequence number."""
        return self._seek_seq

    def seek_immediate(self, target_seconds: float) -> None:
        """Instantly apply an optimistic seek (backwards compatible helper)."""
        self.start_seek(target_seconds)
        self._confirmed_position = self._desired_position or 0.0
        self._last_sync_time = time.monotonic()

    def get_progress_ratio(self) -> float:
        """Returns progress as a 0.0 to 1.0 fraction."""
        if self._duration <= 0.0:
            return 0.0
        return max(0.0, min(1.0, self.get_position() / self._duration))
