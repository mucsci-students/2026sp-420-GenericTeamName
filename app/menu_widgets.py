'''
    File: menu_widgets.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: GUI Components.
'''

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class ContentPanel(QFrame):
    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"background-color: {color}; border: 1px solid #bdc3c7;")
        
        layout = QVBoxLayout(self)
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        
        layout.addWidget(label)
        layout.addStretch()
        
        self.btn = QPushButton("Action")
        layout.addWidget(self.btn)
