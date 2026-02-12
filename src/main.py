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

"""from cli import run_course_management
from cli.course import Course"""
from cli.common import prompt

COURSES_KEY_PATH = ("config", "courses")


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


def ensure_courses_list(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the list at config.courses, creating containers if missing."""
    node: Any = cfg
    for key in COURSES_KEY_PATH[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    leaf_key = COURSES_KEY_PATH[-1]
    if leaf_key not in node or not isinstance(node[leaf_key], list):
        node[leaf_key] = []
    return node[leaf_key]


def backup_file(path: Path) -> Path | None:
    backup_path = path.with_suffix(path.suffix + ".bak")
    try:
        shutil.copy2(path, backup_path)
        return backup_path
    except FileNotFoundError:
        return None


def save_config(cfg: Dict[str, Any], courses: List[Course], config_path: Path) -> None:
    raw_list = ensure_courses_list(cfg)
    raw_list[:] = [c.to_raw() for c in courses]
    backup = backup_file(config_path)
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    if backup is not None:
        print(f"Saved. Backup written to {backup}")
    else:
        print("Saved.")


def run_faculty_management(cfg: Dict[str, Any]) -> bool:
    """Placeholder."""
    print("Faculty Management is not yet implemented.")
    return False

def run_room_management(cfg: Dict[str, Any]) -> bool:
    """Placeholder."""
    print("Room Management is not yet implemented.")
    return False

def run_lab_management(cfg: Dict[str, Any]) -> bool:
    """Placeholder."""
    print("Lab Management is not yet implemented.")
    return False

def main_menu(config_path: Path) -> None:
    cfg = load_config(config_path)
    """raw_courses = ensure_courses_list(cfg)
    courses: List[Course] = [Course.from_raw(c) for c in raw_courses]"""
    dirty = False

    while True:
        print(
            "\n=== Scheduler Config CLI ===\n"
            "1) Course Management\n"
            "2) Faculty Management (coming soon)\n"
            "3) Room Management (coming soon)\n"
            "4) Lab Management (coming soon)\n"
            "5) Save config without exiting\n"
            "6) Save config and exit\n"
            "7) Exit without saving\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            dirty = run_course_management(courses) or dirty
        elif choice == "2":
            dirty = run_faculty_management(cfg) or dirty
        elif choice == "3":
            dirty = run_room_management(cfg) or dirty
        elif choice == "4":
            dirty = run_lab_management(cfg) or dirty    
        elif choice == "5":
            save_config(cfg, courses, config_path)
        elif choice == "6":
            save_config(cfg, courses, config_path)
            return
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
            print("Invalid choice. Please enter 1–5.")

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python main.py path/to/config.json", file=sys.stderr)
        return 1
    config_path = Path(sys.argv[1])
    main_menu(config_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
