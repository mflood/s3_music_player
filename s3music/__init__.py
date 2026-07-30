"""Find music in your S3 buckets, and play it."""

from .cache import TrackCache
from .errors import (
    DownloadError,
    EmptyPlaylist,
    InvalidURI,
    S3MusicError,
    ScanError,
)
from .player import AudioBackend, PlaybackState, PlayerController
from .playlist import Playlist, RepeatMode
from .scanner import AUDIO_EXTENSIONS, S3MusicScanner
from .track import Track

__version__ = "1.0.0"

__all__ = [
    "AUDIO_EXTENSIONS",
    "AudioBackend",
    "DownloadError",
    "EmptyPlaylist",
    "InvalidURI",
    "PlaybackState",
    "PlayerController",
    "Playlist",
    "RepeatMode",
    "S3MusicError",
    "S3MusicScanner",
    "ScanError",
    "Track",
    "TrackCache",
]
