'''
    File: ai_assistant.py
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
        payload = {"ok": True, "message": msg}
        payload.update(extra)
        return json.dumps(payload)

    if name == "get_active_config_path":
        p = getattr(cm, "filepath", None) if cm is not None else None
        return ok("Active config path (may be unset).", path=p or None)

    if name == "get_config_summary_text":
        text = cm.get_summary_text() if cm else "No data."
        return ok("Summary text.", summary=text)

    if name == "show_config_summary_dialog":
        main_window.handle_view_summary()
        return ok("Opened View Summary dialog.")

    if name == "save_config_copy_as":
        path = os.path.expanduser(str(arguments["path"]))
        try:
            parent = os.path.dirname(path) or "."
            os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cm.data, f, indent=4)
        except OSError as e:
            return json.dumps({"ok": False, "error": str(e)})
        return ok(f"Wrote config copy to {path}.")

    if name == "get_schedule_session_info":
        schedules = getattr(main_window, "schedules", []) or []
        idx = int(getattr(main_window, "current_schedule_index", 0))
        return ok(
            "Schedule session state.",
            schedule_count=len(schedules),
            current_index=idx,
            has_schedules=len(schedules) > 0,
        )

    if name == "set_current_schedule_index":
        schedules = getattr(main_window, "schedules", []) or []
        idx = int(arguments["index"])
        if not schedules:
            return json.dumps({"ok": False, "error": "No schedules loaded."})
        if idx < 0 or idx >= len(schedules):
            return json.dumps(
                {"ok": False, "error": f"Index out of range (0..{len(schedules) - 1})."}
            )
        main_window.current_schedule_index = idx
        return ok(f"Current schedule index set to {idx}.")

    if name == "get_current_schedule_display_text":
        schedules = getattr(main_window, "schedules", []) or []
        idx = int(getattr(main_window, "current_schedule_index", 0))
        if not schedules or not (0 <= idx < len(schedules)):
            return json.dumps({"ok": False, "error": "No current schedule to display."})
        schedule = schedules[idx]
        schedule_data = schedule if isinstance(schedule, list) and schedule else []
        if schedule_data and isinstance(schedule_data[0], dict):
            text = cm.get_schedule_spreadsheet(schedule_data)
        else:
            text = str(schedule)
        return ok("Current schedule as tabular text.", text=text, index=idx)

    if name == "open_schedule_viewer":
        mode = str(arguments.get("mode", "all")).lower()
        if mode not in ("all", "faculty", "room", "lab"):
            return json.dumps({"ok": False, "error": f"Invalid mode: {mode!r}"})
        main_window.open_schedule_viewer(mode)
        return ok(f"Opened schedule viewer ({mode}).")

    if name == "export_current_schedule_to_csv":
        schedules = getattr(main_window, "schedules", []) or []
        idx = int(getattr(main_window, "current_schedule_index", 0))
        if not schedules or not (0 <= idx < len(schedules)):
            return json.dumps({"ok": False, "error": "No schedule to export."})
        schedule = schedules[idx]
        if not schedule or not isinstance(schedule, list):
            return json.dumps({"ok": False, "error": "Current schedule is empty or invalid."})
        path = os.path.expanduser(str(arguments["csv_path"]))
        if not path.lower().endswith(".csv"):
            path += ".csv"
        success = cm.export_schedule_to_csv(schedule, path)
        if success:
            return ok(f"Exported schedule #{idx} to {path}.", path=path)
        return json.dumps({"ok": False, "error": f"Failed to write {path}."})

    if name == "import_schedule_from_file":
        path = os.path.expanduser(str(arguments["file_path"]))
        if not os.path.isfile(path):
            return json.dumps({"ok": False, "error": f"File not found: {path}"})
        if path.lower().endswith(".json"):
            schedule_data = cm.import_schedule_from_json(path)
        else:
            schedule_data = cm.import_schedule_from_csv(path)
        if schedule_data is None:
            return json.dumps({"ok": False, "error": "Could not read a valid schedule from file."})
        main_window.imported_schedule = schedule_data
        main_window.schedules.append(schedule_data)
        main_window.current_schedule_index = len(main_window.schedules) - 1
        return ok(
            f"Imported {len(schedule_data)} assignment(s) from {path}.",
            assignments=len(schedule_data),
            current_index=main_window.current_schedule_index,
        )

    if name == "open_native_gui":
        action = str(arguments["action"])
        dispatch = {
            "file_change_config": lambda: main_window.handle_change_path(),
            "file_save_config": lambda: main_window.config_mgr.save(main_window),
            "file_save_config_as": lambda: main_window.save_config_to_file(),
            "faculty_add": lambda: main_window.faculty_manager.add_faculty_via_dialog(main_window),
            "faculty_modify": lambda: main_window.faculty_manager.modify_faculty_via_dialog(main_window),
            "faculty_delete": lambda: main_window.faculty_manager.delete_faculty_via_dialog(main_window),
            "faculty_edit_times": lambda: main_window.faculty_manager.faculty_time_via_dialog(main_window),
            "faculty_edit_preferences": lambda: main_window.faculty_manager.faculty_preference(main_window),
            "course_add": lambda: main_window.course_manager.add_course_via_dialog(main_window),
            "course_modify": lambda: main_window.course_manager.modify_course_via_dialog(main_window),
            "course_delete": lambda: main_window.course_manager.delete_course_via_dialog(main_window),
            "room_add": lambda: main_window.room_manager.add_room_via_dialog(main_window),
            "room_modify": lambda: main_window.room_manager.modify_room_via_dialog(main_window),
            "room_delete": lambda: main_window.room_manager.delete_room_via_dialog(main_window),
            "lab_add": lambda: main_window.lab_manager.add_lab_via_dialog(main_window),
            "lab_modify": lambda: main_window.lab_manager.modify_lab_via_dialog(main_window),
            "lab_delete": lambda: main_window.lab_manager.delete_lab_via_dialog(main_window),
            "generator_set_limit": lambda: main_window.gen_manager.set_limit(main_window),
            "generator_set_optimize": lambda: main_window.gen_manager.set_optimize(main_window),
            "viewer_open_all": lambda: main_window.open_schedule_viewer("all"),
            "viewer_open_faculty": lambda: main_window.open_schedule_viewer("faculty"),
            "viewer_open_room": lambda: main_window.open_schedule_viewer("room"),
            "viewer_open_lab": lambda: main_window.open_schedule_viewer("lab"),
            "viewer_export": lambda: main_window.handle_export_schedule(),
            "viewer_import": lambda: main_window.handle_import_schedule(),
            "viewer_clear_schedules": lambda: main_window.handle_clear_schedule(),
            "meeting_pattern_add": lambda: main_window.meeting_pattern_editor.add_meeting_pattern(
                main_window
            ),
            "meeting_pattern_modify": lambda: main_window.meeting_pattern_editor.modify_meeting_pattern(
                main_window
            ),
            "meeting_pattern_delete": lambda: main_window.meeting_pattern_editor.delete_meeting_pattern(
                main_window
            ),
            "timeslot_add": lambda: main_window.time_slot_editor.add_time_slot(main_window),
            "timeslot_modify": lambda: main_window.time_slot_editor.modify_time_slot(main_window),
            "timeslot_delete": lambda: main_window.time_slot_editor.delete_time_slot(main_window),
        }
        fn = dispatch.get(action)
        if fn is None:
            return json.dumps({"ok": False, "error": f"Unknown action: {action!r}"})
        fn()
        return ok(f"Launched native GUI: {action}.")

    if name == "get_config_json":
        raw = json.dumps(cm.data, indent=2)
        max_len = 80000
        if len(raw) > max_len:
            return ok(
                f"Truncated to {max_len} characters.",
                json_preview=raw[:max_len] + "\n... [truncated]",
            )
        return ok("Full config JSON.", json=raw)

    if name == "reload_config_from_disk":
        cm.load()
        if hasattr(main_window, "mid_panel"):
            main_window.mid_panel.update_title(cm.filepath)
        return ok("Reloaded from disk.")

    if name == "save_config_to_disk":
        _write_config_silent(main_window)
        return ok(f"Saved to {cm.filepath}.")

    if name == "set_active_config_file":
        path = os.path.expanduser(str(arguments["path"]))
        if not os.path.isfile(path):
            return json.dumps({"ok": False, "error": f"File not found: {path}"})
        cm.filepath = path
        cm.load()
        if hasattr(main_window, "mid_panel"):
            main_window.mid_panel.update_title(path)
        return ok(f"Active config is now {path}.")

    if name == "list_timeslots":
        tse = main_window.time_slot_editor
        slots = tse._get_timeslots()
        sched_times = main_window.config_mgr.data.get("time_slot_config", {}).get("times", {})
        return ok(
            "Time slots (normalized GUI shape + scheduler times).",
            time_slots=slots,
            scheduler_times=sched_times,
        )

    if name == "list_meeting_patterns":
        mpe = main_window.meeting_pattern_editor
        patterns = mpe._get_patterns()
        enriched = [{"index": i, **copy.deepcopy(p)} for i, p in enumerate(patterns)]
        sched_classes = main_window.config_mgr.data.get("time_slot_config", {}).get("classes", [])
        return ok(
            "Class meeting patterns (GUI + scheduler classes).",
            patterns=enriched,
            scheduler_classes=copy.deepcopy(sched_classes),
        )

    if name in (
        "add_timeslot_block",
        "update_timeslot_block",
        "remove_timeslot_block",
        "set_timeslot_day_enabled",
    ):
        tse = main_window.time_slot_editor
        day_raw = str(arguments.get("day", ""))
        day_long = _normalize_weekday_for_editor(day_raw, tse.DAY_MAP, tse.REVERSE_DAY_MAP)
        if not day_long:
            return json.dumps({"ok": False, "error": f"Invalid weekday: {day_raw!r}"})

        if name == "add_timeslot_block":
            st = str(arguments["start_time"]).strip()
            et = str(arguments["end_time"]).strip()
            sp = int(arguments["spacing_minutes"])
            if not _parse_hhmm(st) or not _parse_hhmm(et):
                return json.dumps({"ok": False, "error": "start_time and end_time must be HH:MM."})
            if st >= et:
                return json.dumps({"ok": False, "error": "start_time must be before end_time."})
            if sp < 1:
                return json.dumps({"ok": False, "error": "spacing_minutes must be >= 1."})
            time_slots = tse._get_timeslots()
            day_entry = tse._normalize_day_entry(time_slots.get(day_long, {"enabled": True, "blocks": []}))
            block = {
                "start_time": st,
                "end_time": et,
                "spacing_minutes": sp,
                "slots": tse._generate_slots(st, et, sp),
            }
            day_entry.setdefault("blocks", []).append(block)
            day_entry["enabled"] = True
            time_slots[day_long] = day_entry
            tse._sync_time_slot_config()
            _write_config_silent(main_window)
            return ok(f"Added timeslot block for {day_long}.", day=day_long, blocks=day_entry["blocks"])

        if name == "update_timeslot_block":
            bi = int(arguments["block_index"])
            time_slots = tse._get_timeslots()
            day_entry = tse._normalize_day_entry(time_slots.get(day_long, {"enabled": True, "blocks": []}))
            blocks = day_entry.get("blocks", [])
            if bi < 0 or bi >= len(blocks):
                return json.dumps(
                    {"ok": False, "error": f"block_index out of range (0..{max(len(blocks) - 1, 0)})."}
                )
            cur = dict(blocks[bi])
            if "start_time" in arguments and arguments["start_time"] is not None:
                st = str(arguments["start_time"]).strip()
            else:
                st = str(cur["start_time"]).strip()
            if "end_time" in arguments and arguments["end_time"] is not None:
                et = str(arguments["end_time"]).strip()
            else:
                et = str(cur["end_time"]).strip()
            if "spacing_minutes" in arguments and arguments["spacing_minutes"] is not None:
                sp = int(arguments["spacing_minutes"])
            else:
                sp = int(cur["spacing_minutes"])
            if not _parse_hhmm(st) or not _parse_hhmm(et):
                return json.dumps({"ok": False, "error": "start_time and end_time must be HH:MM."})
            if st >= et:
                return json.dumps({"ok": False, "error": "start_time must be before end_time."})
            if sp < 1:
                return json.dumps({"ok": False, "error": "spacing_minutes must be >= 1."})
            blocks[bi] = {
                "start_time": st,
                "end_time": et,
                "spacing_minutes": sp,
                "slots": tse._generate_slots(st, et, sp),
            }
            time_slots[day_long] = day_entry
            tse._sync_time_slot_config()
            _write_config_silent(main_window)
            return ok(f"Updated timeslot block {bi} for {day_long}.", day=day_long, block=blocks[bi])

        if name == "remove_timeslot_block":
            bi = int(arguments["block_index"])
            time_slots = tse._get_timeslots()
            if day_long not in time_slots:
                return json.dumps({"ok": False, "error": f"No timeslots for {day_long}."})
            day_entry = tse._normalize_day_entry(time_slots[day_long])
            blocks = day_entry.get("blocks", [])
            if bi < 0 or bi >= len(blocks):
                return json.dumps(
                    {"ok": False, "error": f"block_index out of range (0..{max(len(blocks) - 1, 0)})."}
                )
            del blocks[bi]
            if not blocks:
                del time_slots[day_long]
            else:
                time_slots[day_long] = day_entry
            tse._sync_time_slot_config()
            _write_config_silent(main_window)
            return ok(f"Removed timeslot block {bi} for {day_long}.")

        if name == "set_timeslot_day_enabled":
            en = bool(arguments["enabled"])
            time_slots = tse._get_timeslots()
            day_entry = tse._normalize_day_entry(time_slots.get(day_long, {"enabled": True, "blocks": []}))
            day_entry["enabled"] = en
            time_slots[day_long] = day_entry
            tse._sync_time_slot_config()
            _write_config_silent(main_window)
            return ok(f"Set {day_long} enabled={en}.")

    if name in ("add_meeting_pattern", "update_meeting_pattern", "delete_meeting_pattern"):
        mpe = main_window.meeting_pattern_editor
        dm, rv = mpe.DAY_MAP, mpe.REVERSE_DAY_MAP

        if name == "add_meeting_pattern":
            meetings_arg = arguments.get("meetings") or []
            if not isinstance(meetings_arg, list):
                return json.dumps({"ok": False, "error": "meetings must be an array."})
            norm, err = _normalize_meeting_entries(meetings_arg, dm, rv)
            if err:
                return json.dumps({"ok": False, "error": err})
            credits = int(arguments["credits"])
            start_time = str(arguments.get("start_time", "")).strip()
            disabled = bool(arguments.get("disabled", False))
            pattern: Dict[str, Any] = {
                "credits": credits,
                "meetings": norm,
                "start_time": start_time,
                "disabled": disabled,
            }
            patterns = mpe._get_patterns()
            patterns.append(pattern)
            mpe._sync_time_slot_config_classes()
            _write_config_silent(main_window)
            return ok("Added meeting pattern.", pattern=pattern, index=len(patterns) - 1)

        if name == "update_meeting_pattern":
            idx = int(arguments["pattern_index"])
            patterns = mpe._get_patterns()
            if idx < 0 or idx >= len(patterns):
                return json.dumps(
                    {"ok": False, "error": f"pattern_index out of range (0..{len(patterns) - 1})."}
                )
            cur = copy.deepcopy(patterns[idx])
            if not isinstance(cur, dict):
                return json.dumps({"ok": False, "error": "Invalid pattern entry."})
            if "credits" in arguments and arguments["credits"] is not None:
                cur["credits"] = int(arguments["credits"])
            if "meetings" in arguments and arguments["meetings"] is not None:
                if not isinstance(arguments["meetings"], list):
                    return json.dumps({"ok": False, "error": "meetings must be an array."})
                norm, err = _normalize_meeting_entries(arguments["meetings"], dm, rv)
                if err:
                    return json.dumps({"ok": False, "error": err})
                cur["meetings"] = norm
            if "start_time" in arguments and arguments["start_time"] is not None:
                cur["start_time"] = str(arguments["start_time"]).strip()
            if "disabled" in arguments and arguments["disabled"] is not None:
                cur["disabled"] = bool(arguments["disabled"])
            if not cur.get("meetings"):
                return json.dumps({"ok": False, "error": "Pattern must have at least one meeting."})
            patterns[idx] = cur
            mpe._sync_time_slot_config_classes()
            _write_config_silent(main_window)
            return ok(f"Updated meeting pattern at index {idx}.", pattern=cur)

        if name == "delete_meeting_pattern":
            idx = int(arguments["pattern_index"])
            patterns = mpe._get_patterns()
            if idx < 0 or idx >= len(patterns):
                return json.dumps(
                    {"ok": False, "error": f"pattern_index out of range (0..{len(patterns) - 1})."}
                )
            del patterns[idx]
            mpe._sync_time_slot_config_classes()
            _write_config_silent(main_window)
            return ok(f"Deleted meeting pattern at index {idx}.")

    cfg = _ensure_config_block(main_window)
    rooms: List[str] = cfg["rooms"]
    labs: List[str] = cfg["labs"]
    courses: List[Dict[str, Any]] = cfg["courses"]
    faculty: List[Any] = cfg["faculty"]

    if name == "list_rooms":
        return ok("Rooms.", rooms=list(rooms))

    if name == "list_labs":
        return ok("Labs.", labs=list(labs))

    if name == "list_faculty":
        names = [_faculty_display_name(f) for f in faculty]
        return ok("Faculty display names.", faculty=names)

    if name == "list_course_ids":
        ids = [str(c.get("course_id", "")) for c in courses if isinstance(c, dict)]
        return ok("Course IDs (may include duplicates).", course_ids=ids)

    if name == "add_room":
        rn = str(arguments["room_name"]).strip()
        if not rn:
            return json.dumps({"ok": False, "error": "Empty room name."})
        if rn not in rooms:
            rooms.append(rn)
            _write_config_silent(main_window)
            return ok(f"Added room {rn!r}.", rooms=rooms)
        return ok(f"Room {rn!r} already present (no change).", rooms=rooms)

    if name == "remove_room":
        rn = str(arguments["room_name"])
        if rn in rooms:
            rooms.remove(rn)
            _write_config_silent(main_window)
            return ok(f"Removed room {rn!r}.", rooms=rooms)
        return json.dumps({"ok": False, "error": f"Room not found: {rn!r}"})

    if name == "rename_room":
        old, new = str(arguments["old_name"]), str(arguments["new_name"]).strip()
        if old not in rooms:
            return json.dumps({"ok": False, "error": f"Room not found: {old!r}"})
        idx = rooms.index(old)
        rooms[idx] = new
        _write_config_silent(main_window)
        return ok(f"Renamed {old!r} -> {new!r}.", rooms=rooms)

    if name == "add_lab":
        lab = str(arguments["lab_name"]).strip()
        if not lab:
            return json.dumps({"ok": False, "error": "Empty lab name."})
        if lab not in labs:
            labs.append(lab)
        _write_config_silent(main_window)
        return ok("Labs updated.", labs=labs)

    if name == "remove_lab":
        lab = str(arguments["lab_name"])
        if lab in labs:
            labs.remove(lab)
            _write_config_silent(main_window)
            return ok(f"Removed lab {lab!r}.", labs=labs)
        return json.dumps({"ok": False, "error": f"Lab not found: {lab!r}"})

    if name == "rename_lab":
        old, new = str(arguments["old_name"]), str(arguments["new_name"]).strip()
        if old not in labs:
            return json.dumps({"ok": False, "error": f"Lab not found: {old!r}"})
        labs[labs.index(old)] = new
        _write_config_silent(main_window)
        return ok(f"Renamed lab {old!r} -> {new!r}.", labs=labs)

    if name == "add_faculty":
        fn = str(arguments["name"]).strip()
        if not fn:
            return json.dumps({"ok": False, "error": "Empty name."})
        faculty.append(fn)
        _write_config_silent(main_window)
        return ok(f"Added faculty {fn!r}.")

    if name == "remove_faculty":
        target = str(arguments["name"])
        idx = _faculty_match_index(faculty, target)
        if idx is None:
            return json.dumps({"ok": False, "error": f"Faculty not found or ambiguous: {target!r}"})
        removed = _faculty_display_name(faculty[idx])
        del faculty[idx]
        _write_config_silent(main_window)
        return ok(f"Removed faculty {removed!r}.")

    if name == "rename_faculty":
        old_n, new_n = str(arguments["old_name"]), str(arguments["new_name"]).strip()
        idx = _faculty_match_index(faculty, old_n)
        if idx is None:
            return json.dumps({"ok": False, "error": f"Faculty not found or ambiguous: {old_n!r}"})
        f = faculty[idx]
        if isinstance(f, dict):
            faculty[idx] = {**f, "name": new_n}
        else:
            faculty[idx] = new_n
        _write_config_silent(main_window)
        return ok(f"Renamed faculty {_faculty_display_name(f)!r} -> {new_n!r}.")

    if name == "merge_faculty_object":
        fname = str(arguments["faculty_name"])
        merge_obj = json.loads(str(arguments["merge_json"]))
        if not isinstance(merge_obj, dict):
            return json.dumps({"ok": False, "error": "merge_json must be a JSON object."})
        idx = _faculty_match_index(faculty, fname)
        if idx is None:
            return json.dumps({"ok": False, "error": f"Faculty not found or ambiguous: {fname!r}"})
        f = faculty[idx]
        base = f if isinstance(f, dict) else {"name": str(f)}
        faculty[idx] = {**base, **merge_obj}
        _write_config_silent(main_window)
        return ok(f"Merged fields into faculty {_faculty_display_name(f)!r}.", entry=faculty[idx])

    if name == "add_course":
        cid = str(arguments["course_id"]).strip()
        creds = int(arguments["credits"])
        new_c = {
            "course_id": cid,
            "credits": creds,
            "room": list(arguments.get("rooms") or []),
            "lab": list(arguments.get("labs") or []),
            "conflicts": list(arguments.get("conflicts") or []),
            "faculty": list(arguments.get("faculty") or []),
        }
        courses.append(new_c)
        _write_config_silent(main_window)
        return ok(f"Added course {cid!r}.", course=new_c)

    if name == "update_course":
        cid = str(arguments["course_id"])
        for c in courses:
            if not isinstance(c, dict) or str(c.get("course_id")) != cid:
                continue
            if "credits" in arguments:
                c["credits"] = int(arguments["credits"])
            if "rooms" in arguments:
                c["room"] = list(arguments["rooms"])
            if "labs" in arguments:
                c["lab"] = list(arguments["labs"])
            if "conflicts" in arguments:
                c["conflicts"] = list(arguments["conflicts"])
            if "faculty" in arguments:
                c["faculty"] = list(arguments["faculty"])
            _write_config_silent(main_window)
            return ok(f"Updated first course {cid!r}.", course=c)
        return json.dumps({"ok": False, "error": f"Course not found: {cid!r}"})

    if name == "delete_course":
        cid = str(arguments["course_id"])
        for i, c in enumerate(courses):
            if isinstance(c, dict) and str(c.get("course_id")) == cid:
                del courses[i]
                _write_config_silent(main_window)
                return ok(f"Deleted first course {cid!r}.")
        return json.dumps({"ok": False, "error": f"Course not found: {cid!r}"})

    if name == "set_schedule_limit":
        lim = int(arguments["limit"])
        main_window.config_mgr.data["limit"] = lim
        _write_config_silent(main_window)
        return ok(f"Set limit to {lim}.")

    if name == "set_optimizer_enabled":
        enabled = bool(arguments["enabled"])
        full_flags = [
            "faculty_course",
            "faculty_room",
            "faculty_lab",
            "same_room",
            "same_lab",
            "pack_rooms",
        ]
        main_window.config_mgr.data["optimizer_flags"] = full_flags if enabled else []
        _write_config_silent(main_window)
        return ok(f"Optimizer {'enabled' if enabled else 'disabled'}.")

    if name == "run_schedule_generation":
        main_window.gen_manager.run_scheduler(main_window)
        return ok("Started schedule generation (progress dialog).")

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
