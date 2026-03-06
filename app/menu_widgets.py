'''
    File: menu_widgets.py
    Date: 02/25/2026
    Author: Kyle Smith & Tyler Strohl
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
        
        self.layout = QVBoxLayout(self)
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        
        self.layout.addWidget(label)
        self.layout.addStretch()