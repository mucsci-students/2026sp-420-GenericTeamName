"""
File: test_course_detail_poppup.py
Date: 04/26/2026
Author: Mohamed Mussa & Kyle Smith
Description: No-qtbot manual lifecycle version.
"""

from __future__ import annotations
import pytest
import gc
from unittest.mock import patch
from PyQt6.QtWidgets import QLabel, QApplication
from gui.course_detail_popup import CourseDetailPopup

@pytest.fixture
def make_popup(monkeypatch):
    # Completely disable threading
    monkeypatch.setattr("PyQt6.QtCore.QThread.start", lambda self: None)
    monkeypatch.setattr("threading.Thread.start", lambda self: None)
    
    # Ensure a QApp exists but don't use qtbot to manage it
    _ = QApplication.instance() or QApplication([])
    
    widgets = []

    def _make(data):
        with patch.object(CourseDetailPopup, 'show', return_value=None):
            popup = CourseDetailPopup(data)
            widgets.append(popup)
            return popup

    yield _make

    # Hard Manual Teardown
    for w in widgets:
        w.setParent(None)
        w.hide()
        w.deleteLater()
    
    widgets.clear()
    if QApplication.instance():
        QApplication.instance().processEvents()
    gc.collect()

def test_creates_dialog(make_popup):
    assert make_popup({"course_id": "TEST"}) is not None

def test_course_id_displayed(make_popup):
    popup = make_popup({"course_id": "CMSC420"})
    label = popup.findChild(QLabel, "course_id_lbl")
    assert label is not None and label.text() == "CMSC420"

def test_section_displayed(make_popup):
    popup = make_popup({"course_id": "CMSC420", "section": "0101"})
    label = popup.findChild(QLabel, "section_lbl")
    assert "0101" in label.text()

def test_resolve_time_string_logic(make_popup):
    course = {"meeting_pattern": [{"days": ["MW"], "start_time": "9:00 AM"}]}
    popup = make_popup(course)
    assert "MW" in popup._resolve_time_string()

def test_faculty_parsing(make_popup):
    popup = make_popup({"faculty": [{"name": "Dr. Smith"}]})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("Dr. Smith" in t for t in texts)
