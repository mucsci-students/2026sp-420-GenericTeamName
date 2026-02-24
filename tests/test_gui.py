'''
    File: test_gui.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Main GUI test suite.
'''

import pytest
from PyQt6.QtCore import Qt
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window

def test_resize_logic(app):
    """Verify the reset_layout function makes panels roughly equal."""
    app.splitter.setSizes([50, 50, 800])
    app.reset_layout()
    
    sizes = app.splitter.sizes()
    assert abs(sizes[0] - sizes[1]) <= 2
    assert abs(sizes[1] - sizes[2]) <= 2

def test_context_menu_detection(app, qtbot):
    """Verify right-click works on the splitter/panels."""
    with qtbot.waitSignal(app.splitter.customContextMenuRequested, timeout=2000):
        qtbot.mouseClick(
            app.mid_panel, 
            Qt.MouseButton.RightButton, 
            pos=app.mid_panel.rect().center()
        )
