'''
    File: test_lab_gui.py
    Date: 04/25/2026
    Author: Chayse Altland
    Class: CMSC 420
    Description: pytests for lab.lab_gui.py
'''
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QMessageBox

from lab.lab_gui import LabConfigManager


def _config_mgr(labs):
    cfg = MagicMock()
    cfg.data = {"config": {"labs": labs}}
    return cfg


def test_get_labs_list():
    labs = ["Linux", "Mac"]
    mgr = LabConfigManager(_config_mgr(labs))
    assert mgr._get_labs_list() == labs


@patch("lab.lab_gui.QMessageBox.warning")
def test_add_lab_no_config(mock_warning):
    cfg = _config_mgr([])
    cfg.data = None
    mgr = LabConfigManager(cfg)

    mgr.add_lab_via_dialog(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QInputDialog.getText", return_value=("Linux", True))
def test_add_lab_success(mock_get_text):
    labs = []
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.add_lab_via_dialog(None)

    assert labs == ["Linux"]
    cfg.save.assert_called_once_with(None)


@patch("lab.lab_gui.QInputDialog.getText", return_value=("", True))
def test_add_lab_empty_text(mock_get_text):
    labs = []
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.add_lab_via_dialog(None)

    assert labs == []
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QInputDialog.getText", return_value=("Linux", False))
def test_add_lab_cancelled(mock_get_text):
    labs = []
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.add_lab_via_dialog(None)

    assert labs == []
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QMessageBox.information")
def test_select_lab_no_labs(mock_info):
    mgr = LabConfigManager(_config_mgr([]))

    assert mgr._select_lab(None) == (None, None)
    mock_info.assert_called_once()


@patch("lab.lab_gui.QInputDialog.getItem", return_value=("Mac", True))
def test_select_lab_success(mock_get_item):
    labs = ["Linux", "Mac"]
    mgr = LabConfigManager(_config_mgr(labs))

    assert mgr._select_lab(None) == (1, "Mac")


@patch("lab.lab_gui.QInputDialog.getItem", return_value=(None, False))
def test_select_lab_cancelled(mock_get_item):
    labs = ["Linux"]
    mgr = LabConfigManager(_config_mgr(labs))

    assert mgr._select_lab(None) == (None, None)


@patch("lab.lab_gui.QMessageBox.warning")
def test_modify_lab_no_config(mock_warning):
    cfg = _config_mgr([])
    cfg.data = None
    mgr = LabConfigManager(cfg)

    mgr.modify_lab_via_dialog(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QInputDialog.getItem", return_value=("Linux", True))
@patch("lab.lab_gui.QInputDialog.getText", return_value=("Mac", True))
def test_modify_lab_success(mock_get_text, mock_get_item):
    labs = ["Linux"]
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.modify_lab_via_dialog(None)

    assert labs == ["Mac"]
    cfg.save.assert_called_once_with(None)


@patch("lab.lab_gui.QInputDialog.getItem", return_value=(None, False))
@patch("lab.lab_gui.QInputDialog.getText")
def test_modify_lab_selection_cancelled(mock_get_text, mock_get_item):
    labs = ["Linux"]
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.modify_lab_via_dialog(None)

    assert labs == ["Linux"]
    mock_get_text.assert_not_called()
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QInputDialog.getItem", return_value=("Linux", True))
@patch("lab.lab_gui.QInputDialog.getText", return_value=("", True))
def test_modify_lab_empty_text(mock_get_text, mock_get_item):
    labs = ["Linux"]
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.modify_lab_via_dialog(None)

    assert labs == ["Linux"]
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QMessageBox.warning")
def test_delete_lab_no_config(mock_warning):
    cfg = _config_mgr([])
    cfg.data = None
    mgr = LabConfigManager(cfg)

    mgr.delete_lab_via_dialog(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QInputDialog.getItem", return_value=("Linux", True))
@patch("lab.lab_gui.QMessageBox.question", return_value=QMessageBox.StandardButton.No)
def test_delete_lab_aborted_by_user(mock_question, mock_get_item):
    labs = ["Linux"]
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.delete_lab_via_dialog(None)

    assert labs == ["Linux"]
    cfg.save.assert_not_called()


@patch("lab.lab_gui.QInputDialog.getItem", return_value=("Linux", True))
@patch("lab.lab_gui.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes)
def test_delete_lab_success(mock_question, mock_get_item):
    labs = ["Linux"]
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.delete_lab_via_dialog(None)

    assert labs == []
    cfg.save.assert_called_once_with(None)


@patch("lab.lab_gui.QInputDialog.getItem", return_value=(None, False))
@patch("lab.lab_gui.QMessageBox.question")
def test_delete_lab_selection_cancelled(mock_question, mock_get_item):
    labs = ["Linux"]
    cfg = _config_mgr(labs)
    mgr = LabConfigManager(cfg)

    mgr.delete_lab_via_dialog(None)

    assert labs == ["Linux"]
    mock_question.assert_not_called()
    cfg.save.assert_not_called()