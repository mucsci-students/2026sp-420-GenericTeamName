'''
    Author: Damion Crawford & Kyle Smith
    Date: 4/26/2026
    Class: CMSC 420
    Description: Pytests for faculty management
'''

from __future__ import annotations
import pytest
import gc
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox, QLabel
from PyQt6.QtCore import Qt

# Adjust these imports to match your 'faculty' folder structure
import faculty.faculty_gui as faculty_gui
from faculty.faculty_gui import FacultyFormDialog, FacultyManager

# --- Fixtures ---

@pytest.fixture(scope="session")
def qapp():
    """Manual QApplication management to avoid runner conflicts."""
    app = QApplication.instance()
    if not app:
        import sys
        app = QApplication(sys.argv)
    return app

@pytest.fixture
def mock_config():
    """Standard mock for the config manager."""
    mgr = MagicMock()
    mgr.data = {
        "config": {
            "faculty": [
                {
                    "name": "Dr. Smith", 
                    "maximum_credits": 12, 
                    "minimum_credits": 3,
                    "unique_course_limit": 2,
                    "times": {"MON": ["09:00-17:00"]},
                    "mandatory_days": ["MON"]
                }
            ]
        }
    }
    return mgr

@pytest.fixture
def mock_viewer():
    """Mock for AI Viewer manager providing pick lists."""
    mgr = MagicMock()
    mgr._get_pick_lists.return_value = {
        "course_ids": ["CMSC101", "CMSC102"],
        "rooms": ["CSI1102"],
        "labs": ["LAB1"]
    }
    return mgr

@pytest.fixture
def faculty_dialog_factory(qapp):
    """Factory to create dialogs with guaranteed manual cleanup."""
    dialogs = []

    def _make(faculty=None, pick_lists=None):
        # Patching show to keep tests headless
        with patch.object(FacultyFormDialog, 'show', return_value=None):
            dialog = FacultyFormDialog(None, faculty=faculty, pick_lists=pick_lists)
            dialogs.append(dialog)
            return dialog

    yield _make

    # Hard cleanup to prevent segfaults on teardown
    for d in dialogs:
        d.hide()
        d.setParent(None)
        d.deleteLater()
    
    dialogs.clear()
    qapp.processEvents()
    gc.collect()

# --- FacultyFormDialog Logic Tests ---

def test_dialog_initialization_empty(faculty_dialog_factory):
    dialog = faculty_dialog_factory()
    assert dialog.name_edit.text() == ""
    assert dialog.min_credit_edit.text() == ""

def test_populate_from_faculty(faculty_dialog_factory):
    data = {
        "name": "Prof. Oak",
        "minimum_credits": 3,
        "maximum_credits": 9,
        "unique_course_limit": 2,
        "times": {"MON": ["08:00-12:00"]},
        "course_preferences": {"CMSC101": 5},
    }
    dialog = faculty_dialog_factory(faculty=data)
    assert dialog.name_edit.text() == "Prof. Oak"
    assert "08:00-12:00" in dialog._times_edit.text()

def test_get_faculty_data_merging(faculty_dialog_factory):
    pick_lists = {"course_ids": ["CMSC101"]}
    dialog = faculty_dialog_factory(pick_lists=pick_lists)
    
    dialog.name_edit.setText("Test Faculty")
    dialog.min_credit_edit.setText("3")
    dialog.max_credit_edit.setText("10")
    dialog.courses_taught_edit.setText("2")
    dialog._times_edit.setText("09:00-10:00")
    
    # Tick Monday
    dialog._days_list.item(0).setCheckState(Qt.CheckState.Checked)
    
    # Add an extra manual pref
    dialog._course_extra.setText("CMSC999:10")
    
    data = dialog.get_faculty_data()
    assert data["name"] == "Test Faculty"
    assert data["course_preferences"]["CMSC999"] == 10
    assert "MON" in data["mandatory_days"]

def test_on_accept_validation_fails(faculty_dialog_factory):
    dialog = faculty_dialog_factory()
    # No data filled
    with patch.object(QMessageBox, 'warning') as mock_warn:
        dialog.on_accept()
        mock_warn.assert_called_once()
        assert dialog.result() != QDialog.DialogCode.Accepted

def test_merge_weighted_value_error_fallback(faculty_dialog_factory):
    dialog = faculty_dialog_factory()
    dialog.course_weight_spin.setValue(5)
    dialog._course_extra.setText("MALFORMED:abc")
    
    # Passing None for checklist, testing the extra_input branch
    result = dialog._merge_weighted(None, dialog._course_extra, dialog.course_weight_spin)
    assert result["MALFORMED"] == 5

# --- FacultyManager Integration Tests ---

def test_manager_get_list(mock_config, mock_viewer):
    manager = FacultyManager(mock_config, mock_viewer)
    lst = manager._get_faculty_list()
    assert len(lst) == 1
    assert lst[0]["name"] == "Dr. Smith"

def test_add_faculty_success(mock_config, mock_viewer, qapp):
    manager = FacultyManager(mock_config, mock_viewer)
    parent = MagicMock()
    
    # Patching via the imported module object
    with patch.object(faculty_gui, "FacultyFormDialog") as MockDialog:
        mock_instance = MockDialog.return_value
        mock_instance.exec.return_value = QDialog.DialogCode.Accepted
        mock_instance.get_faculty_data.return_value = {"name": "New Faculty"}
        
        manager.add_faculty_via_dialog(parent)
        
        faculty_list = mock_config.data["config"]["faculty"]
        assert any(f["name"] == "New Faculty" for f in faculty_list)
        mock_config.save.assert_called_once()

def test_modify_faculty_success(mock_config, mock_viewer, qapp):
    manager = FacultyManager(mock_config, mock_viewer)
    parent = MagicMock()
    
    with patch.object(manager, 'select_faculty', return_value=(0, "Dr. Smith")):
        with patch.object(faculty_gui, "FacultyFormDialog") as MockDialog:
            mock_instance = MockDialog.return_value
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.get_faculty_data.return_value = {"name": "Updated Name"}
            
            manager.modify_faculty_via_dialog(parent)
            
            assert mock_config.data["config"]["faculty"][0]["name"] == "Updated Name"
            mock_config.save.assert_called_once()

def test_delete_faculty_confirmed(mock_config, mock_viewer):
    manager = FacultyManager(mock_config, mock_viewer)
    parent = MagicMock()
    
    with patch.object(manager, 'select_faculty', return_value=(0, "Dr. Smith")):
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            manager.delete_faculty_via_dialog(parent)
            assert len(mock_config.data["config"]["faculty"]) == 0
            mock_config.save.assert_called_once()

def test_select_faculty_no_data(mock_config, mock_viewer):
    mock_config.data["config"]["faculty"] = []
    manager = FacultyManager(mock_config, mock_viewer)
    
    with patch.object(QMessageBox, 'information') as mock_info:
        idx, name = manager.select_faculty(None)
        assert idx is None
        mock_info.assert_called_once()
