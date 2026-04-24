'''
    File: viewer_gui.py
    Date: 04/23/2026
    Author: Tyler Strohl
    Class: CMSC 420
    Description: Holds schedule viewer functions to be used in *main_window.py*.
'''

import json
from typing import Any, Dict, List, Optional, Set, Tuple

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
    QMessageBox, QDialog, QPlainTextEdit, QLabel,
    QMenuBar, QLineEdit, QTableWidget, QHeaderView, 
    QTableWidgetItem, QToolBar, QToolButton,
    )
from PyQt6.QtCore import Qt, QCoreApplication, QSize
from PyQt6.QtGui import QAction, QFont, QColor, QBrush, QKeySequence
from PyQt6.QtWidgets import QInputDialog

#TODO: Finish implementing this new class.
class ViewerManager:

    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        #Bug fix to prevent "No Schedules" warning from popping up at wrong time.
        #See update_schedule_display
        self.clear_clicked = False

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

    def handle_clear_schedule(self, parent) -> None:

        """
        Removes all the currently generated schedules.
        """
        if not parent.schedules or not (0 <= parent.current_schedule_index < len(parent.schedules)):
            QMessageBox.warning(parent, "No Data", "No schedules to clear.")
            return
        else:
            try:
                self.clear_clicked = True
                parent.schedules.clear()
                #Updates imported schedules label
                parent.cfg_panel.update_title(parent.cfg_panel)
                self.config_mgr.import_file = ""
                self.update_schedule_display(parent)
                QMessageBox.information(parent, "Success", "Schedule/s have been cleared.")
            except:
                QMessageBox.critical(parent, "Error", "Clear failed.")

    def handle_view_summary(self, parent):
        """Displays a summary of the current configuration in a monospaced dialog."""
        summary = self.config_mgr.get_summary_text()
        msg = QMessageBox(parent)
        msg.setWindowTitle(f"Summary: {self.config_mgr.filepath}")
        msg.setText(summary)
        msg.setFont(QFont("Courier New", 10))
        msg.exec()

    def show_next_schedule(self, parent):
        """Increments schedule index with wrap-around."""
        if parent.schedules:
            parent.current_schedule_index = (parent.current_schedule_index + 1) % len(parent.schedules)

    def show_prev_schedule(self, parent):
        """Decrements schedule index with wrap-around."""
        if parent.schedules:
            parent.current_schedule_index = (parent.current_schedule_index - 1) % len(parent.schedules)

    def update_schedule_display(self, parent, group_by: str = "all"):
        """
        Refreshes the grid based on the current schedule index and optional filters.
        Also refreshes the grid when new schedules are generated.
        """
        if not parent.schedules:
            parent.calendar_view.setRowCount(0)
            parent.counter_label.setText(
                "No schedules yet — use Generate on the toolbar, or Import (Ctrl+Shift+I)"
            )
            #this is a little buggy because of when the function is called.
            #ex: when clearing schedules.
            if self.clear_clicked == False:
                QMessageBox.warning(parent, "No Schedules", "Generate or import schedule/s first.")
            return

        filter_val = None
        if group_by != "all":
            options = []
            config_section = self.config_mgr.data.get("config", {})
            if group_by == "faculty":
                options = [f["name"] for f in config_section.get("faculty", [])]
            elif group_by == "room":
                options = [r for r in config_section.get("rooms", [])]
            elif group_by == "lab":
                options = [r for r in config_section.get("labs", [])]

            if not options:
                QMessageBox.information(parent, "Filter", f"No {group_by} data available to filter by.")
                group_by = "all"
            
            #Prompts user for selection when choosing a view option:
            else:
                item, ok = QInputDialog.getItem(parent, f"Filter by {group_by.capitalize()}", 
                                              f"Select {group_by}:", options, 0, False)
                if ok and item:
                    filter_val = item
                else:
                    return

        parent._update_path_label_text()
        filter_suffix = f" · Filter: {filter_val}" if filter_val else ""
        parent.counter_label.setText(
            f"Schedule {parent.current_schedule_index + 1} of {len(parent.schedules)}{filter_suffix}"
        )

        days, times, grid = self.config_mgr.get_schedule_grid_data(
            parent.schedules[parent.current_schedule_index],
            filter_type=group_by,
            filter_value=filter_val
        )

        parent.calendar_view.setRowCount(len(times))
        parent.calendar_view.setColumnCount(len(days))
        parent.calendar_view.setHorizontalHeaderLabels(days)
        parent.calendar_view.setVerticalHeaderLabels(times)

        item_font = QFont("Segoe UI", 9)
        for r, row_data in enumerate(grid):
            for c, cell_value in enumerate(row_data):
                item = QTableWidgetItem(cell_value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFont(item_font)
                if cell_value:
                    item.setBackground(QBrush(QColor(37, 99, 235)))
                    item.setForeground(QBrush(QColor(255, 255, 255)))
                parent.calendar_view.setItem(r, c, item)