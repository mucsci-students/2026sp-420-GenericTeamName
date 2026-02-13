# Author: Damion Crawford
# Filename: faculty.py
# Saving, modifying, removing faculty

"""Faculty management module for scheduler config CLI."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .common import prompt, prompt_int, prompt_list

@dataclass
class Faculty:
    name: str

    @classmethod
    def from_raw(cls, raw: Any) -> "Faculty":
        return cls(name=str(raw))

    def to_raw(self) -> Any:
        return self.name

    def faculty_exists(faculty: List[Faculty], name: str) -> bool:
        return any(f.name == name for f in faculty)

    def list_faculty(faculty: List[Faculty]) -> None:
    if not faculty:
        print("No faculty in config.")
        return
    print("\nCurrent faculty:")
    for idx, f in enumerate(faculty):
        print(f"[{idx}] {f.name}")
    print()

    def choose_faculty_index(faculty: List[Faculty]) -> Optional[int]:
    if not faculty:
        print("No faculty to select.")
        return None
    list_faculty(faculty)
    while True:
        raw = prompt("Enter faculty index (blank to cancel)", "")
        if raw == "":
            return None
        try:
            idx = int(raw)
            if 0 <= idx < len(faculty):
                return idx
            print(f"Index out of range. Enter 0–{len(faculty) - 1}.")
        except ValueError:
            print("Please enter a valid integer index.")

    def add_Faculty(faculty: List[Faculty]) -> None:
        print("\nAdd new faculty")
        while True:
            name = prompt("Faculty name (e.g. Smith)").strip()
            if not name:
                print("Faculty name is required.")
                continue
            if faculty_exist(faculty, name):
                print("A faculty member with that name already exists.")
                continue
            break

        faculty.append(Faculty(name=name))
        print("Faculty member added.")

    def modify_Faculty(members: List[Faculty]) -> None:
        idx = choose_faculty_index(members)
        if idx is None:
            return
        current = members[idx]
        print(f"\nModify faculty: {current.name}")
        name = prompt("Faculty name", current.name).strip() or current.name
        
        members[idx] = Faculty(name=name)
        print("Faculty member updated.")

    def delete_Faculty(members: List[Faculty]) -> None:
        idx = choose_faculty_index(members)
        if idx is None:
            return
        faculty = members[idx]
        confirm = prompt(f"Delete faculty member [{idx}] {faculty.name}? Type 'yes' to confirm", "")
        if confirm.lower() == "yes":
            del members[idx]
            print("Faculty member removed from config.")
        else:
            print("Delete cancelled.")
    
    def faculty_time(members: List[Faculty]) -> None:
        idx = choose_faculty_index(members)
        if idx is None:
            return
        faculty = members[idx]
        print(f"\nEnter available time for {faculty.name}")
        time = prompt("Faculty time", current.time).strip()
        print(f"Faculty member {faculty.name} now has available time {time}")

    def faculty_preference(members: List[Faculty]) -> None;
        idx = choose_faculty_index(members)
        if idx is None:
            return
        print(f"\nEnter course preference and weight for {faculty.name}")
        course = prompt("Course ID", course_id).strip()
        weight = prompt("Weight", course_weight).strip()
        print(f"Course ID {course_id} has been assigned with weight {course_weight} to facult {faculty.name}")


def run_faculty_management(members: List[Faculty]) -> bool:
    """
    Run the Faculty Management submenu.
    Mutates faculty in place.
    Returns True if the config was modified.
    """
    dirty = False
    while True:
        print(
            "\n--- Faculty Management ---\n"
            "1) Add faculty member\n"
            "2) Modify faculty member\n"
            "3) Delete faculty member\n"
            "4) Add faculty time preference\n"
            "5) Add faculty course preference and weight\n"
            "6) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            add_Faculty(members)
            dirty = True
        elif choice == "2":
            modify_Faculty(members)
            dirty = True
        elif choice == "3":
            delete_Faculty(members)
            dirty = True
        elif choice == "4":
            faculty_time(members)
        elif choice == "5":
            faculty_preference(members)
        elif choice == "6":
            return dirty
        else:
            print("Invalid choice. Please enter 1–6.")