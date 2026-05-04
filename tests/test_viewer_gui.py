"""
test_viewer_gui.py
====================
Pytests for ``viewer.viewer_gui``.

:date: 04/26/2026
:author: Shane del Villar
:class: CMSC 420
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QMessageBox

from viewer.viewer_gui import ViewerManager


def _config_mgr():
    cm = MagicMock()
    cm.filepath = "/tmp/config.json"
    cm.data = {
        "config": {
            "rooms": ["R1", "r1", None],
            "labs": ["L1", None],
            "faculty": [{"name": "Prof A"}, "Prof B", None],
            "courses": [{"course_id": "C1"}, {"course_id": "C2"}],
        }
    }
    cm.get_schedule_grid_data.return_value = (
        ["Mon", "Tue"],
        ["08:00", "09:00"],
        [["A", ""], ["", "B"]],
        [(0, 0, 2, 1)],
    )
    cm.get_summary_text.return_value = "summary text"
    cm.import_file = ""
    return cm


def _parent():
    p = MagicMock()
    p.schedules = [[{"faculty": ["Prof A"], "room": "R1", "lab": "L1"}]]
    p.current_schedule_index = 0
    p.calendar_view = MagicMock()
    p.counter_label = MagicMock()
    p.detail_view = MagicMock()
    p.path_label = MagicMock()
    p.cfg_panel = MagicMock()
    return p


def test_get_pick_lists_and_exclude():
    vm = ViewerManager(_config_mgr())
    out = vm._get_pick_lists(exclude_course_id_for_conflicts="C1")
    _room_key = lambda x: (x.casefold(), x)
    assert sorted(out["rooms"], key=_room_key) == sorted(["R1", "r1"], key=_room_key)
    assert out["labs"] == ["L1"]
    assert out["faculty"] == ["Prof A", "Prof B"]
    assert out["course_ids"] == ["C2"]


def test_sync_detail_view_missing_widget_noop():
    vm = ViewerManager(_config_mgr())
    parent = SimpleNamespace()
    vm._sync_detail_view(parent)  # no raise


def test_sync_detail_view_success_and_fallback():
    vm = ViewerManager(_config_mgr())
    p = _parent()
    vm._sync_detail_view(p)
    p.detail_view.setPlainText.assert_called_once()

    vm.config_mgr.data = {"bad": set([1])}  # non-json-serializable
    vm._sync_detail_view(p)
    assert "(Unable to display configuration as JSON.)" in p.detail_view.setPlainText.call_args[0][0]


def test_update_path_label_text_with_and_without_filepath():
    cm = _config_mgr()
    vm = ViewerManager(cm)
    p = _parent()
    vm._update_path_label_text(p)
    p.path_label.setText.assert_called_with("Config: config.json")

    cm.filepath = ""
    vm._update_path_label_text(p)
    p.path_label.setText.assert_called_with("Config: (unsaved or unknown path)")


def test_show_next_prev_schedule_wrap():
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = [1, 2]
    p.current_schedule_index = 0
    vm.show_next_schedule(p)
    assert p.current_schedule_index == 1
    vm.show_next_schedule(p)
    assert p.current_schedule_index == 0
    vm.show_prev_schedule(p)
    assert p.current_schedule_index == 1


@patch("viewer.viewer_gui.QMessageBox.warning")
def test_update_schedule_display_no_schedules_warning(mock_warn):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = []
    vm.clear_clicked = False
    vm.update_schedule_display(p)
    p.calendar_view.setRowCount.assert_called_with(0)
    mock_warn.assert_called_once()


@patch("viewer.viewer_gui.QMessageBox.warning")
def test_update_schedule_display_no_schedules_after_clear_no_warning(mock_warn):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = []
    vm.clear_clicked = True
    vm.update_schedule_display(p)
    mock_warn.assert_not_called()


@patch("viewer.viewer_gui.QInputDialog.getItem", return_value=("Prof A", True))
def test_update_schedule_display_filtered_from_schedule_values(_get_item):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = [[{"faculty": ["Prof A"], "room": "R1", "lab": ["L1"]}]]
    vm.update_schedule_display(p, "faculty")
    p.calendar_view.setRowCount.assert_called_with(2)
    p.calendar_view.setColumnCount.assert_called_with(2)
    assert p.calendar_view.setItem.call_count == 4


@patch("viewer.viewer_gui.QMessageBox.information")
def test_update_schedule_display_filter_no_options_falls_back_all(mock_info):
    cm = _config_mgr()
    cm.data = {"config": {"faculty": [], "rooms": [], "labs": [], "courses": []}}
    vm = ViewerManager(cm)
    p = _parent()
    p.schedules = [[{"x": "y"}]]
    vm.update_schedule_display(p, "faculty")
    mock_info.assert_called_once()
    p.calendar_view.setRowCount.assert_called()


@patch("viewer.viewer_gui.QInputDialog.getItem", return_value=("", False))
def test_update_schedule_display_filter_cancel_returns_early(_get_item):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = [[{"faculty": ["Prof A"]}]]
    vm.update_schedule_display(p, "faculty")
    p.calendar_view.setRowCount.assert_not_called()


def test_show_shortcuts_cheat_sheet_exec_called():
    vm = ViewerManager(_config_mgr())
    p = _parent()
    with patch("viewer.viewer_gui.QMessageBox") as MB:
        inst = MB.return_value
        vm._show_shortcuts_cheat_sheet(p)
        inst.exec.assert_called_once()


@patch("viewer.viewer_gui.QFileDialog.getSaveFileName", return_value=("/tmp/new.json", "json"))
def test_save_as_with_path(_dlg):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    vm.save_as(p)
    assert vm.config_mgr.filepath == "/tmp/new.json"
    vm.config_mgr.save.assert_called_once_with(p)


@patch("viewer.viewer_gui.QFileDialog.getSaveFileName", return_value=("", "json"))
def test_save_as_cancel(_dlg):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    vm.save_as(p)
    vm.config_mgr.save.assert_not_called()


@patch("viewer.viewer_gui.QMessageBox.information")
@patch("viewer.viewer_gui.QFileDialog.getOpenFileName", return_value=("/tmp/in.json", "json"))
def test_handle_change_path_success(_open, info):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    vm.handle_change_path(p)
    assert vm.config_mgr.filepath == "/tmp/in.json"
    vm.config_mgr.load.assert_called_once_with(p)
    info.assert_called_once()


@patch("viewer.viewer_gui.QMessageBox.warning")
@patch("viewer.viewer_gui.QFileDialog.getOpenFileName", return_value=("/tmp/in.json", "json"))
def test_handle_change_path_load_warning(_open, warn):
    vm = ViewerManager(_config_mgr())
    vm.config_mgr.load.side_effect = RuntimeError("bad")
    vm.handle_change_path(_parent())
    warn.assert_called_once()


@patch("viewer.viewer_gui.QFileDialog.getOpenFileName", return_value=("", "json"))
def test_handle_change_path_cancel(_open):
    vm = ViewerManager(_config_mgr())
    vm.handle_change_path(_parent())
    vm.config_mgr.load.assert_not_called()


@patch("viewer.viewer_gui.QMessageBox.information")
def test_handle_import_schedule_success(info):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    vm.config_mgr.import_file = "imported.json"
    vm.config_mgr.import_schedule_from_json.return_value = [[{"x": 1}], [{"x": 2}]]
    with patch.object(vm, "update_schedule_display") as upd:
        vm.handle_import_schedule(p)
    assert len(p.schedules) == 2
    assert p.current_schedule_index == 0
    p.cfg_panel.update_title.assert_called()
    upd.assert_called_once()
    info.assert_called_once()


@patch("viewer.viewer_gui._logger")
@patch("viewer.viewer_gui.QMessageBox.information", side_effect=Exception("x"))
def test_handle_import_schedule_info_error(_info, mock_logger):
    """If the success dialog fails, import still completed; failure is logged."""
    vm = ViewerManager(_config_mgr())
    p = _parent()
    vm.config_mgr.import_file = "imported.json"
    vm.config_mgr.import_schedule_from_json.return_value = [[{"x": 1}]]
    with patch.object(vm, "update_schedule_display"):
        vm.handle_import_schedule(p)
    mock_logger.exception.assert_called_once()


def test_handle_import_schedule_none():
    vm = ViewerManager(_config_mgr())
    vm.config_mgr.import_schedule_from_json.return_value = None
    vm.handle_import_schedule(_parent())


@patch("viewer.viewer_gui.QMessageBox.warning")
def test_handle_export_schedule_no_schedules(mock_warn):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = []
    vm.handle_export_schedule(p)
    mock_warn.assert_called_once()


@patch("viewer.viewer_gui.QInputDialog.getItem", return_value=("", False))
def test_handle_export_schedule_cancel(_get):
    vm = ViewerManager(_config_mgr())
    vm.handle_export_schedule(_parent())
    vm.config_mgr.export_schedule_to_json.assert_not_called()


@pytest.mark.parametrize(
    "choice, attr, args",
    [
        ("Full schedules (JSON)", "export_schedule_to_json", 2),
        ("Full schedules (PDF)", "export_schedule_to_pdf", 2),
        ("By room/lab postings (PDF printable)", "export_grouped_printable", 3),
        ("By faculty postings (PDF printable)", "export_grouped_printable", 3),
    ],
)
def test_handle_export_schedule_dispatch(choice, attr, args):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    with patch("viewer.viewer_gui.QInputDialog.getItem", return_value=(choice, True)):
        vm.handle_export_schedule(p)
    method = getattr(vm.config_mgr, attr)
    assert method.called
    assert len(method.call_args[0]) == args


@patch("viewer.viewer_gui.QMessageBox.warning")
def test_handle_clear_schedule_no_data(mock_warn):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = []
    vm.handle_clear_schedule(p)
    mock_warn.assert_called_once()


@patch("viewer.viewer_gui.QMessageBox.information")
def test_handle_clear_schedule_success(info):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = [[{"a": 1}]]
    p.current_schedule_index = 0
    with patch.object(vm, "update_schedule_display") as upd:
        vm.handle_clear_schedule(p)
    assert p.schedules == []
    assert vm.clear_clicked is True
    p.cfg_panel.update_title.assert_called_once()
    upd.assert_called_once()
    info.assert_called_once()


@patch("viewer.viewer_gui.QMessageBox.critical")
def test_handle_clear_schedule_exception(critical):
    vm = ViewerManager(_config_mgr())
    p = _parent()
    p.schedules = [[{"a": 1}]]
    p.current_schedule_index = 0
    with patch.object(vm, "update_schedule_display", side_effect=RuntimeError("x")):
        vm.handle_clear_schedule(p)
    critical.assert_called_once()


def test_handle_view_summary():
    vm = ViewerManager(_config_mgr())
    with patch("viewer.viewer_gui.QMessageBox") as MB:
        inst = MB.return_value
        vm.handle_view_summary(_parent())
        inst.setText.assert_called_with("summary text")
        inst.exec.assert_called_once()
