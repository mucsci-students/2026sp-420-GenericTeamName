'''
    File: menu_widgets.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: GUI Components.
'''

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidgetAction
from PyQt6.QtCore import pyqtSignal

class MenuPanel(QWidget):
    """A single vertical column for the menu."""
    def __init__(self, title, options, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Header
        label = QLabel(f"<b>{title}</b>")
        self.layout.addWidget(label)
        
        # Action Buttons
        self.buttons = []
        for text in options:
            btn = QPushButton(text)
            btn.setFlat(True)  # Makes it look more like a menu item
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding: 8px; border: none; }
                QPushButton:hover { background-color: #e0e0e0; border-radius: 4px; }
            """)
            self.layout.addWidget(btn)
            self.buttons.append(btn)
            
        self.layout.addStretch()

class ThreePanelMenu(QWidgetAction):
    """A custom action that organizes three MenuPanels horizontally."""
    action_clicked = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.container = QWidget()
        self.layout = QHBoxLayout(self.container)
        
        # Define the panels
        self.panels = {
            "File": ["New Project", "Open", "Save All"],
            "Edit": ["Undo", "Redo", "Settings"],
            "Help": ["Docs", "Check Updates", "About"]
        }
        
        for title, options in self.panels.items():
            panel = MenuPanel(title, options)
            self.layout.addWidget(panel)
            
            # Connect buttons to signal
            for btn in panel.buttons:
                btn.clicked.connect(lambda checked, b=btn: self.on_button_click(b.text()))

        self.setDefaultWidget(self.container)

    def on_button_click(self, name):
        self.action_clicked.emit(name)
        # Close the parent menu after click
        if self.parent():
            self.parent().close()
