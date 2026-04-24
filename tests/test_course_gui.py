"""
test_course_gui.py
================
Pytests for ``course.course_gui``
Uses a module-scoped Qt application.
:date: 04/24/2026
:author: Shane del Villar
:class: CMSC 420
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QListWidget, QMessageBox

from course.course_gui import CourseConfigManager, CourseFormDialog


@pytest.fixture(scope="module")
def qt_app():
    """Single QApplication for widget tests; avoids pytest-qt ``qapp`` name."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# --- CourseFormDialog -----------------------------------------------------------------


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_preselected_from_course_no_course(apply_shell, qt_app):
    d = CourseFormDialog(None, course=None, pick_lists={})
    pre = d._preselected_from_course(None)
    assert pre == {
        "rooms": set(), "labs": set(), "faculty": set(), "conflicts": set()
    }
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_preselected_from_course_with_values(apply_shell, qt_app):
    c = {
        "room": ["A"], "lab": ["B"], "faculty": ["C"],
        "conflicts": ["D"],
    }
    d = CourseFormDialog(None, course=None, pick_lists={})
    pre = d._preselected_from_course(c)
    assert pre["rooms"] == {"A"} and pre["conflicts"] == {"D"}


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_populate_section_coerces_non_list(apply_shell, qt_app):
    d = CourseFormDialog(
        None,
        course=None,
        pick_lists={"rooms": ["R1", "R2"]},
    )
    d._populate_section("not-a-list", d._rooms_list, d._rooms_extra, "rooms")
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_populate_from_course_invalid_credits(apply_shell, qt_app):
    d = CourseFormDialog(
        None,
        course=None,
        pick_lists={"rooms": []},
    )
    d.populate_from_course({"course_id": "X", "credits": "bad", "room": []})
    assert d.credits_spin.value() == 0


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_dialog_ctor_populates_from_course(apply_shell, qt_app):
    c = {
        "course_id": "Y",
        "credits": 1,
        "room": [],
        "lab": [],
        "faculty": [],
        "conflicts": [],
    }
    d = CourseFormDialog(None, course=c, pick_lists={})
    assert d.course_id_edit.text() == "Y"
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_add_pref_section_no_catalog_no_listwidget(apply_shell, qt_app):
    d = CourseFormDialog(None, course=None, pick_lists={})
    box = d._add_pref_section("R", "rooms", "rooms")
    assert d._rooms_list is None
    assert d._rooms_extra is not None
    box.parent()
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_add_pref_section_conflicts_excludes_self(apply_shell, qt_app):
    d = CourseFormDialog(
        None,
        course=None,
        pick_lists={"course_ids": ["A", "B", "C"]},
        exclude_conflict_course_id="B",
    )
    d._add_pref_section("C", "course_ids", "conflicts")
    lw = d._conflicts_list
    assert lw is not None
    items = {lw.item(i).text() for i in range(lw.count())}
    assert "B" not in items
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_get_course_data_merge(apply_shell, qt_app):
    d = CourseFormDialog(
        None,
        course=None,
        pick_lists={"rooms": ["A"], "labs": [], "faculty": [], "course_ids": []},
    )
    d.course_id_edit.setText("CMSC 100")
    d.credits_spin.setValue(3)
    room_list: QListWidget = d._rooms_list
    for i in range(room_list.count()):
        it = room_list.item(i)
        if it.text() == "A":
            it.setCheckState(Qt.CheckState.Checked)
    d._rooms_extra.setText("ExtraRoom")
    data = d.get_course_data()
    assert data["course_id"] == "CMSC 100"
    assert data["credits"] == 3
    assert "A" in data["room"] and "ExtraRoom" in data["room"]
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
@patch("course.course_gui.QMessageBox.warning")
def test_on_accept_warns_if_no_course_id(warn, apply_shell, qt_app):
    d = CourseFormDialog(None, course=None, pick_lists={})
    d.course_id_edit.setText("   ")
    d.on_accept()
    warn.assert_called_once()
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
@patch("course.course_gui.CourseFormDialog.accept")
def test_on_accept_accepts(accept, apply_shell, qt_app):
    d = CourseFormDialog(None, course=None, pick_lists={})
    d.course_id_edit.setText("CMSC 1")
    d.on_accept()
    accept.assert_called_once()
    d.close()


@patch("course.course_gui.SchedulerStyles.apply_high_contrast_shell")
def test_populate_from_course_full(apply_shell, qt_app):
    d = CourseFormDialog(
        None,
        course=None,
        pick_lists={
            "rooms": ["A"],
            "labs": ["B"],
            "faculty": ["C"],
            "course_ids": ["D", "E"],
        },
    )
    d.populate_from_course(
        {
            "course_id": "X",
            "credits": 2,
            "room": ["A", "Z"],
            "lab": ["B"],
            "faculty": ["C"],
            "conflicts": ["D"],
        }
    )
    assert d.course_id_edit.text() == "X"
    assert d.credits_spin.value() == 2
    assert "Z" in d._rooms_extra.text()
    d.close()


# --- CourseConfigManager ----------------------------------------------------------------


def _config_mgr(courses, tmp_path):
    m = MagicMock()
    m.data = {"config": {"courses": courses}}
    m.filepath = str(tmp_path / "cfg.json")
    return m


def _viewer_mgr(pick):
    v = MagicMock()
    v._get_pick_lists = MagicMock(return_value=pick)
    return v


@patch("course.course_gui.CourseFormDialog")
def test_add_course_no_config_data(mock_dlg, tmp_path, qt_app):
    cfg = _config_mgr([], tmp_path)
    cfg.data = None
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    with patch("course.course_gui.QMessageBox.warning") as w:
        mgr.add_course_via_dialog(None)
    w.assert_called_once()
    mock_dlg.assert_not_called()


@patch("course.course_gui.CourseFormDialog")
def test_add_course_dialog_rejected(mock_dlg, tmp_path, qt_app):
    inst = mock_dlg.return_value
    inst.exec.return_value = QDialog.DialogCode.Rejected
    cfg = _config_mgr([], tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.add_course_via_dialog(None)
    cfg.save.assert_not_called()


@patch("course.course_gui.CourseFormDialog")
def test_add_course_success(mock_dlg, tmp_path, qt_app):
    inst = mock_dlg.return_value
    inst.exec.return_value = QDialog.DialogCode.Accepted
    inst.get_course_data.return_value = {
        "course_id": "NEW",
        "credits": 1,
        "room": [],
        "lab": [],
        "faculty": [],
        "conflicts": [],
    }
    courses: list = []
    cfg = _config_mgr(courses, tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({"r": [1]}))
    mgr.add_course_via_dialog(None)
    assert courses and courses[-1]["course_id"] == "NEW"
    cfg.save.assert_called_once_with(None)


@patch("course.course_gui.QInputDialog.getItem", return_value=(None, False))
def test_select_course_cancel(mock_item, tmp_path, qt_app):
    cfg = _config_mgr([{"course_id": "A", "credits": 1}], tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    assert mgr._select_course(None) == (None, None)


@patch("course.course_gui.QMessageBox.information")
def test_select_course_no_courses(mock_info, tmp_path, qt_app):
    cfg = _config_mgr([], tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    assert mgr._select_course(None) == (None, None)
    mock_info.assert_called_once()


@patch("course.course_gui.QInputDialog.getItem")
@patch("course.course_gui.CourseFormDialog")
def test_modify_cancel_at_dialog(mock_dlg, mock_get, tmp_path, qt_app):
    mock_get.return_value = (
        "CMSC 100 (3 cr)", True
    )
    c = {
        "course_id": "CMSC 100",
        "credits": 3,
        "room": [],
        "lab": [],
        "faculty": [],
        "conflicts": [],
    }
    courses = [c]
    cfg = _config_mgr(courses, tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    inst = mock_dlg.return_value
    inst.exec.return_value = QDialog.DialogCode.Rejected
    mgr.modify_course_via_dialog(None)
    cfg.save.assert_not_called()


@patch("course.course_gui.QInputDialog.getItem")
@patch("course.course_gui.CourseFormDialog")
def test_modify_success(mock_dlg, mock_get, tmp_path, qt_app):
    c = {
        "course_id": "CMSC 100",
        "credits": 3,
        "room": [],
        "lab": [],
        "faculty": [],
        "conflicts": [],
    }
    courses = [dict(c)]
    mock_get.return_value = ("CMSC 100 (3 cr)", True)
    cfg = _config_mgr(courses, tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    inst = mock_dlg.return_value
    inst.exec.return_value = QDialog.DialogCode.Accepted
    inst.get_course_data.return_value = {
        "course_id": "CMSC 200",
        "credits": 4,
        "room": [],
        "lab": [],
        "faculty": [],
        "conflicts": [],
    }
    mgr.modify_course_via_dialog(None)
    assert courses[0]["course_id"] == "CMSC 200"
    cfg.save.assert_called_once()


@patch(
    "course.course_gui.QMessageBox.question",
    return_value=QMessageBox.StandardButton.No,
)
@patch("course.course_gui.QInputDialog.getItem", return_value=("A (1 cr)", True))
def test_delete_course_aborted_by_user(mock_get, mock_q, tmp_path, qt_app):
    courses = [
        {
            "course_id": "A",
            "credits": 1,
            "room": [],
            "lab": [],
            "faculty": [],
            "conflicts": [],
        }
    ]
    cfg = _config_mgr(courses, tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.delete_course_via_dialog(None)
    assert len(courses) == 1
    cfg.save.assert_not_called()


@patch(
    "course.course_gui.QMessageBox.question",
    return_value=QMessageBox.StandardButton.Yes,
)
@patch("course.course_gui.QInputDialog.getItem", return_value=("A (1 cr)", True))
def test_delete_course_success(mock_get, mock_q, tmp_path, qt_app):
    courses = [
        {
            "course_id": "A",
            "credits": 1,
            "room": [],
            "lab": [],
            "faculty": [],
            "conflicts": [],
        }
    ]
    cfg = _config_mgr(courses, tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.delete_course_via_dialog(None)
    assert courses == []
    cfg.save.assert_called_once_with(None)


@patch("course.course_gui.QMessageBox.warning")
def test_modify_no_config(mock_warn, tmp_path, qt_app):
    cfg = _config_mgr([], tmp_path)
    cfg.data = None
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.modify_course_via_dialog(None)
    mock_warn.assert_called_once()


@patch("course.course_gui.QInputDialog.getItem", return_value=(None, False))
@patch("course.course_gui.CourseFormDialog")
def test_modify_stops_if_selection_cancelled(mock_dlg, mock_get, tmp_path, qt_app):
    c = {
        "course_id": "A",
        "credits": 1,
        "room": [],
        "lab": [],
        "faculty": [],
        "conflicts": [],
    }
    cfg = _config_mgr([c], tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.modify_course_via_dialog(None)
    mock_dlg.assert_not_called()


@patch("course.course_gui.QMessageBox.warning")
def test_delete_no_config(mock_warn, tmp_path, qt_app):
    cfg = _config_mgr([], tmp_path)
    cfg.data = None
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.delete_course_via_dialog(None)
    mock_warn.assert_called_once()


@patch("course.course_gui.QInputDialog.getItem", return_value=(None, False))
@patch("course.course_gui.QMessageBox.question")
def test_delete_stops_if_selection_cancelled(mock_q, mock_get, tmp_path, qt_app):
    courses = [
        {
            "course_id": "A",
            "credits": 1,
            "room": [],
            "lab": [],
            "faculty": [],
            "conflicts": [],
        }
    ]
    cfg = _config_mgr(courses, tmp_path)
    mgr = CourseConfigManager(cfg, _viewer_mgr({}))
    mgr.delete_course_via_dialog(None)
    mock_q.assert_not_called()
