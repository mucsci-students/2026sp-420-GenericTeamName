'''
    File: faculty_gui.py
    Date: 04/18/2026
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
DAYS = ("MON", "TUE", "WED", "THU", "FRI")

class FacultyFormDialog(QDialog):
    """Add/edit faculty with pick lists from config."""

    def __init__(
        self, parent: Optional[QWidget] = None,
        faculty: Optional[Dict[str, Any]] = None,
        pick_lists: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        super().__init__(parent)
        self._pick_lists = pick_lists or {}

        self.setMinimumWidth(520)
        self.resize(560, 680)
        self._setup_containers()
        self._init_form_widgets(faculty)
        self._assemble_form_sections()

        self._add_button_box()
        if faculty:
            self.populate_from_faculty(faculty)
        
        SchedulerStyles.apply_high_contrast_shell(self, self.inner, self.scroll)

    # --- UI SETUP METHODS ---

    def _setup_containers(self):
        """Builds the main scrollable skeleton."""
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

    def _init_form_widgets(self, faculty):
        """Initializes raw input variables."""
        self.name_edit, self.min_credit_edit, self.max_credit_edit, self.courses_taught_edit = [
            QLineEdit(self.inner) for _ in range(4)]
        self._days_list = self._create_day_selector(faculty)
        self._times_edit = QLineEdit(self.inner)
        self._times_edit.setPlaceholderText("MON→FRI order (e.g. 09:00-12:00, 13:00-15:00)")
        
        self.course_weight_spin, self.room_weight_spin, self.lab_weight_spin = [
            QSpinBox(self.inner) for _ in range(3)]
        for s in [self.course_weight_spin, self.room_weight_spin, self.lab_weight_spin]:
            s.setRange(1, 10)

        self._course_list = self._course_extra = self._room_list = \
        self._room_extra = self._lab_list = self._lab_extra = None

    def _assemble_form_sections(self):
        """Groups widgets into visual sections."""
        basics = QGroupBox("Basics", self.inner)
        bf = QFormLayout(basics)
        for label, widget in [("Name:", self.name_edit), ("Min credits:", self.min_credit_edit), 
                              ("Max credits:", self.max_credit_edit), ("Limit:", self.courses_taught_edit)]:
            bf.addRow(label, widget)
        self.form_layout.addWidget(basics)

        avail = QGroupBox("Availability", self.inner)
        av = QVBoxLayout(avail)
        for widget in [QLabel("Tick days:"), self._days_list, QLabel("Time ranges:"), self._times_edit]:
            av.addWidget(widget)
        self.form_layout.addWidget(avail)

        prefs = [
            ("Course preferences", "course_ids", self.course_weight_spin, "course"),
            ("Room preferences", "rooms", self.room_weight_spin, "room"),
            ("Lab preferences", "labs", self.lab_weight_spin, "lab")
        ]
        for title, key, spin, kind in prefs:
            self.form_layout.addWidget(self._section_weighted_prefs(title, self.inner, key, spin, kind))


    def _add_button_box(self):
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.on_accept)
        bbox.rejected.connect(self.reject)
        self.main_layout.addWidget(bbox, 0, Qt.AlignmentFlag.AlignRight)

    # --- DATA PROCESSING & HELPERS ---

    def _create_day_selector(self, faculty: Optional[Dict[str, Any]]) -> QListWidget:
        """Determines saved days and builds the checkbox list widget."""
        selected = set()
        if faculty:
            md = faculty.get("mandatory_days") or []
            td = faculty.get("times") or {}
            source = md if isinstance(md, list) and md else td.keys()
            selected = {str(d).strip().upper() for d in source if d}

        w = QListWidget()
        w.setFixedHeight(100)
        for d in DAYS:
            it = QListWidgetItem(d)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if d in selected else Qt.CheckState.Unchecked)
            w.addItem(it)
        return w

    def _checked_days(self) -> List[str]:
        """Track all days user checks."""
        checked = {
            self._days_list.item(i).text() 
            for i in range(self._days_list.count()) 
            if self._days_list.item(i).checkState() == Qt.CheckState.Checked
        }
        return [d for d in DAYS if d in checked]

    def _populate_weighted_prefs(self, prefs: Any, checklist: Optional[QListWidget], 
                                 extra_edit: Optional[QLineEdit], spin: QSpinBox, catalog_key: str) -> None:
        """Hydrates a preference section with saved weights and checkmarks."""
        if not isinstance(prefs, dict) or not prefs: return
        
        catalog = set(self._pick_lists.get(catalog_key) or [])
        weights = [int(v) for v in prefs.values()]
        if weights:
            spin.setValue(weights[0])
            same = all(v == weights[0] for v in weights)
        else: same = True

        if checklist:
            for i in range(checklist.count()):
                it = checklist.item(i)
                it.setCheckState(Qt.CheckState.Checked if it.text() in prefs else Qt.CheckState.Unchecked)

            extras = [f"{k}:{v}" for k, v in prefs.items() if k not in catalog or (not same and int(v) != spin.value())]
            if extras and extra_edit: extra_edit.setText(", ".join(extras))
        elif extra_edit:
            extra_edit.setText(", ".join(f"{k}:{v}" for k, v in prefs.items()))

    def _section_weighted_prefs(self, title, parent, list_key, weight_spin, kind) -> QGroupBox:
        """Generates a weighted preference section and maps UI references to the class."""
        box = QGroupBox(title, parent)
        lay = QVBoxLayout(box)
        catalog = self._pick_lists.get(list_key) or []
        extra = QLineEdit(box)
        lw = None

        if catalog:
            lw = QListWidget(box); lw.setFixedHeight(120)
            for x in sorted(catalog, key=str.casefold):
                it = QListWidgetItem(x); it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Unchecked); lw.addItem(it)
            lay.addWidget(QLabel(f"Tick {kind}s from config:")); lay.addWidget(lw)
        
        setattr(self, f"_{kind}_list", lw)
        setattr(self, f"_{kind}_extra", extra)

        for lbl in ["Additional (name:weight, ...):", extra, "Default weight:", weight_spin]:
            lay.addWidget(lbl if isinstance(lbl, QWidget) else QLabel(lbl))
        return box

    def populate_from_faculty(self, faculty: Dict[str, Any]) -> None:
        """Populate UI from faculty dictionary."""
        fields = {"name": self.name_edit, "minimum_credits": self.min_credit_edit,
                "maximum_credits": self.max_credit_edit, "unique_course_limit": self.courses_taught_edit}
        for key, widget in fields.items():
            widget.setText(str(faculty.get(key) or (0 if "credits" in key or "limit" in key else "")))

        td = faculty.get("times", {}) or {}
        parts = [str(td[d][0]) for d in DAYS if d in td and td[d]]
        self._times_edit.setText(", ".join(parts))

        prefs_map = {"course": "course_ids", "room": "rooms", "lab": "labs"}
        for kind, cat_key in prefs_map.items():
            self._populate_weighted_prefs(
                faculty.get(f"{kind}_preferences", {}),
                getattr(self, f"_{kind}_list"), 
                getattr(self, f"_{kind}_extra"),
                getattr(self, f"{kind}_weight_spin"), 
                cat_key
            )
    def _merge_weighted(self, checklist, extra_input, spin) -> Dict[str, int]:
        """Merges GUI selections and manual text inputs into a JSON-ready dictionary."""
        default_w = spin.value()
        result = {}

        if checklist:
            for i in range(checklist.count()):
                it = checklist.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    result[it.text()] = default_w

        if extra_input and extra_input.text().strip():
            for entry in extra_input.text().split(","):
                if ":" in entry:
                    name, weight = entry.rsplit(":", 1)
                    try:
                        result[name.strip()] = int(weight.strip())
                    except ValueError:
                        result[name.strip()] = default_w
                elif entry.strip():
                    result[entry.strip()] = default_w
                    
        return result

    def get_faculty_data(self) -> Dict[str, Any]:
        checked_days = self._checked_days()
        time_list = [p.strip() for p in self._times_edit.text().split(",") if p.strip()]
        return {
            "name": self.name_edit.text().strip(),
            "maximum_credits": int(self.max_credit_edit.text() or 0),
            "minimum_credits": int(self.min_credit_edit.text() or 0),
            "unique_course_limit": int(self.courses_taught_edit.text() or 0),
            "mandatory_days": checked_days,
            "times": {d: [time_list[i]] if i < len(time_list) else [] for i, d in enumerate(checked_days)},
            "course_preferences": self._merge_weighted(self._course_list, self._course_extra, self.course_weight_spin),
            "room_preferences": self._merge_weighted(self._room_list, self._room_extra, self.room_weight_spin),
            "lab_preferences": self._merge_weighted(self._lab_list, self._lab_extra, self.lab_weight_spin),
        }

    def on_accept(self) -> None:
        """Checks all input requirements."""
        
        #Gather all the conditions
        has_name = bool(self.name_edit.text().strip())
        has_credits = bool(self.min_credit_edit.text().strip() and self.max_credit_edit.text().strip())
        has_limit = bool(self.courses_taught_edit.text().strip())
        
        checked_days = self._checked_days()
        time_parts = [p.strip() for p in self._times_edit.text().split(",") if p.strip()]
        has_availability = len(checked_days) > 0 and len(time_parts) >= len(checked_days)

        #Bulk check
        if not (has_name and has_credits and has_limit and has_availability):
            QMessageBox.warning(
                self, 
                "Missing Information", 
                "Please ensure all basic fields are filled and you have provided "
                "a time range for every checked weekday."
            )
            return

        self.accept()


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
    def __init__(self, config_mgr, viewer_mgr):
        self.config_mgr = config_mgr
        self.viewer_mgr = viewer_mgr

    def _get_faculty_list(self) -> List[Dict[str, Any]]:
        """Retrieve the list of faculty from the config file."""
        return self.config_mgr.data["config"]["faculty"]
        
    def select_faculty(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
        """Retrieves a specific faculty from list of faculty."""
        faculty_list = self._get_faculty_list()

        if not faculty_list:
            QMessageBox.information(parent, "No faculty", "No faculty found in the config.")
            return None, None

        # labels is for the selection dropdown
        labels = [str(f.get("name", "Unknown Faculty")) for f in faculty_list]

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
        
        # Pass None explicitly to ensure no filtering happens
        pick = self.viewer_mgr._get_pick_lists(exclude_course_id_for_conflicts=None)

        dialog = FacultyFormDialog(parent, faculty=None, pick_lists=pick)
        dialog.setWindowTitle("Add Faculty")

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

        pick = self.viewer_mgr._get_pick_lists(exclude_course_id_for_conflicts=None)
        dialog = FacultyFormDialog(parent, faculty=existing_data, pick_lists=pick)
        dialog.setWindowTitle("Modify Faculty")

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