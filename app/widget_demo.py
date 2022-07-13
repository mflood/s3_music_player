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

        qtw.QMainWindow.__init__(self)

        widget = qtw.QWidget(self)
        widget.setToolTip("up dpown")
        widget.setWindowTitle("MY title")
        s = qtc.Qt.WindowMinimized
        s = qtc.Qt.WindowMaximized
        self.setWindowState(s)



if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())
   

