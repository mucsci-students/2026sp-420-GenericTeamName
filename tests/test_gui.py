'''
    File: test_gui.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Main GUI test suite.
'''

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window

def test_splitter_exists(app):
    """Verify central widget is a splitter with 3 widgets."""
    assert isinstance(app.centralWidget(), QSplitter)
    assert app.centralWidget().count() == 3

def test_resize_logic(app):
    """Verify the reset_layout function updates sizes."""
    app.splitter.setSizes([100, 100, 700])
    app.reset_layout()
    assert app.splitter.sizes() == [300, 300, 300]

def test_context_menu_detection(app, qtbot):
    """Verify right-click works on the middle panel."""
    with qtbot.waitSignal(app.customContextMenuRequested):
        target = app.mid_panel.rect().center()
        global_pos = app.mid_panel.mapTo(app, target)
        qtbot.mouseClick(app, Qt.MouseButton.RightButton, pos=global_pos)
