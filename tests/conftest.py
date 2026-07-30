import os

import boto3
import pytest
from moto import mock_aws

from s3music.track import Track

REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Make sure a stray real profile can never be picked up by a test."""
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SECURITY_TOKEN",
        "AWS_SESSION_TOKEN",
    ):
        monkeypatch.setenv(name, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.delenv("AWS_PROFILE", raising=False)


@pytest.fixture
def s3():
    """A mocked S3 service with a client bound to it."""
    with mock_aws():
        yield boto3.client("s3", region_name=REGION)


@pytest.fixture
def bucket(s3):
    """An empty bucket named 'music'."""
    s3.create_bucket(Bucket="music")
    return "music"


@pytest.fixture
def populated_bucket(s3, bucket):
    """A bucket holding three songs and two files that are not music."""
    contents = {
        "albums/one.mp3": b"ID3fake-one",
        "albums/two.flac": b"fLaCfake-two",
        "albums/nested/three.M4A": b"fake-three",
        "albums/cover.jpg": b"notmusic",
        "albums/notes.txt": b"notmusic",
    }
    for key, body in contents.items():
        s3.put_object(Bucket=bucket, Key=key, Body=body)
    return bucket


def make_tracks(count, bucket="music"):
    return [Track(bucket=bucket, key="song%02d.mp3" % i) for i in range(count)]


class FakeBackend:
    """An AudioBackend that records calls instead of making noise."""

    def __init__(self, duration=1000):
        self.calls = []
        self.loaded = None
        self.volume = None
        self._position = 0
        self._duration = duration
        self._finished_callback = None

    def set_finished_callback(self, callback):
        self._finished_callback = callback

    def finish(self):
        """Pretend the current track played to its end."""
        if self._finished_callback:
            self._finished_callback()

    def load(self, path):
        self.loaded = path
        self.calls.append("load")

    def play(self):
        self.calls.append("play")

    def pause(self):
        self.calls.append("pause")

    def stop(self):
        self.calls.append("stop")
        self._position = 0

    def set_volume(self, volume):
        self.volume = volume
        self.calls.append("set_volume")

    def seek(self, milliseconds):
        self._position = milliseconds
        self.calls.append("seek")

    @property
    def position(self):
        return self._position

    @property
    def duration(self):
        return self._duration


class FakeCache:
    """A TrackCache that hands back fake paths, and can be told to fail."""

    def __init__(self, failing=()):
        self.failing = set(failing)
        self.fetched = []

    def fetch(self, track):
        if track in self.failing:
            raise RuntimeError("cannot download %s" % track.uri)
        self.fetched.append(track)
        return "/tmp/%s" % track.filename


@pytest.fixture
def backend():
    return FakeBackend()


@pytest.fixture
def cache():
    return FakeCache()
