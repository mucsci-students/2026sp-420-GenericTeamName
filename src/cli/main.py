"""
Scheduler Config CLI - main entry point.

User-friendly interface for managing scheduler config files from
https://github.com/mucsci/scheduler. Supports Course Management now;
Faculty and Room management can be added as modules.

"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from cli import run_course_management
from cli.room import run_room_management
from cli.faculty import run_faculty_management
from cli.lab import run_lab_management
from cli.config_mgmt import run_config_management
from cli.course import Course
from cli.room import Room
from cli.faculty import Faculty
from cli.lab import Lab
from cli.common import prompt

COURSES_KEY_PATH = ("config", "courses")
ROOMS_KEY_PATH = ("config", "rooms")
FACULTY_KEY_PATH = ("config", "faculty")
LABS_KEY_PATH = ("config", "labs")


def load_config(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        cfg = json.loads(text)
    except FileNotFoundError:
        raise SystemExit(f"Config file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {path}: {e}")

    if not isinstance(cfg, dict):
        raise SystemExit("Top-level JSON must be an object.")
    return cfg


def ensure_key_path(cfg: Dict[str, Any], key_path: tuple[str, ...], default_type=list) -> list:
    """Return the list at a nested key path, creating containers if missing."""
    node: Any = cfg
    for key in key_path[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    leaf_key = key_path[-1]
    if leaf_key not in node or not isinstance(node[leaf_key], default_type):
        node[leaf_key] = default_type()
    return node[leaf_key]


def backup_file(path: Path) -> Path | None:
    backup_path = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except FileNotFoundError:
        return None


def save_config(
    cfg: Dict[str, Any],
    courses: List[Course],
    rooms: List[Room],
    faculty: List[Faculty],
    labs: List[Lab],
    config_path: Path,
) -> None:
    raw_courses = ensure_key_path(cfg, COURSES_KEY_PATH)
    raw_courses[:] = [c.to_raw() for c in courses]

    raw_rooms = ensure_key_path(cfg, ROOMS_KEY_PATH)
    raw_rooms[:] = [r.to_raw() for r in rooms]

    raw_faculty = ensure_key_path(cfg, FACULTY_KEY_PATH)
    raw_faculty[:] = [f.to_raw() for f in faculty]

    raw_labs = ensure_key_path(cfg, LABS_KEY_PATH)
    raw_labs[:] = [lab.to_raw() for lab in labs]

    backup = backup_file(config_path)
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    if backup is not None:
        print(f"Saved. Backup written to {backup}")
    else:
        print("Saved.")


def main_menu(config_path: Path) -> None:
    cfg = load_config(config_path)
    dirty = False
    raw_courses = ensure_key_path(cfg, COURSES_KEY_PATH)
    courses: List[Course] = [Course.from_raw(c) for c in raw_courses]

    raw_rooms = ensure_key_path(cfg, ROOMS_KEY_PATH)
    rooms: List[Room] = [Room.from_raw(r) for r in raw_rooms]

    raw_faculty = ensure_key_path(cfg, FACULTY_KEY_PATH)
    faculty: List[Faculty] = [Faculty.from_raw(f) for f in raw_faculty]

    raw_labs = ensure_key_path(cfg, LABS_KEY_PATH)
    labs: List[Lab] = [Lab.from_raw(l) for l in raw_labs]

    from run import Run
    run_menu = Run(config_path)

    while True:
        print(
            "\n=== Scheduler Config CLI ===\n"
            "1) Course Management\n"
            "2) Faculty Management\n"
            "3) Room Management\n"
            "4) Lab Management\n"
            "5) Config Management\n"
            "6) Run / display schedule\n"
            "7) Exit without saving\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            dirty = run_course_management(courses) or dirty
        elif choice == "2":
            dirty = run_faculty_management(faculty) or dirty
        elif choice == "3":
            dirty = run_room_management(rooms) or dirty
        elif choice == "4":
            dirty = run_lab_management(labs) or dirty
        elif choice == "5":
            # Sync in-memory state into cfg so "View config summary" is current
            ensure_key_path(cfg, COURSES_KEY_PATH)[:] = [c.to_raw() for c in courses]
            ensure_key_path(cfg, ROOMS_KEY_PATH)[:] = [r.to_raw() for r in rooms]
            ensure_key_path(cfg, FACULTY_KEY_PATH)[:] = [f.to_raw() for f in faculty]
            ensure_key_path(cfg, LABS_KEY_PATH)[:] = [lab.to_raw() for lab in labs]
            def do_save() -> None:
                save_config(cfg, courses, rooms, faculty, labs, config_path)
            save_and_exit, _ = run_config_management(
                cfg, courses, rooms, config_path, do_save
            )
            if save_and_exit:
                return
        elif choice == "6":
            run_menu.run_scheduler_menu()
        elif choice == "7":
            if dirty:
                confirm = prompt(
                    "Discard changes and exit without saving? Type 'yes' to confirm",
                    "",
                )
                if confirm.lower() != "yes":
                    continue
            print("Exiting without saving changes.")
            return
        else:
            print("Invalid choice. Please enter 1–7.")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python main.py path/to/config.json", file=sys.stderr)
        return 1
    config_path = Path(sys.argv[1])
    main_menu(config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
