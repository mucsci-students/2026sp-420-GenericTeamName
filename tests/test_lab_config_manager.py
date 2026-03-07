'''
    File: test_lab_manager.py
    Date: 03/3/2026
    Author: Mohamed Mussa
    Class: CMSC 420
    Description: Lab management test suite.
'''
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from app.lab_gui import LabConfigManager

# pytest tests/test_lab_config_manager.py -v to test

# -----------------------------
# Helper
# -----------------------------

def create_config_file(tmp_path, labs):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "config": {
                "labs": labs
            }
        })
    )
    return config_file


# -----------------------------
# Tests
# -----------------------------

def test_get_labs_list_returns_existing_labs(tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy Lab 140", "Roddy Lab 147"])

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    labs = manager._get_labs_list()

    assert labs == ["Roddy Lab 140", "Roddy Lab 147"]


def test_get_labs_list_creates_missing_structure(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({}))  # no config key

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    labs = manager._get_labs_list()

    assert labs == []
    assert "config" in manager._config_data
    assert "labs" in manager._config_data["config"]


@patch("app.lab_gui.QMessageBox.information")
def test_save_writes_file(mock_info, tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy Lab 140"])

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    # Modify data
    manager._get_labs_list().append("Roddy Lab 150")

    manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert "Roddy Lab 150" in saved_data["config"]["labs"]
    mock_info.assert_called_once()


def test_add_lab_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, [])

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    labs = manager._get_labs_list()
    labs.append("Roddy Lab 200")

    with patch("app.lab_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["labs"] == ["Roddy Lab 200"]


def test_modify_lab_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy Lab 140"])

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    labs = manager._get_labs_list()
    labs[0] = "Roddy Lab 141"

    with patch("app.lab_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["labs"] == ["Roddy Lab 141"]


def test_delete_lab_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy Lab 140", "Roddy Lab 147"])

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    labs = manager._get_labs_list()
    del labs[0]

    with patch("app.lab_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["labs"] == ["Roddy Lab 147"]


@patch("app.lab_gui.QMessageBox.critical")
def test_save_handles_os_error(mock_critical, tmp_path):
    config_file = create_config_file(tmp_path, ["Roddy Lab 140"])

    manager = LabConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
        manager._save(parent=None)

    mock_critical.assert_called_once()