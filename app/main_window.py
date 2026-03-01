import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton

class SecondWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Second Window")
        self.setGeometry(200, 200, 300, 200)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 400, 300)

        button = QPushButton("Open New Window", self)
        button.clicked.connect(self.open_window)

        self.second_window = None  # important!

    def open_window(self):
        self.second_window = SecondWindow()
        self.second_window.show()


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())