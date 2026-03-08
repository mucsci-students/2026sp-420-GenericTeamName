'''
    File: test_course_config_manager.py
    Date: 03/4/2026
    Author: Shane del Villar
    Class: CMSC 420
    Description: Course management tests
'''
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from app.course_gui import CourseConfigManager

# Helper


def create_config_file(tmp_path, courses=None):
    config_file = tmp_path / "config.json"
    courses = courses or []
    config_file.write_text(
        json.dumps({
            "config": {
                "courses": courses
            }
        })
    )
    return config_file


def sample_course(course_id="CMSC 140", credits=4, room=None, lab=None, conflicts=None, faculty=None):
    return {
        "course_id": course_id,
        "credits": credits,
        "room": room or [],
        "lab": lab or [],
        "conflicts": conflicts or [],
        "faculty": faculty or [],
    }


# CourseConfigManager - _get_courses_list


def test_get_courses_list_returns_existing_courses(tmp_path):
    courses = [
        sample_course("CMSC 140", 4),
        sample_course("CMSC 161", 4),
    ]
    config_file = create_config_file(tmp_path, courses)

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    result = manager._get_courses_list()

    assert len(result) == 2
    assert result[0]["course_id"] == "CMSC 140"
    assert result[0]["credits"] == 4
    assert result[1]["course_id"] == "CMSC 161"


def test_get_courses_list_creates_missing_structure(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({}))  # no config key

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    courses = manager._get_courses_list()

    assert courses == []
    assert "config" in manager._config_data
    assert "courses" in manager._config_data["config"]



# CourseConfigManager - _save


@patch("app.course_gui.QMessageBox.information")
def test_save_writes_file(mock_info, tmp_path):
    config_file = create_config_file(tmp_path, [sample_course("CMSC 140")])

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    manager._get_courses_list().append(sample_course("CMSC 161"))

    manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert len(saved_data["config"]["courses"]) == 2
    assert any(c["course_id"] == "CMSC 161" for c in saved_data["config"]["courses"])
    mock_info.assert_called_once()


@patch("app.course_gui.QMessageBox.critical")
def test_save_handles_os_error(mock_critical, tmp_path):
    config_file = create_config_file(tmp_path, [sample_course("CMSC 140")])

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
        manager._save(parent=None)

    mock_critical.assert_called_once()



# CourseConfigManager - add/modify/delete logic (no dialogs)


def test_add_course_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, [])

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    courses = manager._get_courses_list()
    courses.append(sample_course("CMSC 420", 3))

    with patch("app.course_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert len(saved_data["config"]["courses"]) == 1
    assert saved_data["config"]["courses"][0]["course_id"] == "CMSC 420"
    assert saved_data["config"]["courses"][0]["credits"] == 3


def test_modify_course_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, [
        sample_course("CMSC 140", 4),
        sample_course("CMSC 161", 4),
    ])

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    courses = manager._get_courses_list()
    courses[0]["course_id"] = "CMSC 141"
    courses[0]["credits"] = 3

    with patch("app.course_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert saved_data["config"]["courses"][0]["course_id"] == "CMSC 141"
    assert saved_data["config"]["courses"][0]["credits"] == 3


def test_delete_course_logic_without_dialog(tmp_path):
    config_file = create_config_file(tmp_path, [
        sample_course("CMSC 140"),
        sample_course("CMSC 161"),
        sample_course("CMSC 162"),
    ])

    manager = CourseConfigManager()
    manager.config_path = config_file
    manager._config_data = json.loads(config_file.read_text())

    courses = manager._get_courses_list()
    del courses[1]

    with patch("app.course_gui.QMessageBox.information"):
        manager._save(parent=None)

    saved_data = json.loads(config_file.read_text())
    assert len(saved_data["config"]["courses"]) == 2
    assert saved_data["config"]["courses"][0]["course_id"] == "CMSC 140"
    assert saved_data["config"]["courses"][1]["course_id"] == "CMSC 162"
