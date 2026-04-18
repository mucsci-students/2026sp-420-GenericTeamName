'''
    File: test_room_manager.py
    Date: 03/3/2026
    Author: Chayse Altland
    Class: CMSC 420
    Description: Room management test suite.
'''
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from room.room_gui import RoomConfigManager

# pytest tests/test_room_config_manager.py -v to test

# -----------------------------
# Helper
# -----------------------------

def create_config_file(tmp_path, rooms):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "config": {
                "rooms": rooms
            }
        })
    )
    return config_file


# -----------------------------
# Tests
# -----------------------------

def test_get_rooms_list_returns_existing_rooms(tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy 140", "Roddy 147"])

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    rooms = manager._get_rooms_list()

    assert rooms == ["Roddy 140", "Roddy 147"]


def test_get_rooms_list_creates_missing_structure(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({}))  # no config key

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    rooms = manager._get_rooms_list()

    assert rooms == []
    assert "config" in manager._config_data
    assert "rooms" in manager._config_data["config"]


@patch("app.room_gui.QMessageBox.information")
def test_save_writes_file(mock_info, tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy 140"])

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    # Modify data
    manager._get_rooms_list().append("Roddy 150")

    manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert "Roddy 150" in saved_data["config"]["rooms"]
    mock_info.assert_called_once()


def test_add_room_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, [])

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    rooms = manager._get_rooms_list()
    rooms.append("Roddy 200")

    with patch("app.room_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["rooms"] == ["Roddy 200"]


def test_modify_room_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy 140"])

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    rooms = manager._get_rooms_list()
    rooms[0] = "Roddy 141"

    with patch("app.room_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["rooms"] == ["Roddy 141"]


def test_delete_room_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy 140", "Roddy 147"])

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    rooms = manager._get_rooms_list()
    del rooms[0]

    with patch("app.room_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["rooms"] == ["Roddy 147"]


@patch("app.room_gui.QMessageBox.critical")
def test_save_handles_os_error(mock_critical, tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy 140"])

    manager = RoomConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
        manager._save(parent=None)

    mock_critical.assert_called_once()

