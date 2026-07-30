"""Wire the pieces together and hand control to Qt."""

import sys

from PyQt6.QtWidgets import QApplication

from ..cache import TrackCache
from ..player import PlayerController
from ..scanner import S3MusicScanner
from .backend import QtAudioBackend
from .window import PlayerWindow


def build_window(client, cache_dir, location=""):
    """Assemble scanner, cache, backend, controller and window.

    Split out from :func:`run` so tests can construct the whole stack under an
    offscreen QApplication without entering the event loop.
    """
    scanner = S3MusicScanner(client)
    cache = TrackCache(client, cache_dir)
    controller = PlayerController(QtAudioBackend(), cache)
    return PlayerWindow(controller, scanner, initial_location=location)


def run(client, cache_dir, location="", argv=None):
    app = QApplication(argv if argv is not None else sys.argv)
    window = build_window(client, cache_dir, location)
    window.show()
    return app.exec()
