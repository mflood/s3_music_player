"""Track ordering: what plays next, and what happens at the end.

This is deliberately free of both S3 and Qt so the awkward parts -- shuffle
that keeps your place, repeat-one, walking off the end of the list -- can be
tested directly instead of through a GUI.
"""

import random
from enum import Enum


class RepeatMode(Enum):
    OFF = "off"
    ALL = "all"
    ONE = "one"


class Playlist:
    """An ordered list of tracks with a cursor.

    The cursor survives shuffling: shuffle the queue while a track is playing
    and that track stays current, with the others rearranged around it.
    """

    def __init__(self, tracks=(), repeat=RepeatMode.OFF):
        self._tracks = list(tracks)
        self._index = 0 if self._tracks else -1
        self._shuffled = False
        self.repeat = repeat

    def __len__(self):
        return len(self._tracks)

    def __iter__(self):
        return iter(self._tracks)

    def __getitem__(self, index):
        return self._tracks[index]

    def __bool__(self):
        return bool(self._tracks)

    @property
    def tracks(self):
        return tuple(self._tracks)

    @property
    def index(self):
        """Cursor position, or -1 when the playlist is empty."""
        return self._index

    @property
    def current(self):
        """The track under the cursor, or None when empty."""
        if not self._tracks:
            return None
        return self._tracks[self._index]

    @property
    def is_shuffled(self):
        return self._shuffled

    def load(self, tracks):
        """Replace the contents and reset the cursor to the start."""
        self._tracks = list(tracks)
        self._index = 0 if self._tracks else -1
        self._shuffled = False
        return self.current

    def append(self, track):
        self._tracks.append(track)
        if self._index < 0:
            self._index = 0
        return track

    def clear(self):
        self._tracks = []
        self._index = -1
        self._shuffled = False

    def jump_to(self, index):
        """Move the cursor to `index`. Raises IndexError if out of range."""
        if not self._tracks:
            raise IndexError("playlist is empty")
        if not 0 <= index < len(self._tracks):
            raise IndexError(
                "index %d out of range for %d tracks" % (index, len(self._tracks))
            )
        self._index = index
        return self.current

    def jump_to_track(self, track):
        """Move the cursor to `track`. Raises ValueError if not present."""
        self._index = self._tracks.index(track)
        return self.current

    def next(self):
        """Advance the cursor and return the new track.

        Returns None when playback should stop -- the end of the list with
        repeat off. With :attr:`RepeatMode.ONE` the cursor does not move, so
        the same track is returned.
        """
        if not self._tracks:
            return None
        if self.repeat is RepeatMode.ONE:
            return self.current
        if self._index + 1 < len(self._tracks):
            self._index += 1
            return self.current
        if self.repeat is RepeatMode.ALL:
            self._index = 0
            return self.current
        return None

    def previous(self):
        """Step back one track, stopping at the first.

        With repeat-all, stepping back from the first track wraps to the last.
        Repeat-one is ignored here: pressing "previous" twice should not trap
        you on one song.
        """
        if not self._tracks:
            return None
        if self._index > 0:
            self._index -= 1
            return self.current
        if self.repeat is RepeatMode.ALL:
            self._index = len(self._tracks) - 1
            return self.current
        return self.current

    def shuffle(self, seed=None):
        """Randomise order, keeping the current track under the cursor.

        `seed` makes the result reproducible, which is what the tests use.
        """
        if len(self._tracks) < 2:
            self._shuffled = True
            return self.current

        current = self.current
        others = [t for i, t in enumerate(self._tracks) if i != self._index]
        random.Random(seed).shuffle(others)
        self._tracks = [current] + others
        self._index = 0
        self._shuffled = True
        return self.current

    def sort(self):
        """Restore ``(bucket, key)`` order, keeping the current track current."""
        current = self.current
        self._tracks.sort()
        self._shuffled = False
        if current is not None:
            self._index = self._tracks.index(current)
        return self.current
