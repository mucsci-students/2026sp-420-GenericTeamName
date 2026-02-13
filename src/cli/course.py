"""Course management module for scheduler config CLI."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .common import prompt, prompt_int, prompt_list


@dataclass
class Course:
    course_id: str
    credits: int
    room: List[str]
    lab: List[str]
    conflicts: List[str]
    faculty: List[str]

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "Course":
        return cls(
            course_id=str(raw.get("course_id", "")).strip(),
            credits=int(raw.get("credits", 0) or 0),
            room=list(raw.get("room") or []),
            lab=list(raw.get("lab") or []),
            conflicts=list(raw.get("conflicts") or []),
            faculty=list(raw.get("faculty") or []),
        )

    def to_raw(self) -> Dict[str, Any]:
        d = asdict(self)
        return {
            "course_id": d["course_id"],
            "credits": d["credits"],
            "room": d["room"],
            "lab": d["lab"],
            "conflicts": d["conflicts"],
            "faculty": d["faculty"],
        }


def _course_exists(courses: List[Course], course_id: str) -> bool:
    return any(c.course_id == course_id for c in courses)


def _list_courses(courses: List[Course]) -> None:
    if not courses:
        print("No courses in config.")
        return
    print("\nCurrent courses:")
    for idx, c in enumerate(courses):
        rooms = ", ".join(c.room) or "—"
        labs = ", ".join(c.lab) or "—"
        fac = ", ".join(c.faculty) or "—"
        print(
            f"[{idx}] {c.course_id} ({c.credits} cr) | "
            f"rooms: {rooms} | labs: {labs} | faculty: {fac}"
        )
    print()


def _choose_course_index(courses: List[Course]) -> Optional[int]:
    if not courses:
        print("No courses to select.")
        return None
    _list_courses(courses)
    while True:
        raw = prompt("Enter course index (blank to cancel)", "")
        if raw == "":
            return None
        try:
            idx = int(raw)
            if 0 <= idx < len(courses):
                return idx
            print(f"Index out of range. Enter 0–{len(courses) - 1}.")
        except ValueError:
            print("Please enter a valid integer index.")


def _add_course(courses: List[Course]) -> None:
    print("\nAdd new course")
    while True:
        course_id = prompt("Course name (e.g. CMSC 420)").strip()
        if not course_id:
            print("Course name is required.")
            continue
        if _course_exists(courses, course_id):
            print("A course with that ID already exists.")
            continue
        break
    credits = prompt_int("Credits", 4)
    room = prompt_list("Room(s)", [])
    lab = prompt_list("Lab(s) (optional, comma-separated)", [])
    conflicts = prompt_list("Conflicts (course IDs, optional)", [])
    faculty = prompt_list("Faculty who can teach this course (optional)", [])
    courses.append(
        Course(
            course_id=course_id,
            credits=credits,
            room=room,
            lab=lab,
            conflicts=conflicts,
            faculty=faculty,
        )
    )
    print("Course added.")


def _modify_course(courses: List[Course]) -> None:
    idx = _choose_course_index(courses)
    if idx is None:
        return
    current = courses[idx]
    print(f"\nModify course: {current.course_id}")
    course_id = prompt("Course name", current.course_id).strip()
    if not course_id:
        course_id = current.course_id
    credits = prompt_int("Credits", current.credits)
    room = prompt_list("Room(s)", current.room)
    lab = prompt_list("Lab(s) (optional)", current.lab)
    conflicts = prompt_list("Conflicts (optional)", current.conflicts)
    faculty = prompt_list("Faculty (optional)", current.faculty)
    courses[idx] = Course(
        course_id=course_id,
        credits=credits,
        room=room,
        lab=lab,
        conflicts=conflicts,
        faculty=faculty,
    )
    print("Course updated.")


def _delete_course(courses: List[Course]) -> None:
    idx = _choose_course_index(courses)
    if idx is None:
        return
    course = courses[idx]
    confirm = prompt(
        f"Delete course [{idx}] {course.course_id}? Type 'yes' to confirm", ""
    )
    if confirm.lower() == "yes":
        del courses[idx]
        print("Course removed from config.")
    else:
        print("Delete cancelled.")


def run_course_management(courses: List[Course]) -> bool:
    """
    Run the Course Management submenu.
    Mutates courses in place.
    Returns True if the config was modified.
    """
    dirty = False
    while True:
        print(
            "\n--- Course Management ---\n"
            "1) Add course\n"
            "2) Modify course\n"
            "3) Delete course\n"
            "4) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            _add_course(courses)
            dirty = True
        elif choice == "2":
            _modify_course(courses)
            dirty = True
        elif choice == "3":
            _delete_course(courses)
            dirty = True
        elif choice == "4":
            return dirty
        else:
            print("Invalid choice. Please enter 1–4.")

