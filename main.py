<<<<<<< HEAD


import scheduler



def main():
    print("Hello from 2026sp-420-genericteamname!")
=======
'''
    File: main.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Entry point for the main GUI.
'''
>>>>>>> origin/develop

import sys
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
