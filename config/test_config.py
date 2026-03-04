'''
    File: test_config.py
    Date: 03/01/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Test suite for config manager.
'''

import pytest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from config_mgr import ConfigManager

def test_load_nonexistent_file():
    """Verify that loading a missing file raises FileNotFoundError."""
    manager = ConfigManager("non_existent_file.json")
    with pytest.raises(FileNotFoundError):
        manager.load()

def test_load_malformed_json(tmp_path):
    """Verify behavior when the JSON file is corrupted."""
    bad_file = tmp_path / "corrupt.json"
    bad_file.write_text("{ 'invalid_json': True ")
    
    manager = ConfigManager(str(bad_file))
    with pytest.raises(json.JSONDecodeError):
        manager.load()

def test_get_summary_empty_data():
    """Ensure summary handles a fresh manager with no loaded data."""
    manager = ConfigManager("dummy.json")
    # Default state defined in __init__
    summary = manager.get_summary_text()
    
    assert "COURSE ID" in summary
    assert "CS101" not in summary

def test_get_summary_missing_config_key(tmp_path):
    """Edge case: File is valid JSON but missing the 'config' root key."""
    empty_file = tmp_path / "empty.json"
    # Data is not empty, but "config" is missing
    empty_file.write_text(json.dumps({"wrong_key": "some_value"}))

    manager = ConfigManager(str(empty_file))
    manager.load()
    summary = manager.get_summary_text()

    # Now this passes because the manager provides headers
    # even if the specific 'config' key is absent.
    assert "COURSE ID" in summary
    assert "CREDITS" in summary

def test_tabulation_alignment():
    """Verify that columns stay aligned regardless of string length."""
    manager = ConfigManager()
    manager.data["config"]["courses"] = [
        {"course_id": "SHORT", "credits": 1},
        {"course_id": "VERY_LONG_ID_STRING", "credits": 4}
    ]
    
    summary = manager.get_summary_text()
    lines = summary.split("\n")
    
    # Extract data rows (lines containing '|' but not the header text)
    data_lines = [l for l in lines if "|" in l and "COURSE ID" not in l]
    
    # Get the index of the first '|' for every line
    pipe_indices = [line.find("|") for line in data_lines]
    
    # Verify we have data to check
    assert len(pipe_indices) > 0
    # Verify all pipe indices are the same (the set will have length 1)
    assert len(set(pipe_indices)) == 1
    # Verify the width actually expanded to fit the long string
    # "VERY_LONG_ID_STRING" is 19 chars, so index should be at least 20
    assert pipe_indices[0] >= 20

def test_save_creates_new_file(tmp_path):
    """Verify that save() can create a file even if it didn't exist before."""
    new_file = tmp_path / "new_save.json"
    manager = ConfigManager(str(new_file))
    
    manager.data["config"]["rooms"] = ["Lab 1"]
    manager.save()
    
    assert os.path.exists(new_file)
    with open(new_file, 'r') as f:
        saved_data = json.load(f)
        assert "Lab 1" in saved_data["config"]["rooms"]

def test_get_summary_with_extra_attributes():
    """Ensure 'other attributes' logic correctly captures unexpected keys."""
    manager = ConfigManager()
    manager.data["config"]["courses"] = [
        {
            "course_id": "CS101", 
            "credits": 3, 
            "instructor": "Kyle", 
            "difficulty": "Hard"
        }
    ]
    
    summary = manager.get_summary_text()
    assert "instructor: Kyle" in summary
    assert "difficulty: Hard" in summary
