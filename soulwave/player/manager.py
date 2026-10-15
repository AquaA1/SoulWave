"""Player manager for auto-detection and multi-player switching."""

from __future__ import annotations

from typing import Callable, List, Optional
from .base import BasePlayer, PlayerState, PlaybackStatus
from .mpris import MPRISPlayer
from .mock_player import MockPlayer


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
        self._current_player: BasePlayer = self.mock_player if force_demo else MPRISPlayer(on_state_change=on_state_change)
        self._active_player_name: str = "demo" if force_demo else ""
        self._available_players: List[str] = []
        self._player_index: int = 0
        self.refresh_players()

    @property
    def current_player(self) -> BasePlayer:
        return self._current_player

    @property
    def is_demo(self) -> bool:
        return isinstance(self._current_player, MockPlayer)

    def refresh_players(self) -> List[str]:
        """Detect running MPRIS players and update player list."""
        if self.force_demo:
            self._available_players = ["Soulwave Demo"]
            return self._available_players

        detected = MPRISPlayer.list_players()
        self._available_players = detected

        if not detected:
            # If no MPRIS player is running, keep or fallback to mock
            if not isinstance(self._current_player, MockPlayer):
                # If current MPRIS player is disconnected, switch to mock demo
                pass
        else:
            # If user has a preferred player that is in detected, use it
            if self.preferred_player and self.preferred_player in detected:
                if self._active_player_name != self.preferred_player:
                    self.select_player(self.preferred_player)
            elif not self._active_player_name or self._active_player_name not in detected:
                self.select_player(detected[0])

        return self._available_players

    def select_player(self, player_name: str) -> None:
        """Switch to a specific player name."""
        if hasattr(self._current_player, "close"):
            self._current_player.close()

        if player_name == "Soulwave Demo" or self.force_demo:
            self._current_player = self.mock_player
            self._active_player_name = "Soulwave Demo"
            return

        self._active_player_name = player_name
        self._current_player = MPRISPlayer(player_name=player_name, on_state_change=self.on_state_change)
        if player_name in self._available_players:
            self._player_index = self._available_players.index(player_name)

    def switch_next_player(self) -> str:
        """Switch to the next available media player in circular order."""
        self.refresh_players()
        all_options = list(self._available_players)
        all_options.append("Soulwave Demo")

        if not all_options:
            self.select_player("Soulwave Demo")
            return "Soulwave Demo"

        self._player_index = (self._player_index + 1) % len(all_options)
        selected = all_options[self._player_index]
        self.select_player(selected)
        return selected

    def get_state(self) -> PlayerState:
        """Fetch current player state, falling back to demo if disconnected."""
        if self.force_demo:
            return self.mock_player.get_state()

        state = self._current_player.get_state()
        if state.status == PlaybackStatus.DISCONNECTED:
            # Try refreshing players
            players = MPRISPlayer.list_players()
            if players:
                self.select_player(players[0])
                state = self._current_player.get_state()
            else:
                # If no system players available at all, fallback to demo player
                self._current_player = self.mock_player
                self._active_player_name = "Soulwave Demo"
                state = self.mock_player.get_state()

        return state
