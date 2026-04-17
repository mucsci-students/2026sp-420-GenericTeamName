"""
File: test_meeting_pattern_editor.py
Date: 04/05/2026
Author: Chayse Altland
Description: Tests for MeetingPatternEditor logic optimized for CI/CD workflows.
"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QMessageBox, QWidget

from time_slot_config_editor.meeting_pattern_editor import MeetingPatternEditor


class DummyConfigManager:
    def __init__(self, data=None):
        self.data = data or {
            "config": {
                "meeting_patterns": []
            },
            "time_slot_config": {
                "times": {},
                "classes": []
            }
        }
        self.save_called = False

    def save(self, parent):
        self.save_called = True


@pytest.fixture
def parent(qapp):
    return QWidget()


@pytest.fixture
def config_mgr():
    return DummyConfigManager()


@pytest.fixture
def editor(config_mgr):
    return MeetingPatternEditor(config_mgr)


def test_get_patterns_returns_existing_gui_format():
    cfg = DummyConfigManager(
        {
            "config": {
                "meeting_patterns": [
                    {
                        "credits": 3,
                        "meetings": [
                            {"day": "Monday", "duration": 50, "lab": False},
                            {"day": "Wednesday", "duration": 50, "lab": False},
                            {"day": "Friday", "duration": 50, "lab": False},
                        ],
                        "start_time": "",
                        "disabled": False,
                    }
                ]
            },
            "time_slot_config": {
                "times": {},
                "classes": [],
            },
        }
    )
    editor = MeetingPatternEditor(cfg)

    result = editor._get_patterns()

    assert len(result) == 1
    assert result[0]["credits"] == 3
    assert result[0]["meetings"][0]["day"] == "Monday"


def test_get_patterns_falls_back_to_scheduler_format():
    cfg = DummyConfigManager(
        {
            "config": {},
            "time_slot_config": {
                "times": {},
                "classes": [
                    {
                        "credits": 4,
                        "meetings": [
                            {"day": "MON", "duration": 110, "lab": True},
                            {"day": "WED", "duration": 110},
                        ],
                        "start_time": "16:00",
                        "disabled": True,
                    }
                ],
            },
        }
    )
    editor = MeetingPatternEditor(cfg)

    result = editor._get_patterns()

    assert len(result) == 1
    assert result[0]["credits"] == 4
    assert result[0]["meetings"][0]["day"] == "Monday"
    assert result[0]["meetings"][0]["lab"] is True
    assert result[0]["meetings"][1]["day"] == "Wednesday"
    assert result[0]["start_time"] == "16:00"
    assert result[0]["disabled"] is True


def test_sync_time_slot_config_classes(editor):
    editor.config_mgr.data["config"]["meeting_patterns"] = [
        {
            "credits": 3,
            "meetings": [
                {"day": "Monday", "duration": 50, "lab": False},
                {"day": "Wednesday", "duration": 50, "lab": False},
                {"day": "Friday", "duration": 50, "lab": False},
            ],
            "start_time": "",
            "disabled": False,
        }
    ]

    editor._sync_time_slot_config_classes()

    assert editor.config_mgr.data["time_slot_config"]["classes"] == [
        {
            "credits": 3,
            "meetings": [
                {"day": "MON", "duration": 50},
                {"day": "WED", "duration": 50},
                {"day": "FRI", "duration": 50},
            ],
        }
    ]


def test_sync_time_slot_config_classes_includes_optional_fields(editor):
    editor.config_mgr.data["config"]["meeting_patterns"] = [
        {
            "credits": 4,
            "meetings": [
                {"day": "Tuesday", "duration": 110, "lab": True},
                {"day": "Thursday", "duration": 110, "lab": False},
            ],
            "start_time": "16:00",
            "disabled": True,
        }
    ]

    editor._sync_time_slot_config_classes()

    assert editor.config_mgr.data["time_slot_config"]["classes"] == [
        {
            "credits": 4,
            "meetings": [
                {"day": "TUE", "duration": 110, "lab": True},
                {"day": "THU", "duration": 110},
            ],
            "start_time": "16:00",
            "disabled": True,
        }
    ]


def test_sync_preserves_times(editor):
    editor.config_mgr.data["config"]["meeting_patterns"] = [
        {
            "credits": 3,
            "meetings": [
                {"day": "Monday", "duration": 50, "lab": False},
            ],
            "start_time": "",
            "disabled": False,
        }
    ]
    editor.config_mgr.data["time_slot_config"]["times"] = {
        "MON": [{"start": "08:00", "end": "12:00", "spacing": 60}]
    }

    editor._sync_time_slot_config_classes()

    assert editor.config_mgr.data["time_slot_config"]["times"] == {
        "MON": [{"start": "08:00", "end": "12:00", "spacing": 60}]
    }


def test_prompt_yes_no_true(monkeypatch, editor, parent):
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getItem",
        lambda *args, **kwargs: ("True", True),
    )

    result = editor._prompt_yes_no(parent, "Test", "Question")

    assert result is True


def test_prompt_yes_no_false(monkeypatch, editor, parent):
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getItem",
        lambda *args, **kwargs: ("False", True),
    )

    result = editor._prompt_yes_no(parent, "Test", "Question")

    assert result is False


def test_prompt_for_meetings(monkeypatch, editor, parent):
    int_responses = iter([
        (2, True),    # number of meetings
        (50, True),   # duration for meeting 1
        (75, True),   # duration for meeting 2
    ])
    item_responses = iter([
        ("Monday", True),   # meeting 1 day
        ("True", True),     # meeting 1 lab?
        ("Thursday", True), # meeting 2 day
        ("False", True),    # meeting 2 lab?
    ])

    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getInt",
        lambda *args, **kwargs: next(int_responses),
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getItem",
        lambda *args, **kwargs: next(item_responses),
    )

    meetings = editor._prompt_for_meetings(parent)

    assert meetings == [
        {"day": "Monday", "duration": 50, "lab": True},
        {"day": "Thursday", "duration": 75, "lab": False},
    ]


def test_prompt_for_pattern(monkeypatch, editor, parent):
    int_responses = iter([
        (4, True),    # credits
        (2, True),    # number of meetings
        (110, True),  # duration 1
        (110, True),  # duration 2
    ])
    item_responses = iter([
        ("Tuesday", True),  # meeting 1 day
        ("True", True),     # meeting 1 lab?
        ("Thursday", True), # meeting 2 day
        ("False", True),    # meeting 2 lab?
        ("True", True),     # disabled?
    ])
    text_responses = iter([
        ("16:00", True),    # start_time
    ])

    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getInt",
        lambda *args, **kwargs: next(int_responses),
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getItem",
        lambda *args, **kwargs: next(item_responses),
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getText",
        lambda *args, **kwargs: next(text_responses),
    )

    pattern = editor._prompt_for_pattern(parent)

    assert pattern == {
        "credits": 4,
        "meetings": [
            {"day": "Tuesday", "duration": 110, "lab": True},
            {"day": "Thursday", "duration": 110, "lab": False},
        ],
        "start_time": "16:00",
        "disabled": True,
    }


def test_pattern_label(editor):
    pattern = {
        "credits": 4,
        "meetings": [
            {"day": "Tuesday", "duration": 110, "lab": True},
            {"day": "Thursday", "duration": 110, "lab": False},
        ],
        "start_time": "16:00",
        "disabled": True,
    }

    label = editor._pattern_label(pattern, 0)

    assert "Pattern 1" in label
    assert "4 cr" in label
    assert "Tuesday 110 lab" in label
    assert "Thursday 110" in label
    assert "start=16:00" in label
    assert "disabled" in label


def test_add_meeting_pattern_success(monkeypatch, editor, parent):
    monkeypatch.setattr(
        editor,
        "_prompt_for_pattern",
        lambda *args, **kwargs: {
            "credits": 3,
            "meetings": [
                {"day": "Monday", "duration": 50, "lab": False},
                {"day": "Wednesday", "duration": 50, "lab": False},
                {"day": "Friday", "duration": 50, "lab": False},
            ],
            "start_time": "",
            "disabled": False,
        },
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    editor.add_meeting_pattern(parent)

    patterns = editor.config_mgr.data["config"]["meeting_patterns"]
    assert len(patterns) == 1
    assert patterns[0]["credits"] == 3
    assert editor.config_mgr.save_called is True


def test_modify_meeting_pattern_updates_selected(monkeypatch, parent):
    cfg = DummyConfigManager(
        {
            "config": {
                "meeting_patterns": [
                    {
                        "credits": 3,
                        "meetings": [
                            {"day": "Monday", "duration": 50, "lab": False},
                            {"day": "Wednesday", "duration": 50, "lab": False},
                            {"day": "Friday", "duration": 50, "lab": False},
                        ],
                        "start_time": "",
                        "disabled": False,
                    }
                ]
            },
            "time_slot_config": {
                "times": {},
                "classes": [],
            },
        }
    )
    editor = MeetingPatternEditor(cfg)

    first_label = editor._pattern_label(cfg.data["config"]["meeting_patterns"][0], 0)

    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getItem",
        lambda *args, **kwargs: (first_label, True),
    )
    monkeypatch.setattr(
        editor,
        "_prompt_for_pattern",
        lambda *args, **kwargs: {
            "credits": 4,
            "meetings": [
                {"day": "Tuesday", "duration": 110, "lab": True},
                {"day": "Thursday", "duration": 110, "lab": False},
            ],
            "start_time": "16:00",
            "disabled": True,
        },
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    editor.modify_meeting_pattern(parent)

    updated = editor.config_mgr.data["config"]["meeting_patterns"][0]
    assert updated["credits"] == 4
    assert updated["start_time"] == "16:00"
    assert updated["disabled"] is True
    assert editor.config_mgr.save_called is True


def test_delete_meeting_pattern_removes_selected(monkeypatch, parent):
    cfg = DummyConfigManager(
        {
            "config": {
                "meeting_patterns": [
                    {
                        "credits": 3,
                        "meetings": [
                            {"day": "Monday", "duration": 50, "lab": False},
                        ],
                        "start_time": "",
                        "disabled": False,
                    }
                ]
            },
            "time_slot_config": {
                "times": {},
                "classes": [],
            },
        }
    )
    editor = MeetingPatternEditor(cfg)

    first_label = editor._pattern_label(cfg.data["config"]["meeting_patterns"][0], 0)

    monkeypatch.setattr(
        "app.meeting_pattern_editor.QInputDialog.getItem",
        lambda *args, **kwargs: (first_label, True),
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    editor.delete_meeting_pattern(parent)

    assert editor.config_mgr.data["config"]["meeting_patterns"] == []
    assert editor.config_mgr.save_called is True


def test_modify_meeting_pattern_when_none_exist(monkeypatch, editor, parent):
    warning_calls = []
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QMessageBox.warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )

    editor.modify_meeting_pattern(parent)

    assert len(warning_calls) == 1


def test_delete_meeting_pattern_when_none_exist(monkeypatch, editor, parent):
    warning_calls = []
    monkeypatch.setattr(
        "app.meeting_pattern_editor.QMessageBox.warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )

    editor.delete_meeting_pattern(parent)

    assert len(warning_calls) == 1
