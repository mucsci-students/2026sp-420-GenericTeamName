#
# File: conftest.py
# Author: Kyle Smith
# Description: Used for creating sample data for tests.
#

import pytest
import json
import os

@pytest.fixture
def valid_config_dict():
    """Return a dictionary matching expected JSON structure."""
    return {
        "config": {
            "rooms": ["Room A", "Room B"],
            "courses": [{"course_id": "CS101", "credits": 3}],
            "faculty": [{"name": "Dr. Smith", "unique_course_limit": 3}]
        },
        "limit": 10
    }

@pytest.fixture
def temp_config_file(tmp_path, valid_config_dict):
    """Create temp JSON file for loading tests."""
    file_path = tmp_path / "test_config.json"
    file_path.write_text(json.dumps(valid_config_dict))
    return str(file_path)
