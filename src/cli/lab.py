"""
Lab Management System
Author: Mohamed Mussa
Course: CSCI 420
Description:
This program allows the user to display, add, remove, and modify lab sections
stored in a text file (section.txt).
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from .common import prompt


@dataclass
class Lab:
    name: str

    @classmethod
    def from_raw(cls, raw: Any) -> "Lab":
        return cls(name=str(raw).strip())

    def to_raw(self) -> Any:
        return self.name


def _lab_exists(labs: List[Lab], name: str) -> bool:
    return any(l.name == name for l in labs)


def _list_labs(labs: List[Lab]) -> None:
    if not labs:
        print("No labs in config.")
        return
    print("\nCurrent labs:")
    for idx, lab in enumerate(labs):
        print(f"[{idx}] {lab.name}")
    print()


def _choose_lab_index(labs: List[Lab]) -> Optional[int]:
    if not labs:
        print("No labs to select.")
        return None
    _list_labs(labs)
    while True:
        raw = prompt("Enter lab index (blank to cancel)", "")
        if raw == "":
            return None
        try:
            idx = int(raw)
            if 0 <= idx < len(labs):
                return idx
            print(f"Index out of range. Enter 0–{len(labs) - 1}.")
        except ValueError:
            print("Please enter a valid integer index.")


def _add_lab(labs: List[Lab]) -> None:
    print("\nAdd new lab")
    while True:
        name = prompt("Lab name (e.g. Linux, Mac)").strip()
        if not name:
            print("Lab name is required.")
            continue
        if _lab_exists(labs, name):
            print("A lab with that name already exists.")
            continue
        break
    labs.append(Lab(name=name))
    print("Lab added.")


def _modify_lab(labs: List[Lab]) -> None:
    idx = _choose_lab_index(labs)
    if idx is None:
        return
    current = labs[idx]
    print(f"\nModify lab: {current.name}")
    name = prompt("Lab name", current.name).strip() or current.name
    labs[idx] = Lab(name=name)
    print("Lab updated.")


def _delete_lab(labs: List[Lab]) -> None:
    idx = _choose_lab_index(labs)
    if idx is None:
        return
    lab = labs[idx]
    confirm = prompt(f"Delete lab [{idx}] {lab.name}? Type 'yes' to confirm", "")
    if confirm.lower() == "yes":
        del labs[idx]
        print("Lab removed from config.")
    else:
        print("Delete cancelled.")


def run_lab_management(labs: List[Lab]) -> bool:
    """
    Run the Lab Management submenu.
    Mutates labs in place.
    Returns True if the config was modified.
    """
    dirty = False
    while True:
        print(
            "\n--- Lab Management ---\n"
            "1) Add lab\n"
            "2) Modify lab\n"
            "3) Delete lab\n"
            "4) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            _add_lab(labs)
            dirty = True
        elif choice == "2":
            _modify_lab(labs)
            dirty = True
        elif choice == "3":
            _delete_lab(labs)
            dirty = True
        elif choice == "4":
            return dirty
        else:
            print("Invalid choice. Please enter 1–4.")
