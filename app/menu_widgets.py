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
        self.title = title
        self.layout = QVBoxLayout(self)
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.layout.addStretch()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._base_color = color
        self._apply_color(color)

    def _apply_color(self, color: str, text_color: str = "#e0e0e0", border: str = "#444"):
        self.setStyleSheet(f"background-color: {color}; border: 1px solid {border}; color: {text_color};")
        self.label.setStyleSheet(f"font-weight: bold; font-size: 14px; border: none; color: {text_color};")

    def set_theme(self, dark: bool) -> None:
        if dark:
            colors = {"#1a1a1a": ("#1a1a1a", "#e0e0e0", "#444"), "#000000": ("#000000", "#e0e0e0", "#444")}
        else:
            colors = {"#1a1a1a": ("#f5f5f5", "#333", "#bdc3c7"), "#000000": ("#ffffff", "#333", "#bdc3c7")}
        c, t, b = colors.get(self._base_color, colors["#1a1a1a"])
        self._apply_color(c, t, b)