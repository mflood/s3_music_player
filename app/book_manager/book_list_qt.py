"""
    conda activate mypython3
"""
import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtGui as qtg
from PyQt5 import QtCore as qtc
from PyQt5 import QtSql as qts
from PyQt5 import QtMultimedia as qtmm
from myboto import S3Client



class BookForm(qtw.QWidget):

   def __init__(self, books):
    super().__init__()
    self.setLayout(qtw.QFormLayout())

    self.coffee_brand = qtw.QLineEdit()
    self.layout().addRow('Title: ', self.coffee_brand)

    self.coffee_name = qtw.QLineEdit()
    self.layout().addRow('Name: ', self.coffee_name)

    self.roast = qtw.QComboBox()
    self.roast.addItems(books)
    self.layout().addRow('Roast: ', self.roast)

    self.reviews = qtw.QTableWidget(columnCount=3)
    self.reviews.horizontalHeader().setSectionResizeMode(2, qtw.QHeaderView.Stretch)
    self.layout().addRow(self.reviews)



def make_sqlite_connection(filename: str):
    db = qts.QSqlDatabase.addDatabase('QSQLITE')
    db.setDatabaseName(filename)
    if not db.open():
        last_error = db.lastError().text()
        qtw.QMessageBox.critical(None, 'DB Connect Failed', last_error)

    print(type(db))
        




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

    db = make_sqlite_connection(filename="book.db")

    mw = MainWindow()
    mw.show()

    bw = BookForm(books=['heavy', 'loose'])
    bw.show()

    help(qtw.QMessageBox.critical)
    qtw.QMessageBox.critical(None, 'owo', 'two')
    sys.exit(app.exec())
   

