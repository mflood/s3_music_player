import pytest

from s3music.errors import ScanError
from s3music.scanner import S3MusicScanner


def test_finds_only_audio_files(populated_bucket, s3):
    scanner = S3MusicScanner(s3)
    keys = [t.key for t in scanner.scan(populated_bucket)]

    assert "albums/one.mp3" in keys
    assert "albums/two.flac" in keys
    assert "albums/cover.jpg" not in keys
    assert "albums/notes.txt" not in keys


def test_extension_matching_is_case_insensitive(populated_bucket, s3):
    keys = [t.key for t in S3MusicScanner(s3).scan(populated_bucket)]
    assert "albums/nested/three.M4A" in keys


def test_tracks_carry_size_and_etag(populated_bucket, s3):
    tracks = {t.key: t for t in S3MusicScanner(s3).scan(populated_bucket)}
    one = tracks["albums/one.mp3"]

    assert one.size == len(b"ID3fake-one")
    assert one.etag and '"' not in one.etag


def test_empty_bucket_yields_nothing_rather_than_raising(bucket, s3):
    """A bucket with no objects has no Contents key in the response at all."""
    assert list(S3MusicScanner(s3).scan(bucket)) == []


def test_bucket_with_no_audio_yields_nothing(bucket, s3):
    s3.put_object(Bucket=bucket, Key="readme.txt", Body=b"hello")
    assert list(S3MusicScanner(s3).scan(bucket)) == []


def test_prefix_restricts_the_scan(populated_bucket, s3):
    tracks = list(S3MusicScanner(s3).scan(populated_bucket, prefix="albums/nested/"))
    assert [t.key for t in tracks] == ["albums/nested/three.M4A"]


def test_s3_uri_is_accepted_in_place_of_a_bucket_name(populated_bucket, s3):
    tracks = list(S3MusicScanner(s3).scan("s3://%s" % populated_bucket))
    assert len(tracks) == 3


def test_prefix_can_be_embedded_in_the_uri(populated_bucket, s3):
    tracks = list(S3MusicScanner(s3).scan("s3://%s/albums/nested" % populated_bucket))
    assert [t.key for t in tracks] == ["albums/nested/three.M4A"]


def test_explicit_prefix_wins_over_an_embedded_one(populated_bucket, s3):
    tracks = list(
        S3MusicScanner(s3).scan(
            "s3://%s/albums/nested" % populated_bucket, prefix="albums/one"
        )
    )
    assert [t.key for t in tracks] == ["albums/one.mp3"]


def test_directory_markers_are_skipped(bucket, s3):
    s3.put_object(Bucket=bucket, Key="folder.mp3/", Body=b"")
    s3.put_object(Bucket=bucket, Key="folder.mp3/real.mp3", Body=b"x")

    keys = [t.key for t in S3MusicScanner(s3).scan(bucket)]
    assert keys == ["folder.mp3/real.mp3"]


def test_paginates_beyond_one_thousand_objects(bucket, s3):
    """S3 caps a listing page at 1000 keys; the scan must not stop there."""
    for i in range(1005):
        s3.put_object(Bucket=bucket, Key="song%04d.mp3" % i, Body=b"x")

    assert len(list(S3MusicScanner(s3).scan(bucket))) == 1005


def test_scan_is_lazy(bucket, s3):
    """The first track arrives without draining the whole bucket."""
    for i in range(1005):
        s3.put_object(Bucket=bucket, Key="song%04d.mp3" % i, Body=b"x")

    scan = S3MusicScanner(s3).scan(bucket)
    first = next(scan)
    assert first.key == "song0000.mp3"


def test_custom_extension_set(populated_bucket, s3):
    scanner = S3MusicScanner(s3, extensions={".flac"})
    assert [t.key for t in scanner.scan(populated_bucket)] == ["albums/two.flac"]


def test_extensions_are_normalised_to_lowercase(s3):
    assert ".flac" in S3MusicScanner(s3, extensions={".FLAC"}).extensions


def test_keys_without_an_extension_are_ignored(bucket, s3):
    s3.put_object(Bucket=bucket, Key="mp3", Body=b"x")
    assert list(S3MusicScanner(s3).scan(bucket)) == []


def test_missing_bucket_raises_scan_error(s3):
    with pytest.raises(ScanError, match="could not scan"):
        list(S3MusicScanner(s3).scan("no-such-bucket-here"))


def test_list_buckets_returns_sorted_names(s3):
    for name in ("zebra", "apple", "mango"):
        s3.create_bucket(Bucket=name)

    assert S3MusicScanner(s3).list_buckets() == ["apple", "mango", "zebra"]


def test_list_buckets_on_an_empty_account(s3):
    assert S3MusicScanner(s3).list_buckets() == []
