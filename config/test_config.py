#
# File: test_config.py
# Author: Kyle Smith
# Description: Test suite for config management
#

import pytest
from config_mgr import ConfigManager

def test_load_and_display(temp_config_file, capsys):
    # temp_config_file injected from conftest.py
    manager = ConfigManager(temp_config_file)
    manager.load()
    
    # human-readable test
    manager.display_human_summary()
    captured = capsys.readouterr()
    
    assert "SYSTEM CONFIGURATION" in captured.out
    assert "CS101" in captured.out

def test_save_functionality(temp_config_file):
    manager = ConfigManager(temp_config_file)
    manager.load()
    
    manager.data["limit"] = 50
    manager.save()
    
    # verify file save
    manager.load()
    assert manager.data["limit"] == 50
