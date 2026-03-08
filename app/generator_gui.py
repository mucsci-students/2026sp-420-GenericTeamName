'''
    File: generator_gui.py
    Date: 03/05/2026
    Author: Tyler Strohl
    Class: CMSC 420
    Description: Schedule Generator dialogs and helpers for the GUI.
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


class GenConfigManager:

    def __init__(self) -> None:
        
        self.config_path: Optional[Path] = None
        self._config_data: Dict[str, Any] = {}
        self.limit: int = 2
        self.output_format: str = "json"
        self.output_path: Optional[Path] = None
        self.optimize: bool = True

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
    
    def _save(self, parent: QWidget) -> None:
        
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

    #modify the limit variable in the config file.
    def set_limit(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
            return

        def_limit = self._config_data.get("limit", 2)

        text, ok = QInputDialog.getText(
            parent,
            "Specify Limit",
            "# of Schedules:",
            text=str(def_limit)
        )

        if not ok or not text.strip():
            return

        try:
            self._config_data["limit"] = int(text.strip())
            config_mgr = getattr(parent, "config_mgr", None)
            if config_mgr:
                config_mgr.data = self._config_data
                config_mgr.save()
            else:
                self._save(parent)
        except ValueError:
            QMessageBox.warning(parent, "Invalid Input", "Please enter a valid number.")

    #enables/disables the optimization flags in the config file.
    def set_optimize(self, parent: QWidget) -> None:
        
        if not self._ensure_config_loaded(parent):
            return
        
        full_flags = [
            "faculty_course", "faculty_room", "faculty_lab", 
            "same_room", "same_lab", "pack_rooms"
        ]

        current_flags = self._config_data.get("optimizer_flags", [])
        is_currently_on = len(current_flags) > 0
        start_index = 0 if is_currently_on else 1

        text, ok = QInputDialog.getItem(
            parent, "Specify Optimization", "Enable/Disable All:", 
            ["True", "False"], start_index, False
        )

        if ok:
            if text == "True":
                self._config_data["optimizer_flags"] = full_flags
            else:
                self._config_data["optimizer_flags"] = []

            config_mgr = getattr(parent, "config_mgr", None)
            if config_mgr:
                config_mgr.data = self._config_data
                config_mgr.save()
            else:
                self._save(parent)

    #the generate schedules option.
    def run_scheduler(self, parent: QWidget) -> None:
        """Runs the scheduler and displays results in Schedule Viewer. Use Export to save to file."""
        if not self._ensure_config_loaded(parent):
            return

        try:
            from scheduler import Scheduler, load_config_from_file
            from scheduler.config import CombinedConfig
        except ImportError:
            QMessageBox.critical(parent, "Import Error", "Scheduler package not found.")
            return

        try:
            path_str = str(self.config_path.resolve())
            config = load_config_from_file(CombinedConfig, path_str)
            scheduler = Scheduler(config)

            limit = self._config_data.get("limit", 2)
            raw_schedules = []

            for index, schedule in enumerate(scheduler.get_models()):
                if index >= limit:
                    break
                raw_schedules.append(schedule)

            if not raw_schedules:
                QMessageBox.warning(parent, "No Results", "No schedules were generated.")
                return

            # Convert to viewer format using parent's config_mgr
            config_mgr = getattr(parent, "config_mgr", None)
            if config_mgr is None:
                QMessageBox.critical(parent, "Config Error", "Config manager not available.")
                return

            def course_to_dict(c: Any) -> Any:
                if hasattr(c, "model_dump"):
                    return c.model_dump()
                if hasattr(c, "as_dict"):
                    return c.as_dict()
                if hasattr(c, "__dict__"):
                    return c.__dict__
                return str(c)

            viewer_schedules = []
            for sched in raw_schedules:
                sched_dicts = [course_to_dict(c) for c in sched]
                viewer_format = config_mgr.scheduler_output_to_viewer_format(sched_dicts)
                viewer_schedules.append(viewer_format)

            # Store in parent for Schedule Viewer
            parent.schedules = parent.schedules + viewer_schedules
            parent.current_schedule_index = len(parent.schedules) - len(viewer_schedules)

            QMessageBox.information(
                parent, "Success",
                f"Generated {len(viewer_schedules)} schedule(s). View them in Schedule Viewer. Use Export to save to file."
            )

        except Exception as e:
            QMessageBox.critical(parent, "Scheduler Error", f"Execution failed:\n{e}")
