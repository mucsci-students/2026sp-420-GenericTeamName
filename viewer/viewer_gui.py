'''
    File: viewer_gui.py
    Date: 04/18/2026
    Author: Tyler Strohl
    Class: CMSC 420
    Description: Holds schedule viewer functions to be used in *main_window.py*.
'''

import json
from typing import Any, Dict, List, Optional, Set, Tuple

#TODO: Finish implementing this new class.
class ViewerManager:

    def __init__(self, config_mgr):
        #TODO: use parent instead of main_window ?
        #self.mw = main_window
        self.config_mgr = config_mgr

    #Utilized by managers.
    def _get_pick_lists(self, exclude_course_id_for_conflicts: Optional[str] = None) -> Dict[str, List[str]]:
        """Provides lists for rooms, labs, & faculty for drop-down menus."""
        data = self.config_mgr.data["config"]
        
        #Retrieve lists of rooms, labs, faculty for drop-down options.
        rooms = [str(r) for r in data["rooms"] if r is not None]
        labs = [str(l) for l in data["labs"] if l is not None]
        faculty = []
        for f in data["faculty"]:
            if f is None:
                continue
            if isinstance(f, dict):
                faculty.append(str(f.get("name", "Unknown Faculty")))
            else:
                faculty.append(str(f))

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
            "course_ids": sorted(set(course_ids), key=str.casefold),
        }
    
    def _sync_detail_view(self, parent) -> None:
        if not hasattr(parent, "detail_view"):
            return
        try:
            parent.detail_view.setPlainText(json.dumps(self.config_mgr.data, indent=2))
        except (TypeError, ValueError):
            parent.detail_view.setPlainText("(Unable to display configuration as JSON.)")