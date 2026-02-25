'''
    File: main_window.py
    Date: 02/25/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: The main window of the GUI.
'''

from PyQt6.QtWidgets import QMainWindow, QSplitter, QMenu, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from .menu_widgets import ContentPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scheduler Program - GenericTeamName")
        self.resize(900, 600)

        #box-layout for buttons
        self.btn_layout = QHBoxLayout(self)
        #splitter for panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.faculty_btn = QPushButton("Faculty")
        self.course_btn = QPushButton("Course")
        self.room_btn = QPushButton("Room")
        self.lab_btn = QPushButton("Lab")

        self.left_panel = ContentPanel("Config Editor", "#ecf0f1")
        self.mid_panel = ContentPanel("Schedule Generator", "#ffffff")
        self.right_panel = ContentPanel("Schedule Viewer", "#f4f7f6")

        #above panels & buttons are displayed in widgets.
        self.btn_layout.addWidget(self.faculty_btn)
        self.btn_layout.addWidget(self.course_btn)
        self.btn_layout.addWidget(self.room_btn)
        self.btn_layout.addWidget(self.lab_btn)
        self.btn_layout.addStretch()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        #sizes in order of declarations above ^^
        self.splitter.setSizes([300, 300, 300])
        
        container = QWidget()
        master_layout = QVBoxLayout(container)
        master_layout.addLayout(self.btn_layout)
        master_layout.addWidget(self.splitter)
        self.setCentralWidget(container)

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
