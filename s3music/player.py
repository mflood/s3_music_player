"""Playback logic, with the audio device held at arm's length.

:class:`PlayerController` owns the decisions -- fetch the track, start it,
advance when it ends, stop at the end of the queue -- and delegates the actual
noise to an :class:`AudioBackend`. Qt supplies a real backend; the tests supply
a fake one. That split is why playback behaviour here is testable at all: none
of these rules need a sound card or a running event loop to verify.
"""

from enum import Enum
from typing import Protocol

from .errors import EmptyPlaylist
from .playlist import Playlist


class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class AudioBackend(Protocol):
    """What the controller needs from something that can make sound."""

    def load(self, path):
        """Point the device at a local file."""

    def play(self):
        ...

    def pause(self):
        ...

    def stop(self):
        ...

    def set_volume(self, volume):
        """Set volume as a float from 0.0 to 1.0."""

    def seek(self, milliseconds):
        ...

    @property
    def position(self):
        """Current playhead position in milliseconds."""

    @property
    def duration(self):
        """Length of the loaded track in milliseconds, 0 if unknown."""


class PlayerController:
    """Drives a playlist through an audio backend.

    Listeners registered with :meth:`on_track_changed` and
    :meth:`on_state_changed` are how a UI keeps up; nothing in this class
    imports a widget toolkit.
    """

    def __init__(self, backend, cache, playlist=None, volume=0.8):
        self._backend = backend
        self._cache = cache
        self._playlist = playlist if playlist is not None else Playlist()
        self._state = PlaybackState.STOPPED
        self._loaded = None
        self._volume = volume
        self._track_listeners = []
        self._state_listeners = []
        self._error_listeners = []
        backend.set_volume(volume)
        finished_hook = getattr(backend, "set_finished_callback", None)
        if finished_hook is not None:
            finished_hook(self.handle_track_finished)

    @property
    def playlist(self):
        return self._playlist

    @property
    def state(self):
        return self._state

    @property
    def current_track(self):
        return self._playlist.current

    @property
    def loaded_track(self):
        """The track actually handed to the backend, which may lag the cursor."""
        return self._loaded

    @property
    def volume(self):
        return self._volume

    @property
    def is_playing(self):
        return self._state is PlaybackState.PLAYING

    def on_track_changed(self, callback):
        self._track_listeners.append(callback)
        return callback

    def on_state_changed(self, callback):
        self._state_listeners.append(callback)
        return callback

    def on_error(self, callback):
        self._error_listeners.append(callback)
        return callback

    def load_tracks(self, tracks):
        """Replace the queue. Does not start playback."""
        self._playlist.load(tracks)
        self._notify_track(self._playlist.current)
        return self._playlist.current

    def play(self):
        """Start or resume playback of the track under the cursor."""
        track = self._playlist.current
        if track is None:
            raise EmptyPlaylist("nothing to play")

        if self._state is PlaybackState.PAUSED and self._loaded == track:
            self._backend.play()
            self._set_state(PlaybackState.PLAYING)
            return track

        return self._start(track)

    def pause(self):
        if self._state is not PlaybackState.PLAYING:
            return self._state
        self._backend.pause()
        self._set_state(PlaybackState.PAUSED)
        return self._state

    def toggle(self):
        """Pause if playing, otherwise play. What the space bar does."""
        if self._state is PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()
        return self._state

    def stop(self):
        self._backend.stop()
        self._loaded = None
        self._set_state(PlaybackState.STOPPED)
        return self._state

    def next(self):
        """Skip forward. Returns None and stops at the end of the queue."""
        return self._move(self._playlist.next())

    def previous(self):
        return self._move(self._playlist.previous())

    def jump_to(self, index):
        return self._move(self._playlist.jump_to(index))

    def set_volume(self, volume):
        self._volume = min(1.0, max(0.0, volume))
        self._backend.set_volume(self._volume)
        return self._volume

    def seek(self, milliseconds):
        self._backend.seek(max(0, milliseconds))

    @property
    def position(self):
        return self._backend.position

    @property
    def duration(self):
        return self._backend.duration

    def handle_track_finished(self):
        """Called by the backend when a track plays out.

        Advances to the next track and keeps playing, or stops if the queue is
        exhausted. Ignored unless we believe we are playing, so a stray
        end-of-media signal after an explicit stop cannot restart the queue.
        """
        if self._state is not PlaybackState.PLAYING:
            return None
        upcoming = self._playlist.next()
        if upcoming is None:
            self.stop()
            return None
        return self._start(upcoming)

    def _move(self, track):
        """Apply a cursor move, keeping playback running if it already was."""
        if track is None:
            self.stop()
            return None
        self._notify_track(track)
        if self._state is PlaybackState.PLAYING:
            return self._start(track)
        if self._state is PlaybackState.PAUSED:
            self._loaded = None
        return track

    def _start(self, track):
        """Fetch, hand to the backend, and play.

        A track that will not download is reported and skipped rather than
        killing playback. The loop -- rather than recursion -- matters when a
        whole bucket is unreachable and repeat is on: every track is tried at
        most once, then playback stops.
        """
        attempted = set()
        while track is not None:
            try:
                path = self._cache.fetch(track)
            except Exception as exc:  # reported to the UI, never fatal
                self._notify_error(track, exc)
                attempted.add(track)
                upcoming = self._playlist.next()
                track = None if upcoming in attempted else upcoming
                continue

            self._backend.load(path)
            self._backend.play()
            self._loaded = track
            self._notify_track(track)
            self._set_state(PlaybackState.PLAYING)
            return track

        self.stop()
        return None

    def _set_state(self, state):
        if state is self._state:
            return state
        self._state = state
        for listener in self._state_listeners:
            listener(state)
        return state

    def _notify_track(self, track):
        for listener in self._track_listeners:
            listener(track)

    def _notify_error(self, track, exc):
        for listener in self._error_listeners:
            listener(track, exc)
