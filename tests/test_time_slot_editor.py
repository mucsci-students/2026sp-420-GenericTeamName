"""
File: test_time_slot_editor.py
Date: 04/05/2026
Author: Chayse Altland
Description: Tests for TimeSlotEditor logic
"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QMessageBox, QWidget

from timeslot_config.time_slot_editor import TimeSlotEditor


class DummyConfigManager:
    def __init__(self, data=None):
        self.data = data or {
            "config": {
                "time_slots": {}
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
    # Use a real QWidget parent to avoid Qt type issues in dialogs/message boxes.
    return QWidget()


@pytest.fixture
def config_mgr():
    return DummyConfigManager()


@pytest.fixture
def editor(config_mgr):
    return TimeSlotEditor(config_mgr)


def test_generate_slots(editor):
    slots = editor._generate_slots("08:00", "12:00", 60)
    assert slots == ["08:00", "09:00", "10:00", "11:00"]


def test_normalize_old_single_block_format(editor):
    old_entry = {
        "enabled": True,
        "start_time": "08:00",
        "end_time": "12:00",
        "spacing_minutes": 60,
        "slots": ["08:00", "09:00", "10:00", "11:00"],
    }

    normalized = editor._normalize_day_entry(old_entry)

    assert normalized["enabled"] is True
    assert "blocks" in normalized
    assert len(normalized["blocks"]) == 1
    assert normalized["blocks"][0]["start_time"] == "08:00"
    assert normalized["blocks"][0]["end_time"] == "12:00"
    assert normalized["blocks"][0]["spacing_minutes"] == 60


def test_get_timeslots_returns_existing_gui_format():
    cfg = DummyConfigManager(
        {
            "config": {
                "time_slots": {
                    "Monday": {
                        "enabled": True,
                        "blocks": [
                            {
                                "start_time": "08:00",
                                "end_time": "12:00",
                                "spacing_minutes": 60,
                                "slots": ["08:00", "09:00", "10:00", "11:00"],
                            }
                        ],
                    }
                }
            },
            "time_slot_config": {
                "times": {},
                "classes": [],
            },
        }
    )
    editor = TimeSlotEditor(cfg)

    result = editor._get_timeslots()

    assert "Monday" in result
    assert result["Monday"]["enabled"] is True
    assert len(result["Monday"]["blocks"]) == 1


def test_get_timeslots_falls_back_to_scheduler_format():
    cfg = DummyConfigManager(
        {
            "config": {},
            "time_slot_config": {
                "times": {
                    "MON": [
                        {"start": "08:00", "end": "12:00", "spacing": 60},
                    ],
                    "TUE": [
                        {"start": "13:10", "end": "17:10", "spacing": 60},
                        {"start": "17:10", "end": "19:40", "spacing": 30},
                    ],
                },
                "classes": [],
            },
        }
    )
    editor = TimeSlotEditor(cfg)

    result = editor._get_timeslots()

    assert "Monday" in result
    assert "Tuesday" in result
    assert result["Monday"]["blocks"][0]["start_time"] == "08:00"
    assert len(result["Tuesday"]["blocks"]) == 2
    assert result["Tuesday"]["blocks"][1]["spacing_minutes"] == 30


def test_sync_time_slot_config_single_day(editor):
    editor.config_mgr.data["config"]["time_slots"] = {
        "Monday": {
            "enabled": True,
            "blocks": [
                {
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "spacing_minutes": 60,
                    "slots": ["08:00", "09:00", "10:00", "11:00"],
                }
            ],
        }
    }

    editor._sync_time_slot_config()

    assert editor.config_mgr.data["time_slot_config"]["times"] == {
        "MON": [
            {"start": "08:00", "end": "12:00", "spacing": 60}
        ]
    }


def test_sync_time_slot_config_multiple_blocks_same_day(editor):
    editor.config_mgr.data["config"]["time_slots"] = {
        "Tuesday": {
            "enabled": True,
            "blocks": [
                {
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "spacing_minutes": 60,
                    "slots": [],
                },
                {
                    "start_time": "13:10",
                    "end_time": "17:10",
                    "spacing_minutes": 60,
                    "slots": [],
                },
                {
                    "start_time": "17:10",
                    "end_time": "19:40",
                    "spacing_minutes": 30,
                    "slots": [],
                },
            ],
        }
    }

    editor._sync_time_slot_config()

    assert editor.config_mgr.data["time_slot_config"]["times"]["TUE"] == [
        {"start": "08:00", "end": "12:00", "spacing": 60},
        {"start": "13:10", "end": "17:10", "spacing": 60},
        {"start": "17:10", "end": "19:40", "spacing": 30},
    ]


def test_sync_preserves_classes(editor):
    editor.config_mgr.data["config"]["time_slots"] = {
        "Monday": {
            "enabled": True,
            "blocks": [
                {
                    "start_time": "08:00",
                    "end_time": "12:00",
                    "spacing_minutes": 60,
                    "slots": [],
                }
            ],
        }
    }
    editor.config_mgr.data["time_slot_config"]["classes"] = [
        {"credits": 3, "meetings": [{"day": "MON", "duration": 50}]}
    ]

    editor._sync_time_slot_config()

    assert editor.config_mgr.data["time_slot_config"]["classes"] == [
        {"credits": 3, "meetings": [{"day": "MON", "duration": 50}]}
    ]


def test_prompt_for_block_rejects_invalid_range(monkeypatch, editor, parent):
    text_responses = iter([
        ("12:00", True),
        ("08:00", True),
    ])

    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getText",
        lambda *args, **kwargs: next(text_responses),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getInt",
        lambda *args, **kwargs: (60, True),
    )

    warning_calls = []
    monkeypatch.setattr(
        "app.time_slot_editor.QMessageBox.warning",
        lambda *args, **kwargs: warning_calls.append((args, kwargs)),
    )

    result = editor._prompt_for_block(parent, "Test Block")

    assert result is None
    assert len(warning_calls) == 1


def test_add_time_slot_success(monkeypatch, editor, parent):
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getItem",
        lambda *args, **kwargs: ("Monday", True),
    )

    text_responses = iter([
        ("08:00", True),
        ("12:00", True),
    ])
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getText",
        lambda *args, **kwargs: next(text_responses),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getInt",
        lambda *args, **kwargs: (60, True),
    )

    info_calls = []
    monkeypatch.setattr(
        "app.time_slot_editor.QMessageBox.information",
        lambda *args, **kwargs: info_calls.append((args, kwargs)),
    )

    editor.add_time_slot(parent)

    monday = editor.config_mgr.data["config"]["time_slots"]["Monday"]
    assert len(monday["blocks"]) == 1
    assert monday["blocks"][0]["start_time"] == "08:00"
    assert editor.config_mgr.save_called is True
    assert len(info_calls) == 1


def test_add_time_slot_appends_second_block_same_day(monkeypatch, parent):
    cfg = DummyConfigManager(
        {
            "config": {
                "time_slots": {
                    "Monday": {
                        "enabled": True,
                        "blocks": [
                            {
                                "start_time": "08:00",
                                "end_time": "12:00",
                                "spacing_minutes": 60,
                                "slots": ["08:00", "09:00", "10:00", "11:00"],
                            }
                        ],
                    }
                }
            },
            "time_slot_config": {
                "times": {},
                "classes": [],
            },
        }
    )
    editor = TimeSlotEditor(cfg)

    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getItem",
        lambda *args, **kwargs: ("Monday", True),
    )

    text_responses = iter([
        ("13:10", True),
        ("17:10", True),
    ])
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getText",
        lambda *args, **kwargs: next(text_responses),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getInt",
        lambda *args, **kwargs: (60, True),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    editor.add_time_slot(parent)

    monday_blocks = editor.config_mgr.data["config"]["time_slots"]["Monday"]["blocks"]
    assert len(monday_blocks) == 2
    assert monday_blocks[1]["start_time"] == "13:10"


def test_delete_last_block_removes_day(monkeypatch, parent):
    cfg = DummyConfigManager(
        {
            "config": {
                "time_slots": {
                    "Monday": {
                        "enabled": True,
                        "blocks": [
                            {
                                "start_time": "08:00",
                                "end_time": "12:00",
                                "spacing_minutes": 60,
                                "slots": ["08:00", "09:00", "10:00", "11:00"],
                            }
                        ],
                    }
                }
            },
            "time_slot_config": {"times": {}, "classes": []},
        }
    )
    editor = TimeSlotEditor(cfg)

    item_responses = iter([
        ("Monday", True),
        ("Block 1: 08:00 - 12:00 every 60 min", True),
    ])
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getItem",
        lambda *args, **kwargs: next(item_responses),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    editor.delete_time_slot(parent)

    assert "Monday" not in editor.config_mgr.data["config"]["time_slots"]
    assert editor.config_mgr.save_called is True


def test_modify_time_slot_updates_selected_block(monkeypatch, parent):
    cfg = DummyConfigManager(
        {
            "config": {
                "time_slots": {
                    "Tuesday": {
                        "enabled": True,
                        "blocks": [
                            {
                                "start_time": "08:00",
                                "end_time": "12:00",
                                "spacing_minutes": 60,
                                "slots": [],
                            }
                        ],
                    }
                }
            },
            "time_slot_config": {"times": {}, "classes": []},
        }
    )
    editor = TimeSlotEditor(cfg)

    item_responses = iter([
        ("Tuesday", True),
        ("Block 1: 08:00 - 12:00 every 60 min", True),
    ])
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getItem",
        lambda *args, **kwargs: next(item_responses),
    )

    text_responses = iter([
        ("09:00", True),
        ("13:00", True),
    ])
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getText",
        lambda *args, **kwargs: next(text_responses),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QInputDialog.getInt",
        lambda *args, **kwargs: (30, True),
    )
    monkeypatch.setattr(
        "app.time_slot_editor.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    editor.modify_time_slot(parent)

    block = editor.config_mgr.data["config"]["time_slots"]["Tuesday"]["blocks"][0]
    assert block["start_time"] == "09:00"
    assert block["end_time"] == "13:00"
    assert block["spacing_minutes"] == 30
    assert editor.config_mgr.save_called is True
