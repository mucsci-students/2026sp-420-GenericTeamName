'''
    File: time_slot_editor.py
    Date: 04/05/2026
    Author: Chayse Altland
    Class: CMSC 420
    Description: 
'''
import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app