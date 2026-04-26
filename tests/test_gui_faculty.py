'''
    test_gui_faculty.py
    Author: Damion Crawford
    Date: 25 April 2026
    Class: CMSC 420
    Description: Pytests for faculty management
'''

from __future__ import annotations

# import json
import sys
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QListWidget, QMessageBox
from unittest.mock import MagicMock, patch

from faculty.faculty_gui import FacultyManager, FacultyFormDialog

@pytest.fixture(scope="module")
def qt_app():
    # Single application for tests, avoids qapp.
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

# FacultyFormDialog


@patch("faculty.faculty_gui.SchedulerStyles.apply_high_contrast_shell")
def test_checked_days(qtbot):
    dialog = FacultyFormDialog()
    qtbot.addWidget(dialog)

    # Manually check MON and WED
    for i in range(dialog._days_list.count()):
        item = dialog._days_list.item(i)
        if item.text() in {"MON", "WED"}:
            item.setCheckState(Qt.CheckState.Checked)
        else:
            item.setCheckState(Qt.CheckState.Unchecked)

    result = dialog._checked_days()

    assert result == ["MON", "WED"]



@patch("faculty.faculty_gui.SchedulerStyles.apply_high_contrast_shell")
def test_merge_weighted_invalid_weight(qtbot):
    dialog = FacultyFormDialog()
    qtbot.addWidget(dialog)

    dialog.course_weight_spin.setValue(7)
    dialog._course_extra.setText("CMSC 330:abc")

    result = dialog._merge_weighted(None, dialog._course_extra, dialog.course_weight_spin)

    assert result == {"CMSC 330": 7}


@patch("faculty.faculty_gui.SchedulerStyles.apply_high_contrast_shell")
def test_dialog_populates_from_faculty(apply_shell, qt_app):
    f = {
        "name": "Cain",
        "minimum_credits": 0,
        "maximum_credits": 4,
        "unique_course_limit": 3,
        "mandatory_days": ["MON", "TUE", "WED", "FRI"],
        "times": ["10:00-12:00", "14:00-16:00", "13:00-15:00", "10:00-12:00"],
    }
    form = FacultyFormDialog(None, faculty = f, pick_lists = {})
    assert form.name_edit.text() == "Cain"
    form.close()


@patch("faculty.faculty_gui.SchedulerStyles.apply_high_contrast_shell")
@patch("faculty.faculty_gui.QMessageBox.warning")
def test_on_accept_warns_if_missing_info(warn, apply_shell, qt_app):
    form = FacultyFormDialog(None, faculty = None, pick_lists = {})
    form.name_edit.setText("")
    form.on_accept()
    warn.assert_called_once()
    form.close()


@patch("faculty.faculty_gui.SchedulerStyles.apply_high_contrast_shell")
@patch("faculty.faculty_gui.QMessageBox.accept")
@pytest.fixture
def dialog(qtbot):
    dlg = FacultyFormDialog(parent=None, faculty=None, pick_lists={})
    qtbot.addWidget(dlg)
    return dlg


def on_accept_success(dialog, qtbot):
    # --- Fill required basic fields ---
    dialog.name_edit.setText("Hogg")
    dialog.min_credit_edit.setText("0")
    dialog.max_credit_edit.setText("6")
    dialog.courses_taught_edit.setText("2")

    # --- Select ONE day (minimum requirement) ---
    item = dialog._days_list.item(0)  # MON
    item.setCheckState(Qt.CheckState.Checked)

    # --- Provide matching time entry ---
    dialog._times_edit.setText("09:00-10:00")

    # --- Trigger validation ---
    dialog.on_accept()

    # --- Assert dialog accepted ---
    # assert dialog.result() == dialog.DialogCode.Accepted
    accept.assert_called_once()
    dialog.close()


@patch("faculty.faculty_gui.SchedulerStyles.apply_high_contrast_shell")
def test_populate_from_faculty_full(apply_shell, qt_app):
    form = FacultyFormDialog(None, faculty = None, pick_lists = {})
    form.populate_from_faculty(
        {
            "name": "Zoppetti",
            "minimum_credits": 0,
            "maximum_credits": 12,
            "unique_course_limit": 3,
            "mandatory_days": ["MON", "WED", "FRI"],
            "times": ["13:00-16:00", "13:00-15:30", "13:00-16:00"],
            "course_preferences": ["CMSC 362:8"],
            "room_preferences": ["Roddy 136:9"],
            "lab_preferences": ["Mac:9"],
        }
    )
    assert form.name_edit.text() == "Zoppetti"
    assert form.courses_taught_edit.text() == "3"
    form.close()

# Faculty Config Manager

def config_mgr(faculty, tmp_path):
    m = MagicMock()
    m.data = {"config": {"faculty": faculty}}
    m.filepath = str(tmp_path / "config.json")
    return m

def viewer_mgr(pick):
    v = MagicMock
    v.get_pick_lists = MagicMock(return_value = pick)
    return v


@patch("faculty.faculty_gui.FacultyFormDialog")
def test_add_faculty_no_config_data(mock_dlg, tmp_path, qt_app):
    cfg = config_mgr([], tmp_path)
    cfg.data = None
    mgr = FacultyManager(cfg, viewer_mgr({}))
    with patch("faculty.faculty_gui.QMessageBox.warning") as w:
        mgr.add_faculty_via_dialog(None)
    w.assert_called_once
    mock_dlg.assert_not_called()


#10 (passed)
@patch("faculty.faculty_gui.FacultyFormDialog")
def test_select_faculty_cancel(mock_item, tmp_path, qt_app):
    cfg = config_mgr([], tmp_path)
    mgr = FacultyManager(cfg, viewer_mgr({}))
    assert mgr.select_faculty(None) == (None, None)


#14 (passed)
@patch(
    "faculty.faculty_gui.QMessageBox.question",
    return_value=QMessageBox.StandardButton.No,
)
@patch("faculty.faculty_gui.QInputDialog.getItem", return_value=("Xie", True))
def test_delete_faculty_canceled_by_user(mock_get, mock_q, tmp_path, qt_app):
    faculty = [
        {
            "name": "Xie",
            "minimum_credits": 4,
            "maximum_credits": 12,
            "unique_course_limit": 3,
            "mandatory_days": ["MON", "TUES", "FRI"],
            "times": ["13:00-16:00", "14:00-15:30", "13:00-16:00"],
        }
    ]
    cfg = config_mgr(faculty, tmp_path)
    mgr = FacultyManager(cfg, viewer_mgr({}))
    mgr.delete_faculty_via_dialog(None)
    assert len(faculty) == 1
    cfg.save.assert_not_called()

#15 (passed)
@patch(
    "course.course_gui.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("course.course_gui.QInputDialog.getItem", return_value=("Xie", True))
def test_delete_faculty_success(mock_get, mock_q, tmp_path, qt_app):
    faculty = [
        {
            "name": "Xie",
            "minimum_credits": 4,
            "maximum_credits": 12,
            "unique_course_limit": 3,
            "mandatory_days": ["MON", "TUES", "FRI"],
            "times": ["13:00-16:00", "14:00-15:30", "13:00-16:00"],
        }
    ]
    cfg = config_mgr(faculty, tmp_path)
    mgr = FacultyManager(cfg, viewer_mgr({}))
    mgr.delete_faculty_via_dialog(None)
    assert faculty == []
    cfg.save.assert_called_once_with(None)

#16 (passed)
@patch("faculty.faculty_gui.QMessageBox.warning")
def test_modify_no_config(mock_warn, tmp_path, qt_app):
    cfg = config_mgr([], tmp_path)
    cfg.data = None
    mgr = FacultyManager(cfg, viewer_mgr({}))
    mgr.modify_faculty_via_dialog(None)
    mock_warn.assert_called_once

#17 (passed)
@patch("faculty.faculty_gui.QInputDialog.getItem", return_value = (None, False))
@patch("faculty.faculty_gui.FacultyFormDialog")
def test_modify_stops_if_selection_cancelled(mock_dlg, mock_get, tmp_path, qt_app):
    f = {
        "name": "Cain",
        "minimum_credits": 0,
        "maximum_credits": 12,
        "unique_course_limit": 3,
        "mandatory_days": ["MON", "WED", "FRI"],
        "times": ["10:00-12:00", "13:00-15:30", "10:00-12:00"],
    }
    cfg = config_mgr([f], tmp_path)
    mgr = FacultyManager(cfg, viewer_mgr({}))
    mgr.modify_faculty_via_dialog(None)
    mock_dlg.assert_not_called()

#18 (passed)
@patch("faculty.faculty_gui.QMessageBox.warning")
def test_delete_no_config(mock_warn, tmp_path, qt_app):
    cfg = config_mgr([], tmp_path)
    cfg.data = None
    mgr = FacultyManager(cfg, viewer_mgr({}))
    mgr.delete_faculty_via_dialog(None)
    mock_warn.assert_called_once()

#19 (passed)
@patch("faculty.faculty_gui.QInputDialog.getItem", return_value = (None, False))
@patch("faculty.faculty_gui.QMessageBox.question")
def test_delete_stops_if_selection_cancelled(mock_q, mock_get, tmp_path, qt_app):
    faculty = [
        {
            "name": "Xie",
            "minimum_credits": 4,
            "maximum_credits": 12,
            "unique_course_limit": 3,
            "mandatory_days": ["MON", "TUES", "FRI"],
            "times": ["13:00-16:00", "14:00-15:30", "13:00-16:00"],
        }
    ]
    cfg = config_mgr(faculty, tmp_path)
    mgr = FacultyManager(cfg, viewer_mgr({}))
    mgr.delete_faculty_via_dialog(None)
    mock_q.assert_not_called()