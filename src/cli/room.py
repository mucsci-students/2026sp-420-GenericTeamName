# Author: Chayse Altland
# Filename: room.py
# Saving, modifying, and deleting rooms

"""Room management module for scheduler config CLI."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .common import prompt, prompt_int, prompt_list


@dataclass
class Room:
    name: str
    

    @classmethod
    def from_raw(cls, raw: Any) -> "Room":
        return cls(name=str(raw))

    def to_raw(self) -> Any:
        return self.name


def _room_exists(rooms: List[Room], name: str) -> bool:
    return any(r.name == name for r in rooms)


def _list_rooms(rooms: List[Room]) -> None:
    if not rooms:
        print("No rooms in config.")
        return
    print("\nCurrent rooms:")
    for idx, r in enumerate(rooms):
        print(f"[{idx}] {r.name}")
    print()


def _choose_room_index(rooms: List[Room]) -> Optional[int]:
    if not rooms:
        print("No rooms to select.")
        return None
    _list_rooms(rooms)
    while True:
        raw = prompt("Enter room index (blank to cancel)", "")
        if raw == "":
            return None
        try:
            idx = int(raw)
            if 0 <= idx < len(rooms):
                return idx
            print(f"Index out of range. Enter 0–{len(rooms) - 1}.")
        except ValueError:
            print("Please enter a valid integer index.")


def _add_room(rooms: List[Room]) -> None:
    print("\nAdd new room")
    while True:
        name = prompt("Room name (e.g. Room 101)").strip()
        if not name:
            print("Room name is required.")
            continue
        if _room_exists(rooms, name):
            print("A room with that name already exists.")
            continue
        break
   
    rooms.append(Room(name=name))
    print("Room added.")


def _modify_room(rooms: List[Room]) -> None:
    idx = _choose_room_index(rooms)
    if idx is None:
        return
    current = rooms[idx]
    print(f"\nModify room: {current.name}")
    name = prompt("Room name", current.name).strip() or current.name
    
    rooms[idx] = Room(name=name)
    print("Room updated.")


def _delete_room(rooms: List[Room]) -> None:
    idx = _choose_room_index(rooms)
    if idx is None:
        return
    room = rooms[idx]
    confirm = prompt(f"Delete room [{idx}] {room.name}? Type 'yes' to confirm", "")
    if confirm.lower() == "yes":
        del rooms[idx]
        print("Room removed from config.")
    else:
        print("Delete cancelled.")


def run_room_management(rooms: List[Room]) -> bool:
    """
    Run the Room Management submenu.
    Mutates rooms in place.
    Returns True if the config was modified.
    """
    dirty = False
    while True:
        print(
            "\n--- Room Management ---\n"
            "1) Add room\n"
            "2) Modify room\n"
            "3) Delete room\n"
            "4) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            _add_room(rooms)
            dirty = True
        elif choice == "2":
            _modify_room(rooms)
            dirty = True
        elif choice == "3":
            _delete_room(rooms)
            dirty = True
        elif choice == "4":
            return dirty
        else:
            print("Invalid choice. Please enter 1–4.")
