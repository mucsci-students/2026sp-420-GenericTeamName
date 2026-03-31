'''
    File: generator_gui.py
    Date: 03/05/2026
    Author: Tyler Strohl
    Class: CMSC 420
    Description: Schedule Generator dialogs and helpers for the GUI.
'''

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QWidget,
    QProgressDialog,
    QApplication,
    QProgressBar,
)

#the work-around for scheduler function blocking main GUI thread.
class ScheduleWorker(QThread):
    
    #communicate with the main GUI thread
    progress = pyqtSignal(int)
    finished_schedules = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, scheduler, limit):
        super().__init__()
        self.scheduler = scheduler
        self.limit = limit
        self._is_cancelled = False

    def run(self):
        """This runs in the background thread."""
        try:
            raw_schedules = []
            for index, schedule in enumerate(self.scheduler.get_models()):
                if self._is_cancelled or index >= self.limit:
                    break
                raw_schedules.append(schedule)
                #Tell main thread to update the progress bar
                self.progress.emit(index + 1)
            
            #Send final list of schedules back to the main thread
            self.finished_schedules.emit(raw_schedules)
        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        self._is_cancelled = True

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
                config_mgr.save(parent)
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
                config_mgr.save(parent)
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
            # path_str = str(self.config_path.resolve())
            # config = load_config_from_file(CombinedConfig, path_str)
               # --- SANITIZE + CONVERT CONFIG FOR SCHEDULER ---

            # --- SANITIZE + CONVERT CONFIG FOR SCHEDULER ---

            def convert_time_slots(ui_time_slots):
                day_map = {
                    "Monday": "MON",
                    "Tuesday": "TUE",
                    "Wednesday": "WED",
                    "Thursday": "THU",
                    "Friday": "FRI",
                }

                # default fallback (VERY important)
                default_block = {
                    "start": "08:00",
                    "end": "09:00",
                    "spacing": 60
                }

                times = {
                    "MON": [default_block],
                    "TUE": [default_block],
                    "WED": [default_block],
                    "THU": [default_block],
                    "FRI": [default_block],
                }

                for day, data in ui_time_slots.items():
                    if not data.get("enabled"):
                        continue

                    short_day = day_map.get(day)
                    if not short_day:
                        continue

                    times[short_day] = [{
                        "start": data["start_time"],
                        "end": data["end_time"],
                        "spacing": data["spacing_minutes"]
                    }]

                return times


            clean_data = json.loads(json.dumps(self._config_data))

            cfg = clean_data.get("config", {})

            # grab UI timeslots BEFORE deleting
            ui_slots = cfg.pop("time_slots", {})

            # remove unused stuff
            cfg.pop("meeting_patterns", None)

            clean_data = json.loads(json.dumps(self._config_data))

            cfg = clean_data.get("config", {})

            # remove UI-only fields that Scheduler does not accept
            cfg.pop("time_slots", None)
            cfg.pop("meeting_patterns", None)

            # do NOT overwrite existing scheduler-ready time_slot_config
            if "time_slot_config" not in clean_data:
                raise ValueError(
                    "This config file does not contain a top-level time_slot_config. "
                    "Use a config like example.json that already includes scheduler-compatible time_slot_config."
                )

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
                json.dump(clean_data, tmp, indent=2)
                tmp_path = tmp.name

            config = load_config_from_file(CombinedConfig, tmp_path)
            scheduler = Scheduler(config)
            
            
            limit = self._config_data.get("limit", 2)

            #the progress bar setup.
            self.gen_progress = QProgressDialog("Generating Schedules:", "Cancel", 0, limit, parent)
            #progress bar prevents user from interacting with other windows in program.
            self.gen_progress.setWindowModality(Qt.WindowModality.WindowModal)
            self.gen_progress.setMinimumDuration(0)
            self.gen_progress.setValue(0)

            #format: M/N schedules
            bar = self.gen_progress.findChild(QProgressBar)
            if bar:
                bar.setFormat("%v / %m")
            
            self.worker = ScheduleWorker(scheduler, limit)
            
            self.worker.progress.connect(self.gen_progress.setValue)
            self.gen_progress.canceled.connect(self.worker.cancel)
            
            def on_finished(raw_schedules):
                self.gen_progress.close()
                if not raw_schedules:
                    QMessageBox.warning(parent, "No Results", "No schedules were generated.")
                    return

                config_mgr = getattr(parent, "config_mgr", None)
                if config_mgr is None:
                    QMessageBox.critical(parent, "Config Error", "Config manager not available.")
                    return

                def course_to_dict(c: Any) -> Any:
                    if hasattr(c, "model_dump"): return c.model_dump()
                    if hasattr(c, "as_dict"): return c.as_dict()
                    if hasattr(c, "__dict__"): return c.__dict__
                    return str(c)

                viewer_schedules = []
                for sched in raw_schedules:
                    sched_dicts = [course_to_dict(c) for c in sched]
                    viewer_format = config_mgr.scheduler_output_to_viewer_format(sched_dicts)
                    viewer_schedules.append(viewer_format)

                parent.schedules = parent.schedules + viewer_schedules
                parent.current_schedule_index = len(parent.schedules) - len(viewer_schedules)

                if hasattr(parent, 'refresh_ui_metadata'):
                    parent.refresh_ui_metadata()
                if hasattr(parent, 'update_schedule_display'):
                    parent.update_schedule_display()

                QMessageBox.information(
                    parent, "Success",
                    f"Generated {len(viewer_schedules)} schedule(s). View them in Schedule Viewer."
                )

            def on_error(err_msg):
                self.gen_progress.close()
                QMessageBox.critical(parent, "Scheduler Error", f"Execution failed:\n{err_msg}")

            self.worker.finished_schedules.connect(on_finished)
            self.worker.error.connect(on_error)

            self.gen_progress.show()
            self.worker.start()

        except Exception as e:
            QMessageBox.critical(parent, "Scheduler Error", f"Setup failed:\n{e}")
