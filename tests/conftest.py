'''
    File: conftest.py
    Date: 04/26/2026
    Author: Chayse Altland & Kyle Smith
    Class: CMSC 420
    Description: Setup for tests.
'''
import pytest
import os
import sys

# so that 'gui', 'config', etc., can be imported by tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session", autouse=True)
def setup_testing_env():
    """
    Sets up environment variables for testing.
    'offscreen' is useful for headless environments (CI) to prevent segfaults.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    
    os.environ["APP_ENV"] = "testing"
    yield

@pytest.fixture
def mock_config(tmp_path):
    """
    Example of a useful shared fixture: 
    Provides a temporary config file path for managers to use during tests.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text('{"faculty": [], "courses": [], "rooms": []}')
    return str(config_file)
