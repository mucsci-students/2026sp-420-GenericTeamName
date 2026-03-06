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
            
            self._save(parent)

    #the generate schedules option.
    def run_scheduler(self, parent: QWidget) -> None:
        """Runs the scheduler, saves results to new specified json file."""
        if not self._ensure_config_loaded(parent):
            return

        try:
            from scheduler import Scheduler, load_config_from_file
            from scheduler.config import CombinedConfig
        except ImportError:
            QMessageBox.critical(parent, "Import Error", "Scheduler package not found.")
            return

        #Load Scheduler
        try:
            path_str = str(self.config_path.resolve())
            config = load_config_from_file(CombinedConfig, path_str)
            scheduler = Scheduler(config)
            
            #generates up to this many schedules
            limit = self._config_data.get("limit", 2)
            schedules = []

            for index, schedule in enumerate(scheduler.get_models()):
                if index >= limit:
                    break
                schedules.append(schedule)
            
            if not schedules:
                QMessageBox.warning(parent, "No Results", "No schedules were generated.")
                return

            #Prompt for new file location
            default_name = str(self.config_path.parent / "results.json")
            save_path, _ = QFileDialog.getSaveFileName(
                parent, "Save Generated Schedules", default_name, "JSON Files (*.json)"
            )
            
            if not save_path:
                return

            #Convert objects
            def course_to_dict(c: Any) -> Any:
                if hasattr(c, "model_dump"): return c.model_dump()
                if hasattr(c, "as_dict"): return c.as_dict()
                if hasattr(c, "__dict__"): return c.__dict__
                return str(c)

            out_data = [[course_to_dict(c) for c in sched] for sched in schedules]
            
            out_path = Path(save_path)
            out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
            
            QMessageBox.information(
                parent, "Success", 
                f"Generated {len(schedules)} schedules.\nSaved to: {out_path.name}"
            )

        except Exception as e:
            QMessageBox.critical(parent, "Scheduler Error", f"Execution or Save failed:\n{e}")
