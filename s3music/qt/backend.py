"""A real audio device, implementing the :class:`~s3music.player.AudioBackend`
protocol on top of Qt Multimedia.

Everything Qt-specific about playback lives here. The controller talks to this
through the same small interface the tests' fake backend implements, so the
playback rules never depend on Qt being installed or an event loop running.
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer


class QtAudioBackend:
    """Wraps QMediaPlayer, hiding its enums and signal names."""

    def __init__(self):
        self._player = QMediaPlayer()
        self._output = QAudioOutput()
        self._player.setAudioOutput(self._output)
        self._finished_callback = None
        self._player.mediaStatusChanged.connect(self._on_media_status)

    @property
    def player(self):
        """The underlying QMediaPlayer, for wiring UI-only signals."""
        return self._player

    def set_finished_callback(self, callback):
        """Register the controller's end-of-track hook."""
        self._finished_callback = callback

    def load(self, path):
        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def set_volume(self, volume):
        self._output.setVolume(float(volume))

    def seek(self, milliseconds):
        self._player.setPosition(int(milliseconds))

    @property
    def position(self):
        return self._player.position()

    @property
    def duration(self):
        return self._player.duration()

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self._finished_callback:
            self._finished_callback()
