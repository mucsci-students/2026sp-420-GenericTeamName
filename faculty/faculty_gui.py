'''
    File: faculty_gui.py
    Date: 04/17/2026
    Author: Damion Crawford, Tyler Strohl, & Shane del Villar
    Class: CMSC 420
    Description: Faculty management dialogs and helpers for the GUI.
'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from app.ui_styles import SchedulerStyles

WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI")

#TODO: Clean up this class. It is way too long & redundant.
class FacultyFormDialog(QDialog):
    """Add/edit faculty with pick lists from config (like course form)."""

    def __init__(
        self, parent: Optional[QWidget] = None,
        faculty: Optional[Dict[str, Any]] = None,
        pick_lists: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        
        super().__init__(parent)
        self.setWindowTitle("Faculty Details")
        self.setMinimumWidth(520)
        self.resize(560, 680)

        self._pick_lists = pick_lists or {}

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        inner = QWidget()
        inner.setMinimumWidth(500)

        main = QVBoxLayout(self)
        main.setSpacing(0)
        main.setContentsMargins(14, 14, 14, 14)
        main.addWidget(scroll, 1)

        form = QVBoxLayout(inner)
        form.setSpacing(10)
        form.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_edit = QLineEdit(inner)
        self.min_credit_edit = QLineEdit(inner)
        self.max_credit_edit = QLineEdit(inner)
        self.courses_taught_edit = QLineEdit(inner)

        self._days_list = self._make_day_checklist(self._pre_days(faculty))

        self._times_edit = QLineEdit(inner)
        self._times_edit.setPlaceholderText(
            "Comma-separated, one range per checked weekday in MON→FRI order (skip unchecked days)"
        )

        self.course_weight_spin = QSpinBox(inner)
        self.course_weight_spin.setRange(1, 10)
        self.room_weight_spin = QSpinBox(inner)
        self.room_weight_spin.setRange(1, 10)
        self.lab_weight_spin = QSpinBox(inner)
        self.lab_weight_spin.setRange(1, 10)

        self._course_list: Optional[QListWidget] = None
        self._course_extra: Optional[QLineEdit] = None
        self._room_list: Optional[QListWidget] = None
        self._room_extra: Optional[QLineEdit] = None
        self._lab_list: Optional[QListWidget] = None
        self._lab_extra: Optional[QLineEdit] = None

        basics = QGroupBox("Basics", inner)
        bf = QFormLayout(basics)
        bf.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        bf.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        bf.addRow("Faculty name:", self.name_edit)
        bf.addRow("Minimum credits:", self.min_credit_edit)
        bf.addRow("Maximum credits:", self.max_credit_edit)
        bf.addRow("Unique course limit:", self.courses_taught_edit)
        form.addWidget(basics)

        avail = QGroupBox("Availability (weekdays)", inner)
        av = QVBoxLayout(avail)
        _lbl_days = QLabel("Tick days this faculty is available.")
        _lbl_days.setWordWrap(True)
        av.addWidget(_lbl_days)
        av.addWidget(self._days_list)
        _lbl_times = QLabel(
            "Time ranges — one per checked day, MON→FRI order (e.g. MON & WED: 09:00-12:00, 14:00-17:00)."
        )
        _lbl_times.setWordWrap(True)
        av.addWidget(_lbl_times)
        av.addWidget(self._times_edit)
        form.addWidget(avail)

        form.addWidget(self._section_weighted_prefs(
            "Course preferences",
            inner,
            "course_ids",
            self.course_weight_spin,
            "course",
        ))
        form.addWidget(self._section_weighted_prefs(
            "Room preferences",
            inner,
            "rooms",
            self.room_weight_spin,
            "room",
        ))
        form.addWidget(self._section_weighted_prefs(
            "Lab preferences",
            inner,
            "labs",
            self.lab_weight_spin,
            "lab",
        ))

        scroll.setWidget(inner)

        fac_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        fac_buttons.accepted.connect(self.on_accept)
        fac_buttons.rejected.connect(self.reject)
        main.addWidget(fac_buttons, 0, Qt.AlignmentFlag.AlignRight)

        if faculty is not None:
            self.populate_from_faculty(faculty)

        SchedulerStyles.apply_high_contrast_shell(self, inner, scroll)

    def _pre_days(self, faculty: Optional[Dict[str, Any]]) -> Set[str]:
        if not faculty:
            return set()
        md = faculty.get("mandatory_days")
        if isinstance(md, list) and md:
            return {str(d).strip().upper() for d in md}
        td = faculty.get("times") or {}
        if isinstance(td, dict):
            return {str(k).strip().upper() for k in td.keys() if k}
        return set()

    def _make_day_checklist(self, selected: Set[str]) -> QListWidget:
        w = QListWidget()
        w.setFixedHeight(100)
        sel = {d.strip().upper() for d in selected}
        for d in WEEKDAYS:
            it = QListWidgetItem(d)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(
                Qt.CheckState.Checked if d in sel else Qt.CheckState.Unchecked
            )
            w.addItem(it)
        return w

    def _section_weighted_prefs(
        self,
        title: str,
        parent: QWidget,
        list_key: str,
        weight_spin: QSpinBox,
        kind: str,
    ) -> QGroupBox:
        box = QGroupBox(title, parent)
        lay = QVBoxLayout(box)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        catalog = self._pick_lists.get(list_key) or []

        if catalog:
            extra = QLineEdit(box)
            extra.setPlaceholderText(f"Additional {kind} preferences as name:weight, …")
            lw = QListWidget(box)
            lw.setFixedHeight(120)
            for x in sorted(catalog, key=str.casefold):
                it = QListWidgetItem(x)
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Unchecked)
                lw.addItem(it)
            if kind == "course":
                self._course_list = lw
                self._course_extra = extra
            elif kind == "room":
                self._room_list = lw
                self._room_extra = extra
            else:
                self._lab_list = lw
                self._lab_extra = extra
            kind_plural = {"course": "courses", "room": "rooms", "lab": "labs"}[kind]
            _h = QLabel(
                f"Tick {kind_plural} from your config; default weight applies to checked rows."
            )
            _h.setWordWrap(True)
            lay.addWidget(_h)
            lay.addWidget(lw)
            lay.addWidget(QLabel("Additional (comma-separated, name:weight):"))
            lay.addWidget(extra)
        else:
            fallback = QLineEdit(box)
            fallback.setPlaceholderText(f"No {kind}s in config — enter as name:weight, …")
            if kind == "course":
                self._course_extra = fallback
            elif kind == "room":
                self._room_extra = fallback
            else:
                self._lab_extra = fallback
            lay.addWidget(
                QLabel(f"No {kind}s listed in config — enter preferences manually.")
            )
            lay.addWidget(fallback)

        wlabel = "Default preference weight:"
        lay.addWidget(QLabel(wlabel))
        lay.addWidget(weight_spin)
        return box

    def populate_from_faculty(self, faculty: Dict[str, Any]) -> None:
        self.name_edit.setText(str(faculty.get("name") or ""))
        self.min_credit_edit.setText(str(faculty.get("minimum_credits") or 0))
        self.max_credit_edit.setText(str(faculty.get("maximum_credits") or 0))
        self.courses_taught_edit.setText(str(faculty.get("unique_course_limit") or 0))

        times_dict = faculty.get("times", {}) or {}
        parts: List[str] = []
        for d in WEEKDAYS:
            if d in times_dict and times_dict[d]:
                parts.append(str(times_dict[d][0]))
        self._times_edit.setText(", ".join(parts))

        cp = faculty.get("course_preferences") or {}
        rp = faculty.get("room_preferences") or {}
        lp = faculty.get("lab_preferences") or {}

        self._populate_weighted_prefs(cp, self._course_list, self._course_extra, self.course_weight_spin, "course_ids")
        self._populate_weighted_prefs(rp, self._room_list, self._room_extra, self.room_weight_spin, "rooms")
        self._populate_weighted_prefs(lp, self._lab_list, self._lab_extra, self.lab_weight_spin, "labs")

    def _populate_weighted_prefs(
        self,
        prefs: Any,
        checklist: Optional[QListWidget],
        extra_or_fallback: Optional[QLineEdit],
        spin: QSpinBox,
        catalog_key: str,
    ) -> None:
        if not isinstance(prefs, dict) or not prefs:
            return
        catalog = set(self._pick_lists.get(catalog_key) or [])
        weights = list(prefs.values())
        if weights:
            w0 = int(weights[0])
            spin.setValue(w0)
            same = all(int(v) == w0 for v in weights)
        else:
            same = True

        if checklist is not None:
            for i in range(checklist.count()):
                it = checklist.item(i)
                name = it.text()
                if name in prefs:
                    it.setCheckState(Qt.CheckState.Checked)
            extra_parts: List[str] = []
            for k, v in prefs.items():
                if k not in catalog:
                    extra_parts.append(f"{k}:{v}")
                elif not same and int(v) != spin.value():
                    extra_parts.append(f"{k}:{v}")
            if extra_parts and extra_or_fallback is not None:
                extra_or_fallback.setText(", ".join(extra_parts))
        else:
            if extra_or_fallback is not None:
                extra_or_fallback.setText(
                    ", ".join(f"{k}:{v}" for k, v in prefs.items())
                )

    def on_accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Name is required.")
            return
        if not self.min_credit_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Minimum credits are required.")
            return
        if not self.max_credit_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Maximum credits are required.")
            return
        if not self.courses_taught_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Number of courses taught is required.")
            return
        checked_days = self._checked_weekdays()
        if not checked_days:
            QMessageBox.warning(self, "Missing data", "Select at least one weekday.")
            return
        times_parts = self.parse_csv_field(self._times_edit.text())
        if len(times_parts) < len(checked_days):
            QMessageBox.warning(
                self,
                "Missing data",
                "Enter a time range for each checked weekday (comma-separated, same order as MON→FRI).",
            )
            return
        self.accept()

    def parse_csv_field(self, text: str) -> List[str]:
        parts = [p.strip() for p in text.split(",")]
        return [p for p in parts if p]

    def parse_weighted_csv(self, text: str, default_weight: int) -> Dict[str, int]:
        result: Dict[str, int] = {}
        parts = [p.strip() for p in text.split(",") if p.strip()]
        for part in parts:
            if ":" in part:
                name_part, weight_part = part.rsplit(":", 1)
                try:
                    result[name_part.strip()] = int(weight_part.strip())
                except ValueError:
                    result[name_part.strip()] = default_weight
            else:
                result[part] = default_weight
        return result

    def _checked_weekdays(self) -> List[str]:
        checked: Set[str] = set()
        for i in range(self._days_list.count()):
            it = self._days_list.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                checked.add(it.text())
        return [d for d in WEEKDAYS if d in checked]

    def _merge_weighted(
        self,
        checklist: Optional[QListWidget],
        extra_fallback: Optional[QLineEdit],
        spin: QSpinBox,
    ) -> Dict[str, int]:
        d: Dict[str, int] = {}
        if checklist is not None:
            for i in range(checklist.count()):
                it = checklist.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    d[it.text()] = spin.value()
            if extra_fallback is not None:
                d.update(self.parse_weighted_csv(extra_fallback.text(), spin.value()))
        else:
            if extra_fallback is not None:
                d = self.parse_weighted_csv(extra_fallback.text(), spin.value())
        return d

    def get_faculty_data(self) -> Dict[str, Any]:
        checked_days = self._checked_weekdays()
        time_list = self.parse_csv_field(self._times_edit.text())
        times_dict: Dict[str, List[str]] = {}
        for idx, day in enumerate(checked_days):
            slot = [time_list[idx]] if idx < len(time_list) else []
            times_dict[day] = slot

        return {
            "name": self.name_edit.text().strip(),
            "maximum_credits": int(self.max_credit_edit.text().strip() or 0),
            "minimum_credits": int(self.min_credit_edit.text().strip() or 0),
            "unique_course_limit": int(self.courses_taught_edit.text().strip() or 0),
            "maximum_days": len(checked_days),
            "mandatory_days": checked_days,
            "times": times_dict,
            "course_preferences": self._merge_weighted(
                self._course_list, self._course_extra, self.course_weight_spin
            ),
            "room_preferences": self._merge_weighted(
                self._room_list, self._room_extra, self.room_weight_spin
            ),
            "lab_preferences": self._merge_weighted(
                self._lab_list, self._lab_extra, self.lab_weight_spin
            ),
        }


class FacultyManager:
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
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr

    def _get_faculty_list(self) -> List[Dict[str, Any]]:
        """Retrieve the list of faculty from the config file."""
        return self.config_mgr.data["config"]["faculty"]

    #TODO: This function should only be written in one class. Fix that.
    def _get_pick_lists(self, exclude_course_id_for_conflicts: Optional[str] = None) -> Dict[str, List[str]]:
        """Provides lists for rooms, labs, & faculty for drop-down menus."""
        data = self.config_mgr.data["config"]
        
        #Retrieve lists of rooms, labs, faculty for drop-down options.
        rooms = [str(r) for r in data["rooms"] if r is not None]
        labs = [str(l) for l in data["labs"] if l is not None]
        faculty = [self.faculty_display_name(f) for f in data["faculty"]]

        #Filter out the current course ID.
        ex = (exclude_course_id_for_conflicts or "").strip()
        course_ids = [
            str(c["course_id"]).strip() 
            for c in data["courses"] 
            if isinstance(c, dict) and str(c.get("course_id", "")).strip() != ex
        ]

        return {
            "rooms": sorted(set(rooms), key=str.casefold),
            "labs": sorted(set(labs), key=str.casefold),
            "faculty": sorted(set(faculty), key=str.casefold),
            "conflict_course_ids": sorted(set(course_ids), key=str.casefold),
        }

    def faculty_display_name(self, f: Any) -> str:
        """Get display string for a faculty item (usually the 'name' key)."""
        if isinstance(f, dict):
            return str(f.get("name", "Unknown Faculty"))
        return str(f)
        
    def select_faculty(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
        """Retrieves a specific faculty from list of faculty."""
        faculty_list = self._get_faculty_list()

        if not faculty_list:
            QMessageBox.information(parent, "No faculty", "No faculty found in the config.")
            return None, None

        # labels is for the selection dropdown
        labels = [self.faculty_display_name(f) for f in faculty_list]

        item, ok = QInputDialog.getItem(
            parent, "Select Faculty", "Faculty:", labels, 0, False
        )

        if not ok or not item:
            return None, None

        return labels.index(item), item

    def add_faculty_via_dialog(self, parent: QWidget) -> None:
        """Add a new faculty member to config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return
        
        pick = self._get_pick_lists()
        dialog = FacultyFormDialog(parent, faculty=None, pick_lists=pick)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            faculty_data = dialog.get_faculty_data()
            faculty_list = self._get_faculty_list()      
            faculty_list.append(faculty_data)
            self.config_mgr.save(parent)

    def modify_faculty_via_dialog(self, parent: QWidget) -> None:
        """Modify a faculty member in the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return
        
        index, name = self.select_faculty(parent)
        if index is None:
            return

        faculty_list = self._get_faculty_list()     
        existing_data = faculty_list[index]

        pick = self._get_pick_lists()
        dialog = FacultyFormDialog(parent, faculty=existing_data, pick_lists=pick)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_faculty_data()
            faculty_list[index] = updated
            self.config_mgr.save(parent)

    def delete_faculty_via_dialog(self, parent: QWidget) -> None:
        """Remove a faculty member from the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return
        
        index, name = self.select_faculty(parent)
        if index is None:
            return

        reply = QMessageBox.question(
            parent, "Confirm delete",
            f"Delete faculty member '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            faculty_list = self._get_faculty_list()     
            faculty_list.pop(index)
            self.config_mgr.save(parent)
