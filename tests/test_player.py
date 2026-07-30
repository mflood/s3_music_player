import pytest

from conftest import FakeBackend, FakeCache, make_tracks
from s3music.errors import EmptyPlaylist
from s3music.player import PlaybackState, PlayerController
from s3music.playlist import Playlist, RepeatMode


def controller_with(tracks, backend=None, cache=None, repeat=RepeatMode.OFF):
    backend = backend or FakeBackend()
    cache = cache or FakeCache()
    playlist = Playlist(tracks, repeat=repeat)
    return PlayerController(backend, cache, playlist), backend, cache


def test_starts_stopped_and_sets_volume_on_the_backend():
    controller, backend, _ = controller_with(make_tracks(2))

    assert controller.state is PlaybackState.STOPPED
    assert backend.volume == pytest.approx(0.8)


def test_play_fetches_loads_and_starts():
    tracks = make_tracks(2)
    controller, backend, cache = controller_with(tracks)

    assert controller.play() == tracks[0]
    assert cache.fetched == [tracks[0]]
    assert backend.calls[-2:] == ["load", "play"]
    assert controller.state is PlaybackState.PLAYING


def test_play_on_an_empty_playlist_raises():
    controller, _, _ = controller_with([])

    with pytest.raises(EmptyPlaylist):
        controller.play()


def test_pause_then_play_resumes_without_refetching():
    controller, backend, cache = controller_with(make_tracks(2))
    controller.play()
    controller.pause()

    assert controller.state is PlaybackState.PAUSED

    controller.play()

    assert controller.state is PlaybackState.PLAYING
    assert len(cache.fetched) == 1, "resume must not re-download"
    assert backend.calls[-1] == "play"


def test_pause_when_not_playing_does_nothing():
    controller, backend, _ = controller_with(make_tracks(1))
    before = list(backend.calls)

    assert controller.pause() is PlaybackState.STOPPED
    assert backend.calls == before


def test_toggle_alternates():
    controller, _, _ = controller_with(make_tracks(1))

    assert controller.toggle() is PlaybackState.PLAYING
    assert controller.toggle() is PlaybackState.PAUSED
    assert controller.toggle() is PlaybackState.PLAYING


def test_stop_clears_the_loaded_track():
    controller, backend, _ = controller_with(make_tracks(2))
    controller.play()
    controller.stop()

    assert controller.state is PlaybackState.STOPPED
    assert controller.loaded_track is None
    assert "stop" in backend.calls


def test_finishing_a_track_advances_and_keeps_playing():
    tracks = make_tracks(3)
    controller, backend, cache = controller_with(tracks)
    controller.play()

    backend.finish()

    assert controller.current_track == tracks[1]
    assert controller.state is PlaybackState.PLAYING
    assert cache.fetched == [tracks[0], tracks[1]]


def test_finishing_the_last_track_stops():
    tracks = make_tracks(2)
    controller, backend, _ = controller_with(tracks)
    controller.play()
    backend.finish()
    backend.finish()

    assert controller.state is PlaybackState.STOPPED


def test_finishing_the_last_track_under_repeat_all_wraps():
    tracks = make_tracks(2)
    controller, backend, _ = controller_with(tracks, repeat=RepeatMode.ALL)
    controller.play()
    backend.finish()
    backend.finish()

    assert controller.current_track == tracks[0]
    assert controller.state is PlaybackState.PLAYING


def test_finishing_under_repeat_one_replays_the_same_track():
    tracks = make_tracks(3)
    controller, backend, cache = controller_with(tracks, repeat=RepeatMode.ONE)
    controller.play()

    backend.finish()

    assert controller.current_track == tracks[0]
    assert cache.fetched == [tracks[0], tracks[0]]


def test_a_stray_finish_after_stop_does_not_restart_playback():
    """Backends can emit end-of-media after an explicit stop."""
    controller, backend, _ = controller_with(make_tracks(3))
    controller.play()
    controller.stop()

    backend.finish()

    assert controller.state is PlaybackState.STOPPED


def test_next_while_playing_starts_the_next_track():
    tracks = make_tracks(3)
    controller, _, cache = controller_with(tracks)
    controller.play()

    assert controller.next() == tracks[1]
    assert controller.state is PlaybackState.PLAYING
    assert cache.fetched == [tracks[0], tracks[1]]


def test_next_while_stopped_moves_the_cursor_without_playing():
    tracks = make_tracks(3)
    controller, _, cache = controller_with(tracks)

    assert controller.next() == tracks[1]
    assert controller.state is PlaybackState.STOPPED
    assert cache.fetched == []


def test_next_past_the_end_stops():
    controller, _, _ = controller_with(make_tracks(1))
    controller.play()

    assert controller.next() is None
    assert controller.state is PlaybackState.STOPPED


def test_previous_while_playing_restarts_on_the_earlier_track():
    tracks = make_tracks(3)
    controller, _, cache = controller_with(tracks)
    controller.play()
    controller.next()

    assert controller.previous() == tracks[0]
    assert cache.fetched == [tracks[0], tracks[1], tracks[0]]


def test_jump_to_while_playing_switches_track():
    tracks = make_tracks(4)
    controller, _, _ = controller_with(tracks)
    controller.play()

    assert controller.jump_to(3) == tracks[3]
    assert controller.loaded_track == tracks[3]


def test_an_undownloadable_track_is_skipped_not_fatal():
    tracks = make_tracks(3)
    cache = FakeCache(failing={tracks[0]})
    controller, _, _ = controller_with(tracks, cache=cache)

    errors = []
    controller.on_error(lambda track, exc: errors.append(track))

    assert controller.play() == tracks[1]
    assert controller.state is PlaybackState.PLAYING
    assert errors == [tracks[0]]


def test_a_playlist_that_entirely_fails_stops_without_looping():
    """With repeat on and every track broken, this must terminate."""
    tracks = make_tracks(3)
    cache = FakeCache(failing=set(tracks))
    controller, _, _ = controller_with(tracks, cache=cache, repeat=RepeatMode.ALL)

    errors = []
    controller.on_error(lambda track, exc: errors.append(track))

    assert controller.play() is None
    assert controller.state is PlaybackState.STOPPED
    assert len(errors) == 3, "each track tried exactly once"


def test_volume_is_clamped_to_the_valid_range():
    controller, backend, _ = controller_with(make_tracks(1))

    assert controller.set_volume(1.5) == 1.0
    assert controller.set_volume(-0.5) == 0.0
    assert backend.volume == 0.0


def test_seek_never_goes_negative():
    controller, backend, _ = controller_with(make_tracks(1))
    controller.play()
    controller.seek(-100)

    assert backend.position == 0


def test_position_and_duration_come_from_the_backend():
    backend = FakeBackend(duration=4242)
    controller, _, _ = controller_with(make_tracks(1), backend=backend)
    controller.play()
    controller.seek(500)

    assert controller.position == 500
    assert controller.duration == 4242


def test_listeners_are_told_about_track_and_state_changes():
    tracks = make_tracks(2)
    controller, backend, _ = controller_with(tracks)

    seen_tracks, seen_states = [], []
    controller.on_track_changed(seen_tracks.append)
    controller.on_state_changed(seen_states.append)

    controller.play()
    controller.pause()

    assert tracks[0] in seen_tracks
    assert seen_states == [PlaybackState.PLAYING, PlaybackState.PAUSED]


def test_state_listeners_do_not_fire_on_a_no_op():
    controller, _, _ = controller_with(make_tracks(2))
    seen = []
    controller.on_state_changed(seen.append)

    controller.play()
    controller.play()

    assert seen == [PlaybackState.PLAYING]


def test_load_tracks_replaces_the_queue():
    controller, _, _ = controller_with(make_tracks(2))
    replacement = make_tracks(4, bucket="other")

    assert controller.load_tracks(replacement) == replacement[0]
    assert len(controller.playlist) == 4
