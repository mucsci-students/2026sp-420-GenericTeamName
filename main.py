"""
main.py
=======
Entry point for the Scheduler Program GUI. 

This script initializes the QApplication and launches the refactored 
MainWindow using the PyQt6 framework.

:date: 02/24/2026
:author: Kyle Smith
:class: CMSC 420
"""

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    """
    Initializes and executes the main GUI application.
    """
    app = QApplication(sys.argv)
    
    # The refactored MainWindow handles its own manager 
    # initializations and theme applications upon instantiation.
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
