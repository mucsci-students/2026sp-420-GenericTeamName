'''
    File: test_generator.py
    Date: 4/26/2026
    Author: Tyler Strohl & Chayse Altland
    Class: CMSC 420
    Description: Pytests for Schedule Generator tasks.
'''
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QDialog

from generator.generator_gui import GenConfigManager


def _config_mgr(data=None):
    cfg = MagicMock()
    cfg.data = data or {
        "limit": 2,
        "optimizer_flags": [],
        "config": {},
        "time_slot_config": {},
    }
    return cfg


def _manager(data=None):
    cfg = _config_mgr(data)
    viewer = MagicMock()
    return GenConfigManager(cfg, viewer), cfg, viewer


@patch("generator.generator_gui.QMessageBox.warning")
def test_set_limit_no_config(mock_warning):
    mgr, cfg, _ = _manager()
    cfg.data = None

    mgr.set_limit(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("generator.generator_gui.QInputDialog.getText", return_value=("10", True))
def test_set_limit_success(mock_get_text):
    mgr, cfg, _ = _manager()

    mgr.set_limit(None)

    assert mgr.limit == 10
    assert cfg.data["limit"] == 10
    cfg.save.assert_called_once_with(None)


@patch("generator.generator_gui.QMessageBox.warning")
@patch("generator.generator_gui.QInputDialog.getText", return_value=("bad", True))
def test_set_limit_invalid_number(mock_get_text, mock_warning):
    mgr, cfg, _ = _manager()

    mgr.set_limit(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("generator.generator_gui.QInputDialog.getText", return_value=("", True))
def test_set_limit_empty_input(mock_get_text):
    mgr, cfg, _ = _manager()

    mgr.set_limit(None)

    assert cfg.data["limit"] == 2
    cfg.save.assert_not_called()


@patch("generator.generator_gui.QDialog.exec", return_value=QDialog.DialogCode.Accepted)
@patch("generator.generator_gui.QCheckBox.isChecked", return_value=True)
def test_set_optimize_all_true(mock_checked, mock_exec, qapp):
    mgr, cfg, _ = _manager()

    mgr.set_optimize(None)

    assert cfg.data["optimizer_flags"] == [
        "faculty_course",
        "faculty_room",
        "faculty_lab",
        "same_room",
        "same_lab",
        "pack_rooms",
    ]
    cfg.save.assert_called_once_with(None)


@patch("generator.generator_gui.QDialog.exec", return_value=QDialog.DialogCode.Rejected)
def test_set_optimize_cancelled(mock_exec, qapp):
    mgr, cfg, _ = _manager({
        "limit": 2,
        "optimizer_flags": ["faculty_course"],
        "config": {},
        "time_slot_config": {},
    })

    mgr.set_optimize(None)

    assert cfg.data["optimizer_flags"] == ["faculty_course"]
    cfg.save.assert_not_called()


@patch("generator.generator_gui.QMessageBox.critical")
def test_run_scheduler_import_error(mock_critical):
    mgr, cfg, _ = _manager()

    with patch.dict("sys.modules", {"scheduler": None}):
        mgr.run_scheduler(None)

    mock_critical.assert_called_once()