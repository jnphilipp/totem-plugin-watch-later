# -*- coding: utf-8 -*-
# Copyright (C) 2020-2021 J. Nathanael Philipp (jnphilipp) <nathanael@philipp.land>
"""Watch later - Totem Plugin (see README.md).

Based on: https://github.com/yauhen-l/remember-last-position-totem-plugin

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import hashlib
import os
import re
import sys
import time

from argparse import ArgumentParser
from configparser import ConfigParser
from datetime import datetime
from gi.repository import GLib, GObject, Peas, Totem
from threading import Timer
from typing import Optional
from urllib.parse import unquote


__author__ = "J. Nathanael Philipp (jnphilipp)"
__email__ = "nathanael@philipp.land"
__license__ = "GPLv3"
__version__ = "0.2.0"
__github__ = "https://github.com/jnphilipp/totem-plugin-watch-later"


class WatchLaterPlugin(GObject.Object, Peas.Activatable):
    """Watch later totem plugin."""

    __gtype_name__ = "WatchLaterPlugin"
    object = GObject.Property(type=GObject.Object)

    default_config = {
        "restart_last": True,
        "restart_delay": 2,
        "update_interval": 3,
        "rewind_time": 10,
        "min_runtime": 120,
        "max_runtime": 90,
    }

    def __init__(self):
        """Init."""
        GObject.Object.__init__(self)

        self.base_dir, file = os.path.split(
            os.path.normpath(
                os.path.realpath(
                    os.path.normcase(
                        os.path.expandvars(
                            os.path.expanduser(sys.modules[__name__].__file__)
                        )
                    )
                )
            )
        )
        self.last_played_file = os.path.join(self.base_dir, "last_played")
        self.load_config()

        self.file = None
        self.current_time = 0
        self.stream_length = 0
        self._totem = None

    @property
    def hash(self) -> Optional[str]:
        """Hash path as file name."""
        if self.file is None:
            return None
        return hashlib.blake2b(self.relpath.encode(), digest_size=16).hexdigest()

    @property
    def mountpoint(self) -> str:
        """Get mountpoint from file path."""
        if self.file is None:
            return ""
        path = os.path.realpath(unquote(self.file.replace("file://", "")))
        while not os.path.ismount(path):
            path = os.path.dirname(path)
        return "" if path == "/" else path

    @property
    def relpath(self) -> str:
        """Convert totem file."""
        if self.file is None:
            return ""
        mountpoint = self.mountpoint
        if mountpoint == "":
            return unquote(self.file.replace("file://", ""))
        else:
            return unquote(self.file.replace("file://", "")).replace(mountpoint, "")

    @property
    def watch_later_file(self) -> Optional[str]:
        """File to store info."""
        if self.hash is None:
            return None
        return os.path.join(self.base_dir, self.hash)

    def load_config(self):
        """Read the config file."""
        config = ConfigParser(defaults=self.default_config)
        try:
            config.read(os.path.join(self.base_dir, "config"))
        except Exception as e:
            sys.stderr.write(f"Failed to read config file: {e}")

        self.restart_last = config.getboolean("Config", "restart_last")
        self.restart_delay = config.getint("Config", "restart_delay")
        self.update_interval = config.getint("Config", "update_interval")
        self.rewind_time = config.getint("Config", "rewind_time") * 1000
        self.min_runtime = config.getint("Config", "min_runtime") * 1000
        self.max_runtime = config.getint("Config", "max_runtime") * 1000

    def do_activate(self):
        """Activate plugin."""
        self._totem = self.object

        # Register handlers
        self._totem.connect("file-closed", self.on_file_closed)
        self._totem.get_main_window().connect("destroy", self.on_file_closed)
        self._totem.connect("file-has-played", self.on_file_played)
        self._totem.connect("file-opened", self.on_file_opened)

        # Attempt to restore the last played file
        if self.restart_last:
            self.restart_last_timer = Timer(
                self.restart_delay, self.restart_last_played
            )
            self.restart_last_timer.start()

    def do_deactivate(self):
        """Deactive plugin."""
        self.update_properties()
        self._totem = None

    def on_file_opened(self, obj, file: str):
        """Handle file-opened signal."""
        try:
            self.restart_last_timer.cancel()
        except Exception:
            pass

        self.file = file
        if self.watch_later_file:
            try:
                config = ConfigParser()
                config.read(self.watch_later_file)
                self.current_time = config.getint("File", "time", fallback=0)
            except Exception as e:
                sys.stderr.write(f"Failed to read watch later file: {e}")
                self.current_time = 0
        else:
            self.current_time = 0

    def on_file_played(self, obj, file: str):
        """Handle file-has-played signal."""
        if file != self.file:
            raise RuntimeError(
                f"The opened file {self.file} and the played "
                + f"file {file} are not the same."
            )
        self.go_to_last_time()
        self.update_properties(True)

    def on_file_closed(self, obj):
        """Handle file-closed and destroy signal."""
        try:
            self.properties_timer.cancel()
        except Exception:
            pass

        if self.file is None:
            return

        if (
            self.current_time > 0
            and self.current_time >= self.min_runtime + self.rewind_time
            and self.current_time < self.stream_length - self.max_runtime
        ):
            save_time = max(0, self.current_time - self.rewind_time)
        else:
            save_time = 0

        unquoted_file = unquote(self.file.replace("file://", ""))
        if save_time > 0 and os.path.exists(unquoted_file):
            with open(self.watch_later_file, "w", encoding="utf8") as f:
                config = ConfigParser()
                config["File"] = {
                    "file": self.relpath.replace("%", "%%"),
                    "mountpoint": self.mountpoint.replace("%", "%%"),
                    "time": save_time,
                    "created": int(round(time.time() * 1000)),
                }
                config.write(f)
            with open(self.last_played_file, "w", encoding="utf8") as f:
                f.write(f"{self.file}\n")
        elif (
            (save_time == 0 or not os.path.exists(unquoted_file))
            and self.watch_later_file is not None
            and os.path.exists(self.watch_later_file)
        ):
            os.remove(self.watch_later_file)
            if os.path.exists(self.last_played_file):
                os.remove(self.last_played_file)

        self.file = None
        self.current_time = 0
        self.stream_length = 0

    def go_to_last_time(self):
        """Attempt to go to the last time of the opened file."""

        def go_to_last_time_thread(totem, time: int) -> bool:
            if not totem.is_seekable():
                return True
            totem.seek_time(time, True)
            return False

        if self.current_time > 0:
            GLib.timeout_add(50, go_to_last_time_thread, self._totem, self.current_time)

    def update_properties(self, start_timer=False):
        """Read the current position and stream_length from totem."""
        try:
            self.current_time = self._totem.get_property("current-time")
            self.stream_length = self._totem.get_property("stream-length")
        except Exception as e:
            sys.stderr.write(f"Failed to update properties from totem: {e}")

        if start_timer:
            self.properties_timer = Timer(
                self.update_interval, self.update_properties, [True]
            )
            self.properties_timer.start()

    def restart_last_played(self):
        """Restart the last played file."""
        if os.path.exists(self.last_played_file):
            with open(self.last_played_file, "r", encoding="utf8") as f:
                self._totem.remote_command(
                    Totem.RemoteCommand.REPLACE, f.read().strip()
                )


if __name__ == "__main__":
    parser = ArgumentParser(prog="watch_later")
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to check for stored files."
    )
    args = parser.parse_args()

    files = {}
    with os.scandir(args.path) as it:
        for entry in it:
            if entry.is_file() and re.fullmatch(r"[0-9a-z]{32}", entry.name):
                config = ConfigParser()
                config.read(entry.path)

                created = datetime.utcfromtimestamp(
                    config.getint("File", "created") / 1000.0
                ).strftime("%Y-%m-%d %H:%M:%S")

                seconds = int((config.getint("File", "time") / 1000) % 60)
                minutes = int((config.getint("File", "time") / (1000 * 60)) % 60)
                hours = int((config.getint("File", "time") / (1000 * 60 * 60)) % 24)

                mountpoint = config.get("File", "mountpoint", fallback=None)
                file = config.get("File", "file")

                path = (
                    os.path.join(mountpoint, file[1:] if file.startswith("/") else file)
                    if mountpoint
                    else file
                )

                files[created] = [
                    entry.name,
                    created,
                    f"{hours: 2d}:{minutes:02d}:{seconds:02d}",
                    "found  " if os.path.exists(path) else "missing",
                    path,
                ]

    for k, v in sorted(files.items(), key=lambda x: x[0]):
        print(v[0], "", v[1], "", v[2], "", v[3], "", v[4])
