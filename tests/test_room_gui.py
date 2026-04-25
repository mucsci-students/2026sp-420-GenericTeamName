'''
    File: test_room_gui.py
    Date: 04/25/2026
    Author: Chayse Altland
    Class: CMSC 420
    Description: pytests for room.room_gui.py
'''
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QMessageBox

from room.room_gui import RoomConfigManager


def _config_mgr(rooms):
    cfg = MagicMock()
    cfg.data = {"config": {"rooms": rooms}}
    return cfg


def test_get_rooms_list():
    rooms = ["Roddy 140", "Roddy 147"]
    mgr = RoomConfigManager(_config_mgr(rooms))
    assert mgr._get_rooms_list() == rooms


@patch("room.room_gui.QMessageBox.warning")
def test_add_room_no_config(mock_warning):
    cfg = _config_mgr([])
    cfg.data = None
    mgr = RoomConfigManager(cfg)

    mgr.add_room_via_dialog(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("room.room_gui.QInputDialog.getText", return_value=("Roddy 140", True))
def test_add_room_success(mock_get_text):
    rooms = []
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.add_room_via_dialog(None)

    assert rooms == ["Roddy 140"]
    cfg.save.assert_called_once_with(None)


@patch("room.room_gui.QInputDialog.getText", return_value=("", True))
def test_add_room_empty_text(mock_get_text):
    rooms = []
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.add_room_via_dialog(None)

    assert rooms == []
    cfg.save.assert_not_called()


@patch("room.room_gui.QInputDialog.getText", return_value=("Roddy 140", False))
def test_add_room_cancelled(mock_get_text):
    rooms = []
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.add_room_via_dialog(None)

    assert rooms == []
    cfg.save.assert_not_called()


@patch("room.room_gui.QMessageBox.information")
def test_select_room_no_rooms(mock_info):
    mgr = RoomConfigManager(_config_mgr([]))

    assert mgr._select_room(None) == (None, None)
    mock_info.assert_called_once()


@patch("room.room_gui.QInputDialog.getItem", return_value=("Roddy 147", True))
def test_select_room_success(mock_get_item):
    rooms = ["Roddy 140", "Roddy 147"]
    mgr = RoomConfigManager(_config_mgr(rooms))

    assert mgr._select_room(None) == (1, "Roddy 147")


@patch("room.room_gui.QInputDialog.getItem", return_value=(None, False))
def test_select_room_cancelled(mock_get_item):
    rooms = ["Roddy 140"]
    mgr = RoomConfigManager(_config_mgr(rooms))

    assert mgr._select_room(None) == (None, None)


@patch("room.room_gui.QMessageBox.warning")
def test_modify_room_no_config(mock_warning):
    cfg = _config_mgr([])
    cfg.data = None
    mgr = RoomConfigManager(cfg)

    mgr.modify_room_via_dialog(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("room.room_gui.QInputDialog.getItem", return_value=("Roddy 140", True))
@patch("room.room_gui.QInputDialog.getText", return_value=("Roddy 136", True))
def test_modify_room_success(mock_get_text, mock_get_item):
    rooms = ["Roddy 140"]
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.modify_room_via_dialog(None)

    assert rooms == ["Roddy 136"]
    cfg.save.assert_called_once_with(None)


@patch("room.room_gui.QInputDialog.getItem", return_value=(None, False))
@patch("room.room_gui.QInputDialog.getText")
def test_modify_room_selection_cancelled(mock_get_text, mock_get_item):
    rooms = ["Roddy 140"]
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.modify_room_via_dialog(None)

    assert rooms == ["Roddy 140"]
    mock_get_text.assert_not_called()
    cfg.save.assert_not_called()


@patch("room.room_gui.QInputDialog.getItem", return_value=("Roddy 140", True))
@patch("room.room_gui.QInputDialog.getText", return_value=("", True))
def test_modify_room_empty_text(mock_get_text, mock_get_item):
    rooms = ["Roddy 140"]
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.modify_room_via_dialog(None)

    assert rooms == ["Roddy 140"]
    cfg.save.assert_not_called()


@patch("room.room_gui.QMessageBox.warning")
def test_delete_room_no_config(mock_warning):
    cfg = _config_mgr([])
    cfg.data = None
    mgr = RoomConfigManager(cfg)

    mgr.delete_room_via_dialog(None)

    mock_warning.assert_called_once()
    cfg.save.assert_not_called()


@patch("room.room_gui.QInputDialog.getItem", return_value=("Roddy 140", True))
@patch("room.room_gui.QMessageBox.question", return_value=QMessageBox.StandardButton.No)
def test_delete_room_aborted_by_user(mock_question, mock_get_item):
    rooms = ["Roddy 140"]
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.delete_room_via_dialog(None)

    assert rooms == ["Roddy 140"]
    cfg.save.assert_not_called()


@patch("room.room_gui.QInputDialog.getItem", return_value=("Roddy 140", True))
@patch("room.room_gui.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes)
def test_delete_room_success(mock_question, mock_get_item):
    rooms = ["Roddy 140"]
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.delete_room_via_dialog(None)

    assert rooms == []
    cfg.save.assert_called_once_with(None)


@patch("room.room_gui.QInputDialog.getItem", return_value=(None, False))
@patch("room.room_gui.QMessageBox.question")
def test_delete_room_selection_cancelled(mock_question, mock_get_item):
    rooms = ["Roddy 140"]
    cfg = _config_mgr(rooms)
    mgr = RoomConfigManager(cfg)

    mgr.delete_room_via_dialog(None)

    assert rooms == ["Roddy 140"]
    mock_question.assert_not_called()
    cfg.save.assert_not_called()