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
        self.setWindowTitle("Schedule Editor")
        self.resize(900, 600)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_panel = ContentPanel("Navigator", "#ecf0f1")
        self.mid_panel = ContentPanel("Editor", "#ffffff")
        self.right_panel = ContentPanel("Inspector", "#f4f7f6")

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setSizes([200, 500, 200])

        self.setCentralWidget(self.splitter)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        menu = QMenu(self)

        child = self.childAt(position)
        panel_name = "Global"
        if child:
            parent = child
            while parent:
                if isinstance(parent, ContentPanel):
                    panel_name = parent.findChild(QLabel).text()
                    break
                parent = parent.parent()

        menu.setTitle(f"Options for {panel_name}")
        menu.addAction(f"Refresh {panel_name}")
        menu.addSeparator()
        menu.addAction("Reset Layout").triggered.connect(self.reset_layout)

        menu.exec(self.mapToGlobal(position))

    def reset_layout(self):
        self.splitter.setSizes([300, 300, 300])
