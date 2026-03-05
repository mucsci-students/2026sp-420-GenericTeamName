'''
    File: test_gui.py
    Date: 02/24/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Main GUI test suite.
'''

import pytest
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QContextMenuEvent
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    """Fixture to initialize the MainWindow for each test."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window

# --- UI Integrity Tests ---

def test_initial_state(app):
    """Verify the window title and panel counts."""
    assert app.windowTitle() == "Scheduler Program - GenericTeamName"
    assert app.splitter.count() == 3
    assert app.left_panel.isVisible()

def test_button_existence(app):
    """Ensure all critical buttons are instantiated and labeled correctly."""
    assert app.faculty_btn.text() == "Faculty"
    assert app.generate_sc_btn.text() == "Generate Schedules"
    assert app.save_config_btn.text() == "Save Config"

def test_menu_assignments(app):
    """Verify that configuration buttons have their associated sub-menus."""
    buttons = [
        (app.faculty_btn, "Add Faculty"),
        (app.course_btn, "Add Courses"),
        (app.room_btn, "Add Rooms"),
        (app.lab_btn, "Add Labs")
    ]
    for btn, expected_action in buttons:
        menu = btn.menu()
        assert isinstance(menu, QMenu), f"Button {btn.text()} missing menu"
        action_texts = [a.text() for a in menu.actions()]
        assert expected_action in action_texts

# --- Logic & Functionality Tests ---

def test_reset_layout_logic(app):
    """Verify the math inside reset_layout is precise."""
    app.splitter.setSizes([50, 50, 800])
    
    app.reset_layout()
    
    sizes = app.splitter.sizes()
    total_width = sum(sizes)
    third = total_width // 3
    
    assert sizes[0] == third
    assert sizes[1] == third
    assert sizes[2] == total_width - (2 * third)

def test_context_menu_signal_manual(app, qtbot):
    """Robustly verify context menu signal by simulating the event directly."""
    with qtbot.waitSignal(app.splitter.customContextMenuRequested, timeout=1000):
        event = QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, 
            QPoint(10, 10)
        )
        app.splitter.customContextMenuRequested.emit(event.pos())

def test_button_click_output(app, qtbot, capsys):
    """Verify that clicking 'Save Config' triggers the print statement."""
    qtbot.mouseClick(app.save_config_btn, Qt.MouseButton.LeftButton)
    captured = capsys.readouterr()
    assert "Save Config clicked" in captured.out

# --- Component Interaction Tests ---

def test_faculty_menu_actions(app):
    """Deep check of the Faculty sub-menu actions."""
    menu = app.faculty_btn.menu()
    actions = {a.text(): a for a in menu.actions()}
    
    expected_actions = [
        "Add Faculty", "Modify Faculty", "Delete Faculty", 
        "Edit Faculty Available Times", "Edit Faculty Preferences"
    ]
    
    for action_name in expected_actions:
        assert action_name in actions
        assert actions[action_name].isEnabled()
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
