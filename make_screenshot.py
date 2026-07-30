"""Render the player window offscreen and save a PNG for the README.

Run with: QT_QPA_PLATFORM=offscreen python make_screenshot.py docs/player.png
"""

import sys

import boto3
from moto import mock_aws
from PyQt6.QtWidgets import QApplication

from s3music.cache import TrackCache
from s3music.player import PlayerController
from s3music.playlist import RepeatMode
from s3music.qt.window import PlayerWindow
from s3music.scanner import S3MusicScanner

SONGS = [
    "Rush/01 - Tom Sawyer.mp3",
    "Rush/02 - Red Barchetta.mp3",
    "Rush/03 - YYZ.mp3",
    "Talking Heads/01 - Once in a Lifetime.mp3",
    "Talking Heads/02 - Crosseyed and Painless.mp3",
    "Nina Simone/01 - Sinnerman.flac",
    "Nina Simone/02 - Feeling Good.flac",
]


class QuietBackend:
    """Enough of an AudioBackend to paint a window without a sound card."""

    position = 74000
    duration = 276000

    def load(self, path):
        pass

    def play(self):
        pass

    def pause(self):
        pass

    def stop(self):
        pass

    def seek(self, ms):
        pass

    def set_volume(self, volume):
        pass


def main(destination):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="my-music")
        for key in SONGS:
            client.put_object(Bucket="my-music", Key=key, Body=b"x")

        app = QApplication([])
        controller = PlayerController(QuietBackend(), TrackCache(client, "/tmp/cache"))
        window = PlayerWindow(
            controller, S3MusicScanner(client), initial_location="s3://my-music"
        )
        window.resize(720, 460)
        window.show()

        window.start_scan()
        window._scan_thread.wait(5000)
        app.processEvents()

        controller.playlist.repeat = RepeatMode.ALL
        window.repeat_button.setText("Repeat: all")
        controller.jump_to(2)
        controller.play()
        window.position_slider.setRange(0, controller.duration)
        window.position_slider.setValue(controller.position)
        app.processEvents()

        window.grab().save(destination, "PNG")
        print("wrote %s" % destination)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/player.png")
