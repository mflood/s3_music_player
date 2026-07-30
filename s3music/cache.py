"""Local disk cache for tracks fetched out of S3.

Streaming audio straight from S3 means re-downloading on every replay, so
tracks land on disk first and are played from there. Cache filenames are
derived from a hash of the URI rather than from the key itself: object keys
are arbitrary strings and may contain ``../`` or absolute paths, which would
otherwise let a bucket write outside the cache directory.
"""

import hashlib
from pathlib import Path

import botocore.exceptions

from .errors import DownloadError


class TrackCache:
    """Downloads tracks on demand and remembers where it put them."""

    def __init__(self, client, directory):
        self._client = client
        self._directory = Path(directory)

    @property
    def directory(self):
        return self._directory

    def path_for(self, track):
        """The on-disk location for `track`, whether or not it exists yet.

        The name is ``<sha256 of the s3 uri>.<ext>``. Hashing keeps the path
        inside the cache directory no matter what the key contains, and the
        extension is preserved because media backends sniff the format from it.
        """
        digest = hashlib.sha256(track.uri.encode("utf-8")).hexdigest()
        return self._directory / (digest + track.extension)

    def is_cached(self, track):
        path = self.path_for(track)
        return path.exists() and path.stat().st_size > 0

    def fetch(self, track):
        """Return a local path for `track`, downloading it if necessary."""
        path = self.path_for(track)
        if self.is_cached(track):
            return path

        self._directory.mkdir(parents=True, exist_ok=True)
        # Download to a sibling temp name and rename, so an interrupted
        # transfer never leaves a half-file that later looks cached.
        partial = path.with_suffix(path.suffix + ".part")
        try:
            self._client.download_file(track.bucket, track.key, str(partial))
        except (botocore.exceptions.ClientError, OSError) as exc:
            partial.unlink(missing_ok=True)
            raise DownloadError("could not download %s: %s" % (track.uri, exc)) from exc
        partial.replace(path)
        return path

    def clear(self):
        """Delete everything in the cache directory. Returns files removed."""
        if not self._directory.exists():
            return 0
        removed = 0
        for path in self._directory.iterdir():
            if path.is_file():
                path.unlink()
                removed += 1
        return removed

    @property
    def size_bytes(self):
        if not self._directory.exists():
            return 0
        return sum(p.stat().st_size for p in self._directory.iterdir() if p.is_file())
