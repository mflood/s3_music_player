import pytest

from s3music.cache import TrackCache
from s3music.errors import DownloadError
from s3music.track import Track


def test_fetch_downloads_the_object(populated_bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=populated_bucket, key="albums/one.mp3")

    path = cache.fetch(track)

    assert path.exists()
    assert path.read_bytes() == b"ID3fake-one"
    assert cache.is_cached(track)


def test_fetch_is_a_no_op_when_already_cached(populated_bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=populated_bucket, key="albums/one.mp3")

    first = cache.fetch(track)
    first.write_bytes(b"locally-modified")
    second = cache.fetch(track)

    assert second == first
    assert second.read_bytes() == b"locally-modified", "should not re-download"


def test_cache_path_keeps_the_extension(populated_bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=populated_bucket, key="albums/two.flac")

    assert cache.path_for(track).suffix == ".flac"


def test_a_malicious_key_cannot_escape_the_cache_directory(bucket, s3, tmp_path):
    """Object keys are arbitrary strings; the cache path must stay put."""
    cache_dir = tmp_path / "cache"
    cache = TrackCache(s3, cache_dir)
    track = Track(bucket=bucket, key="../../../../etc/passwd.mp3")

    path = cache.path_for(track)

    assert path.parent == cache_dir
    assert ".." not in str(path)


def test_distinct_tracks_get_distinct_paths(bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    first = Track(bucket=bucket, key="a/song.mp3")
    second = Track(bucket=bucket, key="b/song.mp3")

    assert cache.path_for(first) != cache.path_for(second)


def test_the_same_track_always_maps_to_the_same_path(bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=bucket, key="a/song.mp3")

    assert cache.path_for(track) == cache.path_for(track)


def test_missing_object_raises_download_error(bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=bucket, key="not-there.mp3")

    with pytest.raises(DownloadError, match="could not download"):
        cache.fetch(track)


def test_a_failed_download_leaves_nothing_behind(bucket, s3, tmp_path):
    """A half-written file must not later look like a valid cache hit."""
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=bucket, key="not-there.mp3")

    with pytest.raises(DownloadError):
        cache.fetch(track)

    assert not cache.is_cached(track)
    assert list(tmp_path.iterdir()) == []


def test_an_empty_file_does_not_count_as_cached(bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    track = Track(bucket=bucket, key="song.mp3")
    cache.path_for(track).parent.mkdir(parents=True, exist_ok=True)
    cache.path_for(track).touch()

    assert not cache.is_cached(track)


def test_cache_directory_is_created_on_demand(populated_bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path / "deep" / "nested")
    cache.fetch(Track(bucket=populated_bucket, key="albums/one.mp3"))

    assert cache.directory.is_dir()


def test_clear_removes_files_and_reports_the_count(populated_bucket, s3, tmp_path):
    cache = TrackCache(s3, tmp_path)
    cache.fetch(Track(bucket=populated_bucket, key="albums/one.mp3"))
    cache.fetch(Track(bucket=populated_bucket, key="albums/two.flac"))

    assert cache.size_bytes > 0
    assert cache.clear() == 2
    assert cache.size_bytes == 0


def test_clear_on_a_missing_directory_is_harmless(s3, tmp_path):
    assert TrackCache(s3, tmp_path / "never-made").clear() == 0


def test_size_of_a_missing_directory_is_zero(s3, tmp_path):
    assert TrackCache(s3, tmp_path / "never-made").size_bytes == 0
