"""Find audio files in S3 buckets.

The scan is a paginated listing filtered by file extension. Buckets can hold
far more objects than fit in one response and far more than fit in memory, so
:meth:`S3MusicScanner.scan` is a generator driven by a boto3 paginator -- the
caller sees the first track before the last page has been requested.
"""

import botocore.exceptions

from .errors import ScanError
from .track import S3_SCHEME, Track

#: Extensions treated as playable audio. Compared case-insensitively.
AUDIO_EXTENSIONS = frozenset(
    {
        ".mp3",
        ".m4a",
        ".m4b",
        ".m4p",
        ".aac",
        ".flac",
        ".ogg",
        ".oga",
        ".opus",
        ".wav",
        ".wma",
        ".aiff",
        ".aif",
    }
)


class S3MusicScanner:
    """Lists audio objects in buckets reachable by an S3 client."""

    def __init__(self, client, extensions=AUDIO_EXTENSIONS):
        self._client = client
        self._extensions = frozenset(e.lower() for e in extensions)

    @property
    def extensions(self):
        return self._extensions

    def list_buckets(self):
        """Every bucket the credentials can see, sorted by name."""
        try:
            response = self._client.list_buckets()
        except botocore.exceptions.ClientError as exc:
            raise ScanError("could not list buckets: %s" % (exc,)) from exc
        return sorted(bucket["Name"] for bucket in response.get("Buckets", []))

    def scan(self, bucket, prefix=""):
        """Yield every audio :class:`Track` under `prefix` in `bucket`.

        Objects that are not audio, and zero-byte "directory marker" keys
        ending in ``/``, are skipped.
        """
        bucket = bucket[len(S3_SCHEME) :] if bucket.startswith(S3_SCHEME) else bucket
        bucket, _, embedded_prefix = bucket.partition("/")
        prefix = prefix or embedded_prefix

        paginator = self._client.get_paginator("list_objects_v2")
        try:
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            for page in pages:
                # A bucket with no matching objects has no Contents key at all.
                for item in page.get("Contents", []):
                    key = item["Key"]
                    if key.endswith("/"):
                        continue
                    if not self._is_audio(key):
                        continue
                    yield Track(
                        bucket=bucket,
                        key=key,
                        size=item.get("Size", 0),
                        etag=item.get("ETag", "").strip('"'),
                    )
        except botocore.exceptions.ClientError as exc:
            raise ScanError("could not scan %r: %s" % (bucket, exc)) from exc

    def scan_uri(self, uri):
        """Scan from an ``s3://bucket/optional/prefix`` string."""
        return self.scan(uri)

    def _is_audio(self, key):
        name = key.rsplit("/", 1)[-1]
        if "." not in name:
            return False
        return ("." + name.rsplit(".", 1)[-1].lower()) in self._extensions
