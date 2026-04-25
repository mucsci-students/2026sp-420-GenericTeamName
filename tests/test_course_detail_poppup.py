"""
File: test_course_detail_poppup.py
Date: 04/16/2026
Author: Mohamed Mussa
Description: Tests for CourseDetailPopup display logic only
"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QLabel

from gui.course_detail_popup import CourseDetailPopup


@pytest.fixture
def minimal_course():
    return {"course_id": "CMSC420", "section": "0101"}


@pytest.fixture
def full_course():
    return {
        "course_id": "CMSC420",
        "section": "0101",
        "faculty": [{"name": "Dr. Smith"}, {"name": "Dr. Jones"}],
        "meeting_pattern": [
            {"days": ["MWF"], "start_time": "10:00 AM", "end_time": "10:50 AM"}
        ],
        "room": ["CSI 2117"],
        "lab": ["ESJ 0224"],
        "credits": 3,
    }


def test_creates_dialog(qtbot, minimal_course):
    popup = CourseDetailPopup(minimal_course)
    assert popup is not None

def test_minimum_width(qtbot, full_course):
    popup = CourseDetailPopup(full_course)
    assert popup.minimumWidth() == 270

def test_course_data_stored(qtbot, full_course):
    popup = CourseDetailPopup(full_course)
    assert popup._course is full_course

def test_course_id_displayed(qtbot, minimal_course):
    popup = CourseDetailPopup(minimal_course)
    labels = {lbl.objectName(): lbl for lbl in popup.findChildren(QLabel)}
    assert labels["course_id_lbl"].text() == "CMSC420"

def test_section_displayed(qtbot, minimal_course):
    popup = CourseDetailPopup(minimal_course)
    labels = {lbl.objectName(): lbl for lbl in popup.findChildren(QLabel)}
    assert "0101" in labels["section_lbl"].text()

def test_no_section_label_when_missing(qtbot):
    popup = CourseDetailPopup({"course_id": "CMSC420"})
    labels = {lbl.objectName(): lbl for lbl in popup.findChildren(QLabel)}
    if "section_lbl" in labels:
        assert labels["section_lbl"].text() == ""

def test_unknown_course_id_fallback(qtbot):
    popup = CourseDetailPopup({})
    labels = {lbl.objectName(): lbl for lbl in popup.findChildren(QLabel)}
    assert labels["course_id_lbl"].text() == "Unknown"

def test_meeting_pattern_with_end(qtbot):
    course = {"meeting_pattern": [{"days": ["MW"], "start_time": "9:00 AM", "end_time": "9:50 AM"}]}
    result = CourseDetailPopup(course)._resolve_time_string()
    assert "MW" in result
    assert "9:00 AM" in result
    assert "9:50 AM" in result

def test_meeting_pattern_without_end(qtbot):
    course = {"meeting_pattern": [{"days": ["TR"], "start_time": "2:00 PM"}]}
    result = CourseDetailPopup(course)._resolve_time_string()
    assert "TR" in result
    assert "2:00 PM" in result

def test_multiple_meeting_patterns(qtbot):
    course = {
        "meeting_pattern": [
            {"days": ["MW"], "start_time": "10:00 AM", "end_time": "10:50 AM"},
            {"days": ["F"],  "start_time": "10:00 AM", "end_time": "10:50 AM"},
        ]
    }
    assert "\n" in CourseDetailPopup(course)._resolve_time_string()

def test_meeting_pattern_no_days_no_start_returns_tba(qtbot):
    assert CourseDetailPopup({"meeting_pattern": [{}]})._resolve_time_string() == "TBA"

def test_flat_days_and_times(qtbot):
    course = {"days": ["MWF"], "start_time": "11:00 AM", "end_time": "11:50 AM"}
    result = CourseDetailPopup(course)._resolve_time_string()
    assert "MWF" in result
    assert "11:00 AM" in result

def test_flat_days_and_time_slot(qtbot):
    course = {"days": ["TR"], "time_slot": "2:00 PM–3:15 PM"}
    result = CourseDetailPopup(course)._resolve_time_string()
    assert "TR" in result
    assert "2:00 PM–3:15 PM" in result

def test_time_slot_only(qtbot):
    assert CourseDetailPopup({"time_slot": "9:00 AM–9:50 AM"})._resolve_time_string() == "9:00 AM–9:50 AM"

def test_empty_course_returns_tba(qtbot):
    assert CourseDetailPopup({})._resolve_time_string() == "TBA"

def test_meeting_pattern_start_only_no_days(qtbot):
    course = {"meeting_pattern": [{"start_time": "8:00 AM", "end_time": "8:50 AM"}]}
    assert "8:00 AM" in CourseDetailPopup(course)._resolve_time_string()

def test_faculty_list_of_dicts(qtbot, full_course):
    popup = CourseDetailPopup(full_course)
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("Dr. Smith" in t and "Dr. Jones" in t for t in texts)

def test_faculty_empty_list_shows_tba(qtbot):
    popup = CourseDetailPopup({"faculty": []})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("TBA" in t for t in texts)

def test_faculty_plain_string(qtbot):
    popup = CourseDetailPopup({"faculty": "Dr. Brown"})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("Dr. Brown" in t for t in texts)

def test_faculty_missing_shows_tba(qtbot):
    popup = CourseDetailPopup({})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("TBA" in t for t in texts)

def test_faculty_list_of_strings(qtbot):
    popup = CourseDetailPopup({"faculty": ["Prof. A", "Prof. B"]})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("Prof. A" in t and "Prof. B" in t for t in texts)

def test_room_list(qtbot):
    popup = CourseDetailPopup({"room": ["CSI 2117"]})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("CSI 2117" in t for t in texts)

def test_room_alias_rooms(qtbot):
    popup = CourseDetailPopup({"rooms": ["AVW 4172"]})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("AVW 4172" in t for t in texts)

def test_room_empty_shows_tba(qtbot):
    popup = CourseDetailPopup({"room": []})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("TBA" in t for t in texts)

def test_lab_list(qtbot):
    popup = CourseDetailPopup({"lab": ["ESJ 0224"]})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("ESJ 0224" in t for t in texts)

def test_lab_alias_labs(qtbot):
    popup = CourseDetailPopup({"labs": ["CSI 3118"]})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("CSI 3118" in t for t in texts)

def test_lab_empty_shows_none(qtbot):
    popup = CourseDetailPopup({"lab": []})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("None" in t for t in texts)

def test_lab_missing_shows_none(qtbot):
    popup = CourseDetailPopup({})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("None" in t for t in texts)

def test_credits_shown_when_present(qtbot):
    popup = CourseDetailPopup({"credits": 3})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("3" in t for t in texts)

def test_credits_not_shown_when_absent(qtbot):
    popup = CourseDetailPopup({})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert not any(t.strip().upper() == "CREDITS" for t in texts)

def test_credits_zero_shown(qtbot):
    popup = CourseDetailPopup({"credits": 0})
    texts = [lbl.text() for lbl in popup.findChildren(QLabel)]
    assert any("0" in t for t in texts)
