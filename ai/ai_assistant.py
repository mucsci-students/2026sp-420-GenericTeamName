'''
    File: ai_assistant.py
    Date: 4/17/26
    Author: Shane del Villar & Kyle Smith
    Description: OpenAI tool-calling assistant that mutates the active scheduler config
    and triggers GUI actions (e.g. add rooms, courses, run generation).
'''

from __future__ import annotations

import copy
import csv
import inspect
import io
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

# ---------------------------------------------------------------------------
# WHERE TO PUT YOUR API KEY 
#
#    assign your key to OPENAI_API_KEY_IN_CODE (use your real key, never commit it to git):
# ---------------------------------------------------------------------------
OPENAI_API_KEY_IN_CODE: str = ""

# Model used for chat completions (change if your account uses another default).
OPENAI_MODEL: str = "gpt-5-mini"


SYSTEM_PROMPT = """You are an assistant inside a PyQt6 scheduler configuration application.
You can drive almost everything the menus do via tools.

Config (JSON file): load/save, switch file, edit rooms/labs/faculty/courses, set generation limit and optimizer flags.
Generator: start schedule generation (progress dialog).
Schedules in memory: use get_schedule_session_info; set_current_schedule_index to choose which generated/imported schedule is "current";
get_current_schedule_display_text to read the tabular view as text; open_schedule_viewer opens the same Schedule Viewer window as the menu
(mode: all, faculty, room, lab); export_current_schedule_to_csv writes the current schedule to a path (no file picker);
export_all_schedules_to_pdf and export_all_schedules_to_json write every loaded schedule option to a path (no dialogs).
import_schedule_from_file loads CSV or JSON into the schedule list.
undo_configuration_change / redo_configuration_change step through a small stack of configuration snapshots from assistant-driven edits (reload from disk, course updates/deletes, etc.); they do not undo manual GUI edits outside the assistant.
Summary: get_config_summary_text returns the table summary as text; show_config_summary_dialog opens the menu's summary message box.
Timeslots: config.time_slots (per weekday blocks: start_time, end_time, spacing_minutes, generated slots). list_timeslots; add_timeslot_block; update_timeslot_block; remove_timeslot_block; set_timeslot_day_enabled. Syncs to time_slot_config.times for the scheduler.
Class meeting patterns: config.meeting_patterns (credits, meetings with day/duration/lab, optional start_time, disabled). list_meeting_patterns; add_meeting_pattern; update_meeting_pattern; delete_meeting_pattern. Syncs to time_slot_config.classes.
Weekdays: accept full names (Monday) or MON/TUE/... .
Native menus: open_native_gui runs File/Edit/Generator/Viewer/Timeslot actions that need interactive dialogs (file pickers, forms, limit/optimize prompts).
When the user asks to change the config, call the appropriate tools. After tools succeed, briefly confirm what you did.
Prefer tools over telling the user to edit JSON manually. If a room/course/faculty is missing, say so and use list tools or get_config_json.
Saving: most mutation tools persist to disk immediately."""

# Tools that work without an active config filepath (in-memory schedules or global GUI).
_SKIP_ACTIVE_CONFIG_PATH = frozenset(
    {
        "get_active_config_path",
        "get_schedule_session_info",
        "get_current_schedule_display_text",
        "set_current_schedule_index",
        "open_schedule_viewer",
        "open_native_gui",
        "export_current_schedule_to_csv",
        "export_all_schedules_to_pdf",
        "export_all_schedules_to_json",
        "import_schedule_from_file",
        "get_config_summary_text",
        "show_config_summary_dialog",
        "undo_configuration_change",
        "redo_configuration_change",
        "set_active_config_file",
        "save_config_copy_as",
    }
)


DEFAULT_OPTIMIZER_FLAGS: List[str] = [
    "faculty_course",
    "faculty_room",
    "faculty_lab",
    "same_room",
    "same_lab",
    "pack_rooms",
]


def _sync_config_inspector(mw: Any) -> None:
    """Push ``config_mgr.data`` into the left JSON inspector (``ViewerManager._sync_detail_view``)."""
    vm = getattr(mw, "viewer_mgr", None)
    if vm is not None and hasattr(vm, "_sync_detail_view"):
        vm._sync_detail_view(mw)


def _ensure_config_block(main_window: Any) -> Dict[str, Any]:
    data = main_window.config_mgr.data
    if not isinstance(data, dict):
        main_window.config_mgr.data = {}
        data = main_window.config_mgr.data
    cfg = data.setdefault("config", {})
    if not isinstance(cfg, dict):
        data["config"] = {}
        cfg = data["config"]
    for key, default in (
        ("rooms", []),
        ("labs", []),
        ("courses", []),
        ("faculty", []),
    ):
        if key not in cfg or not isinstance(cfg[key], list):
            cfg[key] = list(default) if default == [] else default
    return cfg


def _write_config_silent(main_window: Any) -> None:
    # Snapshot before writes so assistant undo/redo works for any tool that persists config.
    if hasattr(main_window, "assistant_push_config_undo_snapshot"):
        main_window.assistant_push_config_undo_snapshot()
    path = main_window.config_mgr.filepath
    with open(path, "w", encoding="utf-8") as f:
        json.dump(main_window.config_mgr.data, f, indent=4)


def _faculty_display_name(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("name", entry))
    return str(entry)


def _normalize_weekday_for_editor(day: str, day_map: Dict[str, str], reverse: Dict[str, str]) -> Optional[str]:
    """Return long weekday name (e.g. Monday) for TimeSlotEditor / MeetingPatternEditor."""
    s = (day or "").strip()
    if not s:
        return None
    if s in day_map:
        return s
    up = s.upper()
    if up in reverse:
        return reverse[up]
    # Title case fallback
    tc = s[:1].upper() + s[1:].lower() if s else ""
    if tc in day_map:
        return tc
    return None


def _parse_hhmm(t: str) -> bool:
    try:
        parts = str(t).strip().split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except (TypeError, ValueError):
        return False


def _normalize_meeting_entries(
    meetings: List[Any],
    day_map: Dict[str, str],
    reverse: Dict[str, str],
) -> tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    out: List[Dict[str, Any]] = []
    for m in meetings:
        if not isinstance(m, dict):
            return None, "Each meeting must be an object."
        day = _normalize_weekday_for_editor(str(m.get("day", "")), day_map, reverse)
        if not day:
            return None, f"Invalid weekday: {m.get('day')!r}"
        try:
            dur = int(m.get("duration", 50))
        except (TypeError, ValueError):
            return None, "duration must be an integer."
        if dur < 1:
            return None, "duration must be >= 1."
        out.append(
            {
                "day": day,
                "duration": dur,
                "lab": bool(m.get("lab", False)),
            }
        )
    if not out:
        return None, "At least one meeting is required."
    return out, None


def _faculty_match_index(faculty: List[Any], target: str) -> Optional[int]:
    """Resolve faculty by display name: exact (case-insensitive), else unique substring match."""
    t = target.strip()
    if not t:
        return None
    t_cf = t.casefold()
    names = [(i, _faculty_display_name(f)) for i, f in enumerate(faculty)]
    for i, name in names:
        if name.strip().casefold() == t_cf:
            return i
    substr = [i for i, name in names if t_cf in name.casefold()]
    if len(substr) == 1:
        return substr[0]
    return None


def get_tool_schemas() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_active_config_path",
                "description": "Return the active config JSON path, or null if none selected yet.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_config_json",
                "description": "Return the full active config as formatted JSON (may be truncated if extremely large).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "reload_config_from_disk",
                "description": "Reload the active config file from disk into the editor.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_config_to_disk",
                "description": "Write the in-memory config to the active file path.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_active_config_file",
                "description": "Switch to another JSON config file on disk (must exist). Loads it as the active config.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Absolute or relative path to .json"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_room",
                "description": "Append a room name to config.rooms if not already present, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"room_name": {"type": "string"}},
                    "required": ["room_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_room",
                "description": "Remove the first matching room name from config.rooms, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"room_name": {"type": "string"}},
                    "required": ["room_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rename_room",
                "description": "Rename a room string in config.rooms (exact match), then save.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_name": {"type": "string"},
                        "new_name": {"type": "string"},
                    },
                    "required": ["old_name", "new_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_lab",
                "description": "Append a lab name to config.labs if not already present, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"lab_name": {"type": "string"}},
                    "required": ["lab_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_lab",
                "description": "Remove the first matching lab name from config.labs, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"lab_name": {"type": "string"}},
                    "required": ["lab_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rename_lab",
                "description": "Rename a lab string in config.labs (exact match), then save.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_name": {"type": "string"},
                        "new_name": {"type": "string"},
                    },
                    "required": ["old_name", "new_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_faculty",
                "description": "Append a faculty name (plain string entry) to config.faculty, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_faculty",
                "description": "Remove faculty entry whose display name matches (first match), then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rename_faculty",
                "description": "Rename faculty by display name (first match). Dict entries update 'name'; strings become dict with name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "old_name": {"type": "string"},
                        "new_name": {"type": "string"},
                    },
                    "required": ["old_name", "new_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "merge_faculty_object",
                "description": (
                    "Shallow-merge a JSON object into the first faculty entry whose display name matches. "
                    "Use for times, course_preferences, room_preferences, lab_preferences, credits limits, etc."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "faculty_name": {"type": "string"},
                        "merge_json": {
                            "type": "string",
                            "description": 'JSON object string, e.g. {"room_preferences": {"Roddy 136": 5}}',
                        },
                    },
                    "required": ["faculty_name", "merge_json"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_course",
                "description": "Append a course object to config.courses, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_id": {"type": "string"},
                        "credits": {"type": "integer"},
                        "rooms": {"type": "array", "items": {"type": "string"}},
                        "labs": {"type": "array", "items": {"type": "string"}},
                        "conflicts": {"type": "array", "items": {"type": "string"}},
                        "faculty": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["course_id", "credits"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_course",
                "description": "Update the first course with matching course_id. Omitted fields stay unchanged.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_id": {"type": "string"},
                        "credits": {"type": "integer"},
                        "rooms": {"type": "array", "items": {"type": "string"}},
                        "labs": {"type": "array", "items": {"type": "string"}},
                        "conflicts": {"type": "array", "items": {"type": "string"}},
                        "faculty": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["course_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_course",
                "description": "Delete the first course with matching course_id, then save.",
                "parameters": {
                    "type": "object",
                    "properties": {"course_id": {"type": "string"}},
                    "required": ["course_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_schedule_limit",
                "description": "Set top-level 'limit' (number of schedules the generator produces). Saves file.",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                    "required": ["limit"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_optimizer_enabled",
                "description": "Enable or disable all default optimizer_flags on the config root.",
                "parameters": {
                    "type": "object",
                    "properties": {"enabled": {"type": "boolean"}},
                    "required": ["enabled"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_schedule_generation",
                "description": "Start the same schedule generation flow as the Generate Schedules button (progress UI).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_rooms",
                "description": "List room names in the active config.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_labs",
                "description": "List lab names in the active config.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_faculty",
                "description": "List faculty display names in order (strings or dict.name).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_course_ids",
                "description": "List course_id values in order.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_timeslots",
                "description": (
                    "Return config.time_slots after normalization: each weekday with enabled flag and "
                    "blocks (start_time, end_time, spacing_minutes, slots). Also notes scheduler time_slot_config.times."
                ),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_timeslot_block",
                "description": "Append a time block for one weekday; regenerates slot list and syncs scheduler times, then saves.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day": {
                            "type": "string",
                            "description": "Monday..Friday or MON..FRI",
                        },
                        "start_time": {"type": "string", "description": "HH:MM"},
                        "end_time": {"type": "string", "description": "HH:MM"},
                        "spacing_minutes": {"type": "integer", "description": "Minutes between slot starts"},
                    },
                    "required": ["day", "start_time", "end_time", "spacing_minutes"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_timeslot_block",
                "description": "Replace one block by index for a weekday (0-based). Omitted time/spacing fields keep previous values.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "string"},
                        "block_index": {"type": "integer", "description": "0-based index within that day's blocks"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "spacing_minutes": {"type": "integer"},
                    },
                    "required": ["day", "block_index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_timeslot_block",
                "description": "Delete one timeslot block by weekday and 0-based block index; removes the day entry if no blocks left.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "string"},
                        "block_index": {"type": "integer"},
                    },
                    "required": ["day", "block_index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_timeslot_day_enabled",
                "description": "Enable or disable all blocks for a weekday (scheduler skips disabled days).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "string"},
                        "enabled": {"type": "boolean"},
                    },
                    "required": ["day", "enabled"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_meeting_patterns",
                "description": "List class meeting patterns (index, credits, meetings, start_time, disabled) as JSON.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "add_meeting_pattern",
                "description": "Append a meeting pattern; syncs to time_slot_config.classes and saves.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "credits": {"type": "integer"},
                        "meetings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "day": {"type": "string", "description": "Monday..Friday or MON..FRI"},
                                    "duration": {"type": "integer", "description": "Minutes"},
                                    "lab": {"type": "boolean"},
                                },
                                "required": ["day", "duration"],
                            },
                            "description": "At least one meeting with valid weekday",
                        },
                        "start_time": {"type": "string", "description": "Optional fixed HH:MM"},
                        "disabled": {"type": "boolean", "description": "If true, pattern is disabled"},
                    },
                    "required": ["credits", "meetings"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_meeting_pattern",
                "description": "Update pattern at pattern_index (0-based). Only provided fields replace existing values.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern_index": {"type": "integer"},
                        "credits": {"type": "integer"},
                        "meetings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "day": {"type": "string"},
                                    "duration": {"type": "integer"},
                                    "lab": {"type": "boolean"},
                                },
                                "required": ["day", "duration"],
                            },
                        },
                        "start_time": {"type": "string"},
                        "disabled": {"type": "boolean"},
                    },
                    "required": ["pattern_index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_meeting_pattern",
                "description": "Remove meeting pattern at pattern_index (0-based), sync and save.",
                "parameters": {
                    "type": "object",
                    "properties": {"pattern_index": {"type": "integer"}},
                    "required": ["pattern_index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_config_summary_text",
                "description": "Return the same tabulated config summary text as the File > View Summary menu (no dialog).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "show_config_summary_dialog",
                "description": "Open the File > View Summary message box (interactive).",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "save_config_copy_as",
                "description": "Write the in-memory config JSON to a new file path (like Save Config As, but path is required).",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Destination .json path"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_schedule_session_info",
                "description": "How many schedules are loaded (generated/imported), and the current index used for export.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "set_current_schedule_index",
                "description": "Select which schedule is current (0-based) for export and for the 'all' viewer.",
                "parameters": {
                    "type": "object",
                    "properties": {"index": {"type": "integer"}},
                    "required": ["index"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_schedule_display_text",
                "description": "Tabular text for the current schedule (same format as Schedule Viewer for 'all').",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_schedule_viewer",
                "description": "Open the Schedule Viewer window (same as Viewer menu). mode=all shows spreadsheet with prev/next.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": ["all", "faculty", "room", "lab"],
                            "description": "Grouping: all=generated schedules; faculty/room/lab show config lists as JSON in the viewer.",
                        }
                    },
                    "required": ["mode"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_current_schedule_to_csv",
                "description": "Export the currently selected schedule to a CSV path (no file dialog).",
                "parameters": {
                    "type": "object",
                    "properties": {"csv_path": {"type": "string"}},
                    "required": ["csv_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "import_schedule_from_file",
                "description": "Import a schedule from CSV or JSON path into the app (no file dialog).",
                "parameters": {
                    "type": "object",
                    "properties": {"file_path": {"type": "string"}},
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_all_schedules_to_pdf",
                "description": (
                    "Export all loaded schedule options (same as Viewer Export Schedules PDF) to an absolute path; "
                    "no file dialog."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "Destination .pdf path (e.g. /tmp/schedules.pdf)",
                        }
                    },
                    "required": ["pdf_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_all_schedules_to_json",
                "description": (
                    "Export all loaded schedule options to one JSON file (same grid format as the menu export); "
                    "no file dialog."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "json_path": {
                            "type": "string",
                            "description": "Destination .json path",
                        }
                    },
                    "required": ["json_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "undo_configuration_change",
                "description": (
                    "Undo the last assistant-driven configuration change (reload, silent course save, etc.). "
                    "Does not affect schedule memory (generated/imported schedules)."
                ),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "redo_configuration_change",
                "description": "Redo after undo_configuration_change.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_native_gui",
                "description": (
                    "Open the same interactive dialogs as the menu bar (file pickers, add/modify forms, generator limit/optimize prompts, "
                    "Edit>Courses>Timeslots for class patterns and timeslots, Viewer>Clear Schedules). "
                    "Use when the user wants to click through the normal UI instead of silent tools."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "file_change_config",
                                "file_save_config",
                                "file_save_config_as",
                                "faculty_add",
                                "faculty_modify",
                                "faculty_delete",
                                "faculty_edit_times",
                                "faculty_edit_preferences",
                                "course_add",
                                "course_modify",
                                "course_delete",
                                "room_add",
                                "room_modify",
                                "room_delete",
                                "lab_add",
                                "lab_modify",
                                "lab_delete",
                                "generator_set_limit",
                                "generator_set_optimize",
                                "viewer_open_all",
                                "viewer_open_faculty",
                                "viewer_open_room",
                                "viewer_open_lab",
                                "viewer_export",
                                "viewer_import",
                                "viewer_clear_schedules",
                                "meeting_pattern_add",
                                "meeting_pattern_modify",
                                "meeting_pattern_delete",
                                "timeslot_add",
                                "timeslot_modify",
                                "timeslot_delete",
                            ],
                        }
                    },
                    "required": ["action"],
                },
            },
        },
    ]


def execute_tool(main_window: Any, name: str, arguments: Dict[str, Any]) -> str:
    try:
        return _execute_tool_impl(main_window, name, arguments)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})

def _execute_tool_impl(main_window: Any, name: str, arguments: Dict[str, Any]) -> str:
    cm = main_window.config_mgr
    
    if name not in _SKIP_ACTIVE_CONFIG_PATH and not getattr(cm, "filepath", None):
        return json.dumps({"ok": False, "error": "No active config file path."})

    def ok(msg: str, **extra: Any) -> str:
        return json.dumps({"ok": True, "message": msg, **extra})

    handlers = {
        "get_active_config_path": lambda: ok("Active config path.", path=getattr(cm, "filepath", None)),
        "get_config_summary_text": lambda: ok("Summary text.", summary=cm.get_summary_text() if cm else "No data."),
        "show_config_summary_dialog": lambda: (
            main_window.viewer_mgr.handle_view_summary(main_window),
            ok("Opened View Summary dialog."),
        )[1],
        "open_schedule_viewer": lambda: _handle_open_schedule_viewer(main_window, arguments, ok),
        "get_schedule_session_info": lambda: _handle_session_info(main_window, ok),
        "run_schedule_generation": lambda: (main_window.gen_manager.run_scheduler(main_window), ok("Started generation."))[1],
        "get_config_json": lambda: _handle_get_json(cm, ok),
        "reload_config_from_disk": lambda: _handle_reload(main_window, cm, ok),
        "save_config_to_disk": lambda: (_write_config_silent(main_window), ok(f"Saved to {cm.filepath}."))[1],
        "open_native_gui": lambda: _handle_native_gui(main_window, arguments, ok),
        "export_all_schedules_to_pdf": lambda: _export_all_schedules_pdf(main_window, arguments, ok),
        "export_all_schedules_to_json": lambda: _export_all_schedules_json(main_window, arguments, ok),
        "undo_configuration_change": lambda: _assistant_undo(main_window, ok),
        "redo_configuration_change": lambda: _assistant_redo(main_window, ok),
        "set_active_config_file": lambda: _tool_set_active_config_file(main_window, arguments, ok),
        "save_config_copy_as": lambda: _tool_save_config_copy_as(main_window, arguments, ok),
        "set_current_schedule_index": lambda: _tool_set_current_schedule_index(main_window, arguments, ok),
        "get_current_schedule_display_text": lambda: _tool_get_current_schedule_display_text(
            main_window, arguments, ok
        ),
        "export_current_schedule_to_csv": lambda: _tool_export_current_schedule_to_csv(
            main_window, arguments, ok
        ),
        "import_schedule_from_file": lambda: _tool_import_schedule_from_file(main_window, arguments, ok),
    }

    if name in handlers:
        return handlers[name]()

    return _execute_crud_operations(main_window, name, arguments, ok)

def _handle_session_info(mw, ok_fn):
    schedules = getattr(mw, "schedules", []) or []
    return ok_fn("Schedule session state.", 
                 schedule_count=len(schedules),
                 current_index=int(getattr(mw, "current_schedule_index", 0)),
                 has_schedules=len(schedules) > 0)

def _handle_get_json(cm, ok_fn):
    raw = json.dumps(cm.data, indent=2)
    return ok_fn("JSON.", json=raw if len(raw) <= 80000 else raw[:80000] + "... [truncated]")

def _handle_reload(mw, cm, ok_fn):
    mw.assistant_push_config_undo_snapshot()
    loaded = cm.load(mw)
    if loaded is None:
        return json.dumps(
            {"ok": False, "error": "Failed to reload config (missing file or invalid JSON)."}
        )
    if hasattr(mw, "cfg_panel") and hasattr(mw.cfg_panel, "update_title"):
        mw.cfg_panel.update_title(mw.cfg_panel, cm.filepath)
    elif hasattr(mw, "mid_panel") and hasattr(mw.mid_panel, "update_title"):
        mw.mid_panel.update_title(cm.filepath)
    _sync_config_inspector(mw)
    return ok_fn("Reloaded from disk.")


def _export_all_schedules_pdf(mw, args: Dict[str, Any], ok_fn):
    path = str(args.get("pdf_path", "")).strip()
    if not path:
        return json.dumps({"ok": False, "error": "pdf_path is required."})
    path = os.path.abspath(os.path.expanduser(path))
    if not path.lower().endswith(".pdf"):
        path = path + ".pdf"
    schedules = getattr(mw, "schedules", []) or []
    if not schedules:
        return json.dumps({"ok": False, "error": "No schedules loaded."})
    try:
        mw.config_mgr._write_schedules_pdf(path, schedules)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})
    return ok_fn(f"Exported {len(schedules)} schedule option(s) to PDF.", path=path)


def _export_all_schedules_json(mw, args: Dict[str, Any], ok_fn):
    path = str(args.get("json_path", "")).strip()
    if not path:
        return json.dumps({"ok": False, "error": "json_path is required."})
    path = os.path.abspath(os.path.expanduser(path))
    if not path.lower().endswith(".json"):
        path = path + ".json"
    schedules = getattr(mw, "schedules", []) or []
    if not schedules:
        return json.dumps({"ok": False, "error": "No schedules loaded."})
    try:
        mw.config_mgr.write_schedules_json_file(path, schedules)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})
    return ok_fn(f"Exported {len(schedules)} schedule option(s) to JSON.", path=path)


def _assistant_undo(mw, ok_fn):
    if not mw.assistant_undo_config_change():
        return json.dumps(
            {
                "ok": False,
                "error": "Nothing to undo (stack holds assistant-driven config changes only).",
            }
        )
    return ok_fn("Undid the last assistant configuration change.")


def _assistant_redo(mw, ok_fn):
    if not mw.assistant_redo_config_change():
        return json.dumps({"ok": False, "error": "Nothing to redo."})
    return ok_fn("Redid the last undone configuration change.")


def _assistant_sync_time_slots(cm: Any) -> None:
    from timeslot_config.time_slot_editor import TimeSlotEditor

    TimeSlotEditor(cm)._sync_time_slot_config()


def _assistant_sync_meeting_classes(cm: Any) -> None:
    from timeslot_config.meeting_pattern_editor import MeetingPatternEditor

    MeetingPatternEditor(cm)._sync_time_slot_config_classes()


def _generate_slot_strings(start_time: str, end_time: str, spacing: int) -> List[str]:
    slots: List[str] = []
    try:
        current = datetime.strptime(str(start_time).strip(), "%H:%M")
        end = datetime.strptime(str(end_time).strip(), "%H:%M")
    except ValueError:
        return []
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=int(spacing))
    return slots


def _format_schedule_grid_text(cm: Any, schedule: List[Dict[str, Any]]) -> str:
    days, times, grid, _spans = cm.get_schedule_grid_data(schedule, filter_type="all")
    lines = ["\t".join([""] + list(days))]
    for i, t in enumerate(times):
        row_cells = [str(t)] + [str(grid[i][j]).replace("\n", " / ") for j in range(len(days))]
        lines.append("\t".join(row_cells))
    return "\n".join(lines)


def _tool_set_active_config_file(mw: Any, args: Dict[str, Any], ok) -> str:
    path = os.path.abspath(os.path.expanduser(str(args.get("path", "")).strip()))
    if not path.lower().endswith(".json"):
        return json.dumps({"ok": False, "error": "path must be a .json file."})
    if not os.path.isfile(path):
        return json.dumps({"ok": False, "error": f"File not found: {path}"})
    if hasattr(mw, "assistant_push_config_undo_snapshot"):
        mw.assistant_push_config_undo_snapshot()
    mw.config_mgr.filepath = path
    loaded = mw.config_mgr.load(mw)
    if loaded is None:
        return json.dumps({"ok": False, "error": "Failed to load JSON from path."})
    if hasattr(mw, "cfg_panel") and hasattr(mw.cfg_panel, "update_title"):
        mw.cfg_panel.update_title(mw.cfg_panel, mw.config_mgr.filepath)
    _sync_config_inspector(mw)
    return ok(f"Switched active config to {path}.", path=path)


def _tool_save_config_copy_as(mw: Any, args: Dict[str, Any], ok) -> str:
    path = os.path.abspath(os.path.expanduser(str(args.get("path", "")).strip()))
    if not path:
        return json.dumps({"ok": False, "error": "path is required."})
    if not path.lower().endswith(".json"):
        path = path + ".json"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mw.config_mgr.data, f, indent=4)
    except OSError as e:
        return json.dumps({"ok": False, "error": str(e)})
    return ok(f"Wrote config copy to {path}.", path=path)


def _tool_set_current_schedule_index(mw: Any, args: Dict[str, Any], ok) -> str:
    schedules = getattr(mw, "schedules", None) or []
    try:
        idx = int(args["index"])
    except (KeyError, TypeError, ValueError):
        return json.dumps({"ok": False, "error": "index must be an integer."})
    if not schedules:
        return json.dumps({"ok": False, "error": "No schedules loaded."})
    if idx < 0 or idx >= len(schedules):
        return json.dumps(
            {"ok": False, "error": f"index out of range (0..{len(schedules) - 1})."}
        )
    mw.current_schedule_index = idx
    return ok(f"Current schedule index set to {idx}.", index=idx)


def _tool_get_current_schedule_display_text(mw: Any, args: Dict[str, Any], ok) -> str:
    schedules = getattr(mw, "schedules", None) or []
    idx = int(getattr(mw, "current_schedule_index", 0))
    if not schedules or idx < 0 or idx >= len(schedules):
        return json.dumps({"ok": False, "error": "No current schedule to display."})
    text = _format_schedule_grid_text(mw.config_mgr, schedules[idx])
    return ok("Schedule grid text (tab-separated).", text=text)


def _tool_export_current_schedule_to_csv(mw: Any, args: Dict[str, Any], ok) -> str:
    path = os.path.abspath(os.path.expanduser(str(args.get("csv_path", "")).strip()))
    if not path:
        return json.dumps({"ok": False, "error": "csv_path is required."})
    if not path.lower().endswith(".csv"):
        path = path + ".csv"
    schedules = getattr(mw, "schedules", None) or []
    idx = int(getattr(mw, "current_schedule_index", 0))
    if not schedules or idx < 0 or idx >= len(schedules):
        return json.dumps({"ok": False, "error": "No current schedule to export."})
    rows = schedules[idx]
    if not rows:
        return json.dumps({"ok": False, "error": "Current schedule is empty."})
    fieldnames: List[str] = []
    for row in rows:
        if isinstance(row, dict):
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(str(k))
    if not fieldnames:
        fieldnames = ["course_id", "day", "time", "faculty", "room", "lab"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        if isinstance(row, dict):
            flat = {k: json.dumps(row[k]) if isinstance(row[k], (list, dict)) else row[k] for k in fieldnames}
            w.writerow(flat)
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue())
    except OSError as e:
        return json.dumps({"ok": False, "error": str(e)})
    return ok(f"Exported current schedule to {path}.", path=path)


def _tool_import_schedule_from_file(mw: Any, args: Dict[str, Any], ok) -> str:
    path = os.path.abspath(os.path.expanduser(str(args.get("file_path", "")).strip()))
    if not path or not os.path.isfile(path):
        return json.dumps({"ok": False, "error": "file_path must exist."})
    low = path.lower()
    if not low.endswith(".json"):
        return json.dumps({"ok": False, "error": "Only .json schedule import is supported."})
    data = mw.config_mgr.import_schedule_from_json(filename=path, parent=None)
    if not data:
        return json.dumps({"ok": False, "error": "Import failed or file was empty/invalid."})
    mw.schedules = data
    mw.current_schedule_index = 0
    if hasattr(mw, "viewer_mgr"):
        mw.viewer_mgr.update_schedule_display(mw, "all")
    if hasattr(mw, "cfg_panel") and hasattr(mw.cfg_panel, "update_title"):
        mw.cfg_panel.update_title(mw.cfg_panel, getattr(mw.config_mgr, "import_file", None))
    return ok(f"Imported {len(data)} schedule option(s).", count=len(data))


def _invoke_native_action(fn: Callable[..., Any], mw: Any) -> None:
    """Call a zero-arg lambda or a manager method that expects ``parent`` as its only argument."""
    if fn is None or not callable(fn):
        return
    try:
        sig = inspect.signature(fn)
        skip = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        param_count = len([p for p in sig.parameters.values() if p.kind not in skip])
    except (TypeError, ValueError):
        param_count = 1
    if param_count == 0:
        fn()
    else:
        fn(mw)


def _handle_open_schedule_viewer(mw, args: Dict[str, Any], ok_fn):
    mode = str(args.get("mode", "all"))
    if mode not in ("all", "faculty", "room", "lab"):
        return json.dumps({"ok": False, "error": f"Invalid mode: {mode!r}."})
    mw.viewer_mgr.update_schedule_display(mw, mode)
    return ok_fn(f"Updated schedule viewer ({mode}).")


def _handle_native_gui(mw, args, ok_fn):
    action = str(args["action"])
    dispatch = {
        "file_change_config": lambda: mw.viewer_mgr.handle_change_path(mw),
        "file_save_config": lambda: mw.config_mgr.save(mw),
        "file_save_config_as": lambda: mw.viewer_mgr.save_as(mw),
        "faculty_add": mw.faculty_manager.add_faculty_via_dialog,
        "faculty_modify": mw.faculty_manager.modify_faculty_via_dialog,
        "faculty_delete": mw.faculty_manager.delete_faculty_via_dialog,
        "faculty_edit_times": mw.faculty_manager.modify_faculty_via_dialog,
        "faculty_edit_preferences": mw.faculty_manager.modify_faculty_via_dialog,
        "course_add": mw.course_manager.add_course_via_dialog,
        "course_modify": mw.course_manager.modify_course_via_dialog,
        "course_delete": mw.course_manager.delete_course_via_dialog,
        "room_add": mw.room_manager.add_room_via_dialog,
        "room_modify": mw.room_manager.modify_room_via_dialog,
        "room_delete": mw.room_manager.delete_room_via_dialog,
        "lab_add": mw.lab_manager.add_lab_via_dialog,
        "lab_modify": mw.lab_manager.modify_lab_via_dialog,
        "lab_delete": mw.lab_manager.delete_lab_via_dialog,
        "generator_set_limit": mw.gen_manager.set_limit,
        "generator_set_optimize": mw.gen_manager.set_optimize,
        "viewer_open_all": lambda: mw.viewer_mgr.update_schedule_display(mw, "all"),
        "viewer_open_faculty": lambda: mw.viewer_mgr.update_schedule_display(mw, "faculty"),
        "viewer_open_room": lambda: mw.viewer_mgr.update_schedule_display(mw, "room"),
        "viewer_open_lab": lambda: mw.viewer_mgr.update_schedule_display(mw, "lab"),
        "viewer_export": lambda: mw.viewer_mgr.handle_export_schedule(mw),
        "viewer_import": lambda: mw.viewer_mgr.handle_import_schedule(mw),
        "viewer_clear_schedules": lambda: mw.viewer_mgr.handle_clear_schedule(mw),
        "meeting_pattern_add": mw.meeting_pattern_editor.add_meeting_pattern,
        "meeting_pattern_modify": mw.meeting_pattern_editor.modify_meeting_pattern,
        "meeting_pattern_delete": mw.meeting_pattern_editor.delete_meeting_pattern,
        "timeslot_add": mw.time_slot_editor.add_time_slot,
        "timeslot_modify": mw.time_slot_editor.modify_time_slot,
        "timeslot_delete": mw.time_slot_editor.delete_time_slot,
    }
    fn = dispatch.get(action)
    if not fn:
        return json.dumps({"ok": False, "error": f"Action {action} not mapped."})
    _invoke_native_action(fn, mw)
    return ok_fn(f"Launched {action}.")

def _execute_crud_operations(mw, name, args, ok):
    """Silent JSON config mutations and list tools (schemas must match ``get_tool_schemas``)."""
    cm = mw.config_mgr
    cfg = _ensure_config_block(mw)
    rooms: List[Any] = cfg.setdefault("rooms", [])
    labs: List[Any] = cfg.setdefault("labs", [])
    faculty: List[Any] = cfg.setdefault("faculty", [])
    courses: List[Any] = cfg.setdefault("courses", [])

    def _rooms_cf() -> Dict[str, int]:
        return {str(r).casefold(): i for i, r in enumerate(rooms)}

    def _labs_cf() -> Dict[str, int]:
        return {str(r).casefold(): i for i, r in enumerate(labs)}

    # --- Rooms / labs ---
    if name == "add_room":
        rname = str(args.get("room_name", "")).strip()
        if not rname:
            return json.dumps({"ok": False, "error": "room_name is required."})
        if any(str(r).casefold() == rname.casefold() for r in rooms):
            return json.dumps({"ok": False, "error": f"Room {rname!r} already exists."})
        rooms.append(rname)
        _write_config_silent(mw)
        return ok(f"Added room {rname!r}.", rooms=list(rooms))

    if name == "remove_room":
        rname = str(args.get("room_name", "")).strip()
        m = _rooms_cf()
        if rname.casefold() not in m:
            return json.dumps({"ok": False, "error": f"Room {rname!r} not found."})
        rooms.pop(m[rname.casefold()])
        _write_config_silent(mw)
        return ok(f"Removed room {rname!r}.", rooms=list(rooms))

    if name == "rename_room":
        old_n, new_n = str(args.get("old_name", "")).strip(), str(args.get("new_name", "")).strip()
        if not old_n or not new_n:
            return json.dumps({"ok": False, "error": "old_name and new_name are required."})
        try:
            idx = next(i for i, r in enumerate(rooms) if str(r) == old_n)
        except StopIteration:
            return json.dumps({"ok": False, "error": f"Room {old_n!r} not found (exact match)."})
        if any(str(r).casefold() == new_n.casefold() and i != idx for i, r in enumerate(rooms)):
            return json.dumps({"ok": False, "error": f"Room {new_n!r} already exists."})
        rooms[idx] = new_n
        _write_config_silent(mw)
        return ok(f"Renamed room {old_n!r} -> {new_n!r}.", rooms=list(rooms))

    if name == "add_lab":
        lname = str(args.get("lab_name", "")).strip()
        if not lname:
            return json.dumps({"ok": False, "error": "lab_name is required."})
        if any(str(x).casefold() == lname.casefold() for x in labs):
            return json.dumps({"ok": False, "error": f"Lab {lname!r} already exists."})
        labs.append(lname)
        _write_config_silent(mw)
        return ok(f"Added lab {lname!r}.", labs=list(labs))

    if name == "remove_lab":
        lname = str(args.get("lab_name", "")).strip()
        m = _labs_cf()
        if lname.casefold() not in m:
            return json.dumps({"ok": False, "error": f"Lab {lname!r} not found."})
        labs.pop(m[lname.casefold()])
        _write_config_silent(mw)
        return ok(f"Removed lab {lname!r}.", labs=list(labs))

    if name == "rename_lab":
        old_n, new_n = str(args.get("old_name", "")).strip(), str(args.get("new_name", "")).strip()
        if not old_n or not new_n:
            return json.dumps({"ok": False, "error": "old_name and new_name are required."})
        try:
            idx = next(i for i, x in enumerate(labs) if str(x) == old_n)
        except StopIteration:
            return json.dumps({"ok": False, "error": f"Lab {old_n!r} not found (exact match)."})
        if any(str(x).casefold() == new_n.casefold() and i != idx for i, x in enumerate(labs)):
            return json.dumps({"ok": False, "error": f"Lab {new_n!r} already exists."})
        labs[idx] = new_n
        _write_config_silent(mw)
        return ok(f"Renamed lab {old_n!r} -> {new_n!r}.", labs=list(labs))

    if name == "list_rooms":
        return ok("Rooms.", rooms=list(rooms))
    if name == "list_labs":
        return ok("Labs.", labs=list(labs))
    if name == "list_faculty":
        return ok("Faculty.", faculty=[_faculty_display_name(f) for f in faculty])
    if name == "list_course_ids":
        return ok(
            "Course ids.",
            course_ids=[str(c.get("course_id", "")) for c in courses if isinstance(c, dict)],
        )

    # --- Faculty ---
    if name == "add_faculty":
        fname = str(args.get("name", "")).strip()
        if not fname:
            return json.dumps({"ok": False, "error": "name is required."})
        if any(_faculty_display_name(f).casefold() == fname.casefold() for f in faculty):
            return json.dumps({"ok": False, "error": f"Faculty {fname!r} already exists."})
        faculty.append(fname)
        _write_config_silent(mw)
        return ok(f"Added faculty {fname!r}.")

    if name == "remove_faculty":
        fname = str(args.get("name", "")).strip()
        idx = _faculty_match_index(faculty, fname)
        if idx is None:
            return json.dumps({"ok": False, "error": f"Faculty {fname!r} not found."})
        faculty.pop(idx)
        _write_config_silent(mw)
        return ok(f"Removed faculty matching {fname!r}.")

    if name == "rename_faculty":
        old_n, new_n = str(args.get("old_name", "")).strip(), str(args.get("new_name", "")).strip()
        idx = _faculty_match_index(faculty, old_n)
        if idx is None:
            return json.dumps({"ok": False, "error": f"Faculty {old_n!r} not found."})
        entry = faculty[idx]
        if isinstance(entry, dict):
            entry["name"] = new_n
        else:
            faculty[idx] = {"name": new_n}
        _write_config_silent(mw)
        return ok(f"Renamed faculty {old_n!r} -> {new_n!r}.")

    if name == "merge_faculty_object":
        fname = str(args.get("faculty_name", "")).strip()
        idx = _faculty_match_index(faculty, fname)
        if idx is None:
            return json.dumps({"ok": False, "error": f"Faculty {fname!r} not found."})
        try:
            merge = json.loads(str(args.get("merge_json", "{}")))
        except json.JSONDecodeError as e:
            return json.dumps({"ok": False, "error": f"Invalid merge_json: {e}"})
        if not isinstance(merge, dict):
            return json.dumps({"ok": False, "error": "merge_json must be a JSON object."})
        entry = faculty[idx]
        if isinstance(entry, str):
            entry = {"name": entry}
            faculty[idx] = entry
        entry.update(merge)
        _write_config_silent(mw)
        return ok(f"Merged fields into faculty matching {fname!r}.", faculty_entry=entry)

    # --- Courses ---
    if name == "add_course":
        cid = str(args.get("course_id", "")).strip()
        if not cid:
            return json.dumps({"ok": False, "error": "course_id is required."})
        try:
            cred = int(args["credits"])
        except (KeyError, TypeError, ValueError):
            return json.dumps({"ok": False, "error": "credits must be an integer."})
        new_c: Dict[str, Any] = {
            "course_id": cid,
            "credits": cred,
            "room": list(args.get("rooms", []) or []),
            "lab": list(args.get("labs", []) or []),
            "conflicts": list(args.get("conflicts", []) or []),
            "faculty": list(args.get("faculty", []) or []),
        }
        courses.append(new_c)
        _write_config_silent(mw)
        return ok(f"Added course {cid}.", course=new_c)

    if name == "update_course":
        cid = str(args["course_id"])
        for c in courses:
            if isinstance(c, dict) and str(c.get("course_id")) == cid:
                if "rooms" in args:
                    c["room"] = list(args["rooms"])
                if "labs" in args:
                    c["lab"] = list(args["labs"])
                if "credits" in args:
                    c["credits"] = int(args["credits"])
                if "faculty" in args:
                    c["faculty"] = list(args["faculty"])
                if "conflicts" in args:
                    c["conflicts"] = list(args["conflicts"])
                _write_config_silent(mw)
                return ok(f"Updated course {cid}.", course=c)
        return json.dumps({"ok": False, "error": f"Course {cid} not found."})

    if name == "delete_course":
        cid = str(args["course_id"])
        for i, c in enumerate(courses):
            if isinstance(c, dict) and str(c.get("course_id")) == cid:
                del courses[i]
                _write_config_silent(mw)
                return ok(f"Deleted course {cid}.")
        return json.dumps({"ok": False, "error": f"Course {cid} not found."})

    # --- Root-level generator settings ---
    if name == "set_schedule_limit":
        try:
            lim = int(args["limit"])
        except (KeyError, TypeError, ValueError):
            return json.dumps({"ok": False, "error": "limit must be an integer."})
        if lim < 1:
            return json.dumps({"ok": False, "error": "limit must be >= 1."})
        cm.data["limit"] = lim
        _write_config_silent(mw)
        return ok(f"Set schedule limit to {lim}.", limit=lim)

    if name == "set_optimizer_enabled":
        try:
            en = bool(args["enabled"])
        except (KeyError, TypeError, ValueError):
            return json.dumps({"ok": False, "error": "enabled must be a boolean."})
        cm.data["optimizer_flags"] = list(DEFAULT_OPTIMIZER_FLAGS) if en else []
        _write_config_silent(mw)
        return ok(
            "Optimizer flags updated.",
            optimizer_flags=list(cm.data.get("optimizer_flags", [])),
        )

    # --- Timeslots (config.time_slots + sync to time_slot_config.times) ---
    if name == "list_timeslots":
        from timeslot_config.time_slot_editor import TimeSlotEditor

        editor = TimeSlotEditor(cm)
        ts = editor._get_timeslots()
        sched_times = cm.data.get("time_slot_config", {}).get("times", {})
        return ok("Time slots.", time_slots=ts, scheduler_times=sched_times)

    if name in ("add_timeslot_block", "update_timeslot_block", "remove_timeslot_block", "set_timeslot_day_enabled"):
        from timeslot_config.time_slot_editor import TimeSlotEditor

        editor = TimeSlotEditor(cm)
        dmap = TimeSlotEditor.DAY_MAP
        rev = {v: k for k, v in dmap.items()}
        day_long = _normalize_weekday_for_editor(str(args.get("day", "")), dmap, rev)
        if not day_long:
            return json.dumps({"ok": False, "error": "Invalid or missing weekday in day."})
        ts = editor._get_timeslots()
        if name == "set_timeslot_day_enabled":
            try:
                en = bool(args["enabled"])
            except (KeyError, TypeError, ValueError):
                return json.dumps({"ok": False, "error": "enabled must be a boolean."})
            if day_long not in ts:
                ts[day_long] = {"enabled": en, "blocks": []}
            else:
                ts[day_long]["enabled"] = en
            cfg["time_slots"] = ts
            _assistant_sync_time_slots(cm)
            _write_config_silent(mw)
            return ok(f"Set {day_long} enabled={en}.", time_slots=ts)

        if day_long not in ts:
            ts[day_long] = {"enabled": True, "blocks": []}
        blocks = ts[day_long].setdefault("blocks", [])

        if name == "add_timeslot_block":
            st, et = str(args.get("start_time", "")).strip(), str(args.get("end_time", "")).strip()
            try:
                sp = int(args["spacing_minutes"])
            except (KeyError, TypeError, ValueError):
                return json.dumps({"ok": False, "error": "spacing_minutes must be an integer."})
            if not _parse_hhmm(st) or not _parse_hhmm(et):
                return json.dumps({"ok": False, "error": "start_time and end_time must be HH:MM."})
            slot_list = _generate_slot_strings(st, et, sp)
            if not slot_list:
                return json.dumps({"ok": False, "error": "No slots generated (check times and spacing)."})
            blocks.append(
                {"start_time": st, "end_time": et, "spacing_minutes": sp, "slots": slot_list}
            )
            cfg["time_slots"] = ts
            _assistant_sync_time_slots(cm)
            _write_config_silent(mw)
            return ok(f"Added timeslot block on {day_long}.", time_slots=ts)

        try:
            bi = int(args["block_index"])
        except (KeyError, TypeError, ValueError):
            return json.dumps({"ok": False, "error": "block_index must be an integer."})
        if bi < 0 or bi >= len(blocks):
            return json.dumps({"ok": False, "error": "block_index out of range."})

        if name == "remove_timeslot_block":
            blocks.pop(bi)
            if not blocks:
                ts.pop(day_long, None)
            cfg["time_slots"] = ts
            _assistant_sync_time_slots(cm)
            _write_config_silent(mw)
            return ok(f"Removed block {bi} on {day_long}.", time_slots=ts)

        # update_timeslot_block
        blk = blocks[bi]
        if "start_time" in args and str(args["start_time"]).strip():
            blk["start_time"] = str(args["start_time"]).strip()
        if "end_time" in args and str(args["end_time"]).strip():
            blk["end_time"] = str(args["end_time"]).strip()
        if "spacing_minutes" in args:
            blk["spacing_minutes"] = int(args["spacing_minutes"])
        st = str(blk.get("start_time", "08:00"))
        et = str(blk.get("end_time", "17:00"))
        sp = int(blk.get("spacing_minutes", 60))
        blk["slots"] = _generate_slot_strings(st, et, sp)
        cfg["time_slots"] = ts
        _assistant_sync_time_slots(cm)
        _write_config_silent(mw)
        return ok(f"Updated block {bi} on {day_long}.", time_slots=ts)

    # --- Meeting patterns ---
    if name == "list_meeting_patterns":
        from timeslot_config.meeting_pattern_editor import MeetingPatternEditor

        patterns = MeetingPatternEditor(cm)._get_patterns()
        return ok("Meeting patterns.", meeting_patterns=patterns)

    if name in ("add_meeting_pattern", "update_meeting_pattern", "delete_meeting_pattern"):
        from timeslot_config.meeting_pattern_editor import MeetingPatternEditor

        editor = MeetingPatternEditor(cm)
        dmap = MeetingPatternEditor.DAY_MAP
        rev = {v: k for k, v in dmap.items()}
        pat = editor._get_patterns()

        if name == "delete_meeting_pattern":
            try:
                pi = int(args["pattern_index"])
            except (KeyError, TypeError, ValueError):
                return json.dumps({"ok": False, "error": "pattern_index must be an integer."})
            if pi < 0 or pi >= len(pat):
                return json.dumps({"ok": False, "error": "pattern_index out of range."})
            pat.pop(pi)
            cfg["meeting_patterns"] = pat
            _assistant_sync_meeting_classes(cm)
            _write_config_silent(mw)
            return ok("Deleted meeting pattern.", meeting_patterns=pat)

        if name == "add_meeting_pattern":
            meetings, err = _normalize_meeting_entries(args.get("meetings", []), dmap, rev)
            if err or not meetings:
                return json.dumps({"ok": False, "error": err or "meetings required."})
            try:
                cred = int(args["credits"])
            except (KeyError, TypeError, ValueError):
                return json.dumps({"ok": False, "error": "credits must be an integer."})
            new_p = {
                "credits": cred,
                "meetings": meetings,
                "start_time": str(args.get("start_time", "") or ""),
                "disabled": bool(args.get("disabled", False)),
            }
            pat.append(new_p)
            cfg["meeting_patterns"] = pat
            _assistant_sync_meeting_classes(cm)
            _write_config_silent(mw)
            return ok("Added meeting pattern.", meeting_patterns=pat)

        # update_meeting_pattern
        try:
            pi = int(args["pattern_index"])
        except (KeyError, TypeError, ValueError):
            return json.dumps({"ok": False, "error": "pattern_index must be an integer."})
        if pi < 0 or pi >= len(pat):
            return json.dumps({"ok": False, "error": "pattern_index out of range."})
        cur = pat[pi]
        if "credits" in args:
            cur["credits"] = int(args["credits"])
        if "start_time" in args:
            cur["start_time"] = str(args.get("start_time") or "")
        if "disabled" in args:
            cur["disabled"] = bool(args["disabled"])
        if "meetings" in args:
            meetings, err = _normalize_meeting_entries(args["meetings"], dmap, rev)
            if err:
                return json.dumps({"ok": False, "error": err})
            cur["meetings"] = meetings
        cfg["meeting_patterns"] = pat
        _assistant_sync_meeting_classes(cm)
        _write_config_silent(mw)
        return ok("Updated meeting pattern.", pattern=cur)

    return json.dumps({"ok": False, "error": f"Unknown tool: {name}"})

def default_api_key() -> str:
    """API key: OPENAI_API_KEY_IN_CODE, then config/openai_key.txt, then OPENAI_API_KEY env."""
    inline = (OPENAI_API_KEY_IN_CODE or "").strip()
    if inline:
        return inline
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        key_path = os.path.join(root, "config", "openai_key.txt")
        if os.path.isfile(key_path):
            with open(key_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("sk-your-key"):
                        return line.strip()
    except OSError:
        pass
    return os.environ.get("OPENAI_API_KEY", "").strip()


class AssistantChatWorker(QThread):
    """Runs OpenAI chat + tool loops in a background thread; tool execution happens on the GUI thread."""

    finished_reply = pyqtSignal(str)
    failed = pyqtSignal(str)
    need_tools = pyqtSignal(list)

    def __init__(
        self,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> None:
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.messages = messages
        self.out_messages: List[Dict[str, Any]] = []
        self._done = threading.Event()
        self._tool_results: List[Dict[str, str]] = []

    def deliver_tool_results(self, results: List[Dict[str, str]]) -> None:
        self._tool_results = results
        self._done.set()

    def run(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            self.failed.emit(f"OpenAI package not installed: {e}")
            return

        client = OpenAI(api_key=self.api_key)
        tools = get_tool_schemas()

        try:
            while True:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=tools,
                    tool_choice="auto",
                )
                choice = response.choices[0]
                msg = choice.message
                if msg.tool_calls:
                    assistant_msg: Dict[str, Any] = {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "{}",
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                    self.messages.append(assistant_msg)

                    serializable = [
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        }
                        for tc in msg.tool_calls
                    ]
                    self._done.clear()
                    self._tool_results = []
                    self.need_tools.emit(serializable)
                    if not self._done.wait(timeout=180):
                        self.failed.emit("Timed out waiting for tool execution.")
                        return

                    for tr in self._tool_results:
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tr["id"],
                                "content": tr["content"],
                            }
                        )
                    continue

                text = (msg.content or "").strip() or "(No text reply.)"
                self.messages.append({"role": "assistant", "content": text})
                self.out_messages = copy.deepcopy(self.messages)
                self.finished_reply.emit(text)
                return
        except Exception as exc:
            self.failed.emit(str(exc))
