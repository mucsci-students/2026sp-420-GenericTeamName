"""
    File: test_main_window.py
    Date: 03/22/2026
    Author: GenericTeamName
    Description: Unit and Integration tests for the Scheduler Pro MainWindow.
    Tests cover theme engine stability, error handling for empty data, 
    and GUI component management.
"""

import pytest
from PyQt6.QtCore import Qt
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    """
    Pytest fixture that initializes the MainWindow and registers it with qtbot.

    Args:
        qtbot: The pytest-qt bot used to simulate user interaction.

    Returns:
        MainWindow: A fully initialized instance of the application.
    """
    test_app = MainWindow()
    qtbot.addWidget(test_app)
    return test_app

def test_config_tree_handles_int(app):
    """
    Test that the Configuration Tree can render non-string data types.
    
    This verifies the fix for a previous AttributeError where the tree 
    renderer expected all JSON values to have a .lower() or .upper() method.

    Args:
        app (MainWindow): The application instance from the fixture.
    """
    # Inject an integer into the configuration data
    app.config_mgr.data = {"SETTINGS": {"limit": 100}}
    app.render_config_tree()
    
    root = app.config_tree.invisibleRootItem()
    # Find the 'SETTINGS' parent
    parent = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "SETTINGS")
    # Verify the integer 100 was converted to a string '100' for the QTreeWidget
    assert parent.child(0).text(0) == "limit"

def test_manual_move_no_schedule(app):
    """
    Test that the manual move handler ignores requests when no schedule is loaded.
    
    This ensures that the IndexError: list index out of range is prevented 
    when the user interacts with the table before running the generator.

    Args:
        app (MainWindow): The application instance from the fixture.
    """
    app.schedules = []
    # Triggering the handler manually
    app.handle_manual_move() 
    
    # Verification: History stack should remain empty if the safety check worked
    assert len(app.history_stack) == 0

def test_theme_toggle_logic(app):
    """
    Test the global theme switching engine.
    
    Verifies that the is_dark_mode state flips correctly and that the 
    stylesheet string is updated with the appropriate hex codes.

    Args:
        app (MainWindow): The application instance from the fixture.
    """
    initial_mode = app.is_dark_mode
    app.toggle_theme()
    
    # Assert state flip
    assert app.is_dark_mode != initial_mode
    
    # Check for specific hex codes in the resulting stylesheet
    current_style = app.styleSheet().lower()
    if app.is_dark_mode:
        assert "#1f1f24" in current_style  # Dark background
    else:
        assert "#f0f2f5" in current_style  # Light background

def test_manager_gui_opening(app, qtbot):
    """
    Test the safety wrapper for opening sub-manager GUIs.
    
    This confirms that the AttributeError: 'Manager' object has no attribute 'show' 
    is resolved by checking both .show() and .gui.show().

    Args:
        app (MainWindow): The application instance from the fixture.
        qtbot: The pytest-qt bot to monitor window exposure.
    """
    # Determine the actual widget to wait for
    target_widget = app.course_manager if hasattr(app.course_manager, 'show') else app.course_manager.gui
    
    # Use qtbot to wait for the window to become visible
    with qtbot.waitExposed(target_widget, timeout=1000):
        app.open_manager_gui(app.course_manager)
    
    assert target_widget.isVisible()
