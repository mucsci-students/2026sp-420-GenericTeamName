"""
File    : config_mgmt.py
Author  : Shane del Villar
Desc    : Config management submenu: 
          save, view summary, and related options."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from common import prompt
from course import Course
from room import Room


def _view_config_summary(cfg: Dict[str, Any]) -> None:
    """Display a human-readable summary of the current config (in-memory)."""
    from config import ConfigManager
    # Use a manager and inject current in-memory cfg so we show unsaved state
    manager = ConfigManager("")
    manager.data = cfg
    manager.display_human_summary()


def run_config_management(
    cfg: Dict[str, Any],
    courses: List[Course],
    rooms: List[Room],
    config_path: Path,
    save_config_fn: Callable[[], None],
) -> tuple[bool, bool]:
    """
    Run the Config Management submenu.
    Returns (save_and_exit, dirty). If save_and_exit is True, caller should save and exit.
    """
    while True:
        print(
            "\n--- Config Management ---\n"
            "1) View config summary\n"
            "2) Save config (without exiting)\n"
            "3) Save config and exit\n"
            "4) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            _view_config_summary(cfg)
        elif choice == "2":
            save_config_fn()
        elif choice == "3":
            save_config_fn()
            return (True, False)  # signal: save and exit
        elif choice == "4":
            return (False, False)
        else:
            print("Invalid choice. Please enter 1–4.")
