'''
    File: test_gui.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Main GUI test suite.
'''

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    test_app = MainWindow()
    qtbot.addWidget(test_app)
    return test_app

def test_window_initial_state(app):
    assert "Right-click" in app.label.text()

def test_panel_content_loading(app):
    # We manually trigger the menu creation logic
    from app.menu_widgets import ThreePanelMenu
    panel_action = ThreePanelMenu(app)
    
    # Check if all 3 panels were created
    # 1 label + 3 buttons per panel = 12 widgets total + layout items
    buttons = panel_action.container.findChildren(QPushButton)
    assert len(buttons) == 9  # 3 buttons * 3 panels
    assert buttons[0].text() == "New Project"

def test_action_triggering(app, qtbot):
    # Simulate a menu click
    from app.menu_widgets import ThreePanelMenu
    panel_action = ThreePanelMenu(app)
    
    # Spy on the signal
    with qtbot.waitSignal(panel_action.action_clicked) as blocker:
        # Find the "Settings" button and click it
        settings_btn = [b for b in panel_action.container.findChildren(QPushButton) 
                       if b.text() == "Settings"][0]
        qtbot.mouseClick(settings_btn, Qt.MouseButton.LeftButton)
    
    assert blocker.args == ["Settings"]
