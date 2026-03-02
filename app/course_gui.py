'''
    File: course_gui.py
    Date: 02/27/2026
    Author: Shane del Villar
    Class: CMSC 420
    Description: Course management dialogs and helpers for the GUI.
'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QWidget,
)


class CourseFormDialog(QDialog):
    """Dialog for creating or editing a single course entry."""

    def __init__(self, parent: Optional[QWidget] = None, course: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Course Details")

        self.course_id_edit = QLineEdit(self)
        self.credits_spin = QSpinBox(self)
        self.credits_spin.setRange(0, 20)

        self.rooms_edit = QLineEdit(self)
        self.labs_edit = QLineEdit(self)
        self.conflicts_edit = QLineEdit(self)
        self.faculty_edit = QLineEdit(self)

        form = QFormLayout(self)
        form.addRow("Course ID:", self.course_id_edit)
        form.addRow("Credits:", self.credits_spin)
        form.addRow("Rooms (comma-separated):", self.rooms_edit)
        form.addRow("Labs (comma-separated):", self.labs_edit)
        form.addRow("Conflicts (course IDs, comma-separated):", self.conflicts_edit)
        form.addRow("Faculty (comma-separated):", self.faculty_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if course is not None:
            self._populate_from_course(course)

    def _populate_from_course(self, course: Dict[str, Any]) -> None:
        self.course_id_edit.setText(str(course.get("course_id", "")))
        self.credits_spin.setValue(int(course.get("credits", 0) or 0))
        self.rooms_edit.setText(", ".join(course.get("room", []) or []))
        self.labs_edit.setText(", ".join(course.get("lab", []) or []))
        self.conflicts_edit.setText(", ".join(course.get("conflicts", []) or []))
        self.faculty_edit.setText(", ".join(course.get("faculty", []) or []))

    def _on_accept(self) -> None:
        if not self.course_id_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Course ID is required.")
            return
        self.accept()

    def _parse_csv_field(self, text: str) -> List[str]:
        parts = [p.strip() for p in text.split(",")]
        return [p for p in parts if p]

    def get_course_data(self) -> Dict[str, Any]:
        """Return a dict compatible with the JSON config structure."""
        return {
            "course_id": self.course_id_edit.text().strip(),
            "credits": int(self.credits_spin.value()),
            "room": self._parse_csv_field(self.rooms_edit.text()),
            "lab": self._parse_csv_field(self.labs_edit.text()),
            "conflicts": self._parse_csv_field(self.conflicts_edit.text()),
            "faculty": self._parse_csv_field(self.faculty_edit.text()),
        }


class CourseConfigManager:
    """
    Helper to load, modify, and save course entries in a scheduler config JSON file.
    """

    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self._config_data: Dict[str, Any] = {}

    def _ensure_config_loaded(self, parent: QWidget) -> bool:
        """
        Ensure a config file is loaded.
        If none is loaded yet, prompt the user to choose one.
        """
        if self.config_path is None:
            filename, _ = QFileDialog.getOpenFileName(
                parent,
                "Select Scheduler Config JSON",
                "",
                "JSON Files (*.json);;All Files (*)",
            )
            if not filename:
                return False
            self.config_path = Path(filename)

        if not self._config_data:
            try:
                text = self.config_path.read_text(encoding="utf-8")
                self._config_data = json.loads(text)
            except FileNotFoundError:
                QMessageBox.critical(
                    parent,
                    "Config not found",
                    f"Config file not found:\n{self.config_path}",
                )
                self.config_path = None
                self._config_data = {}
                return False
            except json.JSONDecodeError as e:
                QMessageBox.critical(
                    parent,
                    "Invalid JSON",
                    f"Failed to parse JSON:\n{e}",
                )
                self.config_path = None
                self._config_data = {}
                return False

        return True

    def _get_courses_list(self) -> List[Dict[str, Any]]:
        cfg = self._config_data.setdefault("config", {})
        courses = cfg.setdefault("courses", [])
        # Ensure list of dicts
        if not isinstance(courses, list):
            cfg["courses"] = []
        return cfg["courses"]

    def _save(self, parent: QWidget) -> None:
        if self.config_path is None:
            return
        try:
            self.config_path.write_text(json.dumps(self._config_data, indent=2), encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(
                parent,
                "Save failed",
                f"Failed to save config:\n{e}",
            )
            return
        QMessageBox.information(
            parent,
            "Config saved",
            f"Configuration saved to:\n{self.config_path}",
        )

    def _select_course(self, parent: QWidget) -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
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
        if not self._ensure_config_loaded(parent):
            return
        dialog = CourseFormDialog(parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        course_data = dialog.get_course_data()
        courses = self._get_courses_list()
        courses.append(course_data)
        self._save(parent)

    def modify_course_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return
        index, existing = self._select_course(parent)
        if index is None or existing is None:
            return
        dialog = CourseFormDialog(parent, existing)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.get_course_data()
        courses = self._get_courses_list()
        if 0 <= index < len(courses):
            courses[index] = updated
            self._save(parent)

    def delete_course_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
            self._save(parent)

