<<<<<<< HEAD
def main():
    print("Hello from 2026sp-420-genericteamname!")


if __name__ == "__main__":
    main()
=======
'''
    File: main.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Entry point for the main GUI.
'''

import sys
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
>>>>>>> 520d930334f070793416c54c6bf4fd46882aa51c
