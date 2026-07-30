"""The player window.

Deliberately thin: widgets emit, the controller decides, listeners push state
back into the widgets. No playback rule is implemented here.
"""

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..player import PlaybackState
from ..playlist import RepeatMode

TICK_MS = 200


class ScanThread(QThread):
    """Scans a bucket off the UI thread so the window stays responsive."""

    found = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished_scanning = pyqtSignal(int)

    def __init__(self, scanner, location, parent=None):
        super().__init__(parent)
        self._scanner = scanner
        self._location = location

    def run(self):
        count = 0
        try:
            for track in self._scanner.scan(self._location):
                self.found.emit(track)
                count += 1
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished_scanning.emit(count)


class PlayerWindow(QMainWindow):
    """Bucket box, track list, transport controls."""

    def __init__(self, controller, scanner, initial_location=""):
        super().__init__()
        self._controller = controller
        self._scanner = scanner
        self._scan_thread = None
        self._tracks = []

        self.setWindowTitle("S3 Music Player")
        self.setMinimumSize(640, 420)
        self._build_ui(initial_location)

        controller.on_track_changed(self._on_track_changed)
        controller.on_state_changed(self._on_state_changed)
        controller.on_error(self._on_error)

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._refresh_position)
        self._timer.start()

    def _build_ui(self, initial_location):
        root = QWidget()
        layout = QVBoxLayout(root)

        source_row = QHBoxLayout()
        self.location_edit = QLineEdit(initial_location)
        self.location_edit.setPlaceholderText("s3://bucket/optional/prefix")
        self.location_edit.returnPressed.connect(self.start_scan)
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan)
        source_row.addWidget(QLabel("Bucket:"))
        source_row.addWidget(self.location_edit, 1)
        source_row.addWidget(self.scan_button)
        layout.addLayout(source_row)

        self.track_list = QListWidget()
        self.track_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.track_list, 1)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderReleased.connect(self._on_seek)
        layout.addWidget(self.position_slider)

        transport = QHBoxLayout()
        self.previous_button = QPushButton("Prev")
        self.previous_button.clicked.connect(self._controller.previous)
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._on_play_clicked)
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._controller.next)
        self.shuffle_button = QPushButton("Shuffle")
        self.shuffle_button.clicked.connect(self._on_shuffle)
        self.repeat_button = QPushButton("Repeat: off")
        self.repeat_button.clicked.connect(self._on_repeat)
        for widget in (
            self.previous_button,
            self.play_button,
            self.next_button,
            self.shuffle_button,
            self.repeat_button,
        ):
            transport.addWidget(widget)

        transport.addStretch(1)
        transport.addWidget(QLabel("Volume"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setValue(int(self._controller.volume * 100))
        self.volume_slider.valueChanged.connect(self._on_volume)
        transport.addWidget(self.volume_slider)
        layout.addLayout(transport)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Enter a bucket and press Scan")

    def start_scan(self):
        location = self.location_edit.text().strip()
        if not location:
            self.statusBar().showMessage("Enter a bucket first")
            return
        if self._scan_thread is not None and self._scan_thread.isRunning():
            return

        self.track_list.clear()
        self._tracks = []
        self.scan_button.setEnabled(False)
        self.statusBar().showMessage("Scanning %s ..." % location)

        self._scan_thread = ScanThread(self._scanner, location, self)
        self._scan_thread.found.connect(self._on_track_found)
        self._scan_thread.failed.connect(self._on_scan_failed)
        self._scan_thread.finished_scanning.connect(self._on_scan_finished)
        self._scan_thread.start()

    def _on_track_found(self, track):
        self._tracks.append(track)
        self.track_list.addItem(QListWidgetItem(track.display_name))

    def _on_scan_failed(self, message):
        self.scan_button.setEnabled(True)
        self.statusBar().showMessage("Scan failed: %s" % message)
        QMessageBox.warning(self, "Scan failed", message)

    def _on_scan_finished(self, count):
        self.scan_button.setEnabled(True)
        self._controller.load_tracks(self._tracks)
        self.statusBar().showMessage("Found %d track%s" % (count, "" if count == 1 else "s"))

    def _on_item_activated(self, item):
        self._controller.jump_to(self.track_list.row(item))
        if not self._controller.is_playing:
            self._controller.play()

    def _on_play_clicked(self):
        if not self._controller.playlist:
            self.statusBar().showMessage("Nothing to play -- scan a bucket first")
            return
        self._controller.toggle()

    def _on_shuffle(self):
        self._controller.playlist.shuffle()
        self._rebuild_list()

    def _on_repeat(self):
        order = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        playlist = self._controller.playlist
        playlist.repeat = order[(order.index(playlist.repeat) + 1) % len(order)]
        self.repeat_button.setText("Repeat: %s" % playlist.repeat.value)

    def _on_volume(self, value):
        self._controller.set_volume(value / 100.0)

    def _on_seek(self):
        self._controller.seek(self.position_slider.value())

    def _rebuild_list(self):
        self.track_list.clear()
        for track in self._controller.playlist:
            self.track_list.addItem(QListWidgetItem(track.display_name))
        self._highlight_current()

    def _highlight_current(self):
        index = self._controller.playlist.index
        if 0 <= index < self.track_list.count():
            self.track_list.setCurrentRow(index)

    def _on_track_changed(self, track):
        self._highlight_current()
        if track is not None:
            self.statusBar().showMessage(track.display_name)

    def _on_state_changed(self, state):
        self.play_button.setText("Pause" if state is PlaybackState.PLAYING else "Play")
        if state is PlaybackState.STOPPED:
            self.position_slider.setRange(0, 0)

    def _on_error(self, track, exc):
        self.statusBar().showMessage("Skipped %s: %s" % (track.title, exc))

    def _refresh_position(self):
        if self._controller.state is PlaybackState.STOPPED:
            return
        if self.position_slider.isSliderDown():
            return
        duration = self._controller.duration
        if duration > 0:
            self.position_slider.setRange(0, duration)
        self.position_slider.setValue(self._controller.position)

    def closeEvent(self, event):
        self._timer.stop()
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.requestInterruption()
            self._scan_thread.wait(1000)
        super().closeEvent(event)
