'''
    File: menu_widgets.py
    Date: 03/22/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: GUI Components.
'''

import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

class ContentPanel(QFrame):
    def __init__(self, title, color, parent=None, stretch_middle: bool = True):
        super().__init__(parent)
        self.title = title
        self.layout = QVBoxLayout(self)
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        if stretch_middle:
            self.layout.addStretch()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._base_color = color
        self._apply_color(color)

    def _apply_color(self, color: str, text_color: str = "#e0e0e0", border: str = "#444"):
        self.setStyleSheet(f"background-color: {color}; border: 1px solid {border}; color: {text_color};")
        self.label.setStyleSheet(f"font-weight: bold; font-size: 14px; border: none; color: {text_color};")

    def _is_dark(self, hex_color: str) -> bool:
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5

    def _adjust(self, hex_color: str, amount: float, darken: bool) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        if darken:
            r, g, b = max(0, int(r * (1 - amount))), max(0, int(g * (1 - amount))), max(0, int(b * (1 - amount)))
        else:
            r, g, b = min(255, int(r + 255 * amount)), min(255, int(g + 255 * amount)), min(255, int(b + 255 * amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    def set_color(self, hex_color: str, border: str = None) -> None:
        dark = self._is_dark(hex_color)
        text_color = "#e0e0e0" if dark else "#333333"
        panel_color = self._adjust(hex_color, 0.03, dark) if self._base_color == "#000000" else hex_color
        if border is None:
            border = "#ffffff" if dark else "#000000"
        self._apply_color(panel_color, text_color, border)

    #called when the user changes their config file.
    def update_title(self, file_path):
        
        display_text = os.path.basename(file_path)
        self.title = file_path
        self.label.setText(f"Active Config: {display_text}")

