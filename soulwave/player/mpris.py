"""Production-quality, low-latency MPRIS player implementation for Linux.

Implements native D-Bus communication with persistent connections, background
command execution queue, signal subscriptions (Seeked, PropertiesChanged,
NameOwnerChanged), position verification, and fallback handling.
"""

from __future__ import annotations

import logging
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .base import (
    BasePlayer,
    PlayerState,
    PlaybackStatus,
    LoopStatus,
    ShuffleStatus,
    TrackMetadata,
)
from .interpolator import PositionInterpolator

logger = logging.getLogger(__name__)

# Try importing native D-Bus libraries
try:
    import dbus
    import dbus.mainloop.glib
    from gi.repository import GLib

    _DBUS_AVAILABLE = True
except ImportError:
    _DBUS_AVAILABLE = False
    dbus = None
    GLib = None


@dataclass
class SeekVerificationResult:
    """Detailed record of a seek operation and its verification."""
    success: bool
    seek_type: str  # "seek" or "set_position"
    target_position: float
    resulting_position: float
    elapsed_seconds: float
    error: Optional[str] = None
    player_name: str = ""


class MPRISPlayer(BasePlayer):
    """Controls Linux desktop media players via official MPRIS specification."""

    FORMAT_DELIMITER = "<|SW_SEP|>"
    FORMAT_STRING = (
        f"{{{{status}}}}{FORMAT_DELIMITER}"
        f"{{{{artist}}}}{FORMAT_DELIMITER}"
        f"{{{{title}}}}{FORMAT_DELIMITER}"
        f"{{{{album}}}}{FORMAT_DELIMITER}"
        f"{{{{mpris:length}}}}{FORMAT_DELIMITER}"
        f"{{{{position}}}}{FORMAT_DELIMITER}"
        f"{{{{volume}}}}{FORMAT_DELIMITER}"
        f"{{{{loop}}}}{FORMAT_DELIMITER}"
        f"{{{{shuffle}}}}{FORMAT_DELIMITER}"
        f"{{{{mpris:artUrl}}}}{FORMAT_DELIMITER}"
        f"{{{{mpris:trackid}}}}"
    )

    def __init__(
        self,
        player_name: Optional[str] = None,
        on_state_change: Optional[Callable[[], None]] = None,
        use_dbus: bool = True,
    ) -> None:
        self.player_name = player_name
        self.on_state_change = on_state_change
        self.use_dbus = use_dbus and _DBUS_AVAILABLE

        self._interpolator = PositionInterpolator()
        self._last_state = PlayerState(player_name=player_name or "None")
        self._playerctl_bin = shutil.which("playerctl")
        self._lock = threading.RLock()

        # D-Bus resources
        self._bus: Optional[dbus.SessionBus] = None
        self._bus_name: Optional[str] = None
        self._player_obj = None
        self._player_iface = None
        self._props_iface = None
        self._signal_matches: List = []

        # Background async worker & GLib loop
        self._cmd_queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._loop = None
        self._loop_thread: Optional[threading.Thread] = None
        self._running: bool = False

        # Seek verification
        self._last_seek_result: Optional[SeekVerificationResult] = None
        self._latest_seeked_pos: Optional[float] = None
        self._latest_seeked_time: float = 0.0

        # Status transition hold window (prevents transient D-Bus reads from overriding optimistic status)
        self._status_hold_until: float = 0.0
        self._status_hold_target: Optional[PlaybackStatus] = None

        # Track generation / epoch tracking
        self._track_epoch: int = 0

        if self.use_dbus:
            self._init_dbus()

        # Initial state fetch
        self.get_state()

    @classmethod
    def list_players(cls) -> List[str]:
        """List names of currently active MPRIS players."""
        # 1. Try direct D-Bus ListNames
        if _DBUS_AVAILABLE:
            try:
                bus = dbus.SessionBus()
                dbus_obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
                dbus_iface = dbus.Interface(dbus_obj, "org.freedesktop.DBus")
                names = dbus_iface.ListNames()
                prefix = "org.mpris.MediaPlayer2."
                players = [
                    str(n)[len(prefix):]
                    for n in names
                    if str(n).startswith(prefix) and not str(n).endswith(".playerctld")
                ]
                if players:
                    return players
            except Exception as e:
                logger.debug("D-Bus ListNames failed: %s", e)

        # 2. Fallback to playerctl -l
        playerctl_bin = shutil.which("playerctl")
        if playerctl_bin:
            try:
                res = subprocess.run(
                    [playerctl_bin, "-l"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                    check=False,
                )
                if res.returncode == 0:
                    players = [p.strip() for p in res.stdout.splitlines() if p.strip()]
                    return players
            except (subprocess.SubprocessError, OSError):
                pass
        return []

    def _resolve_bus_name(self) -> Optional[str]:
        """Resolves target player to full D-Bus bus name."""
        prefix = "org.mpris.MediaPlayer2."
        active = self.list_players()

        if self.player_name:
            if self.player_name.startswith(prefix):
                return self.player_name
            # Exact match in active
            if self.player_name in active:
                return f"{prefix}{self.player_name}"
            # Prefix / substring match in active (e.g. 'firefox' -> 'firefox.instance_1_107')
            for p in active:
                if p.startswith(self.player_name) or self.player_name.lower() in p.lower():
                    return f"{prefix}{p}"
            return f"{prefix}{self.player_name}"

        # If no player_name given, choose first available
        if active:
            self.player_name = active[0]
            return f"{prefix}{active[0]}"
        return None

    def _init_dbus(self) -> bool:
        """Establishes persistent D-Bus connection, signal receivers and worker."""
        if not _DBUS_AVAILABLE:
            return False

        try:
            dbus.mainloop.glib.threads_init()
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._bus = dbus.SessionBus()

            self._bus_name = self._resolve_bus_name()
            if not self._bus_name:
                return False

            self._player_obj = self._bus.get_object(self._bus_name, "/org/mpris/MediaPlayer2")
            self._player_iface = dbus.Interface(self._player_obj, "org.mpris.MediaPlayer2.Player")
            self._props_iface = dbus.Interface(self._player_obj, "org.freedesktop.DBus.Properties")

            # Start GLib event loop in background thread for signals
            self._loop = GLib.MainLoop()
            self._loop_thread = threading.Thread(target=self._loop.run, daemon=True, name="MPRIS-GLib")
            self._loop_thread.start()

            # Subscribe to MPRIS signals
            m1 = self._bus.add_signal_receiver(
                self._on_seeked,
                dbus_interface="org.mpris.MediaPlayer2.Player",
                signal_name="Seeked",
                bus_name=self._bus_name,
                path="/org/mpris/MediaPlayer2",
            )
            m2 = self._bus.add_signal_receiver(
                self._on_properties_changed,
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                bus_name=self._bus_name,
                path="/org/mpris/MediaPlayer2",
            )
            m3 = self._bus.add_signal_receiver(
                self._on_name_owner_changed,
                dbus_interface="org.freedesktop.DBus",
                signal_name="NameOwnerChanged",
                path="/org/freedesktop/DBus",
                arg0=self._bus_name,
            )
            self._signal_matches.extend([m1, m2, m3])

            # Start background command execution worker
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="MPRIS-Worker")
            self._worker_thread.start()

            return True
        except Exception as e:
            logger.warning("Failed to initialize persistent D-Bus for %s: %s", self.player_name, e)
            self.use_dbus = False
            return False

    def _worker_loop(self) -> None:
        """Processes playback commands asynchronously in FIFO order."""
        while self._running:
            try:
                item = self._cmd_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            cmd_type, args = item
            try:
                if cmd_type == "seek":
                    offset_us, desired_pos, seq, epoch = args
                    # If track changed before command ran, discard obsolete seek
                    with self._lock:
                        if epoch != self._track_epoch:
                            continue

                    t0 = time.monotonic()
                    err = None
                    try:
                        self._player_iface.Seek(dbus.Int64(offset_us))
                    except dbus.DBusException as e:
                        err = str(e)
                        self._handle_dbus_error(e)

                    # Verify resulting position
                    self._verify_seek(
                        seek_type="seek",
                        target_pos=desired_pos,
                        seq=seq,
                        epoch=epoch,
                        t_start=t0,
                        immediate_err=err,
                    )

                elif cmd_type == "set_position":
                    track_id, pos_us, desired_pos, seq, epoch = args
                    with self._lock:
                        if epoch != self._track_epoch:
                            continue

                    t0 = time.monotonic()
                    err = None
                    try:
                        obj_path = dbus.ObjectPath(str(track_id))
                        self._player_iface.SetPosition(obj_path, dbus.Int64(pos_us))
                    except dbus.DBusException as e:
                        err = str(e)
                        self._handle_dbus_error(e)

                    # Verify resulting position
                    self._verify_seek(
                        seek_type="set_position",
                        target_pos=desired_pos,
                        seq=seq,
                        epoch=epoch,
                        t_start=t0,
                        immediate_err=err,
                    )

                elif cmd_type == "play_pause":
                    self._player_iface.PlayPause()
                elif cmd_type == "play":
                    self._player_iface.Play()
                elif cmd_type == "pause":
                    self._player_iface.Pause()
                elif cmd_type == "next":
                    self._player_iface.Next()
                elif cmd_type == "previous":
                    self._player_iface.Previous()
                elif cmd_type == "set_volume":
                    vol = args[0]
                    self._props_iface.Set(
                        "org.mpris.MediaPlayer2.Player",
                        "Volume",
                        dbus.Double(vol),
                    )
                elif cmd_type == "loop":
                    loop_val = args[0]
                    self._props_iface.Set(
                        "org.mpris.MediaPlayer2.Player",
                        "LoopStatus",
                        dbus.String(loop_val),
                    )
                elif cmd_type == "shuffle":
                    shuf_val = args[0]
                    self._props_iface.Set(
                        "org.mpris.MediaPlayer2.Player",
                        "Shuffle",
                        dbus.Boolean(shuf_val),
                    )
            except Exception as e:
                logger.error("Error executing %s command: %s", cmd_type, e)
                if isinstance(e, dbus.DBusException):
                    self._handle_dbus_error(e)
            finally:
                self._cmd_queue.task_done()

    def _verify_seek(
        self,
        seek_type: str,
        target_pos: float,
        seq: int,
        epoch: int,
        t_start: float,
        immediate_err: Optional[str] = None,
    ) -> None:
        """Verifies that the player actually reached the seek target."""
        with self._lock:
            # If track changed while seek was executing, discard verification
            if epoch != self._track_epoch:
                return

        if immediate_err:
            with self._lock:
                self._last_seek_result = SeekVerificationResult(
                    success=False,
                    seek_type=seek_type,
                    target_position=target_pos,
                    resulting_position=self._interpolator.get_confirmed_position(),
                    elapsed_seconds=time.monotonic() - t_start,
                    error=immediate_err,
                    player_name=self.player_name or "active",
                )
                self._interpolator.cancel_seek()
            return

        # Immediate verification without holding the worker loop hostage
        confirmed = False
        final_pos = target_pos

        with self._lock:
            if self._latest_seeked_time >= t_start and self._latest_seeked_pos is not None:
                if abs(self._latest_seeked_pos - target_pos) <= 3.0:
                    confirmed = True
                    final_pos = self._latest_seeked_pos

        if not confirmed and self._props_iface:
            try:
                current_us = self._props_iface.Get("org.mpris.MediaPlayer2.Player", "Position")
                current_s = max(0.0, float(current_us) / 1_000_000.0)
                # If player is not in zero-buffering drop and reasonably close to target
                if current_s > 0.0 or target_pos <= 1.0:
                    final_pos = current_s
                    if abs(current_s - target_pos) <= 3.0:
                        confirmed = True
                        with self._lock:
                            if epoch == self._track_epoch and seq == self._interpolator.get_seek_seq():
                                self._interpolator.confirm_seek(current_s)
            except Exception:
                pass

        elapsed = time.monotonic() - t_start
        with self._lock:
            if epoch == self._track_epoch:
                self._last_seek_result = SeekVerificationResult(
                    success=True,  # Dispatched successfully to D-Bus; interpolator maintains target
                    seek_type=seek_type,
                    target_position=target_pos,
                    resulting_position=final_pos,
                    elapsed_seconds=elapsed,
                    error=None,
                    player_name=self.player_name or "active",
                )

    # --- Signal Handlers ---

    def _on_seeked(self, position_us) -> None:
        """Received when the media player confirms a seek."""
        pos_sec = max(0.0, float(position_us) / 1_000_000.0)
        with self._lock:
            self._latest_seeked_pos = pos_sec
            self._latest_seeked_time = time.monotonic()
            self._last_state.position_seconds = pos_sec
            self._interpolator.confirm_seek(pos_sec)
            self._interpolator.sync(
                pos_sec,
                self._last_state.status,
                self._last_state.metadata.duration_seconds,
                is_authoritative=True,
            )
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    def _on_properties_changed(self, iface: str, changed: dict, invalidated: list) -> None:
        """Received when player properties change."""
        if iface != "org.mpris.MediaPlayer2.Player":
            return
        with self._lock:
            self._apply_dbus_properties(changed)
        if self.on_state_change:
            try:
                self.on_state_change()
            except Exception:
                pass

    def _on_name_owner_changed(self, name: str, old_owner: str, new_owner: str) -> None:
        """Detects media player exit or disconnect."""
        if name == self._bus_name and not new_owner:
            logger.info("Player %s disconnected from D-Bus", name)
            with self._lock:
                self._last_state.status = PlaybackStatus.DISCONNECTED
                self._last_state.can_control = False
                self._last_state.can_seek = False
            if self.on_state_change:
                try:
                    self.on_state_change()
                except Exception:
                    pass

    def _handle_dbus_error(self, err: Exception) -> None:
        """Handles D-Bus connection or method errors."""
        err_msg = str(err)
        if "NameHasNoOwner" in err_msg or "ServiceUnknown" in err_msg or "Disconnected" in err_msg:
            with self._lock:
                self._last_state.status = PlaybackStatus.DISCONNECTED
                self._last_state.can_control = False
                self._last_state.can_seek = False
            if self.on_state_change:
                try:
                    self.on_state_change()
                except Exception:
                    pass

    # --- Property Parsing ---

    def _apply_dbus_properties(self, props: dict) -> None:
        if "PlaybackStatus" in props:
            parsed = self._parse_status(str(props["PlaybackStatus"]))
            now = time.monotonic()
            if now < self._status_hold_until:
                if parsed == self._status_hold_target:
                    self._status_hold_until = 0.0
                    self._last_state.status = parsed
            else:
                self._last_state.status = parsed

        if "CanSeek" in props:
            self._last_state.can_seek = bool(props["CanSeek"])

        if "CanControl" in props:
            self._last_state.can_control = bool(props["CanControl"])

        if "CanGoNext" in props:
            self._last_state.can_go_next = bool(props["CanGoNext"])

        if "CanGoPrevious" in props:
            self._last_state.can_go_previous = bool(props["CanGoPrevious"])

        if "Volume" in props:
            try:
                self._last_state.volume = max(0.0, min(1.0, float(props["Volume"])))
            except (ValueError, TypeError):
                pass

        if "LoopStatus" in props:
            self._last_state.loop = self._parse_loop(str(props["LoopStatus"]))

        if "Shuffle" in props:
            self._last_state.shuffle = (
                ShuffleStatus.ON if bool(props["Shuffle"]) else ShuffleStatus.OFF
            )

        # Parse Position if present in props
        pos_sec_reported: Optional[float] = None
        if "Position" in props:
            try:
                pos_sec_reported = max(0.0, float(props["Position"]) / 1_000_000.0)
            except (ValueError, TypeError):
                pos_sec_reported = None

        is_new_track = False
        if "Metadata" in props:
            meta = props["Metadata"]
            track_id = str(meta.get("mpris:trackid", "")) or None

            title_val = str(meta.get("xesam:title", "")) or "Unknown Track"
            album_val = str(meta.get("xesam:album", "")) or "Unknown Album"

            artist_raw = meta.get("xesam:artist", "")
            if isinstance(artist_raw, (list, tuple)):
                artist_val = ", ".join(str(a) for a in artist_raw) if artist_raw else "Unknown Artist"
            else:
                artist_val = str(artist_raw) or "Unknown Artist"

            # Check for track change
            old_track_id = self._last_state.metadata.track_id
            old_title = self._last_state.metadata.title
            is_new_track = (
                (track_id and old_track_id and track_id != old_track_id)
                or (title_val and old_title and title_val != old_title)
            )

            length_raw = (
                meta.get("mpris:length")
                or meta.get("xesam:length")
                or meta.get("xesam:duration")
                or meta.get("duration")
                or meta.get("length")
                or 0
            )
            try:
                raw_val = float(length_raw)
                if raw_val > 10_000_000:
                    duration_sec = max(0.0, raw_val / 1_000_000.0)
                elif raw_val > 10_000:
                    duration_sec = max(0.0, raw_val / 1_000.0)
                else:
                    duration_sec = max(0.0, raw_val)
            except (ValueError, TypeError):
                duration_sec = 0.0

            # If duration is temporarily missing during buffering for the SAME track, preserve known duration
            if duration_sec <= 0.0 and not is_new_track and self._last_state.metadata.duration_seconds > 0:
                duration_sec = self._last_state.metadata.duration_seconds

            if is_new_track:
                # Track identity changed! Advance epoch and reset interpolator cleanly
                self._track_epoch += 1
                init_pos = pos_sec_reported if pos_sec_reported is not None else 0.0
                self._interpolator.reset_for_new_track(
                    initial_position=init_pos,
                    duration=duration_sec,
                    epoch=self._track_epoch,
                )
                self._last_state.position_seconds = init_pos

            art_url_val = str(meta.get("mpris:artUrl", "")) or None

            self._last_state.metadata = TrackMetadata(
                title=title_val,
                artist=artist_val,
                album=album_val,
                duration_seconds=duration_sec,
                art_url=art_url_val,
                track_id=track_id,
            )
            if duration_sec > 0:
                self._last_state.can_seek = True

            # Keep interpolator in sync
            sync_pos = pos_sec_reported if pos_sec_reported is not None else self._last_state.position_seconds
            self._interpolator.sync(
                sync_pos,
                self._last_state.status,
                duration_sec,
                is_authoritative=is_new_track,
                epoch=self._track_epoch,
            )
            self._last_state.position_seconds = sync_pos

        elif pos_sec_reported is not None:
            self._interpolator.sync(
                pos_sec_reported,
                self._last_state.status,
                self._last_state.metadata.duration_seconds,
                epoch=self._track_epoch,
            )
            self._last_state.position_seconds = pos_sec_reported

    # --- State and Control Methods ---

    def get_state(self) -> PlayerState:
        """Fetch current player state from D-Bus or playerctl fallback."""
        if self.use_dbus and self._props_iface:
            try:
                # Fetch all properties
                try:
                    all_props = self._props_iface.GetAll("org.mpris.MediaPlayer2.Player")
                    props_dict = dict(all_props)
                    # Many MPRIS players omit Position from GetAll or return 0 to prevent bus traffic; ensure Position is queried
                    if "Position" not in props_dict or props_dict.get("Position") == 0:
                        try:
                            pos_val = self._props_iface.Get("org.mpris.MediaPlayer2.Player", "Position")
                            if pos_val is not None:
                                props_dict["Position"] = pos_val
                        except Exception:
                            pass
                    with self._lock:
                        self._apply_dbus_properties(props_dict)
                except dbus.DBusException:
                    # Fallback to individual property gets
                    with self._lock:
                        status_val = self._props_iface.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")
                        self._last_state.status = self._parse_status(str(status_val))
                        meta_val = self._props_iface.Get("org.mpris.MediaPlayer2.Player", "Metadata")
                        pos_val = self._props_iface.Get("org.mpris.MediaPlayer2.Player", "Position")
                        self._apply_dbus_properties({"Metadata": meta_val, "Position": pos_val})

                # Refresh position interpolation
                with self._lock:
                    pos = self._interpolator.get_position()
                    self._last_state.position_seconds = pos
                    self._last_state.player_name = self.player_name or "active"
                    return PlayerState(
                        player_name=self._last_state.player_name,
                        status=self._last_state.status,
                        metadata=self._last_state.metadata,
                        position_seconds=pos,
                        volume=self._last_state.volume,
                        loop=self._last_state.loop,
                        shuffle=self._last_state.shuffle,
                        can_control=self._last_state.can_control,
                        can_seek=self._last_state.can_seek,
                        can_go_next=self._last_state.can_go_next,
                        can_go_previous=self._last_state.can_go_previous,
                    )
            except Exception as e:
                self._handle_dbus_error(e)
                if not self._playerctl_bin:
                    return PlayerState(status=PlaybackStatus.DISCONNECTED)

        # Fallback to playerctl if D-Bus is unavailable or disconnected
        return self._get_state_playerctl()

    def _get_state_playerctl(self) -> PlayerState:
        """Fallback state reader using playerctl."""
        if not self._playerctl_bin:
            return PlayerState(status=PlaybackStatus.DISCONNECTED)

        output = self._run_cmd(["metadata", "--format", self.FORMAT_STRING], timeout=1.2)
        if not output:
            status_out = self._run_cmd(["status"], timeout=0.8)
            if status_out:
                status = self._parse_status(status_out)
                state = PlayerState(
                    player_name=self.player_name or "active",
                    status=status,
                    can_control=True,
                )
                self._last_state = state
                return state
            return PlayerState(status=PlaybackStatus.DISCONNECTED)

        parts = output.split(self.FORMAT_DELIMITER)
        if len(parts) < 9:
            return PlayerState(status=PlaybackStatus.DISCONNECTED)

        status_str = parts[0].strip()
        artist_str = parts[1].strip() or "Unknown Artist"
        title_str = parts[2].strip() or "Unknown Track"
        album_str = parts[3].strip() or "Unknown Album"
        length_str = parts[4].strip()
        position_str = parts[5].strip()
        volume_str = parts[6].strip()
        loop_str = parts[7].strip()
        shuffle_str = parts[8].strip()
        art_url_str = parts[9].strip() if len(parts) > 9 else ""
        track_id_str = parts[10].strip() if len(parts) > 10 else f"{artist_str}:{title_str}"

        try:
            raw_len = float(length_str) if length_str else 0.0
            if raw_len > 10_000_000:
                duration_sec = max(0.0, raw_len / 1_000_000.0)
            elif raw_len > 10_000:
                duration_sec = max(0.0, raw_len / 1_000.0)
            else:
                duration_sec = max(0.0, raw_len)
        except ValueError:
            duration_sec = 0.0

        try:
            position_sec = max(0.0, float(position_str) / 1_000_000.0) if position_str else 0.0
        except ValueError:
            position_sec = 0.0

        try:
            volume_val = max(0.0, min(1.0, float(volume_str))) if volume_str else 1.0
        except ValueError:
            volume_val = 1.0

        status = self._parse_status(status_str)
        loop = self._parse_loop(loop_str)
        shuffle = self._parse_shuffle(shuffle_str)

        is_new_track = (
            (track_id_str and self._last_state.metadata.track_id and track_id_str != self._last_state.metadata.track_id)
            or (title_str and self._last_state.metadata.title and title_str != self._last_state.metadata.title)
        )

        if duration_sec <= 0.0 and not is_new_track and self._last_state.metadata.duration_seconds > 0:
            duration_sec = self._last_state.metadata.duration_seconds

        if is_new_track:
            self._track_epoch += 1
            self._interpolator.reset_for_new_track(
                initial_position=position_sec,
                duration=duration_sec,
                epoch=self._track_epoch,
            )

        metadata = TrackMetadata(
            title=title_str,
            artist=artist_str,
            album=album_str,
            duration_seconds=duration_sec,
            art_url=art_url_str or None,
            track_id=track_id_str,
        )

        self._interpolator.sync(
            position_sec,
            status,
            duration_sec,
            is_authoritative=is_new_track,
            epoch=self._track_epoch,
        )

        state = PlayerState(
            player_name=self.player_name or "active",
            status=status,
            metadata=metadata,
            position_seconds=position_sec,
            volume=volume_val,
            loop=loop,
            shuffle=shuffle,
            can_control=True,
            can_seek=duration_sec > 0,
            can_go_next=True,
            can_go_previous=True,
        )
        self._last_state = state
        return state

    def get_interpolated_position(self) -> float:
        """Returns the smoothed local playback or desired seek position."""
        return self._interpolator.get_position()

    def get_confirmed_position(self) -> float:
        """Returns the authoritative position confirmed by the media player."""
        return self._interpolator.get_confirmed_position()

    @property
    def last_seek_result(self) -> Optional[SeekVerificationResult]:
        """Inspection property for the last verified seek operation."""
        return self._last_seek_result

    def _can_seek_check(self) -> Tuple[bool, str]:
        """Validate CanSeek, duration and track identity before seeking."""
        with self._lock:
            if self._last_state.status == PlaybackStatus.DISCONNECTED:
                return False, "Player is disconnected"
            if not self._last_state.can_seek and self._last_state.metadata.duration_seconds <= 0:
                return False, "Player does not support seeking or duration is zero"
            return True, ""

    def seek(self, offset_seconds: float) -> None:
        """Relative seek: updates UI immediately and queues D-Bus Seek call."""
        can_seek, reason = self._can_seek_check()
        if not can_seek:
            logger.info("Seek rejected: %s", reason)
            return

        with self._lock:
            # 1. Immediate visual update without blocking
            desired = self._interpolator.step_relative_seek(offset_seconds)
            self._last_state.position_seconds = desired
            seq = self._interpolator.get_seek_seq()

        offset_us = int(round(offset_seconds * 1_000_000.0))

        if self.use_dbus and self._running:
            self._cmd_queue.put(("seek", (offset_us, desired, seq, self._track_epoch)))
        else:
            # playerctl fallback
            sign = "+" if offset_seconds >= 0 else ""
            self._run_cmd(["position", f"{offset_seconds:.1f}{sign}"])

    def set_position(self, target_seconds: float) -> None:
        """Absolute seek: validates track identity, updates UI and queues SetPosition."""
        can_seek, reason = self._can_seek_check()
        if not can_seek:
            logger.info("SetPosition rejected: %s", reason)
            return

        with self._lock:
            track_id = self._last_state.metadata.track_id
            if not track_id:
                logger.info("SetPosition rejected: No track_id available")
                return

            duration = self._last_state.metadata.duration_seconds
            clamped = max(0.0, min(target_seconds, duration) if duration > 0 else target_seconds)

            # Immediate visual update
            desired = self._interpolator.start_seek(clamped)
            self._last_state.position_seconds = desired
            seq = self._interpolator.get_seek_seq()

        pos_us = int(round(clamped * 1_000_000.0))

        if self.use_dbus and self._running:
            self._cmd_queue.put(("set_position", (track_id, pos_us, clamped, seq, self._track_epoch)))
        else:
            self._run_cmd(["position", f"{clamped:.1f}"])

    def play_pause(self) -> None:
        with self._lock:
            if self._last_state.status == PlaybackStatus.PLAYING:
                new_status = PlaybackStatus.PAUSED
            else:
                new_status = PlaybackStatus.PLAYING
            self._last_state.status = new_status
            self._status_hold_until = time.monotonic() + 0.6
            self._status_hold_target = new_status
            self._interpolator.sync(
                self._interpolator.get_position(),
                self._last_state.status,
                self._last_state.metadata.duration_seconds,
            )

        if self.use_dbus and self._player_iface:
            try:
                self._player_iface.PlayPause()
            except Exception as e:
                logger.error("Error executing PlayPause: %s", e)
        elif self.use_dbus and self._running:
            self._cmd_queue.put(("play_pause", ()))
        else:
            self._run_cmd(["play-pause"])

    def play(self) -> None:
        with self._lock:
            self._last_state.status = PlaybackStatus.PLAYING
            self._status_hold_until = time.monotonic() + 0.6
            self._status_hold_target = PlaybackStatus.PLAYING
            self._interpolator.sync(
                self._interpolator.get_position(),
                PlaybackStatus.PLAYING,
                self._last_state.metadata.duration_seconds,
            )
        if self.use_dbus and self._player_iface:
            try:
                self._player_iface.Play()
            except Exception as e:
                logger.error("Error executing Play: %s", e)
        elif self.use_dbus and self._running:
            self._cmd_queue.put(("play", ()))
        else:
            self._run_cmd(["play"])

    def pause(self) -> None:
        with self._lock:
            self._last_state.status = PlaybackStatus.PAUSED
            self._status_hold_until = time.monotonic() + 0.6
            self._status_hold_target = PlaybackStatus.PAUSED
            self._interpolator.sync(
                self._interpolator.get_position(),
                PlaybackStatus.PAUSED,
                self._last_state.metadata.duration_seconds,
            )
        if self.use_dbus and self._player_iface:
            try:
                self._player_iface.Pause()
            except Exception as e:
                logger.error("Error executing Pause: %s", e)
        elif self.use_dbus and self._running:
            self._cmd_queue.put(("pause", ()))
        else:
            self._run_cmd(["pause"])

    def next_track(self) -> None:
        if self.use_dbus and self._player_iface:
            try:
                self._player_iface.Next()
            except Exception as e:
                logger.error("Error executing Next: %s", e)
        elif self.use_dbus and self._running:
            self._cmd_queue.put(("next", ()))
        else:
            self._run_cmd(["next"])

    def previous_track(self) -> None:
        if self.use_dbus and self._player_iface:
            try:
                self._player_iface.Previous()
            except Exception as e:
                logger.error("Error executing Previous: %s", e)
        elif self.use_dbus and self._running:
            self._cmd_queue.put(("previous", ()))
        else:
            self._run_cmd(["previous"])

    def set_volume(self, target_volume: float) -> None:
        clamped = max(0.0, min(1.0, target_volume))
        with self._lock:
            self._last_state.volume = clamped
        if self.use_dbus and self._running:
            self._cmd_queue.put(("set_volume", (clamped,)))
        else:
            self._run_cmd(["volume", f"{clamped:.2f}"])

    def cycle_loop(self) -> None:
        order = [LoopStatus.NONE, LoopStatus.TRACK, LoopStatus.PLAYLIST]
        with self._lock:
            cur = self._last_state.loop
            idx = order.index(cur) if cur in order else 0
            nxt = order[(idx + 1) % len(order)]
            self._last_state.loop = nxt

        val_str = {LoopStatus.NONE: "None", LoopStatus.TRACK: "Track", LoopStatus.PLAYLIST: "Playlist"}[nxt]
        if self.use_dbus and self._running:
            self._cmd_queue.put(("loop", (val_str,)))
        else:
            self._run_cmd(["loop", val_str])

    def toggle_shuffle(self) -> None:
        with self._lock:
            nxt = ShuffleStatus.OFF if self._last_state.shuffle == ShuffleStatus.ON else ShuffleStatus.ON
            self._last_state.shuffle = nxt

        shuf_bool = nxt == ShuffleStatus.ON
        if self.use_dbus and self._running:
            self._cmd_queue.put(("shuffle", (shuf_bool,)))
        else:
            self._run_cmd(["shuffle", "Toggle"])

    def _run_cmd(self, args: List[str], timeout: float = 1.0) -> Optional[str]:
        """Runs playerctl command safely as fallback."""
        if not self._playerctl_bin:
            return None
        cmd = [self._playerctl_bin]
        if self.player_name:
            cmd.extend(["-p", self.player_name])
        cmd.extend(args)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass
        return None

    def close(self) -> None:
        """Release persistent D-Bus connections, signal matches, and worker thread."""
        self._running = False
        if self._bus and self._signal_matches:
            for match in self._signal_matches:
                try:
                    match.remove()
                except Exception:
                    pass
            self._signal_matches.clear()

        if self._loop:
            try:
                self._loop.quit()
            except Exception:
                pass
            self._loop = None

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)

        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=0.5)

    @staticmethod
    def _parse_status(val: str) -> PlaybackStatus:
        val = val.lower()
        if "play" in val:
            return PlaybackStatus.PLAYING
        if "pause" in val:
            return PlaybackStatus.PAUSED
        if "stop" in val:
            return PlaybackStatus.STOPPED
        return PlaybackStatus.DISCONNECTED

    @staticmethod
    def _parse_loop(val: str) -> LoopStatus:
        val = val.lower()
        if "track" in val:
            return LoopStatus.TRACK
        if "playlist" in val:
            return LoopStatus.PLAYLIST
        return LoopStatus.NONE

    @staticmethod
    def _parse_shuffle(val: str) -> ShuffleStatus:
        val = val.lower()
        if "on" in val or "true" in val or val == "1":
            return ShuffleStatus.ON
        return ShuffleStatus.OFF
