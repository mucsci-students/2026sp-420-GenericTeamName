'''
    File: main_window.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: The main window of the GUI.
'''

from PyQt6.QtWidgets import QMainWindow, QSplitter, QMenu
from PyQt6.QtCore import Qt
from .menu_widgets import ContentPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resizable 3-Panel Layout")
        self.resize(900, 600)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_panel = ContentPanel("Navigator", "#ecf0f1")
        self.mid_panel = ContentPanel("Editor", "#ffffff")
        self.right_panel = ContentPanel("Inspector", "#f4f7f6")

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([300, 300, 300])
        
        self.setCentralWidget(self.splitter)

        self.splitter.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.splitter.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Reset Layout").triggered.connect(self.reset_layout)
        menu.exec(self.splitter.mapToGlobal(position))

    def reset_layout(self):
        total_width = sum(self.splitter.sizes())
        third = total_width // 3
        self.splitter.setSizes([third, third, total_width - (2 * third)])
