"""
FILE: proxy_manager.py
AUTHORS: Kyle Smith
DESCRIPTION: Initializes managers and controls access.
"""

import json
import logging
from typing import Any, Dict, Callable

from config.config_mgr import ConfigManager
from faculty.faculty_gui import FacultyManager
from course.course_gui import CourseConfigManager
from room.room_gui import RoomConfigManager
from lab.lab_gui import LabConfigManager
from generator.generator_gui import GenConfigManager
from time_slot_config_editor.time_slot_editor import TimeSlotEditor
from time_slot_config_editor.meeting_pattern_editor import MeetingPatternEditor
from viewer.viewer_gui import ViewerManager
from .ai_viewer_gui import AIViewerManager

class ProxyManager:
    def __init__(self, main_window: Any):
        self._mw = main_window
        self.logger = logging.getLogger("ProxyManager")

        self.config_mgr = ConfigManager("config/config.json")
        self.config_mgr.load(self._mw)
        
        self.viewer_mgr = ViewerManager(self.config_mgr)
        self.faculty_manager = FacultyManager(self.config_mgr, self.viewer_mgr)
        self.course_manager = CourseConfigManager(self.config_mgr, self.viewer_mgr)
        self.room_manager = RoomConfigManager(self.config_mgr)
        self.lab_manager = LabConfigManager(self.config_mgr)
        self.gen_manager = GenConfigManager(self.config_mgr)
        self.time_slot_editor = TimeSlotEditor(self.config_mgr)
        self.meeting_pattern_editor = MeetingPatternEditor(self.config_mgr)
        self.ai_viewer_mgr = AIViewerManager(main_window)

        # Action registry
        self._registry: Dict[str, Callable] = {
            "faculty_add": self.faculty_manager.add_faculty_via_dialog,
            "faculty_modify": self.faculty_manager.modify_faculty_via_dialog,
            "faculty_delete": self.faculty_manager.delete_faculty_via_dialog,
            "course_add": self.course_manager.add_course_via_dialog,
            "room_add": self.room_manager.add_room_via_dialog,
            "lab_add": self.lab_manager.add_lab_via_dialog,
            "save_config": lambda mw: self.config_mgr.save(mw),
            "generate": self.gen_manager.run_scheduler,
            "change_path": lambda mw: mw.handle_change_path(), # Handled by UI
        }

    def execute(self, action_key: str, use_undo: bool = True, *args, **kwargs) -> bool:
        func = self._registry.get(action_key)
        if not func:
            return False

        try:
            if use_undo and hasattr(self._mw, "run_with_undo"):
                self._mw.run_with_undo(lambda: func(self._mw, *args, **kwargs))
            else:
                func(self._mw, *args, **kwargs)

            if hasattr(self._mw, "_sync_detail_view"):
                self._mw._sync_detail_view()
            return True
        except Exception as e:
            self.logger.error(f"Error executing {action_key}: {e}")
            return False
