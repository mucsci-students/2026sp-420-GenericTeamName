'''
    File: ai_assistant.py
    Date: 4/17/26
    Author: Shane del Villar & Kyle Smith
    Description: OpenAI tool-calling assistant that mutates the active scheduler config
    and triggers GUI actions (e.g. add rooms, courses, run generation).
'''

from __future__ import annotations

import copy
import json
import os
import threading
from typing import Any, Dict, List, Optional

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
import_schedule_from_file loads CSV or JSON into the schedule list.
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
        "import_schedule_from_file",
        "get_config_summary_text",
        "show_config_summary_dialog",
    }
)


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
        "show_config_summary_dialog": lambda: (main_window.handle_view_summary(), ok("Opened View Summary dialog."))[1],
        "get_schedule_session_info": lambda: _handle_session_info(main_window, ok),
        "run_schedule_generation": lambda: (main_window.gen_manager.run_scheduler(main_window), ok("Started generation."))[1],
        "get_config_json": lambda: _handle_get_json(cm, ok),
        "reload_config_from_disk": lambda: _handle_reload(main_window, cm, ok),
        "save_config_to_disk": lambda: (_write_config_silent(main_window), ok(f"Saved to {cm.filepath}."))[1],
        "open_native_gui": lambda: _handle_native_gui(main_window, arguments, ok),
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
    cm.load()
    if hasattr(mw, "mid_panel"): mw.mid_panel.update_title(cm.filepath)
    return ok_fn("Reloaded.")

def _handle_native_gui(mw, args, ok_fn):
    action = str(args["action"])
    dispatch = {
        "faculty_add": mw.faculty_manager.add_faculty_via_dialog,
        "faculty_modify": mw.faculty_manager.modify_faculty_via_dialog,
        "course_add": mw.course_manager.add_course_via_dialog,
        "course_modify": mw.course_manager.modify_course_via_dialog,
        "course_delete": mw.course_manager.delete_course_via_dialog,
        "room_add": mw.room_manager.add_room_via_dialog,
        "file_save_config": lambda: mw.config_mgr.save(mw),
        "viewer_open_all": lambda: mw.open_schedule_viewer("all"),
    }
    fn = dispatch.get(action)
    if not fn: return json.dumps({"ok": False, "error": f"Action {action} not mapped."})
    fn(mw) if callable(fn) else None
    return ok_fn(f"Launched {action}.")

def _execute_crud_operations(mw, name, args, ok):
    cfg = _ensure_config_block(mw)
    courses = cfg.get("courses", [])

    if name == "update_course":
        cid = str(args["course_id"])
        for c in courses:
            if isinstance(c, dict) and str(c.get("course_id")) == cid:
                if "rooms" in args: c["room"] = list(args["rooms"])
                if "credits" in args: c["credits"] = int(args["credits"])
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

    if name == "list_rooms": return ok("Rooms.", rooms=list(cfg.get("rooms", [])))
    
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
