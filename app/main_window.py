'''
    File: main_window.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: The main window of the GUI.
'''

from PyQt6.QtWidgets import QMainWindow, QMenu, QLabel
from PyQt6.QtCore import Qt
from .menu_widgets import ThreePanelMenu
from .actions import handle_action

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt Modular Context Menu")
        self.resize(600, 400)
        
        self.label = QLabel("Right-click anywhere to see the 3-panel menu")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.label)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        menu = QMenu(self)
        
        # Inject the modular 3-panel widget
        panel_action = ThreePanelMenu(menu)
        panel_action.action_clicked.connect(self.process_menu_selection)
        menu.addAction(panel_action)
        
        menu.exec(self.mapToGlobal(position))

    def process_menu_selection(self, text):
        result = handle_action(text)
        self.label.setText(f"Last Action: {result}")
