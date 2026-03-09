'''
    Author: Damion Crawford
    Date: 2 March 2026
    Filename: faculty_gui.py
    Faculty management module for scheduler config CLI.
'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QWidget,
)

class FacultyManager:

    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self.config_data: Dict[str, any] = {}

    # Internal Methods/Helpers
    
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
        self.config_data = config_mgr.data
        return True
    

    def list_faculty(self) -> List[Any]:
        cfg = self.config_data.setdefault("config", {})
        faculty = cfg.setdefault("faculty", [])
        if not isinstance(faculty, list):
            cfg["faculty"] = []
        return cfg["faculty"]

    def _faculty_display_name(self, f: Any) -> str:
        """Get display string for a faculty item (string or dict with 'name')."""
        if isinstance(f, dict):
            return str(f.get("name", f))
        return str(f)
    
    def save(self, parent: QWidget) -> None:
        config_mgr = getattr(parent, "config_mgr", None)
        if config_mgr:
            config_mgr.data = self.config_data
            config_mgr.save()
        else:
            if self.config_path is None:
                return
            try:
                self.config_path.write_text(
                    json.dumps(self.config_data, indent=2),
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
            "Configuration saved.",
        )

    def select_faculty(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
        faculty = self.list_faculty()

        if not faculty:
            QMessageBox.information(parent, "No faculty", "No faculty found in the config.")
            return None, None

        labels = [self._faculty_display_name(f) for f in faculty]

        item, ok = QInputDialog.getItem(
            parent,
            "Select Faculty",
            "Faculty:",
            labels,
            0,
            False,
        )

        if not ok or not item:
            return None, None

        index = labels.index(item)
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

        index, existing = self.select_faculty(parent)
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
        existing_item = faculty[index]
        if isinstance(existing_item, dict):
            faculty[index] = {**existing_item, "name": text.strip()}
        else:
            faculty[index] = text.strip()
        self.save(parent)

    def delete_faculty_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return

        index, existing = self.select_faculty(parent)
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

        index, existing = self.select_faculty(parent)
        if index is None or existing is None:
            return

        text, ok = QInputDialog.getText(
            parent,
            "Add Faculty Time",
            "Faculty time:"
        )

        if not ok or not text.strip():
            return

        self.save(parent)


    def faculty_preference(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return
        
        index, existing = self.select_faculty(parent)
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

        self.save(parent)