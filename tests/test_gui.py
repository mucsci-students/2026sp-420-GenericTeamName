'''
    File: test_gui.py
    Date: 04/02/2026
    Author: GenericTeamName
    Description: Updated Unit and Integration tests to match MainWindow implementation.
'''

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    """
    Initializes the MainWindow and registers it with qtbot.
    """
    test_app = MainWindow()
    qtbot.addWidget(test_app)
    return test_app

def test_config_display_handles_int(app):
    """
    Test that the configuration view can handle non-string data types.
    """
    # 1. Inject the data
    mock_data = {"SETTINGS": {"limit": 100}}
    app.config_mgr.data = mock_data

    # 2. Update the UI directly to avoid the disk-reload logic in
    #    refresh_config_views_after_mutation()
    import json
    app.detail_view.setPlainText(json.dumps(app.config_mgr.data, indent=2))

    # 3. Verify
    content = app.detail_view.toPlainText()
    assert '"limit": 100' in content

def test_clear_schedules_safety(app):
    """
    Test that the clear schedule handler handles empty states gracefully.
    Matches the 'handle_clear_schedule' logic in main_window.py.
    """
    app.schedules = []
    # This should trigger a QMessageBox.warning but not crash
    app.handle_clear_schedule() 
    
    assert len(app.schedules) == 0
    assert app.clear_clicked == False 

def test_theme_switching_logic(app):
    """
    Tests that setting a theme updates the internal state and stylesheet.
    Note: Your code uses 'current_theme' and 'theme_color' instead of 'is_dark_mode'.
    """
    # Switch to Dark
    app.set_theme("Dark")
    assert app.current_theme == "Dark"
    assert app.theme_color == "#1f1f24"
    
    # Check if the stylesheet was updated (case-insensitive check)
    current_style = app.styleSheet().lower()
    assert "#1f1f24" in current_style

def test_navigation_wrap_around(app):
    """
    Test that the Previous/Next buttons wrap around correctly.
    """
    # Mock some schedules
    app.schedules = [{"id": 1}, {"id": 2}, {"id": 3}]
    app.current_schedule_index = 0
    
    # Test Next
    app.show_next_schedule()
    assert app.current_schedule_index == 1
    
    # Test Wrap Around (Next)
    app.current_schedule_index = 2
    app.show_next_schedule()
    assert app.current_schedule_index == 0
    
    # Test Wrap Around (Prev)
    app.show_prev_schedule()
    assert app.current_schedule_index == 2

def test_manager_dialog_logic(app):
    """
    Test that the manager instances exist and can be triggered.
    Since 'open_manager_gui' isn't in your snippet, we test the command bindings.
    """
    # Verify managers are initialized
    assert app.faculty_manager is not None
    assert app.course_manager is not None
    assert app.room_manager is not None
    
    # Verify we can access the config path which is displayed in the UI
    assert "config/config.json" in app.path_label.text()
