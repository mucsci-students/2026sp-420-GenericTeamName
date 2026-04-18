'''
    Author: Damion Crawford
    Date: 4 March 2026
    Class: CMSC 420
    Description: Pytests for faculty management
'''

import json
import pytest
from pathlib import Path
from unittest.mock import patch
from faculty.faculty_gui import FacultyManager

# Helper

def create_config_file(tmp_path, faculty):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({
            "config": {
                "faculty": faculty
            }
        })
    )
    return config_file

def test_get_faculty_list_returns_existing_faculty(tmp_path):
    config_file = create_config_file(tmp_path, ['Hogg', 'Xie', 'Zoppetti'])

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    faculty = manager.list_faculty()
    assert faculty == ['Hogg', 'Xie', 'Zoppetti']

def test_get_faculty_list_creates_missing_structure(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({}))  # no config key

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    faculty = manager.list_faculty()

    assert faculty == []
    assert "config" in manager.config_data
    assert "faculty" in manager.config_data["config"]

@patch("app.faculty_gui.QMessageBox.information")
def test_save_writes_file(mock_info, tmp_path):
    config_file = create_config_file(tmp_path, ['Hogg'])

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    # Modify data
    manager.list_faculty().append("Schwartz")

    manager.save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert "Schwartz" in saved_data["config"]["faculty"]
    mock_info.assert_called_once()

def test_add_faculty_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, [])

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    faculty = manager.list_faculty()
    faculty.append("Xie")

    with patch("app.faculty_gui.QMessageBox.information"):
        manager.save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["faculty"] == ['Xie']

def test_modify_faculty_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, ['Hogg'])

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    faculty = manager.list_faculty()
    faculty[0] = "Schwartz"

    with patch("app.faculty_gui.QMessageBox.information"):
        manager.save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["faculty"] == ['Schwartz']

def test_delete_faculty_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, ['Cain','Hogg'])

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    faculty = manager.list_faculty()
    del faculty[0]

    with patch("app.faculty_gui.QMessageBox.information"):
        manager.save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["faculty"] == ["Hogg"]


@patch("app.faculty_gui.QMessageBox.critical")
def test_save_handles_os_error(mock_critical, tmp_path):
    config_file = create_config_file(tmp_path, ['Hardy'])

    manager = FacultyManager()
    manager.config_path = config_file
    manager.config_data = json.loads(config_file.read_text())

    with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
        manager.save(parent=None)

    mock_critical.assert_called_once()
