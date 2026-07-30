"""Offscreen tests for the Qt layer.

These build the real window against Qt's ``offscreen`` platform plugin, so CI
exercises the widget wiring without a display server. They deliberately do not
re-test playback rules -- those live in test_player.py, where they can be
checked without a toolkit at all. What is worth checking here is only what the
view is responsible for: that signals reach the controller and that controller
callbacks reach the widgets.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6", reason="GUI extra not installed")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from conftest import FakeBackend, FakeCache, make_tracks  # noqa: E402
from s3music.player import PlaybackState, PlayerController  # noqa: E402
from s3music.playlist import RepeatMode  # noqa: E402
from s3music.qt.backend import QtAudioBackend  # noqa: E402
from s3music.qt.window import PlayerWindow  # noqa: E402
from s3music.scanner import S3MusicScanner  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qapp, s3):
    """A real window over a fake audio device.

    The view's job is wiring, not decoding, so these tests use FakeBackend and
    leave the real QMediaPlayer to the dedicated backend test below. Handing a
    real device a fake cache path would only prove FFmpeg reports missing
    files.
    """
    controller = PlayerController(FakeBackend(), FakeCache())
    window = PlayerWindow(controller, S3MusicScanner(s3))
    yield window
    window.close()


def test_window_builds_with_the_expected_controls(window):
    assert window.windowTitle() == "S3 Music Player"
    for name in (
        "location_edit",
        "scan_button",
        "track_list",
        "play_button",
        "next_button",
        "previous_button",
        "volume_slider",
        "position_slider",
    ):
        assert hasattr(window, name), name


def test_scanning_populates_the_track_list(window, populated_bucket):
    window.location_edit.setText(populated_bucket)
    window.start_scan()
    window._scan_thread.wait(5000)
    QApplication.processEvents()

    assert window.track_list.count() == 3
    assert len(window._controller.playlist) == 3
    assert "Found 3 tracks" in window.statusBar().currentMessage()


def test_scanning_a_missing_bucket_reports_in_the_status_bar(window, monkeypatch):
    monkeypatch.setattr(
        "s3music.qt.window.QMessageBox.warning", lambda *a, **k: None
    )
    window.location_edit.setText("no-such-bucket-anywhere")
    window.start_scan()
    window._scan_thread.wait(5000)
    QApplication.processEvents()

    assert "Scan failed" in window.statusBar().currentMessage()
    assert window.scan_button.isEnabled(), "button must be usable again"


def test_scanning_with_an_empty_box_does_not_start_a_thread(window):
    window.location_edit.setText("   ")
    window.start_scan()

    assert window._scan_thread is None
    assert "Enter a bucket" in window.statusBar().currentMessage()


def test_play_button_label_follows_playback_state(window):
    window._controller.load_tracks(make_tracks(2))

    window.play_button.click()
    assert window.play_button.text() == "Pause"
    assert window._controller.state is PlaybackState.PLAYING

    window.play_button.click()
    assert window.play_button.text() == "Play"


def test_play_button_with_nothing_loaded_says_so_instead_of_raising(window):
    window.play_button.click()

    assert "Nothing to play" in window.statusBar().currentMessage()
    assert window._controller.state is PlaybackState.STOPPED


def test_repeat_button_cycles_through_the_modes(window):
    playlist = window._controller.playlist

    assert playlist.repeat is RepeatMode.OFF
    window.repeat_button.click()
    assert playlist.repeat is RepeatMode.ALL
    window.repeat_button.click()
    assert playlist.repeat is RepeatMode.ONE
    window.repeat_button.click()
    assert playlist.repeat is RepeatMode.OFF
    assert window.repeat_button.text() == "Repeat: off"


def test_volume_slider_drives_the_controller(window):
    window.volume_slider.setValue(25)
    assert window._controller.volume == pytest.approx(0.25)


def test_shuffle_rebuilds_the_visible_list(window):
    window._controller.load_tracks(make_tracks(8))
    window._rebuild_list()
    before = [window.track_list.item(i).text() for i in range(window.track_list.count())]

    window.shuffle_button.click()
    after = [window.track_list.item(i).text() for i in range(window.track_list.count())]

    assert sorted(after) == sorted(before)
    assert window.track_list.count() == 8


def test_track_change_highlights_the_current_row(window):
    window._controller.load_tracks(make_tracks(5))
    window._rebuild_list()

    window._controller.jump_to(3)

    assert window.track_list.currentRow() == 3


def test_next_button_advances_the_selection(window):
    window._controller.load_tracks(make_tracks(3))
    window._rebuild_list()

    window.next_button.click()

    assert window._controller.playlist.index == 1
    assert window.track_list.currentRow() == 1


def test_qt_backend_implements_what_the_controller_needs(qapp):
    backend = QtAudioBackend()
    for method in ("load", "play", "pause", "stop", "set_volume", "seek"):
        assert callable(getattr(backend, method)), method
    assert isinstance(backend.position, int)
    assert isinstance(backend.duration, int)

    backend.set_volume(0.5)
    backend.stop()


def test_build_window_assembles_the_whole_stack(qapp, s3, tmp_path):
    from s3music.qt.app import build_window

    window = build_window(s3, tmp_path)
    try:
        assert window.windowTitle() == "S3 Music Player"
        assert window._controller.playlist is not None
    finally:
        window.close()
