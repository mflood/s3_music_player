import pytest

from conftest import make_tracks
from s3music.playlist import Playlist, RepeatMode
from s3music.track import Track


def test_empty_playlist_has_no_current_track():
    playlist = Playlist()

    assert len(playlist) == 0
    assert playlist.current is None
    assert playlist.index == -1
    assert not playlist


def test_loading_sets_the_cursor_to_the_first_track():
    tracks = make_tracks(3)
    playlist = Playlist()

    assert playlist.load(tracks) == tracks[0]
    assert playlist.index == 0
    assert len(playlist) == 3


def test_next_walks_forward_then_stops_at_the_end():
    tracks = make_tracks(3)
    playlist = Playlist(tracks)

    assert playlist.next() == tracks[1]
    assert playlist.next() == tracks[2]
    assert playlist.next() is None
    assert playlist.current == tracks[2], "cursor stays on the last track"


def test_repeat_all_wraps_to_the_start():
    tracks = make_tracks(2)
    playlist = Playlist(tracks, repeat=RepeatMode.ALL)

    assert playlist.next() == tracks[1]
    assert playlist.next() == tracks[0]


def test_repeat_one_returns_the_same_track_without_moving():
    tracks = make_tracks(3)
    playlist = Playlist(tracks, repeat=RepeatMode.ONE)

    assert playlist.next() == tracks[0]
    assert playlist.next() == tracks[0]
    assert playlist.index == 0


def test_previous_stops_at_the_first_track():
    tracks = make_tracks(3)
    playlist = Playlist(tracks)
    playlist.jump_to(1)

    assert playlist.previous() == tracks[0]
    assert playlist.previous() == tracks[0]


def test_previous_wraps_backwards_under_repeat_all():
    tracks = make_tracks(3)
    playlist = Playlist(tracks, repeat=RepeatMode.ALL)

    assert playlist.previous() == tracks[2]


def test_previous_ignores_repeat_one():
    """Repeat-one must not trap you on a track you are trying to leave."""
    tracks = make_tracks(3)
    playlist = Playlist(tracks, repeat=RepeatMode.ONE)
    playlist.jump_to(2)

    assert playlist.previous() == tracks[1]


def test_next_and_previous_on_an_empty_playlist_return_none():
    playlist = Playlist()

    assert playlist.next() is None
    assert playlist.previous() is None


def test_jump_to_rejects_out_of_range():
    playlist = Playlist(make_tracks(3))

    with pytest.raises(IndexError):
        playlist.jump_to(3)
    with pytest.raises(IndexError):
        playlist.jump_to(-1)


def test_jump_to_on_empty_playlist_raises():
    with pytest.raises(IndexError, match="empty"):
        Playlist().jump_to(0)


def test_jump_to_track_finds_by_value():
    tracks = make_tracks(3)
    playlist = Playlist(tracks)

    assert playlist.jump_to_track(tracks[2]) == tracks[2]
    assert playlist.index == 2


def test_jump_to_track_rejects_a_stranger():
    playlist = Playlist(make_tracks(2))

    with pytest.raises(ValueError):
        playlist.jump_to_track(Track(bucket="other", key="nope.mp3"))


def test_shuffle_keeps_the_current_track_current():
    tracks = make_tracks(10)
    playlist = Playlist(tracks)
    playlist.jump_to(4)
    current = playlist.current

    playlist.shuffle(seed=1)

    assert playlist.current == current
    assert playlist.is_shuffled
    assert sorted(playlist.tracks) == sorted(tracks), "no track lost or duplicated"


def test_shuffle_actually_reorders():
    tracks = make_tracks(10)
    playlist = Playlist(tracks)

    playlist.shuffle(seed=7)

    assert playlist.tracks != tuple(tracks)


def test_shuffle_is_reproducible_with_a_seed():
    first = Playlist(make_tracks(10))
    second = Playlist(make_tracks(10))

    first.shuffle(seed=42)
    second.shuffle(seed=42)

    assert first.tracks == second.tracks


def test_shuffling_a_single_track_is_harmless():
    playlist = Playlist(make_tracks(1))

    assert playlist.shuffle(seed=1) == playlist.tracks[0]
    assert playlist.is_shuffled


def test_shuffling_an_empty_playlist_is_harmless():
    playlist = Playlist()
    assert playlist.shuffle(seed=1) is None


def test_sort_restores_order_and_keeps_the_cursor():
    tracks = make_tracks(6)
    playlist = Playlist(tracks)
    playlist.jump_to(3)
    current = playlist.current
    playlist.shuffle(seed=3)

    playlist.sort()

    assert playlist.tracks == tuple(tracks)
    assert playlist.current == current
    assert not playlist.is_shuffled


def test_append_to_an_empty_playlist_sets_the_cursor():
    playlist = Playlist()
    track = Track(bucket="music", key="a.mp3")

    playlist.append(track)

    assert playlist.current == track
    assert playlist.index == 0


def test_clear_empties_and_resets():
    playlist = Playlist(make_tracks(3))
    playlist.clear()

    assert len(playlist) == 0
    assert playlist.current is None
    assert playlist.index == -1


def test_playlist_is_iterable_and_indexable():
    tracks = make_tracks(3)
    playlist = Playlist(tracks)

    assert list(playlist) == tracks
    assert playlist[1] == tracks[1]
