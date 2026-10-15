"""Mock Firefox MPRIS D-Bus service running as a standalone process."""

import sys
import time
import threading
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib


class FirefoxMockService(dbus.service.Object):
    def __init__(self, bus_name: str, conn: dbus.SessionBus):
        self.bus_name_obj = dbus.service.BusName(bus_name, conn)
        super().__init__(conn, "/org/mpris/MediaPlayer2")
        self._position_us = 30_000_000  # 30.0s
        self._duration_us = 240_000_000  # 240.0s
        self._track_id = "/org/mpris/MediaPlayer2/firefox"
        self._status = "Playing"
        self._buffering_until = 0.0
        self._lock = threading.Lock()

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature="x", out_signature="")
    def Seek(self, offset: int):
        with self._lock:
            self._position_us = max(0, min(self._duration_us, self._position_us + offset))
            # Emulate YouTube/Firefox buffering quirk: Position reads as 0 for 250ms
            self._buffering_until = time.monotonic() + 0.25
            pos = self._position_us
        self.Seeked(dbus.Int64(pos))

    @dbus.service.method("org.mpris.MediaPlayer2.Player", in_signature="ox", out_signature="")
    def SetPosition(self, track_id: str, position: int):
        with self._lock:
            if str(track_id) != self._track_id:
                return
            self._position_us = max(0, min(self._duration_us, position))
            self._buffering_until = time.monotonic() + 0.25
            pos = self._position_us
        self.Seeked(dbus.Int64(pos))

    @dbus.service.signal("org.mpris.MediaPlayer2.Player", signature="x")
    def Seeked(self, position: int):
        pass

    @dbus.service.signal("org.freedesktop.DBus.Properties", signature="sa{sv}as")
    def PropertiesChanged(self, iface: str, changed: dict, invalidated: list):
        pass

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v")
    def Get(self, iface: str, prop: str):
        with self._lock:
            if prop == "Position":
                if time.monotonic() < self._buffering_until:
                    return dbus.Int64(0)
                return dbus.Int64(self._position_us)
            if prop == "PlaybackStatus":
                return dbus.String(self._status)
            if prop == "CanSeek":
                return dbus.Boolean(True)
            if prop == "CanControl":
                return dbus.Boolean(True)
            if prop == "Metadata":
                return self._get_metadata()
            raise dbus.DBusException(f"Unknown property: {prop}")

    @dbus.service.method("org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface: str):
        with self._lock:
            pos = dbus.Int64(0) if time.monotonic() < self._buffering_until else dbus.Int64(self._position_us)
            return dbus.Dictionary({
                dbus.String("PlaybackStatus"): dbus.String(self._status, variant_level=1),
                dbus.String("Position"): dbus.Int64(pos, variant_level=1),
                dbus.String("CanSeek"): dbus.Boolean(True, variant_level=1),
                dbus.String("CanControl"): dbus.Boolean(True, variant_level=1),
                dbus.String("Metadata"): self._get_metadata(),
                dbus.String("Volume"): dbus.Double(1.0, variant_level=1),
                dbus.String("LoopStatus"): dbus.String("None", variant_level=1),
                dbus.String("Shuffle"): dbus.Boolean(False, variant_level=1),
            }, signature="sv")

    def _get_metadata(self):
        return dbus.Dictionary({
            dbus.String("mpris:trackid"): dbus.ObjectPath(self._track_id, variant_level=1),
            dbus.String("mpris:length"): dbus.Int64(self._duration_us, variant_level=1),
            dbus.String("xesam:title"): dbus.String("Kendrick Lamar - Not Like Us", variant_level=1),
            dbus.String("xesam:artist"): dbus.Array([dbus.String("Kendrick Lamar")], signature="s", variant_level=1),
            dbus.String("xesam:album"): dbus.String("Single", variant_level=1),
        }, signature="sv", variant_level=1)


def main():
    bus_name = sys.argv[1] if len(sys.argv) > 1 else "org.mpris.MediaPlayer2.firefox_standalone"
    dbus.mainloop.glib.threads_init()
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    svc = FirefoxMockService(bus_name, bus)
    print("READY", flush=True)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
