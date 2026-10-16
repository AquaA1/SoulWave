"""Main Textual application for Soulwave."""

from __future__ import annotations

import os
import time
from pathlib import Path
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Label, Static, DataTable
from rich.text import Text
from rich.style import Style
from rich.table import Table

from ..config import Config
from ..player.base import PlaybackStatus, PlayerState
from ..player.manager import PlayerManager
from ..mascot.animator import MascotAnimator, MascotState
from ..mascot.scene import RoomScene
from ..theme.palettes import get_theme, cycle_theme_name, Theme
from ..theme.dynamic import get_song_accent_color, RGB
from ..lyrics.client import LyricsClient
from ..lyrics.cache import LyricsCache
from .widgets.mascot_view import MascotView
from .widgets.now_playing import NowPlayingView
from .widgets.progress_bar import ProgressBarView
from .widgets.controls import ControlsView
from .widgets.lyrics_panel import LyricsPanelView
from .widgets.visualizer import VisualizerView
from .widgets.companion_view import CompanionDanceView



class HelpModal(Screen):
    """Full-screen keybinding reference modal — press h, Enter, or Escape to close."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Close", priority=True),
        Binding("enter", "app.pop_screen", "Close", priority=True, show=False),
        Binding("h", "app.pop_screen", "Close", priority=True, show=False),
        Binding("q", "app.pop_screen", "Close", priority=True, show=False),
    ]

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #help-box {
        width: 56;
        height: auto;
        max-height: 90%;
        background: #1e293b;
        border: tall #38bdf8;
        padding: 1 2;
    }

    #help-title {
        content-align: center middle;
        width: 100%;
        color: #38bdf8;
        text-style: bold;
        margin-bottom: 1;
    }

    #help-table {
        width: 100%;
        height: auto;
    }
    """

    _SHORTCUTS = [
        ("Space",   "Play / Pause"),
        ("n",       "Next track"),
        ("p",       "Previous track"),
        ("→ / ←",   "Seek forward / backward 5 s"),
        ("↑ / ↓",   "Volume up / down"),
        ("Tab",     "Switch MPRIS player"),
        ("s",       "Toggle shuffle"),
        ("r",       "Cycle loop mode"),
        ("l",       "Toggle lyrics panel"),
        ("v",       "Toggle visualizer"),
        ("t",       "Cycle colour theme"),
        ("m",       "Toggle mini mode"),
        ("[ / ]",   "Lyrics offset −100 ms / +100 ms"),
        ("h",       "Show / close this help menu"),
        ("q",       "Quit Soulwave"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Static("🎧  SOULWAVE  SHORTCUTS", id="help-title")
            table = DataTable(id="help-table", show_header=False, show_cursor=False)
            yield table

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Key", "Action")
        for key, action in self._SHORTCUTS:
            table.add_row(
                Text(f" {key} ", style="bold white on #334155"),
                Text(f"  {action}", style="#cbd5e1"),
            )


class SoulwaveApp(App):
    """The Soulwave Terminal Music Controller application."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        Binding("space", "play_pause", "Play/Pause", priority=True),
        Binding("n", "next", "Next Track", priority=True),
        Binding("p", "previous", "Prev Track", priority=True),
        Binding("right", "seek_forward", "Seek +5s", priority=True),
        Binding("left", "seek_backward", "Seek -5s", priority=True),
        Binding("up", "volume_up", "Vol Up", priority=True),
        Binding("down", "volume_down", "Vol Down", priority=True),
        Binding("+", "volume_up", "Vol Up", show=False),
        Binding("-", "volume_down", "Vol Down", show=False),
        Binding("s", "shuffle", "Shuffle", priority=True),
        Binding("r", "loop", "Loop", priority=True),
        Binding("tab", "switch_player", "Switch Player", priority=True),
        Binding("l", "toggle_lyrics", "Lyrics", priority=True),
        Binding("v", "toggle_visualizer", "Visualizer", priority=True),
        Binding("t", "cycle_theme", "Theme", priority=True),
        Binding("m", "toggle_mini", "Mini Mode", priority=True),
        Binding("[", "lyrics_offset_earlier", "-100ms", priority=True),
        Binding("]", "lyrics_offset_later", "+100ms", priority=True),
        Binding("h", "toggle_help", "Help", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        config: Config | None = None,
        force_demo: bool = False,
        start_mini: bool = False,
        preferred_player: str = "",
    ) -> None:
        super().__init__()
        self.config = config or Config.load()
        if start_mini:
            self.config.mini_mode = True

        self.player_manager = PlayerManager(
            preferred_player=preferred_player or self.config.default_player,
            force_demo=force_demo,
            on_state_change=self._on_player_state_changed,
        )

        self.mascot_animator = MascotAnimator(base_fps=self.config.fps)
        self.scene = RoomScene(width=34, height=12)
        self.lyrics_cache = LyricsCache(Path(self.config.lyrics_cache_dir))
        self.lyrics_client = LyricsClient(self.lyrics_cache)

        self.active_theme_name = self.config.theme
        self.active_theme: Theme = get_theme(self.active_theme_name)
        self.accent_color: RGB = (56, 189, 248)

        self.current_track_key: str = ""
        self._loaded_lyrics_track_key: str = ""
        self._fetching_lyrics_track_key: str = ""
        self._last_state: PlayerState = PlayerState()
        self._known_durations: dict[str, float] = {}
        self._auto_dance_active: bool = False
        self._no_lyrics_track_key: str = ""

        # Widgets
        self.mascot_view = MascotView(self.mascot_animator, self.scene, id="mascot-view")
        self.now_playing_view = NowPlayingView(id="now-playing-view")
        self.progress_bar_view = ProgressBarView(id="progress-bar-view")
        self.controls_view = ControlsView(id="controls-view")
        self.lyrics_view = LyricsPanelView(id="lyrics-view")
        self.companion_view = CompanionDanceView(id="companion-view")
        self.visualizer_view = VisualizerView(id="visualizer-view")
        self.top_bar = Static(id="top-bar")

    def compose(self) -> ComposeResult:
        with Vertical(id="app-root"):
            yield self.top_bar
            with Horizontal(id="main-container"):
                with Vertical(id="left-panel"):
                    yield self.mascot_view
                with Vertical(id="right-panel"):
                    with Container(id="now-playing-container"):
                        yield self.now_playing_view
                    with Container(id="lyrics-container"):
                        yield self.lyrics_view
                        yield self.companion_view
            with Vertical(id="bottom-controls"):
                yield self.progress_bar_view
                yield self.controls_view
                with Container(id="visualizer-container"):
                    yield self.visualizer_view

    def on_mount(self) -> None:
        if self.config.mini_mode:
            self.screen.add_class("mini-mode")

        self.lyrics_view.display = self.config.show_lyrics
        self.companion_view.display = not self.config.show_lyrics

        self._apply_theme()
        self._sync_player_state()

        # High frequency animation & interpolation timer (10 - 15 fps)
        interval = 1.0 / max(8, min(20, self.config.fps))
        self.set_interval(interval, self._animation_tick)

        # Low frequency player state sync (every 0.8s)
        self.set_interval(0.8, self._sync_player_state)

    def _apply_theme(self) -> None:
        """Apply colors according to theme and dynamic accent."""
        self.active_theme = get_theme(self.active_theme_name)
        bg = self.active_theme.background
        surf = self.active_theme.surface
        bdr = self.active_theme.border
        txt = self.active_theme.text

        css = f"""
        Screen {{
            background: rgb({bg[0]},{bg[1]},{bg[2]});
            color: rgb({txt[0]},{txt[1]},{txt[2]});
        }}
        #top-bar, #bottom-controls {{
            background: rgb({surf[0]},{surf[1]},{surf[2]});
            border-top: solid rgb({bdr[0]},{bdr[1]},{bdr[2]});
        }}
        #left-panel {{
            border-right: tall rgb({bdr[0]},{bdr[1]},{bdr[2]});
        }}
        #now-playing-container {{
            border-bottom: solid rgb({bdr[0]},{bdr[1]},{bdr[2]});
        }}
        """
        self.screen.styles.background = f"rgb({bg[0]},{bg[1]},{bg[2]})"
        self.screen.styles.color = f"rgb({txt[0]},{txt[1]},{txt[2]})"

        # Update top bar
        self._update_top_bar()

    def _update_top_bar(self) -> None:
        t = Text()
        t.append("🎧 SOULWAVE", style=Style(color="rgb(255, 255, 255)", bold=True))
        t.append("   Player: ", style=Style(color="rgb(148, 163, 184)"))
        p_name = self._last_state.player_name or "None"
        t.append(f"[{p_name}]", style=Style(color=f"rgb({self.accent_color[0]},{self.accent_color[1]},{self.accent_color[2]})", bold=True))
        t.append("   Theme: ", style=Style(color="rgb(148, 163, 184)"))
        t.append(self.active_theme.name, style=Style(color="rgb(203, 213, 225)"))
        t.append("   [h] Help", style=Style(color="rgb(100, 116, 139)"))
        self.top_bar.update(t)

    def _on_player_state_changed(self) -> None:
        """Invoked from background MPRIS worker when player state/metadata updates."""
        try:
            self.call_from_thread(self._sync_player_state)
        except Exception:
            pass

    def _sync_player_state(self) -> None:
        """Fetch latest authoritative player state from MPRIS or demo."""
        state = self.player_manager.get_state()
        meta = state.metadata
        track_key = f"{meta.artist}::{meta.title}"

        # If state duration is valid, cache it for this track
        if meta.duration_seconds > 0.0:
            self._known_durations[track_key] = meta.duration_seconds
        elif track_key in self._known_durations:
            # Restore duration from track duration cache if MPRIS is temporarily buffering/missing
            meta.duration_seconds = self._known_durations[track_key]
        elif (
            self._last_state.metadata.duration_seconds > 0.0
            and track_key == self.current_track_key
        ):
            # Same track, keep known duration
            meta.duration_seconds = self._last_state.metadata.duration_seconds

        self._last_state = state

        # Check track change
        if track_key != self.current_track_key:
            self.current_track_key = track_key
            self._loaded_lyrics_track_key = ""
            self._fetching_lyrics_track_key = ""
            self._auto_dance_active = False
            self.lyrics_view.cancel_countdown()
            self.lyrics_view.set_lyrics(None, None, duration=meta.duration_seconds)
            self.lyrics_view.set_loading()
            if self.config.show_lyrics:
                self.lyrics_view.display = True
                self.companion_view.display = False
            else:
                self.lyrics_view.display = False
                self.companion_view.display = True

            self.accent_color = get_song_accent_color(meta.title, meta.artist)
            self.mascot_animator.set_track(meta.title, meta.artist)
            self.mascot_animator.set_accent_color(self.accent_color)
            self.mascot_view.accent_color = self.accent_color

            # Update lyrics
            self.lyrics_view.duration_seconds = meta.duration_seconds
            self._load_lyrics_for_track(meta.artist, meta.title, meta.album, meta.duration_seconds)
            self._update_top_bar()
        else:
            if meta.duration_seconds > 0.0:
                self.lyrics_view.duration_seconds = meta.duration_seconds

        # Update animator base state
        is_playing = state.status == PlaybackStatus.PLAYING
        is_connected = state.status != PlaybackStatus.DISCONNECTED
        has_track = bool(meta.title.strip())
        self.mascot_animator.update_playback_state(is_playing, is_connected, has_track)

        # Update Views
        self.now_playing_view.update_state(state, self.accent_color)
        self.controls_view.update_state(state, self.accent_color)
        self.progress_bar_view.update_progress(
            state.position_seconds,
            meta.duration_seconds,
            self.accent_color,
        )

    def _animation_tick(self) -> None:
        """High-frequency tick for smooth mascot animation, progress interpolation, and visualizer."""
        is_playing = self._last_state.status == PlaybackStatus.PLAYING
        is_paused = self._last_state.status == PlaybackStatus.PAUSED

        energy = getattr(self.visualizer_view, "current_energy", 0.0)

        # Update room scene physics
        self.scene.update(is_playing, is_paused, self.accent_color, energy=energy)
        self.mascot_view.refresh()

        # Local progress interpolation
        if hasattr(self.player_manager.current_player, "get_interpolated_position"):
            pos = self.player_manager.current_player.get_interpolated_position()
        else:
            pos = self._last_state.position_seconds

        self.progress_bar_view.update_progress(
            pos,
            self._last_state.metadata.duration_seconds,
            self.accent_color,
        )

        # Update lyrics scrolling or companion dance view
        if self.companion_view.display:
            energy = getattr(self.visualizer_view, "current_energy", 0.0)
            self.companion_view.update_state(
                is_playing=is_playing,
                is_paused=is_paused,
                accent=self.accent_color,
                energy=energy,
            )
        if self.lyrics_view.display:
            self.lyrics_view.update_position(
                pos,
                self.accent_color,
                self._last_state.metadata.duration_seconds,
            )

        # Update visualizer
        if self.config.show_visualizer:
            self.visualizer_view.update_params(
                is_playing=is_playing,
                volume=self._last_state.volume,
                bpm=self.mascot_animator.bpm,
                accent=self.accent_color,
            )

    def _load_lyrics_for_track(
        self,
        artist: str,
        title: str,
        album: str,
        duration: float,
    ) -> None:
        """Fetch lyrics asynchronously or from demo mock player."""
        current_key = f"{artist}::{title}"
        if not bool(title.strip()):
            self.lyrics_view.set_lyrics(None, None, duration=duration)
            self._loaded_lyrics_track_key = current_key
            self._fetching_lyrics_track_key = ""
            return

        offset = self.lyrics_cache.get_offset(artist, title)

        # If in demo mode and mock player has lyrics, use them directly
        if self.player_manager.is_demo:
            mock_lrc = getattr(self.player_manager.mock_player, "get_current_lyrics", lambda: "")()
            self.lyrics_view.set_lyrics(mock_lrc, None, offset=offset, duration=duration)
            self._loaded_lyrics_track_key = current_key
            self._fetching_lyrics_track_key = ""
            return

        self._fetching_lyrics_track_key = current_key
        self.lyrics_view.set_loading()

        def on_lyrics_fetched(data: dict | None) -> None:
            current_key = f"{self._last_state.metadata.artist}::{self._last_state.metadata.title}"
            fetched_key = f"{artist}::{title}"
            if current_key != fetched_key:
                return

            self._loaded_lyrics_track_key = fetched_key
            self._fetching_lyrics_track_key = ""

            if data and (data.get("syncedLyrics") or data.get("plainLyrics")):
                synced = data.get("syncedLyrics")
                plain = data.get("plainLyrics")
                lrclib_dur = data.get("duration")
                if lrclib_dur and self._last_state.metadata.duration_seconds <= 0.0:
                    try:
                        d_val = float(lrclib_dur)
                        if d_val > 0.0:
                            self._last_state.metadata.duration_seconds = d_val
                            self._known_durations[current_key] = d_val
                            if hasattr(self.player_manager.current_player, "_interpolator"):
                                self.player_manager.current_player._interpolator.sync(
                                    self._last_state.position_seconds,
                                    self._last_state.status,
                                    d_val,
                                )
                    except (ValueError, TypeError):
                        pass

                def apply_lyrics():
                    self.lyrics_view.cancel_countdown()
                    self._auto_dance_active = False
                    if self.config.show_lyrics:
                        self.lyrics_view.display = True
                        self.companion_view.display = False
                    self.lyrics_view.set_lyrics(
                        synced,
                        plain,
                        offset=offset,
                        duration=self._last_state.metadata.duration_seconds,
                    )
                    if self.config.show_lyrics:
                        pos = self.player_manager.current_player.get_interpolated_position()
                        self.lyrics_view.update_position(
                            pos,
                            self.accent_color,
                            self._last_state.metadata.duration_seconds,
                        )

                self.call_from_thread(apply_lyrics)
            else:
                def trigger_no_lyrics_fallback():
                    if self._no_lyrics_track_key == current_key and (self.lyrics_view.is_countdown_active or self._auto_dance_active):
                        return
                    self._no_lyrics_track_key = current_key

                    def on_countdown_done():
                        if self.config.show_lyrics:
                            self._auto_dance_active = True
                            self.lyrics_view.display = False
                            self.companion_view.display = True
                            energy = getattr(self.visualizer_view, "current_energy", 0.0)
                            self.companion_view.update_state(
                                is_playing=(self._last_state.status == PlaybackStatus.PLAYING),
                                is_paused=(self._last_state.status == PlaybackStatus.PAUSED),
                                accent=self.accent_color,
                                energy=energy,
                            )

                    if self.config.show_lyrics:
                        self.lyrics_view.start_no_lyrics_countdown(
                            on_complete=on_countdown_done,
                            countdown_seconds=5,
                        )
                    else:
                        self.lyrics_view.set_lyrics(None, None, duration=self._last_state.metadata.duration_seconds)

                self.call_from_thread(trigger_no_lyrics_fallback)

        self.lyrics_client.fetch_lyrics_async(
            artist=artist,
            title=title,
            album=album,
            duration=duration,
            callback=on_lyrics_fetched,
        )

    # --- Actions / Keybinding Handlers ---

    def action_play_pause(self) -> None:
        self.player_manager.current_player.play_pause()
        self._last_state = self.player_manager.get_state()
        self.controls_view.update_state(self._last_state, self.accent_color)
        is_playing = self._last_state.status == PlaybackStatus.PLAYING
        is_connected = self._last_state.status != PlaybackStatus.DISCONNECTED
        has_track = bool(self._last_state.metadata.title.strip())
        self.mascot_animator.update_playback_state(is_playing, is_connected, has_track)

    def action_next(self) -> None:
        self.player_manager.current_player.next_track()
        self.mascot_animator.begin_track_transition()
        if hasattr(self, "companion_view"):
            self.companion_view.set_track_transition(True)
        self._sync_player_state()

    def action_previous(self) -> None:
        self.player_manager.current_player.previous_track()
        self.mascot_animator.begin_track_transition()
        if hasattr(self, "companion_view"):
            self.companion_view.set_track_transition(True)
        self._sync_player_state()

    def action_seek_forward(self) -> None:
        self.player_manager.current_player.seek(self.config.seek_step_seconds)
        self.mascot_animator.trigger_reaction(MascotState.SEEKING, duration=0.5)
        pos = self.player_manager.current_player.get_interpolated_position()
        self.progress_bar_view.update_progress(
            pos,
            self._last_state.metadata.duration_seconds,
            self.accent_color,
        )
        if self.config.show_lyrics:
            self.lyrics_view.update_position(
                pos,
                self.accent_color,
                self._last_state.metadata.duration_seconds,
            )

    def action_seek_backward(self) -> None:
        self.player_manager.current_player.seek(-self.config.seek_step_seconds)
        self.mascot_animator.trigger_reaction(MascotState.SEEKING, duration=0.5)
        pos = self.player_manager.current_player.get_interpolated_position()
        self.progress_bar_view.update_progress(
            pos,
            self._last_state.metadata.duration_seconds,
            self.accent_color,
        )
        if self.config.show_lyrics:
            self.lyrics_view.update_position(
                pos,
                self.accent_color,
                self._last_state.metadata.duration_seconds,
            )

    def action_volume_up(self) -> None:
        new_vol = min(1.0, self._last_state.volume + self.config.volume_step_percent)
        self.player_manager.current_player.set_volume(new_vol)
        self._last_state.volume = new_vol
        self.mascot_animator.trigger_reaction(MascotState.VOL_UP, duration=0.7)
        self.controls_view.update_state(self._last_state, self.accent_color)

    def action_volume_down(self) -> None:
        new_vol = max(0.0, self._last_state.volume - self.config.volume_step_percent)
        self.player_manager.current_player.set_volume(new_vol)
        self._last_state.volume = new_vol
        self.mascot_animator.trigger_reaction(MascotState.VOL_DOWN, duration=0.7)
        self.controls_view.update_state(self._last_state, self.accent_color)

    def action_shuffle(self) -> None:
        self.player_manager.current_player.toggle_shuffle()
        self._sync_player_state()

    def action_loop(self) -> None:
        self.player_manager.current_player.cycle_loop()
        self._sync_player_state()

    def action_switch_player(self) -> None:
        switched = self.player_manager.switch_next_player()
        self.mascot_animator.trigger_reaction(MascotState.TRACK_CHANGE, duration=0.6)
        self._sync_player_state()
        self._update_top_bar()

    def action_toggle_lyrics(self) -> None:
        self.config.show_lyrics = not self.config.show_lyrics
        if self._auto_dance_active:
            if self.config.show_lyrics:
                self._auto_dance_active = False
                self.lyrics_view.display = True
                self.companion_view.display = False
            else:
                self.lyrics_view.display = False
                self.companion_view.display = True
        else:
            self.lyrics_view.display = self.config.show_lyrics
            self.companion_view.display = not self.config.show_lyrics

        if not self.lyrics_view.display:
            energy = getattr(self.visualizer_view, "current_energy", 0.0)
            self.companion_view.update_state(
                is_playing=(self._last_state.status == PlaybackStatus.PLAYING),
                is_paused=(self._last_state.status == PlaybackStatus.PAUSED),
                accent=self.accent_color,
                energy=energy,
            )
        else:
            meta = self._last_state.metadata
            current_key = f"{meta.artist}::{meta.title}"
            # If returning to lyrics view, ensure lyrics are up-to-date with current track
            if self._loaded_lyrics_track_key != current_key and bool(meta.title.strip()):
                self._load_lyrics_for_track(meta.artist, meta.title, meta.album, meta.duration_seconds)
            pos = self.player_manager.current_player.get_interpolated_position()
            self.lyrics_view.update_position(
                pos,
                self.accent_color,
                self._last_state.metadata.duration_seconds,
            )
            self.lyrics_view.refresh()

    def action_toggle_visualizer(self) -> None:
        self.config.show_visualizer = not self.config.show_visualizer
        vis_container = self.query_one("#visualizer-container")
        vis_container.display = self.config.show_visualizer

    def action_cycle_theme(self) -> None:
        self.active_theme_name = cycle_theme_name(self.active_theme_name)
        self._apply_theme()

    def action_toggle_mini(self) -> None:
        self.config.mini_mode = not self.config.mini_mode
        if self.config.mini_mode:
            self.screen.add_class("mini-mode")
        else:
            self.screen.remove_class("mini-mode")

    def action_lyrics_offset_earlier(self) -> None:
        new_offset = self.lyrics_view.adjust_offset(-0.1)
        meta = self._last_state.metadata
        self.lyrics_cache.set_offset(meta.artist, meta.title, new_offset)

    def action_lyrics_offset_later(self) -> None:
        new_offset = self.lyrics_view.adjust_offset(0.1)
        meta = self._last_state.metadata
        self.lyrics_cache.set_offset(meta.artist, meta.title, new_offset)

    def action_toggle_help(self) -> None:
        if isinstance(self.screen, HelpModal):
            self.pop_screen()
        else:
            self.push_screen(HelpModal())

    # --- Event Handlers ---

    def on_progress_bar_view_seek_requested(self, message: ProgressBarView.SeekRequested) -> None:
        self.player_manager.current_player.set_position(message.target_seconds)
        self.mascot_animator.trigger_reaction(MascotState.SEEKING, duration=0.5)
        pos = self.player_manager.current_player.get_interpolated_position()
        self.progress_bar_view.update_progress(
            pos,
            self._last_state.metadata.duration_seconds,
            self.accent_color,
        )
        if self.config.show_lyrics:
            self.lyrics_view.update_position(
                pos,
                self.accent_color,
                self._last_state.metadata.duration_seconds,
            )

    def on_controls_view_action_triggered(self, message: ControlsView.ActionTriggered) -> None:
        action_map = {
            "play_pause": self.action_play_pause,
            "next": self.action_next,
            "previous": self.action_previous,
            "shuffle": self.action_shuffle,
            "loop": self.action_loop,
        }
        fn = action_map.get(message.action)
        if fn:
            fn()

    def action_quit(self) -> None:
        if hasattr(self.player_manager, "close"):
            self.player_manager.close()
        self.exit()

    def on_unmount(self) -> None:
        if hasattr(self.player_manager, "close"):
            self.player_manager.close()
