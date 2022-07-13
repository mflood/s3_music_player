"""
    conda activate mypython3
"""
import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PyQt5 import QtCore as qtc


from PyQt5 import QtMultimedia as qtmm

from myboto import S3Client

class MainWindow(qtw.QMainWindow):
    def __init__(self):

        self.playing = False
        self.media_player = qtmm.QMediaPlayer()
        self.s3_client = S3Client()

        qtw.QMainWindow.__init__(self)

        self.setMinimumSize(qtc.QSize(320, 140))    
        self.setWindowTitle("PyQt Line Edit example (textfield) - pythonprogramminglanguage.com") 

        self.add_line_edit(label="Sound S3 Url:", ypos=20)

        pybutton = qtw.QPushButton('OK', self)
        pybutton.clicked.connect(self.clickMethod)
        pybutton.resize(200,32)
        pybutton.move(80, 60)        

        self.combobox = qtw.QComboBox(self)
        self.combobox.move(80, 100)


    def add_line_edit(self, label: str, ypos: int):
        self.line_edit_label = qtw.QLabel(self)
        self.line_edit_label.setText(label)
        # x: 20, y: 20
        self.line_edit_label.move(20, ypos)

        self.line_edit = qtw.QLineEdit(self)
        self.line_edit.setText("s3://bucket/path)
        # x: 140 y: 20
        self.line_edit.move(140, ypos)
        self.line_edit.resize(400, 32)

    def clickMethod(self):
        s3_url = self.line_edit.text()
        if not s3_url:
            print("empty")
            return
        self.populateComboBox(name=s3_url)
        print("Downloading file")
        self.s3_client.download_s3_file(s3_url, "mysound.mp3")
        self.play_local_file("mysound.mp3")

    def play_local_file(self, filename):
        print("Playing file")
        #file = qtc.QUrl('file:///Users/matthewflood/Downloads/Korean made easy for beginners 2nd.Ed._017.mp3')
        #file = qtc.QUrl.fromLocalFile(qtc.QFile(filename).absoluteFilePath());
        info1 = qtc.QFileInfo(filename)
        print(info1.absoluteFilePath())
        file = qtc.QUrl('file://' + info1.absoluteFilePath())
        #file = qtc.QUrl('file:///Users/matthewflood/github_mflood/s3_music_player/app/mysound.mp3')
        content = qtmm.QMediaContent(file)
        self.media_player.setMedia(content)
        self.media_player.stateChanged.connect(self.hear_end)
        self.media_player.positionChanged.connect(self.handle_position_changed)
        self.media_player.setNotifyInterval(100)

        self.media_player.setPosition(1000 * 0.2)
        self.media_player.setPlaybackRate(.9)
        self.playing = True
        self.media_player.play()

    def handle_position_changed(self, somearg):
        print(f"plsition changed: {somearg}")
        if not self.playing:
            print("derp")
            return

        if somearg > 3000:
            self.playing = False
            print(f"state: {self.media_player.state()}")
            print("stopping...")
            self.media_player.pause()
        print("end of method")

    def populateComboBox(self, name):
        self.combobox.addItem('One')
        self.combobox.addItem('Two')
        self.combobox.addItem('Three')
        self.combobox.addItem('Four')

        # combobox3.insertItem(2, 'Hello!')
        self.combobox.insertItem(2, name)

        #combobox4.addItems(['One', 'Two', 'Three', 'Four'])
        #combobox4.insertItems(2, ['Hello!', 'again'])

        #icon_penguin = QIcon('animal-penguin.png')
        #icon_monkey = QIcon('animal-monkey.png')
        #icon_bauble = QIcon('bauble.png')
        #combobox5.addItem(icon_penguin, 'Linux')
        #combobox5.addItem(icon_monkey, 'Monkeyix')
        #combobox5.insertItem(1, icon_bauble, 'Baublix')

    def hear_end(self, arg):
        if arg == 1:
            print("WE ARe PLAYING")
            self.playing = True
        else:
            print("WE ARE sTOPPED")
            self.playing = False
    


class MainWindow2(qtw.QWidget):

    def __init__(self):
        super().__init__()

        self.media_player = qtmm.QMediaPlayer()
        self.combobox = self.add_combobox()
        #self.add_player()
        # f = self.get_file()
        file = qtc.QUrl('file:///Users/matthewflood/Downloads/summer nights.mp3')
        file = qtc.QUrl('file:///Users/matthewflood/Downloads/Korean made easy for beginners 2nd.Ed._017.mp3')
        content = qtmm.QMediaContent(file)
        self.media_player.setMedia(content)
#        self.media_player.playbackStateChanged.connect(self.hear_end)
        self.media_player.stateChanged.connect(self.hear_end)
        self.media_player.play()

        # post setup
        self.show()

    def add_combobox(self):
        combobox = qtw.QComboBox(self)
        combobox.addItem('Lemon', 1)
        combobox.addItem('Apple', 1)
        combobox.addItem('Orange', 3)
        combobox.setCurrentIndex(2)
        return combobox


    def hear_end(self, arg):
        print(arg)
        

    def get_file(self):
        fn, _ = qtw.QFileDialog.getOpenFileUrl(
            self,
            "Select File",
            qtc.QDir.homePath(),
            "Audio files (*.wav *.mp3 *.flac);; All Files (*)")
        print(fn)
        if fn:
            return fn


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
   

