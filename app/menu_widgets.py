"""
    File: menu_widgets.py
    Date: 03/22/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: GUI Container Components with Theme-Aware styling.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class ContentPanel(QFrame):
    def __init__(self, title, color, parent=None):
        super().__init__(parent)
        self.title = title
        self._base_color = color
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.update_theme(color)

    def update_theme(self, bg_color, is_dark=True):
        """Updates the panel style based on the global theme selection."""
        self._base_color = bg_color
        text_color = "#e0e0e0" if is_dark else "#222222"
        border_color = "#444444" if is_dark else "#bbbbbb"
        header_bg = "rgba(0, 0, 0, 0.2)" if is_dark else "rgba(0, 0, 0, 0.05)"

        self.setStyleSheet(f"""
            ContentPanel {{
                background-color: {bg_color}; 
                border: 1px solid {border_color}; 
                border-radius: 4px;
            }}
        """)
        self.label.setStyleSheet(f"""
            font-weight: bold; font-size: 13px; border: none; 
            color: {text_color}; padding: 5px;
            background-color: {header_bg};
            border-bottom: 1px solid {border_color};
        """)
