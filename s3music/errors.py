"""Every exception this package raises on purpose."""


class S3MusicError(Exception):
    """Base class for all errors raised by s3music."""


class InvalidURI(S3MusicError):
    """A string was not a usable ``s3://bucket/key`` URI."""


class ScanError(S3MusicError):
    """A bucket could not be listed."""


class DownloadError(S3MusicError):
    """An object could not be fetched from S3."""


class EmptyPlaylist(S3MusicError):
    """A playback operation was attempted with nothing loaded."""
