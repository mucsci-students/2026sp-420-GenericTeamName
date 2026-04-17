'''
    File: faculty_gui.py
    Date: 04/16/2026
    Author: Damion Crawford & Tyler Strohl
    Class: CMSC 420
    Description: Faculty management dialogs and helpers for the GUI.
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

class FacultyFormDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, faculty: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Faculty Details")

        self.name_edit = QLineEdit(self)
        self.min_credit_edit = QLineEdit(self)
        self.max_credit_edit = QLineEdit(self)
        self.courses_taught_edit = QLineEdit(self)
        self.day_edit = QLineEdit(self)
        self.time_edit = QLineEdit(self)
        self.course_pref_edit = QLineEdit(self)
        self.course_weight_spin = QSpinBox(self)
        self.course_weight_spin.setRange(1, 10)
        self.room_pref_edit = QLineEdit(self)
        self.room_weight_spin = QSpinBox(self)
        self.room_weight_spin.setRange(1, 10)
        self.lab_pref_edit = QLineEdit(self)
        self.lab_weight_spin = QSpinBox(self)
        self.lab_weight_spin.setRange(1, 10)

        fac_form = QFormLayout(self)
        fac_form.addRow("Faculty Name:", self.name_edit)
        fac_form.addRow("Min. Credits:", self.min_credit_edit)
        fac_form.addRow("Max. Credits:", self.max_credit_edit)
        fac_form.addRow("Number of courses taught:", self.courses_taught_edit)
        fac_form.addRow("Available Days (comma-separated):", self.day_edit)
        fac_form.addRow("Available Times (comma-separated by available day):", self.time_edit)
        fac_form.addRow("Course Preference:", self.course_pref_edit)
        fac_form.addRow("Course Pref. Weight:", self.course_weight_spin)
        fac_form.addRow("Room Preference:", self.room_pref_edit)
        fac_form.addRow("Room Pref. Weight:", self.room_weight_spin)
        fac_form.addRow("Lab Preference:", self.lab_pref_edit)
        fac_form.addRow("Lab Pref. Weight:", self.lab_weight_spin)

        fac_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent = self
        )
        fac_buttons.accepted.connect(self.on_accept)
        fac_buttons.rejected.connect(self.reject)
        fac_form.addRow(fac_buttons)

    def populate_from_faculty(self, faculty: Dict[str, Any]) -> None:
        
        #Retrieve the keys used in JSON file
        #setText requires strings
        self.name_edit.setText(str(faculty.get("name") or ""))
        self.min_credit_edit.setText(str(faculty.get("minimum_credits") or 0))
        self.max_credit_edit.setText(str(faculty.get("maximum_credits") or 0))
        self.courses_taught_edit.setText(str(faculty.get("unique_course_limit") or 0))

        #times dictionary, shows which days faculty are available
        times_dict = faculty.get("times", {})
        available_days = [day for day, slots in times_dict.items() if slots]
        self.day_edit.setText(", ".join(available_days))

        #Extract time ranges from the nested lists in the times dictionary
        time_strings = []
        for day in available_days:
            slots = times_dict.get(day, [])
            if slots and isinstance(slots, list):
                # Grab the first time range string from the list
                time_strings.append(str(slots[0]))
        self.time_edit.setText(", ".join(time_strings))

        #Helper for formatting preferences (these have weights attached)
        def format_pref(prefs: Any) -> str:
            if isinstance(prefs, dict):
                return ", ".join([f"{k}:{v}" for k, v in prefs.items()])
            return ""

        #If preferences are dicts, show the keys as a comma-separated string
        self.course_pref_edit.setText(format_pref(faculty.get("course_preferences", {})))
        self.room_pref_edit.setText(format_pref(faculty.get("room_preferences", {})))
        self.lab_pref_edit.setText(format_pref(faculty.get("lab_preferences", {})))



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
        if not self.day_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Available days are required.")
            return
        if not self.time_edit.text().strip():
            QMessageBox.warning(self, "Missing data", "Available times are required.")
            return
        self.accept()

    #helps parse data from JSON config file
    def parse_csv_field(self, text: str) -> List[str]:
        parts = [p.strip() for p in text.split(",")]
        return [p for p in parts if p]

    #helps parse the preferences, which have weights
    def parse_weighted_csv(self, text: str, default_weight: int) -> Dict[str, int]:
        result = {}
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

    #Ensures that the day inputted by user is same as config file.
    def format_day_name(self, day: str) -> str:

        day = day.strip().upper()
        if day.startswith("MON"): return "MON"
        if day.startswith("TUE"): return "TUE"
        if day.startswith("WED"): return "WED"
        if day.startswith("THU"): return "THU"
        if day.startswith("FRI"): return "FRI"
        return day

    def get_faculty_data(self) -> Dict[str, Any]:

         #MON, TUE, etc.
        raw_days = self.parse_csv_field(self.day_edit.text())
        day_list = [self.format_day_name(d) for d in raw_days]
        # 09:00-15:00, etc.
        time_list = self.parse_csv_field(self.time_edit.text())

        #"times" dictionary: {"MON": ["09:00-15:00"], ...}
        times_dict = {}
        for index, day in enumerate(day_list):
            if index < len(time_list):
                times_dict[day] = [time_list[index]]
            else:
                times_dict[day] = []

        return {
            "name": self.name_edit.text().strip(),
            "maximum_credits": int(self.max_credit_edit.text().strip() or 0),
            "minimum_credits": int(self.min_credit_edit.text().strip() or 0),
            "unique_course_limit": int(self.courses_taught_edit.text().strip() or 0),
            "maximum_days": len(day_list),
            "mandatory_days": day_list, 
            #these below are stored & retrieved different
            "times": times_dict,
            "course_preferences": self.parse_weighted_csv(
                self.course_pref_edit.text(), self.course_weight_spin.value()
            ),
            "room_preferences": self.parse_weighted_csv(
                self.room_pref_edit.text(), self.room_weight_spin.value()
            ),
            "lab_preferences": self.parse_weighted_csv(
                self.lab_pref_edit.text(), self.lab_weight_spin.value()
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

        #labels is for the selection dropdown
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
        
        dialog = FacultyFormDialog(parent)
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
        if index is None: return

        faculty_list = self._get_faculty_list()     
        existing_data = faculty_list[index]

        dialog = FacultyFormDialog(parent)
        dialog.populate_from_faculty(existing_data)
        
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
        if index is None: return

        reply = QMessageBox.question(
            parent, "Confirm delete",
            f"Delete faculty member '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            faculty_list = self._get_faculty_list()     
            faculty_list.pop(index)
            self.config_mgr.save(parent)