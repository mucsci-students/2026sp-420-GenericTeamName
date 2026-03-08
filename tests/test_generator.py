'''
    File: test_generator.py
    Date: 03/06/2026
    Author: Tyler Strohl
    Class: CMSC 420
    Description: Pytests for Schedule Generator tasks.
'''
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.generator_gui import GenConfigManager

#test command:  python -m pytest tests/test_generator.py

def test_set_limit(tmp_path, mocker):

    manager = GenConfigManager()
    parent = MagicMock()
    config_file = tmp_path / "config.json"
    config_file.write_text('{"limit": 2}', encoding="utf-8")
    
    manager.config_path = config_file
    manager._config_data = {"limit": 2}

    mocker.patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("10", True))
    mocker.patch("PyQt6.QtWidgets.QMessageBox.information")

    manager.set_limit(parent)

    assert manager._config_data["limit"] == 10
    assert '"limit": 10' in config_file.read_text()

def test_set_optimize_true(tmp_path, mocker):

    manager = GenConfigManager()
    parent = MagicMock()
    manager.config_path = tmp_path / "config.json"
    manager._config_data = {"optimizer_flags": []}
    
    mocker.patch("PyQt6.QtWidgets.QInputDialog.getItem", return_value=("True", True))
    mocker.patch("PyQt6.QtWidgets.QMessageBox.information")

    manager.set_optimize(parent)

    assert len(manager._config_data["optimizer_flags"]) == 6
    assert "faculty_course" in manager._config_data["optimizer_flags"]

def test_set_optimize_false(tmp_path, mocker):
    
    manager = GenConfigManager()
    parent = MagicMock()
    manager.config_path = tmp_path / "config.json"
    manager._config_data = {"optimizer_flags": ["faculty_course"]}
    
    mocker.patch("PyQt6.QtWidgets.QInputDialog.getItem", return_value=("False", True))
    mocker.patch("PyQt6.QtWidgets.QMessageBox.information")
    mocker.patch.object(manager, "_ensure_config_loaded", return_value=True)

    manager.set_optimize(parent)

    assert len(manager._config_data["optimizer_flags"]) == 0

def test_save_writes_file(tmp_path, mocker):

    manager = GenConfigManager()
    parent = MagicMock()
    test_path = tmp_path / "test_save.json"
    manager.config_path = test_path
    manager._config_data = {"key": "value"}
    
    mock_info = mocker.patch("PyQt6.QtWidgets.QMessageBox.information")

    manager._save(parent)

    assert test_path.exists()
    assert json.loads(test_path.read_text())["key"] == "value"
    mock_info.assert_called_once()

def test_save_handles_os_error(tmp_path, mocker):
    
    manager = GenConfigManager()
    parent = MagicMock()
    config_file = tmp_path / "config.json"
    manager.config_path = config_file
    manager._config_data = {"limit": 2}

    mock_critical = mocker.patch("PyQt6.QtWidgets.QMessageBox.critical")
    mocker.patch.object(Path, "write_text", side_effect=OSError("Disk full"))

    manager._save(parent)

    mock_critical.assert_called_once()
    assert mock_critical.call_args[0][1] == "Save failed"

def test_gen_new_file(tmp_path, mocker):
    
    temp_config = {"limit": 1}
    config_file = tmp_path / "test_config.json"
    config_file.write_text(json.dumps(temp_config), encoding="utf-8")

    manager = GenConfigManager()
    manager.config_path = config_file
    manager._config_data = temp_config
    parent = MagicMock()

    mock_sched_instance = MagicMock()
    mock_sched_instance.get_models.return_value = [[{"course_id": "CMSC 140"}]]

    mocker.patch("scheduler.Scheduler", return_value=mock_sched_instance)
    mocker.patch("scheduler.load_config_from_file")
    mocker.patch.object(manager, "_ensure_config_loaded", return_value=True)

    save_path = str(tmp_path / "test_results.json")
    mocker.patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(save_path, ""))
    mocker.patch("PyQt6.QtWidgets.QMessageBox.information")

    manager.run_scheduler(parent)

    assert Path(save_path).exists()
    output_data = json.loads(Path(save_path).read_text())
    assert "CMSC 140" in output_data[0][0]
