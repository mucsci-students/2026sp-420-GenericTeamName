'''
    File: course_gui.py
    Date: 04/18/2026
    Author: Shane del Villar & Tyler Strohl
    Class: CMSC 420
    Description: Course management dialogs and helpers for the GUI.
'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QGroupBox, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QScrollArea,
    QSpinBox, QVBoxLayout, QWidget,
)
from gui.ui_styles import SchedulerStyles

class CourseFormDialog(QDialog):
    """
    Add/edit courses with pick lists from config (mirrors Faculty setup).
    
    This class implements the following design patterns:
        -Dependency Injection
        -Template Logic
        -Memento
        -Command
    """

    def __init__(
        self, parent: Optional[QWidget] = None,
        course: Optional[Dict[str, Any]] = None,
        pick_lists: Optional[Dict[str, List[str]]] = None,
        exclude_conflict_course_id: Optional[str] = None, # Unique to Course
    ) -> None:
        super().__init__(parent)
        self._pick_lists = pick_lists or {}
        self._exclude_conflict = (exclude_conflict_course_id or "").strip()

        self.setMinimumWidth(520)
        self.resize(560, 680)
        
        self._setup_containers()
        self._init_form_widgets(course)
        self._assemble_form_sections()

        self._add_button_box()
        if course:
            self.populate_from_course(course)
        
        SchedulerStyles.apply_high_contrast_shell(self, self.inner, self.scroll)

    # --- UI SETUP METHODS ---

    def _setup_containers(self):
        """Builds the main scrollable skeleton (identical to Faculty)."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        self.inner = QWidget()
        self.form_layout = QVBoxLayout(self.inner)
        self.form_layout.setSpacing(10)
        self.form_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.inner)
        self.main_layout.addWidget(self.scroll, 1)

    def _init_form_widgets(self, course):
        """Initializes raw input variables (No weights)."""
        self.course_id_edit = QLineEdit(self.inner)
        self.credits_spin = QSpinBox(self.inner)
        self.credits_spin.setRange(0, 20)

        self._rooms_list = self._rooms_extra = None
        self._labs_list = self._labs_extra = None
        self._faculty_list = self._faculty_extra = None
        self._conflicts_list = self._conflicts_extra = None

    def _assemble_form_sections(self):
        """Groups course widgets into visual sections (Weight-free version)."""
        basics = QGroupBox("Course Basics", self.inner)
        bf = QFormLayout(basics)
        bf.addRow("Course ID:", self.course_id_edit)
        bf.addRow("Credits:", self.credits_spin)
        self.form_layout.addWidget(basics)

        prefs = [
            ("Rooms this course may use", "rooms", "rooms"),
            ("Labs this course may use", "labs", "labs"),
            ("Faculty", "faculty", "faculty"),
            ("Cannot overlap with (conflicts)", "course_ids", "conflicts")
        ]
        
        for title, key, kind in prefs:
            section_box = self._add_pref_section(title, key, kind)
            self.form_layout.addWidget(section_box)

    def _add_button_box(self):
        """Standard Dialog buttons."""
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.on_accept)
        bbox.rejected.connect(self.reject)
        self.main_layout.addWidget(bbox, 0, Qt.AlignmentFlag.AlignRight)

    # --- DATA PROCESSING & HELPERS ---

    def _preselected_from_course(self, course: Optional[Dict[str, Any]]) -> Dict[str, set]:
        """Finds what was already saved in the JSON."""
        
        if not course:
            return {"rooms": set(), "labs": set(), "faculty": set(), "conflicts": set()}
        return {
            "rooms": set(course.get("room", []) or []),
            "labs": set(course.get("lab", []) or []),
            "faculty": set(course.get("faculty", []) or []),
            "conflicts": set(course.get("conflicts", []) or []),
        }

    def _populate_section(self, selected_list: List[str], checklist: Optional[QListWidget], 
                          extra_edit: QLineEdit, catalog_key: str) -> None:
        """Checks boxes for items in the config; puts others in the text box."""
        if not isinstance(selected_list, list):
            selected_list = []
            
        catalog = set(self._pick_lists.get(catalog_key) or [])
        
        if checklist:
            for i in range(checklist.count()):
                it = checklist.item(i)
                it.setCheckState(Qt.CheckState.Checked if it.text() in selected_list else Qt.CheckState.Unchecked)

        extras = [x for x in selected_list if x not in catalog]
        extra_edit.setText(", ".join(extras))

    def _add_pref_section(self, title, list_key, kind) -> QGroupBox:
        """Builds a section for Rooms, Labs, etc. without weight spinboxes."""
        box = QGroupBox(title, self.inner)
        lay = QVBoxLayout(box)
        
        catalog = list(self._pick_lists.get(list_key) or [])
        if kind == "conflicts" and self._exclude_conflict:
            catalog = [c for c in catalog if c != self._exclude_conflict]

        extra = QLineEdit(box)
        lw = None

        if catalog:
            lw = QListWidget(box)
            lw.setFixedHeight(120)
            for x in sorted(catalog, key=str.casefold):
                it = QListWidgetItem(x)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Unchecked)
                lw.addItem(it)
            lay.addWidget(QLabel(f"Select {kind}:"))
            lay.addWidget(lw)

        setattr(self, f"_{kind}_list", lw)
        setattr(self, f"_{kind}_extra", extra)

        lay.addWidget(QLabel(f"Additional {kind} (comma-separated):"))
        lay.addWidget(extra)
        return box

    def populate_from_course(self, course: Dict[str, Any]) -> None:
        """Populates UI fields from a course dictionary."""
        self.course_id_edit.setText(str(course.get("course_id") or ""))
        
        try:
            val = int(course.get("credits", 0))
            self.credits_spin.setValue(val)
        except (ValueError, TypeError):
            self.credits_spin.setValue(0)

        prefs_map = {
            "rooms": "room",      
            "labs": "lab",        
            "faculty": "faculty",  
            "conflicts": "conflicts" 
        }

        for ui_kind, json_key in prefs_map.items():
            saved_list = course.get(json_key, []) or []
            
            self._populate_section(
                saved_list,
                getattr(self, f"_{ui_kind}_list"),
                getattr(self, f"_{ui_kind}_extra"),
                "course_ids" if ui_kind == "conflicts" else ui_kind
            )

    def _merge_list(self, checklist, extra_input) -> List[str]:
        """Simple scraper that returns a list of names (No weights)."""
        result = []
        if checklist:
            for i in range(checklist.count()):
                it = checklist.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    result.append(it.text())
        
        if extra_input and extra_input.text().strip():
            for entry in extra_input.text().split(","):
                name = entry.strip()
                if name and name not in result:
                    result.append(name)
        return result

    def get_course_data(self) -> Dict[str, Any]:
        return {
            "course_id": self.course_id_edit.text().strip(),
            "credits": self.credits_spin.value(),
            "room": self._merge_list(self._rooms_list, self._rooms_extra),
            "lab": self._merge_list(self._labs_list, self._labs_extra),
            "faculty": self._merge_list(self._faculty_list, self._faculty_extra),
            "conflicts": self._merge_list(self._conflicts_list, self._conflicts_extra),
        }

    def on_accept(self) -> None:
        """Validation: Ensures Course ID is provided before closing."""
        if not self.course_id_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Course ID is required.")
            return
        self.accept()


class CourseConfigManager:
    """
    Helper to load, modify, and save course entries in a scheduler config JSON file.
    
    This class implements the following design patterns:
        -Dependency Injection
        -Delegation
        -Model-View-Controller (controller)
        -Facade
        -Factory
        -Template Logic
    """

    def __init__(self, config_mgr, viewer_mgr):
        self.config_mgr = config_mgr
        self.viewer_mgr = viewer_mgr

    def _get_courses_list(self) -> List[Dict[str, Any]]:
        """Retrieve the list of courses from the config file."""
        return self.config_mgr.data["config"]["courses"]

    def _select_course(self, parent: QWidget) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        """Retrieves a specific course from list of courses."""
        courses = self._get_courses_list()
        if not courses:
            QMessageBox.information(parent, "No courses", "No courses found in the config.")
            return None, None
        labels = [
            f"{c.get('course_id', '')} ({c.get('credits', '?')} cr)"
            for c in courses
        ]
        item, ok = QInputDialog.getItem(
            parent,
            "Select Course",
            "Course:",
            labels,
            0,
            False,
        )
        if not ok or not item:
            return None, None
        index = labels.index(item)
        return index, courses[index]

    def add_course_via_dialog(self, parent: QWidget) -> None:
        """Add a new course to config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return
        
        pick = self.viewer_mgr._get_pick_lists(exclude_course_id_for_conflicts=None)
        dialog = CourseFormDialog(parent, course=None, pick_lists=pick)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        course_data = dialog.get_course_data()
        courses = self._get_courses_list()
        courses.append(course_data)
        self.config_mgr.save(parent)

    def modify_course_via_dialog(self, parent: QWidget) -> None:
        """Modify a course in the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return
        
        index, existing = self._select_course(parent)
        if index is None or existing is None:
            return
        cid = str(existing.get("course_id", "")).strip()
        pick = self.viewer_mgr._get_pick_lists(exclude_course_id_for_conflicts=cid)
        dialog = CourseFormDialog(
            parent,
            existing,
            pick_lists=pick,
            exclude_conflict_course_id=cid,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.get_course_data()
        courses = self._get_courses_list()
        if 0 <= index < len(courses):
            courses[index] = updated
            self.config_mgr.save(parent)

    def delete_course_via_dialog(self, parent: QWidget) -> None:
        """Remove a course from the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        index, existing = self._select_course(parent)
        if index is None or existing is None:
            return
        course_label = existing.get("course_id", "this course")
        reply = QMessageBox.question(
            parent,
            "Confirm delete",
            f"Delete course '{course_label}' from the config?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        courses = self._get_courses_list()
        if 0 <= index < len(courses):
            del courses[index]
            self.config_mgr.save(parent)