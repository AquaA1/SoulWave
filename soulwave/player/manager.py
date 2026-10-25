"""Player manager for auto-detection and multi-player switching."""

from __future__ import annotations

import logging
from typing import Callable, List, Optional
from .base import BasePlayer, PlayerState, PlaybackStatus
from .mpris import MPRISPlayer
from .mock_player import MockPlayer

logger = logging.getLogger(__name__)


class PlayerManager:
    """Coordinates active player, auto-detection, and player switching."""

    def __init__(
        self,
        preferred_player: str = "",
        force_demo: bool = False,
        on_state_change: Optional[Callable[[], None]] = None,
    ) -> None:
        self.preferred_player = preferred_player
        self.force_demo = force_demo
        self.on_state_change = on_state_change
        self.mock_player = MockPlayer()
        self._manual_demo_selected: bool = False
        self._active_player_name: str = "Soulwave Demo" if force_demo else ""
        self._available_players: List[str] = []
        self._player_index: int = 0

        if force_demo:
            self._current_player: BasePlayer = self.mock_player
        else:
            self._current_player = MPRISPlayer(
                player_name=preferred_player,
                on_state_change=self._on_subplayer_state_change,
            )
            self.refresh_players()

    @property
    def current_player(self) -> BasePlayer:
        return self._current_player

    @property
    def is_demo(self) -> bool:
        return self.force_demo or self._manual_demo_selected or isinstance(self._current_player, MockPlayer)

    def _on_subplayer_state_change(self) -> None:
        """Invoked when underlying MPRIS player or D-Bus bus reports state change."""
        if not self.force_demo and not self._manual_demo_selected:
            self.check_player_sync()
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    def find_best_player(self, detected: List[str]) -> Optional[str]:
        """Find the best player among detected, prioritizing actively PLAYING players."""
        if not detected:
            return None

        # 1. If preferred player is running and playing, prioritize it
        if self.preferred_player and self.preferred_player in detected:
            if MPRISPlayer.probe_player_status(self.preferred_player) == PlaybackStatus.PLAYING:
                return self.preferred_player

        # 2. Check if any detected player is actively PLAYING
        playing_candidates: List[str] = []
        for p in detected:
            if MPRISPlayer.probe_player_status(p) == PlaybackStatus.PLAYING:
                playing_candidates.append(p)

        if playing_candidates:
            if self.preferred_player and self.preferred_player in playing_candidates:
                return self.preferred_player
            # If current player is among playing, keep current
            if self._active_player_name in playing_candidates:
                return self._active_player_name
            return playing_candidates[0]

        # 3. If no player is actively playing, prefer user's preferred player if present
        if self.preferred_player and self.preferred_player in detected:
            return self.preferred_player

        # 4. Otherwise, if current active player is still in detected, stick with it
        if self._active_player_name and self._active_player_name in detected:
            return self._active_player_name

        # 5. Fallback to first detected player
        return detected[0]

    def refresh_players(self) -> List[str]:
        """Detect running MPRIS players and update player list."""
        if self.force_demo:
            self._available_players = ["Soulwave Demo"]
            return self._available_players

        detected = MPRISPlayer.list_players()
        self._available_players = detected

        if not detected:
            # If no MPRIS player is running, keep in disconnected/waiting state
            if not self._manual_demo_selected:
                self._active_player_name = ""
        else:
            best = self.find_best_player(detected)
            if best and (not self._active_player_name or self._active_player_name not in detected or best != self._active_player_name):
                self.select_player(best)

        return self._available_players

    def check_player_sync(self) -> bool:
        """Periodic or event-driven check ensuring Soulwave stays connected to the active player.

        Returns True if the active player was changed or reconnected.
        """
        if self.force_demo or self._manual_demo_selected:
            return False

        detected = MPRISPlayer.list_players()
        self._available_players = detected

        if not detected:
            if self._active_player_name != "":
                logger.info("All media players disconnected. Entering waiting state.")
                self._active_player_name = ""
                if hasattr(self._current_player, "close"):
                    self._current_player.close()
                self._current_player = MPRISPlayer(on_state_change=self._on_subplayer_state_change)
                return True
            return False

        best = self.find_best_player(detected)
        if not best:
            return False

        # If currently disconnected or no active player, switch immediately to best
        current_state = self._current_player.get_state()
        if not self._active_player_name or current_state.status == PlaybackStatus.DISCONNECTED:
            logger.info("Auto-connecting to detected player: %s", best)
            self.select_player(best)
            return True

        # If another player is PLAYING while current player is not PLAYING, auto-switch to it
        if best != self._active_player_name:
            best_status = MPRISPlayer.probe_player_status(best)
            if best_status == PlaybackStatus.PLAYING and current_state.status != PlaybackStatus.PLAYING:
                logger.info("Auto-switching to actively playing media player: %s", best)
                self.select_player(best)
                return True

        return False

    def select_player(self, player_name: str) -> None:
        """Switch to a specific player name."""
        if hasattr(self._current_player, "close"):
            self._current_player.close()

        if player_name == "Soulwave Demo" or self.force_demo:
            self._current_player = self.mock_player
            self._active_player_name = "Soulwave Demo"
            return

        self._active_player_name = player_name
        self._current_player = MPRISPlayer(
            player_name=player_name,
            on_state_change=self._on_subplayer_state_change,
        )
        if player_name in self._available_players:
            self._player_index = self._available_players.index(player_name)

    def switch_next_player(self) -> str:
        """Switch to the next available media player in circular order."""
        self.refresh_players()
        all_options = list(self._available_players)
        all_options.append("Soulwave Demo")

        if not all_options:
            self._manual_demo_selected = True
            self.select_player("Soulwave Demo")
            return "Soulwave Demo"

        self._player_index = (self._player_index + 1) % len(all_options)
        selected = all_options[self._player_index]
        self._manual_demo_selected = (selected == "Soulwave Demo")
        self.select_player(selected)
        return selected

    def get_state(self) -> PlayerState:
        """Fetch current player state."""
        if self.force_demo or self._manual_demo_selected:
            return self.mock_player.get_state()

        state = self._current_player.get_state()
        if state.status == PlaybackStatus.DISCONNECTED:
            # Check if any players appeared
            players = MPRISPlayer.list_players()
            if players:
                best = self.find_best_player(players)
                if best:
                    self.select_player(best)
                    state = self._current_player.get_state()

        return state

