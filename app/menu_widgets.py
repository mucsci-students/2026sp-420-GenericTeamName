"""
menu_widgets.py
===============
Custom widgets used for the layout of the Scheduler GUI.

This module defines the ContentPanel class, which provides a stylized
container for the different sections of the main window.

:file: app/menu_widgets.py
:author: Kyle Smith & Tyler Strohl
:date: 03/25/2026
:class: CMSC 420
"""

import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class ContentPanel(QFrame):
    """
    A stylized QFrame used for the main panels in the MainWindow.
    
    This class handles internal styling, title updates, and dynamic
    theme adjustments based on luminance.
    """

    def __init__(self, title, color, parent=None, stretch_middle: bool = True):
        """
        Initializes the panel with a title and a base color.
        """
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.layout.addStretch()

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._base_color = color
        self.update_theme_styles("Init", color)

    def set_color(self, hex_color, border_color=None):
        """
        Bridge method called by MainWindow to update the panel theme.
        
        This method satisfies the 'set_color' call from the MainWindow 
        while delegating the actual style logic to update_theme_styles.

        :param hex_color: The primary theme color hex string.
        :param border_color: Optional border color (calculated internally if None).
        """
        self.update_theme_styles("Update", hex_color)

    def update_theme_styles(self, name, hex_color):
        """
        Updates the stylesheet based on theme luminance and base color.

        :param name: A descriptor for the update event (e.g., 'Init' or 'Update').
        :param hex_color: The hex color string to apply/adjust.
        """
        dark = self._is_dark(hex_color)
        text_color = "#e0e0e0" if dark else "#333333"
        border = "#ffffff" if dark else "#000000"
        
        # Logic to adjust specific panels (like the Mid Panel) slightly 
        # differently than the theme background if the base was black.
        panel_color = (self._adjust(hex_color, 0.03, dark) 
                       if self._base_color == "#000000" 
                       else hex_color)
        
        self.setStyleSheet(
            f"background-color: {panel_color}; "
            f"border: 1px solid {border}; "
            f"color: {text_color};"
        )
        self.label.setStyleSheet(
            f"font-weight: bold; font-size: 14px; "
            f"border: none; color: {text_color};"
        )

    def update_title(self, label, file_path = None):
        """
        Updates the file_path label using the basename of current file_path.

        :param file_path: The full path to the active configuration file.
        """
        #Fall into here when clearing imported schedules
        if file_path == None:
            self.label.setText("NO FILE IMPORTED")
            return

        display_text = os.path.basename(file_path)
        #Change which schedule filepath is displayed
        if (isinstance(label, ContentPanel)):
            self.label.setText(f"Schedules Imported: {display_text}")
        else:
            label.setText(f"Active Config: {display_text}")

    def _is_dark(self, hex_color):
        """
        Calculates if a color is dark using the YIQ luminance formula.

        :param hex_color: Hex string of the color.
        :return: True if the color is considered dark.
        """
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        # Standard luminance formula
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.5

    def _adjust(self, hex_color, amount, darken):
        """
        Adjusts a hex color by a percentage amount.

        :param hex_color: Hex string of the color.
        :param amount: Float representing the percentage change (0.0 to 1.0).
        :param darken: Boolean; if True, darkens the color, otherwise lightens it.
        :return: A new hex color string.
        """
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        
        if darken:
            r, g, b = max(0, int(r*(1-amount))), max(0, int(g*(1-amount))), max(0, int(b*(1-amount)))
        else:
            r, g, b = min(255, int(r+255*amount)), min(255, int(g+255*amount)), min(255, int(b+255*amount))
            
        return f"#{r:02x}{g:02x}{b:02x}"
