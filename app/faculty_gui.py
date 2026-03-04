'''
    Author: Damion Crawford
    Date: 2 March 2026
    Filename: faculty_gui.py
    Saving, modifying, removing faculty
'''

"""Faculty management module for scheduler config CLI."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QWidget
)

@dataclass
class FacultyManager:

    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self.config_data: Dict[str, any] = {}

    # Internal Methods/Helpers
    
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
    

    def list_faculty(self) -> List[str]:
        cfg = self._config_data.setdefault("config", {})
        faculty = cfg.setdefault("faculty", [])
        if not isinstance(faculty, list):
            cfg["faculty"] = []
        return cfg["faculty"]
    
    def save(self, parent: QWidget) -> None:
        if self.config_path is None:
            return
        try:
            self.config_path.write_text(
                json.dumps(self._config_data, indent=2),
                encoding="utf-8"
            )
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

    def select_faculty(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
        faculty = self.list_faculty()

        if not faculty:
            QMessageBox.information(parent, "No faculty", "No faculty found in the config.")
            return None, None

        item, ok = QInputDialog.getItem(
            parent,
            "Select Faculty",
            "Faculty:",
            faculty,
            0,
            False,
        )

        if not ok or not item:
            return None, None

        index = faculty.index(item)
        return index, item
    
    # Public Methods

    def add_faculty_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return

        text, ok = QInputDialog.getText(
            parent,
            "Add Faculty",
            "Faculty name:"
        )

        if not ok or not text.strip():
            return

        faculty = self.list_faculty()
        faculty.append(text.strip())
        self.save(parent)

    def modify_faculty_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return

        index, existing = self._select_room(parent)
        if index is None or existing is None:
            return

        text, ok = QInputDialog.getText(
            parent,
            "Modify Faculty",
            "Faculty name:",
            text=existing
        )

        if not ok or not text.strip():
            return

        faculty = self.list_faculty()
        faculty[index] = text.strip()
        self.save(parent)

    def delete_faculty_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return

        index, existing = self.list_faculty(parent)
        if index is None or existing is None:
            return

        reply = QMessageBox.question(
            parent,
            "Confirm delete",
            f"Delete faculty '{existing}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        faculty = self.list_faculty()
        del faculty[index]
        self.save(parent)
    
    def faculty_time_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return

        index, existing = self.list_faculty(parent)
        if index is None or existing is None:
            return

        text, ok = QInputDialog.getText(
            parent,
            "Add Faculty Time",
            "Faculty time:"
        )

        if not ok or not text.strip():
            return

        faculty = self.list_faculty
        faculty.time = text.strip()
        self.save(parent)


    def faculty_preference(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return
        
        index, existing = self.list_faculty(parent)
        if index is None or existing is None:
            return

        text, ok = QInputDialog.getText(
            parent,
            "Choose Course",
            "Course:"
        )

        if not ok or not text.strip():
            return
        
        text2, ok2 = QInputDialog.getText(
            parent,
            "Enter Weight",
            "Weight (1-10):"
        )

        if not ok2 or not text2.strip():
            return
        
        faculty = self.list_faculty(parent)
        course = text.strip()
        weight = text2.strip()

        self.save(parent)