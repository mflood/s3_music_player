import pytest

from s3music.errors import InvalidURI
from s3music.track import Track


def test_uri_is_assembled_from_bucket_and_key():
    track = Track(bucket="music", key="albums/song.mp3")
    assert track.uri == "s3://music/albums/song.mp3"


def test_filename_title_and_extension():
    track = Track(bucket="music", key="albums/Deep Cut.MP3")

    assert track.filename == "Deep Cut.MP3"
    assert track.title == "Deep Cut"
    assert track.extension == ".mp3", "extension is normalised, title is not"


def test_a_key_without_an_extension():
    track = Track(bucket="music", key="albums/untitled")

    assert track.extension == ""
    assert track.title == "untitled"


def test_display_name_includes_the_folder():
    track = Track(bucket="music", key="Rush/Moving Pictures/01 - Tom Sawyer.mp3")

    assert track.folder == "Moving Pictures"
    assert track.display_name == "Moving Pictures — 01 - Tom Sawyer"


def test_display_name_falls_back_to_the_title_at_the_bucket_root():
    track = Track(bucket="music", key="loose.mp3")

    assert track.folder == ""
    assert track.display_name == "loose"


def test_display_name_with_a_single_folder_level():
    track = Track(bucket="music", key="Rush/YYZ.mp3")

    assert track.display_name == "Rush — YYZ"


def test_a_dotted_name_uses_only_the_last_segment():
    track = Track(bucket="music", key="a.b.c.flac")

    assert track.extension == ".flac"
    assert track.title == "a.b.c"


@pytest.mark.parametrize(
    "uri,bucket,key",
    [
        ("s3://music/song.mp3", "music", "song.mp3"),
        ("s3://music/a/b/c.mp3", "music", "a/b/c.mp3"),
        ("s3://m/ /space.mp3", "m", " /space.mp3"),
    ],
)
def test_from_uri_round_trips(uri, bucket, key):
    track = Track.from_uri(uri)

    assert (track.bucket, track.key) == (bucket, key)
    assert track.uri == uri


@pytest.mark.parametrize(
    "bad",
    ["https://music/song.mp3", "music/song.mp3", "s3://music", "s3://music/", "s3://"],
)
def test_from_uri_rejects_junk(bad):
    with pytest.raises(InvalidURI):
        Track.from_uri(bad)


def test_a_track_needs_both_bucket_and_key():
    with pytest.raises(InvalidURI):
        Track(bucket="", key="song.mp3")
    with pytest.raises(InvalidURI):
        Track(bucket="music", key="")


def test_equality_ignores_size_and_etag():
    """The same object listed twice must compare equal even if metadata differs."""
    first = Track(bucket="m", key="s.mp3", size=1, etag="a")
    second = Track(bucket="m", key="s.mp3", size=999, etag="z")

    assert first == second
    assert len({first, second}) == 1


def test_tracks_sort_by_bucket_then_key():
    tracks = [
        Track(bucket="b", key="a.mp3"),
        Track(bucket="a", key="z.mp3"),
        Track(bucket="a", key="a.mp3"),
    ]

    assert [t.uri for t in sorted(tracks)] == [
        "s3://a/a.mp3",
        "s3://a/z.mp3",
        "s3://b/a.mp3",
    ]


def test_str_is_the_uri():
    assert str(Track(bucket="m", key="s.mp3")) == "s3://m/s.mp3"
