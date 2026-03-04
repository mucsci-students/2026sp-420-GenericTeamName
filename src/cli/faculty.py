from __future__ import annotations
"""
File    : faculty.py
Author  : Damion Crawford & Shane del Villar
Desc    : Saving, modifying, removing faculty
"""

"""Faculty management module for scheduler config CLI."""

# from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from common import prompt, prompt_int, prompt_list


# Default structure matching scheduler config schema
def _default_times() -> Dict[str, List[str]]:
    return {
        "MON": [], "TUE": [], "WED": [], "THU": [], "FRI": [],
    }


@dataclass
class Faculty:
    name: str
    maximum_credits: int = 12
    minimum_credits: int = 0
    unique_course_limit: int = 2
    maximum_days: Optional[int] = None
    mandatory_days: List[str] = field(default_factory=list)
    times: Dict[str, List[str]] = field(default_factory=_default_times)
    course_preferences: Dict[str, int] = field(default_factory=dict)
    room_preferences: Dict[str, int] = field(default_factory=dict)
    lab_preferences: Dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Any) -> "Faculty":
        if not isinstance(raw, dict):
            return cls(name=str(raw).strip())
        times = raw.get("times")
        if not isinstance(times, dict):
            times = _default_times()
        else:
            times = {k: list(v) if isinstance(v, list) else [] for k, v in times.items()}
        return cls(
            name=str(raw.get("name", "")).strip(),
            maximum_credits=int(raw.get("maximum_credits", 12) or 12),
            minimum_credits=int(raw.get("minimum_credits", 0) or 0),
            unique_course_limit=int(raw.get("unique_course_limit", 2) or 2),
            maximum_days=int(raw["maximum_days"]) if raw.get("maximum_days") is not None else None,
            mandatory_days=list(raw.get("mandatory_days") or []),
            times=times,
            course_preferences=dict(raw.get("course_preferences") or {}),
            room_preferences=dict(raw.get("room_preferences") or {}),
            lab_preferences=dict(raw.get("lab_preferences") or {}),
        )

    def to_raw(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "maximum_credits": self.maximum_credits,
            "minimum_credits": self.minimum_credits,
            "unique_course_limit": self.unique_course_limit,
            "times": self.times,
            "course_preferences": self.course_preferences,
            "room_preferences": self.room_preferences,
            "lab_preferences": self.lab_preferences,
        }
        if self.maximum_days is not None:
            d["maximum_days"] = self.maximum_days
        if self.mandatory_days:
            d["mandatory_days"] = self.mandatory_days
        return d


def _faculty_exists(faculty: List[Faculty], name: str) -> bool:
    return any(f.name == name for f in faculty)


def _list_faculty(faculty: List[Faculty]) -> None:
    if not faculty:
        print("No faculty in config.")
        return
    print("\nCurrent faculty:")
    for idx, f in enumerate(faculty):
        print(f"[{idx}] {f.name} (max {f.maximum_credits} cr, limit {f.unique_course_limit} courses)")
    print()


def _choose_faculty_index(faculty: List[Faculty]) -> Optional[int]:
    if not faculty:
        print("No faculty to select.")
        return None
    _list_faculty(faculty)
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


def _add_faculty(faculty: List[Faculty]) -> None:
    print("\nAdd new faculty")
    while True:
        name = prompt("Faculty name (e.g. Smith)").strip()
        if not name:
            print("Faculty name is required.")
            continue
        if _faculty_exists(faculty, name):
            print("A faculty member with that name already exists.")
            continue
        break
    max_cr = prompt_int("Maximum credits", 12)
    min_cr = prompt_int("Minimum credits", 0)
    limit = prompt_int("Unique course limit", 2)
    faculty.append(
        Faculty(
            name=name,
            maximum_credits=max_cr,
            minimum_credits=min_cr,
            unique_course_limit=limit,
        )
    )
    print("Faculty member added.")


def _modify_faculty(faculty_list: List[Faculty]) -> None:
    idx = _choose_faculty_index(faculty_list)
    if idx is None:
        return
    current = faculty_list[idx]
    print(f"\nModify faculty: {current.name}")
    name = prompt("Faculty name", current.name).strip() or current.name
    max_cr = prompt_int("Maximum credits", current.maximum_credits)
    min_cr = prompt_int("Minimum credits", current.minimum_credits)
    limit = prompt_int("Unique course limit", current.unique_course_limit)
    faculty_list[idx] = Faculty(
        name=name,
        maximum_credits=max_cr,
        minimum_credits=min_cr,
        unique_course_limit=limit,
        maximum_days=current.maximum_days,
        mandatory_days=current.mandatory_days,
        times=current.times,
        course_preferences=current.course_preferences,
        room_preferences=current.room_preferences,
        lab_preferences=current.lab_preferences,
    )
    print("Faculty member updated.")


def _delete_faculty(faculty_list: List[Faculty]) -> None:
    idx = _choose_faculty_index(faculty_list)
    if idx is None:
        return
    f = faculty_list[idx]
    confirm = prompt(f"Delete faculty member [{idx}] {f.name}? Type 'yes' to confirm", "")
    if confirm.lower() == "yes":
        del faculty_list[idx]
        print("Faculty member removed from config.")
    else:
        print("Delete cancelled.")


def _edit_faculty_times(faculty_list: List[Faculty]) -> None:
    idx = _choose_faculty_index(faculty_list)
    if idx is None:
        return
    f = faculty_list[idx]
    print(f"\nEdit available times for {f.name} (e.g. MON: 09:00-15:00)")
    days = list(f.times.keys())
    for day in days:
        current = ", ".join(f.times[day]) if f.times[day] else ""
        raw = prompt(f"  {day} (comma-separated time ranges, blank to keep)", current).strip()
        if raw:
            f.times[day] = [s.strip() for s in raw.split(",") if s.strip()]
    print("Times updated.")


def _edit_faculty_course_preference(faculty_list: List[Faculty]) -> None:
    idx = _choose_faculty_index(faculty_list)
    if idx is None:
        return
    f = faculty_list[idx]
    print(f"\nCourse preferences for {f.name} (course_id weight, e.g. CMSC 420 5)")
    course_id = prompt("Course ID", "").strip()
    if not course_id:
        print("Cancelled.")
        return
    weight = prompt_int("Weight (1-10)", 5)
    f.course_preferences[course_id] = weight
    print(f"Course {course_id} preference set to weight {weight}.")


def run_faculty_management(faculty_list: List[Faculty]) -> bool:
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
            "4) Edit faculty available times\n"
            "5) Add faculty course preference (and weight)\n"
            "6) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            _add_faculty(faculty_list)
            dirty = True
        elif choice == "2":
            _modify_faculty(faculty_list)
            dirty = True
        elif choice == "3":
            _delete_faculty(faculty_list)
            dirty = True
        elif choice == "4":
            _edit_faculty_times(faculty_list)
            dirty = True
        elif choice == "5":
            _edit_faculty_course_preference(faculty_list)
            dirty = True
        elif choice == "6":
            return dirty
        else:
            print("Invalid choice. Please enter 1–6.")
