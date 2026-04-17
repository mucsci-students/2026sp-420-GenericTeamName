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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .ui_styles import SchedulerStyles


def _faculty_display_name(entry: Any) -> str:
    if isinstance(entry, dict):
        return str(entry.get("name", entry))
    return str(entry)


class CourseFormDialog(QDialog):
    """Dialog for creating or editing a single course entry."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        course: Optional[Dict[str, Any]] = None,
        pick_lists: Optional[Dict[str, List[str]]] = None,
        exclude_conflict_course_id: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Course Details")
        self.setMinimumWidth(520)
        self.resize(560, 560)

        self._pick_lists = pick_lists or {}
        self._exclude_conflict = (exclude_conflict_course_id or "").strip()

        # Rooms / labs / faculty / conflicts — created only in the branch that uses them
        # (orphan QLineEdits as children of the dialog with no layout appear top-left).
        self._rooms_list: Optional[QListWidget] = None
        self._rooms_extra: Optional[QLineEdit] = None
        self._labs_list: Optional[QListWidget] = None
        self._labs_extra: Optional[QLineEdit] = None
        self._faculty_list: Optional[QListWidget] = None
        self._faculty_extra: Optional[QLineEdit] = None
        self._conflicts_list: Optional[QListWidget] = None
        self._conflicts_extra: Optional[QLineEdit] = None
        self._rooms_fallback: Optional[QLineEdit] = None
        self._labs_fallback: Optional[QLineEdit] = None
        self._faculty_fallback: Optional[QLineEdit] = None
        self._conflicts_fallback: Optional[QLineEdit] = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        self.course_id_edit = QLineEdit(inner)
        self.credits_spin = QSpinBox(inner)
        self.credits_spin.setRange(0, 20)
        form = QVBoxLayout(inner)

        id_row = QFormLayout()
        id_row.addRow("Course ID:", self.course_id_edit)
        id_row.addRow("Credits:", self.credits_spin)
        form.addLayout(id_row)

        pre = self._preselected_from_course(course)

        form.addWidget(self._section_rooms(pre["rooms"]))
        form.addWidget(self._section_labs(pre["labs"]))
        form.addWidget(self._section_faculty(pre["faculty"]))
        form.addWidget(self._section_conflicts(pre["conflicts"]))

        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        if course is not None:
            self._populate_from_course(course)

        SchedulerStyles.apply_high_contrast_shell(self, inner, scroll)

    def _preselected_from_course(self, course: Optional[Dict[str, Any]]) -> Dict[str, set]:
        if not course:
            return {"rooms": set(), "labs": set(), "faculty": set(), "conflicts": set()}
        return {
            "rooms": set(course.get("room", []) or []),
            "labs": set(course.get("lab", []) or []),
            "faculty": set(course.get("faculty", []) or []),
            "conflicts": set(course.get("conflicts", []) or []),
        }

    def _make_checklist(self, items: List[str], selected: set[str]) -> QListWidget:
        w = QListWidget()
        row_h = 22
        visible = min(len(items), 8)
        w.setMinimumHeight(max(80, visible * row_h + 8))
        for x in sorted(items, key=str.casefold):
            it = QListWidgetItem(x)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(
                Qt.CheckState.Checked if x in selected else Qt.CheckState.Unchecked
            )
            w.addItem(it)
        return w

    def _extra_row(self, label: str, edit: QLineEdit, tip: str) -> QWidget:
        row = QWidget()
        lay = QFormLayout(row)
        lay.setContentsMargins(8, 0, 0, 8)
        edit.setPlaceholderText(tip)
        lay.addRow(QLabel(label), edit)
        return row

    def _section_rooms(self, pre: set[str]) -> QGroupBox:
        box = QGroupBox("Rooms this course may use")
        lay = QVBoxLayout(box)
        rooms = self._pick_lists.get("rooms") or []
        if rooms:
            self._rooms_list = self._make_checklist(rooms, pre)
            self._rooms_extra = QLineEdit(box)
            lay.addWidget(QLabel("Tick all that apply (from your config)."))
            lay.addWidget(self._rooms_list)
            lay.addWidget(
                self._extra_row(
                    "Additional rooms (comma-separated)",
                    self._rooms_extra,
                    "Any room names not listed above",
                )
            )
        else:
            self._rooms_fallback = QLineEdit(box)
            lay.addWidget(
                QLabel("No rooms are defined in the config yet — enter names manually.")
            )
            lay.addWidget(self._rooms_fallback)
        return box

    def _section_labs(self, pre: set[str]) -> QGroupBox:
        box = QGroupBox("Labs this course may use")
        lay = QVBoxLayout(box)
        labs = self._pick_lists.get("labs") or []
        if labs:
            self._labs_list = self._make_checklist(labs, pre)
            self._labs_extra = QLineEdit(box)
            lay.addWidget(QLabel("Tick all that apply (from your config)."))
            lay.addWidget(self._labs_list)
            lay.addWidget(
                self._extra_row(
                    "Additional labs (comma-separated)",
                    self._labs_extra,
                    "Any lab names not listed above",
                )
            )
        else:
            self._labs_fallback = QLineEdit(box)
            lay.addWidget(
                QLabel("No labs are defined in the config yet — enter names manually.")
            )
            lay.addWidget(self._labs_fallback)
        return box

    def _section_faculty(self, pre: set[str]) -> QGroupBox:
        box = QGroupBox("Faculty")
        lay = QVBoxLayout(box)
        fac = self._pick_lists.get("faculty") or []
        if fac:
            self._faculty_list = self._make_checklist(fac, pre)
            self._faculty_extra = QLineEdit(box)
            lay.addWidget(QLabel("Tick all instructors (from your config)."))
            lay.addWidget(self._faculty_list)
            lay.addWidget(
                self._extra_row(
                    "Additional faculty (comma-separated)",
                    self._faculty_extra,
                    "Names must match how they appear in the faculty list",
                )
            )
        else:
            self._faculty_fallback = QLineEdit(box)
            lay.addWidget(
                QLabel("No faculty are defined in the config yet — enter names manually.")
            )
            lay.addWidget(self._faculty_fallback)
        return box

    def _section_conflicts(self, pre: set[str]) -> QGroupBox:
        box = QGroupBox("Cannot overlap with these courses (conflicts)")
        lay = QVBoxLayout(box)
        ids = list(self._pick_lists.get("conflict_course_ids") or [])
        if self._exclude_conflict:
            ids = [i for i in ids if i != self._exclude_conflict]
        if ids:
            self._conflicts_list = self._make_checklist(ids, pre)
            self._conflicts_extra = QLineEdit(box)
            lay.addWidget(
                QLabel("Tick course IDs that must not run at the same time as this course.")
            )
            lay.addWidget(self._conflicts_list)
            lay.addWidget(
                self._extra_row(
                    "Additional conflict IDs (comma-separated)",
                    self._conflicts_extra,
                    "Course IDs not shown above",
                )
            )
        else:
            self._conflicts_fallback = QLineEdit(box)
            lay.addWidget(
                QLabel("No other courses in config — add more courses first, or type IDs.")
            )
            lay.addWidget(self._conflicts_fallback)
        return box

    def _extras_not_in_catalog(self, selected: set[str], catalog: List[str]) -> str:
        cat = set(catalog)
        extra = [x for x in selected if x not in cat]
        return ", ".join(extra)

    def _populate_from_course(self, course: Dict[str, Any]) -> None:
        self.course_id_edit.setText(str(course.get("course_id", "")))
        self.credits_spin.setValue(int(course.get("credits", 0) or 0))
        pre = self._preselected_from_course(course)
        rooms_cat = self._pick_lists.get("rooms") or []
        labs_cat = self._pick_lists.get("labs") or []
        fac_cat = self._pick_lists.get("faculty") or []
        conf_cat = self._pick_lists.get("conflict_course_ids") or []

        if self._rooms_list is None:
            if self._rooms_fallback is not None:
                self._rooms_fallback.setText(", ".join(course.get("room", []) or []))
        else:
            x = self._extras_not_in_catalog(pre["rooms"], rooms_cat)
            if x and self._rooms_extra is not None:
                self._rooms_extra.setText(x)

        if self._labs_list is None:
            if self._labs_fallback is not None:
                self._labs_fallback.setText(", ".join(course.get("lab", []) or []))
        else:
            x = self._extras_not_in_catalog(pre["labs"], labs_cat)
            if x and self._labs_extra is not None:
                self._labs_extra.setText(x)

        if self._faculty_list is None:
            if self._faculty_fallback is not None:
                self._faculty_fallback.setText(", ".join(course.get("faculty", []) or []))
        else:
            x = self._extras_not_in_catalog(pre["faculty"], fac_cat)
            if x and self._faculty_extra is not None:
                self._faculty_extra.setText(x)

        if self._conflicts_list is None:
            if self._conflicts_fallback is not None:
                self._conflicts_fallback.setText(", ".join(course.get("conflicts", []) or []))
        else:
            x = self._extras_not_in_catalog(pre["conflicts"], conf_cat)
            if x and self._conflicts_extra is not None:
                self._conflicts_extra.setText(x)

    def _on_accept(self) -> None:
        if not self.course_id_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Course ID is required.")
            return
        self.accept()

    def _parse_csv_field(self, text: str) -> List[str]:
        parts = [p.strip() for p in text.split(",")]
        return [p for p in parts if p]

    def _merge_pick(
        self,
        checklist: Optional[QListWidget],
        fallback: Optional[QLineEdit],
        extra: Optional[QLineEdit],
    ) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()

        def add_one(s: str) -> None:
            s = s.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)

        if checklist is not None:
            for i in range(checklist.count()):
                it = checklist.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    add_one(it.text())
            extra_txt = extra.text() if extra is not None else ""
            for p in self._parse_csv_field(extra_txt):
                add_one(p)
        else:
            fb_txt = fallback.text() if fallback is not None else ""
            for p in self._parse_csv_field(fb_txt):
                add_one(p)
        return out

    def _merge_conflicts(self) -> List[str]:
        if self._conflicts_list is not None:
            return self._merge_pick(
                self._conflicts_list,
                self._conflicts_fallback,
                self._conflicts_extra,
            )
        if self._conflicts_fallback is not None:
            return self._parse_csv_field(self._conflicts_fallback.text())
        return []

    def get_course_data(self) -> Dict[str, Any]:
        rooms = self._merge_pick(self._rooms_list, self._rooms_fallback, self._rooms_extra)
        labs = self._merge_pick(self._labs_list, self._labs_fallback, self._labs_extra)
        faculty = self._merge_pick(self._faculty_list, self._faculty_fallback, self._faculty_extra)
        conflicts = self._merge_conflicts()
        return {
            "course_id": self.course_id_edit.text().strip(),
            "credits": int(self.credits_spin.value()),
            "room": rooms,
            "lab": labs,
            "conflicts": conflicts,
            "faculty": faculty,
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
        Use the config file selected via the Change Config File button.
        """
        config_mgr = getattr(parent, "config_mgr", None)
        if config_mgr is None or not getattr(config_mgr, "filepath", None):
            QMessageBox.warning(
                parent,
                "No Config",
                "Please select a config file first using the Change Config File button."
            )
            return False
        try:
            config_mgr.load()
        except Exception as e:
            QMessageBox.critical(
                parent,
                "Config Error",
                f"Could not load config:\n{e}",
            )
            return False
        self.config_path = Path(config_mgr.filepath)
        self._config_data = config_mgr.data
        return True

    def _get_courses_list(self) -> List[Dict[str, Any]]:
        cfg = self._config_data.setdefault("config", {})
        courses = cfg.setdefault("courses", [])
        # Ensure list of dicts
        if not isinstance(courses, list):
            cfg["courses"] = []
        return cfg["courses"]

    def _get_pick_lists(self, exclude_course_id_for_conflicts: Optional[str] = None) -> Dict[str, List[str]]:
        cfg = self._config_data.get("config", {}) or {}
        rooms = [str(r) for r in (cfg.get("rooms") or []) if r is not None]
        labs = [str(l) for l in (cfg.get("labs") or []) if l is not None]
        faculty: List[str] = []
        for f in cfg.get("faculty") or []:
            faculty.append(_faculty_display_name(f))
        course_ids: List[str] = []
        ex = (exclude_course_id_for_conflicts or "").strip()
        for c in cfg.get("courses") or []:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("course_id", "")).strip()
            if cid and cid != ex:
                course_ids.append(cid)
        return {
            "rooms": sorted(set(rooms), key=str.casefold),
            "labs": sorted(set(labs), key=str.casefold),
            "faculty": sorted(set(faculty), key=str.casefold),
            "conflict_course_ids": sorted(set(course_ids), key=str.casefold),
        }

    def _save(self, parent: QWidget) -> None:
        config_mgr = getattr(parent, "config_mgr", None)
        if config_mgr:
            config_mgr.data = self._config_data
            config_mgr.save(parent)
        else:
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
            "Configuration saved.",
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
        pick = self._get_pick_lists(exclude_course_id_for_conflicts=None)
        dialog = CourseFormDialog(parent, course=None, pick_lists=pick)
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
        cid = str(existing.get("course_id", "")).strip()
        pick = self._get_pick_lists(exclude_course_id_for_conflicts=cid)
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
