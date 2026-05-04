'''
    File: test_config.py
    Date: 03/01/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Test suite for config manager. Updated to handle PyQt6 dependencies.
'''

import pytest
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config_mgr import ConfigManager

@pytest.fixture
def temp_config_file(tmp_path):
    """Creates a temporary JSON config file."""
    d = tmp_path / "test_config.json"
    data = {
        "config": {
            "courses": [
                {"course_id": "CMSC101", "credits": 3, "room": ["101"], "faculty": ["Smith"]},
                {"course_id": "CMSC102", "credits": 4, "room": ["102"]}
            ]
        }
    }
    d.write_text(json.dumps(data))
    return str(d)

@pytest.fixture
def config_mgr(temp_config_file):
    return ConfigManager(filepath=temp_config_file)

## --- 1. Initialization and File I/O Tests ---

def test_init_defaults():
    mgr = ConfigManager()
    assert mgr.filepath == "config.json"
    assert "config" in mgr.data
    assert mgr.data["config"]["rooms"] == []

def test_load_success(config_mgr):
    parent = MagicMock()
    data = config_mgr.load(parent)
    assert len(data["config"]["courses"]) == 2
    assert data["config"]["courses"][0]["course_id"] == "CMSC101"

def test_load_file_not_found():
    mgr = ConfigManager(filepath="non_existent.json")
    parent = MagicMock()
    with patch("PyQt6.QtWidgets.QMessageBox.critical"):
        assert mgr.load(parent) is None

def test_save_success(config_mgr, tmp_path):
    parent = MagicMock()
    new_path = tmp_path / "save_test.json"
    config_mgr.filepath = str(new_path)
    config_mgr.data["config"]["rooms"] = ["Room A"]
    
    with patch("PyQt6.QtWidgets.QMessageBox.information") as mock_info:
        config_mgr.save(parent)
        mock_info.assert_called_once()
        
    with open(new_path, "r") as f:
        saved_data = json.load(f)
        assert saved_data["config"]["rooms"] == ["Room A"]

## --- 2. String Formatting & Summary Tests ---

def test_get_summary_text_empty():
    mgr = ConfigManager()
    mgr.data = {}
    assert mgr.get_summary_text() == "No data loaded."

def test_get_summary_text_with_courses(config_mgr):
    config_mgr.load(MagicMock())
    summary = config_mgr.get_summary_text()
    assert "COURSE ID" in summary
    assert "CMSC101" in summary
    assert "3" in summary
    
def test_get_schedule_spreadsheet(config_mgr):
    schedule_data = [
        {"course_id": "CS101", "day": "Mon", "time": "08:00"},
        {"course_id": "CS102", "day": "Tue", "time": "09:00"}
    ]
    sheet = config_mgr.get_schedule_spreadsheet(schedule_data)
    assert "Mon" in sheet
    assert "CS101" in sheet
    assert "08:00" in sheet

def test_get_grouped_schedule_text(config_mgr):
    schedule_data = [
        {"course_id": "CS101", "faculty": "Alice", "day": "Mon", "time": "08:00"},
        {"course_id": "CS102", "faculty": "Bob", "day": "Tue", "time": "09:00"}
    ]
    # Test grouping by faculty
    grouped = config_mgr.get_grouped_schedule_text(schedule_data, "faculty")
    assert "FACULTY" in grouped
    assert "Alice" in grouped
    assert "Bob" in grouped

## --- 3. Data Transformation Tests ---

def test_scheduler_output_to_viewer_format(config_mgr):
    raw_data = [{
        "course_id": "CMSC 161",
        "section": "01",
        "times": [{"day": 1, "start": 480}] # 08:00
    }]
    formatted = config_mgr.scheduler_output_to_viewer_format(raw_data)
    assert len(formatted) == 1
    assert formatted[0]["course_id"] == "CMSC 161.01"
    assert formatted[0]["day"] == "Mon"
    assert formatted[0]["time"] == "08:00"


def test_scheduler_output_to_viewer_format_merges_config_faculty(config_mgr):
    config_mgr.data.setdefault("config", {}).setdefault("courses", []).append(
        {"course_id": "CMSC 161", "faculty": ["Zoppetti"], "room": [], "lab": []}
    )
    raw_data = [{
        "course_id": "CMSC 161",
        "section": "01",
        "times": [{"day": 1, "start": 480, "duration": 50}],
    }]
    formatted = config_mgr.scheduler_output_to_viewer_format(raw_data)
    assert formatted[0]["faculty"] == ["Zoppetti"]
    assert formatted[0].get("duration_minutes") == 50


def test_scheduler_output_keeps_solver_faculty_room_lab(config_mgr):
    """Shapes like ``CourseInstance.model_dump``: course_str + scalar assignments."""
    raw_data = [{
        "course_str": "CMSC 499.03",
        "faculty": "Pat Q. Teacher",
        "room": "ITE 257",
        "lab": "Linux Suite",
        "times": [{"day": 3, "start": 600, "duration": 50}],
    }]
    formatted = config_mgr.scheduler_output_to_viewer_format(raw_data)
    assert len(formatted) == 1
    row = formatted[0]
    assert row["course_id"] == "CMSC 499.03"
    assert row["faculty"] == ["Pat Q. Teacher"]
    assert row["room"] == ["ITE 257"]
    assert row["lab"] == ["Linux Suite"]
    assert row["day"] == "Wed"


def test_scheduler_solver_faculty_overrides_heavier_config_lists(config_mgr):
    config_mgr.data.setdefault("config", {}).setdefault("courses", []).append(
        {
            "course_id": "TEST 301",
            "faculty": ["Faculty Only In Config"],
            "room": ["Room On File"],
            "lab": [],
        }
    )
    raw_data = [{
        "course_str": "TEST 301.01",
        "faculty": "Solver Picked Instructor",
        "room": "Solver Room A",
        "times": [{"day": 1, "start": 480, "duration": 50}],
    }]
    formatted = config_mgr.scheduler_output_to_viewer_format(raw_data)[0]
    assert formatted["faculty"] == ["Solver Picked Instructor"]
    assert formatted["room"] == ["Solver Room A"]

## --- 4. Export / Import Tests ---

def test_export_schedule_to_json_cancel(config_mgr):
    parent = MagicMock()
    with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=("", "")):
        result = config_mgr.export_schedule_to_json([{"test": "data"}], parent)
        assert result is False


def test_export_schedule_to_pdf_cancel(config_mgr):
    parent = MagicMock()
    with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=("", "")):
        result = config_mgr.export_schedule_to_pdf([{"test": "data"}], parent)
        assert result is False


def test_export_schedule_to_json_success(config_mgr, tmp_path):
    parent = MagicMock()
    save_path = str(tmp_path / "export.json")
    schedule_data = [{"course_id": "BIO1", "day": "Mon", "time": "08:00"}]
    
    with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(save_path, "JSON (*.json)")):
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            result = config_mgr.export_schedule_to_json([schedule_data], parent)
            assert result is True
            assert os.path.exists(save_path)


def test_export_schedule_to_pdf_success(config_mgr, tmp_path):
    parent = MagicMock()
    save_path = str(tmp_path / "export.pdf")
    schedule_data = [{"course_id": "BIO1", "day": "Mon", "time": "08:00"}]

    with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(save_path, "PDF (*.pdf)")):
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            result = config_mgr.export_schedule_to_pdf([schedule_data], parent)
            assert result is True
            assert os.path.exists(save_path)
            with open(save_path, "rb") as f:
                assert f.read(5).startswith(b"%PDF-")


def test_export_grouped_room_lab_pdf_success(config_mgr, tmp_path):
    parent = MagicMock()
    save_path = str(tmp_path / "room_lab.pdf")
    schedule_data = [{"course_id": "CMSC101", "day": "Mon", "time": "08:00"}]

    with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(save_path, "PDF (*.pdf)")):
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            result = config_mgr.export_grouped_printable([schedule_data], parent, "room_lab")
            assert result is True
            assert os.path.exists(save_path)
            with open(save_path, "rb") as f:
                assert f.read(5).startswith(b"%PDF-")


def test_export_grouped_faculty_pdf_success(config_mgr, tmp_path):
    parent = MagicMock()
    save_path = str(tmp_path / "faculty.pdf")
    schedule_data = [{"course_id": "CMSC101", "day": "Mon", "time": "08:00"}]

    with patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=(save_path, "PDF (*.pdf)")):
        with patch("PyQt6.QtWidgets.QMessageBox.information"):
            result = config_mgr.export_grouped_printable([schedule_data], parent, "faculty")
            assert result is True
            assert os.path.exists(save_path)
            with open(save_path, "rb") as f:
                assert f.read(5).startswith(b"%PDF-")


def test_grouped_faculty_uses_all_matching_course_entries(config_mgr):
    config_mgr.data["config"]["courses"] = [
        {"course_id": "CMSC101", "faculty": ["Dr. A"]},
        {"course_id": "CMSC101", "faculty": []},
    ]
    schedule_data = [{"course_id": "CMSC101.01", "day": "Mon", "time": "08:00"}]
    grouped = config_mgr._build_grouped_schedule_rows(schedule_data, "faculty")
    assert "Dr. A" in grouped
    assert "Unassigned" not in grouped

def test_import_schedule_from_json(config_mgr, tmp_path):
    parent = MagicMock()
    # Mocking the grid structure expected by import_schedule_from_json
    mock_json_content = [[
        ["TIME", "Mon", "Tue"],
        ["08:00", "CS101", ""]
    ]]
    import_path = tmp_path / "import.json"
    import_path.write_text(json.dumps(mock_json_content))

    with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=(str(import_path), "")):
        imported = config_mgr.import_schedule_from_json(parent=parent)
        assert len(imported) == 1
        assert imported[0][0]["course_id"] == "CS101"
        assert imported[0][0]["time"] == "08:00"

## --- 5. Grid Logic & Filtering Tests ---

def test_get_schedule_grid_data_all(config_mgr):
    config_mgr.load(MagicMock())
    schedule_data = [{"course_id": "CMSC101", "day": "Mon", "time": "08:00"}]
    days, times, grid, spans = config_mgr.get_schedule_grid_data(schedule_data, filter_type="all")

    row = times.index("08:00")
    assert "CMSC101" in grid[row][0]
    assert "Smith" in grid[row][0]
    assert any(rs > 1 for _r, _c, rs, _cs in spans)

def test_get_schedule_grid_data_filter_success(config_mgr):
    config_mgr.load(MagicMock())
    schedule_data = [
        {"course_id": "CMSC101", "day": "Mon", "time": "08:00"}, # Has 'Smith' in master config
        {"course_id": "CMSC102", "day": "Tue", "time": "09:00"}  # No 'Smith'
    ]
    
    # Filter for faculty "Smith"
    days, times, grid, _spans = config_mgr.get_schedule_grid_data(schedule_data, filter_type="faculty", filter_value="Smith")
    
    r8 = times.index("08:00")
    assert "CMSC101" in grid[r8][0]
    for r in range(len(times)):
        assert grid[r][1] == ""

def test_get_schedule_grid_data_collision(config_mgr):
    config_mgr.load(MagicMock())
    schedule_data = [
        {"course_id": "C1", "day": "Mon", "time": "10:00"},
        {"course_id": "C2", "day": "Mon", "time": "10:00"}
    ]
    _, times, grid, _ = config_mgr.get_schedule_grid_data(schedule_data)
    r10 = times.index("10:00")
    assert "C1" in grid[r10][0] and "C2" in grid[r10][0]


def test_scheduler_demo_json_validates_and_runs_scheduler():
    """``config/scheduler_demo.json`` matches ``course-constraint-scheduler`` schema."""
    from scheduler import Scheduler
    from scheduler.config import CombinedConfig

    path = Path(__file__).resolve().parent / "scheduler_demo.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = CombinedConfig(**raw)
    engine = Scheduler(cfg)
    first = next(engine.get_models(), None)
    assert first is not None
