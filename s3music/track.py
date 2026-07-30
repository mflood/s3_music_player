"""A single audio object living in S3."""

from dataclasses import dataclass, field

from .errors import InvalidURI

S3_SCHEME = "s3://"


@dataclass(frozen=True, order=True)
class Track:
    """An audio file in a bucket.

    Ordering is by ``(bucket, key)`` so a scan result sorts into a stable,
    human-sensible order regardless of what order S3 listed it in.
    """

    bucket: str
    key: str
    size: int = field(default=0, compare=False)
    etag: str = field(default="", compare=False)

    def __post_init__(self):
        if not self.bucket:
            raise InvalidURI("track has no bucket")
        if not self.key:
            raise InvalidURI("track has no key")

    @property
    def uri(self):
        return "%s%s/%s" % (S3_SCHEME, self.bucket, self.key)

    @property
    def filename(self):
        """The last path segment of the key."""
        return self.key.rsplit("/", 1)[-1]

    @property
    def extension(self):
        """Lower-cased extension including the dot, or empty string."""
        name = self.filename
        if "." not in name:
            return ""
        return "." + name.rsplit(".", 1)[-1].lower()

    @property
    def title(self):
        """A display name: the filename without its extension."""
        name = self.filename
        extension = self.extension
        return name[: -len(extension)] if extension else name

    @property
    def folder(self):
        """The immediate folder the key sits in, or empty at the bucket root."""
        if "/" not in self.key:
            return ""
        return self.key.rsplit("/", 2)[-2]

    @property
    def display_name(self):
        """Title with its folder, so ``01 - Intro`` stays distinguishable.

        Track numbering repeats across albums, and a list of bare titles is
        unreadable once more than one album is loaded.
        """
        folder = self.folder
        return "%s — %s" % (folder, self.title) if folder else self.title

    @classmethod
    def from_uri(cls, uri, size=0, etag=""):
        """Parse ``s3://bucket/path/to/song.mp3`` into a Track."""
        if not uri.startswith(S3_SCHEME):
            raise InvalidURI("%r is not an s3:// URI" % (uri,))
        remainder = uri[len(S3_SCHEME) :]
        bucket, separator, key = remainder.partition("/")
        if not separator or not key:
            raise InvalidURI("%r names a bucket but no object" % (uri,))
        return cls(bucket=bucket, key=key, size=size, etag=etag)

    def __str__(self):
        return self.uri
