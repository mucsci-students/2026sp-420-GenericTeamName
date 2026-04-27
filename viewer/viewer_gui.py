'''
    File: viewer_gui.py
    Date: 04/25/2026
    Author: Tyler Strohl
    Class: CMSC 420
    Description: Holds schedule viewer functions to be used in *main_window.py*.
'''

import json
import os
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
    
    #=================================================================================
    """Display Handlers:"""
    #=================================================================================

    def _sync_detail_view(self, parent) -> None:
        """Updates detail view with latest JSON info."""
        if not hasattr(parent, "detail_view"):
            return
        try:
            parent.detail_view.setPlainText(json.dumps(self.config_mgr.data, indent=2))
        except (TypeError, ValueError):
            parent.detail_view.setPlainText("(Unable to display configuration as JSON.)")

    def _update_path_label_text(self, parent) -> None:
        """Updates filepath text for active config."""
        if not hasattr(parent, "path_label"):
            return
        fp = (getattr(self.config_mgr, "filepath", None) or "").strip()
        if fp:
            parent.path_label.setText(f"Config: {os.path.basename(fp)}")
            parent.path_label.setToolTip(fp)
        else:
            parent.path_label.setText("Config: (unsaved or unknown path)")
            parent.path_label.setToolTip("")

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
            values = set()

            # Prefer filter options from the loaded schedules themselves.
            for schedule in parent.schedules:
                for entry in schedule:
                    entry_val = entry.get(group_by)

                    if isinstance(entry_val, list):
                        for v in entry_val:
                            if str(v).strip():
                                values.add(str(v).strip())
                    elif entry_val is not None and str(entry_val).strip():
                        values.add(str(entry_val).strip())

            options = sorted(values)

            # Fallback to config if schedule entries do not contain metadata.
            if not options:
                config_section = self.config_mgr.data.get("config", {})
                if group_by == "faculty":
                    options = [
                        f.get("name", "Unknown Faculty") if isinstance(f, dict) else str(f)
                        for f in config_section.get("faculty", [])
                        if f is not None
                    ]
                elif group_by == "room":
                    options = [str(r) for r in config_section.get("rooms", []) if r is not None]
                elif group_by == "lab":
                    options = [str(r) for r in config_section.get("labs", []) if r is not None]

            if not options:
                QMessageBox.information(parent, "Filter", f"No {group_by} data available to filter by.")
                group_by = "all"
            else:
                item, ok = QInputDialog.getItem(
                    parent,
                    f"Filter by {group_by.capitalize()}",
                    f"Select {group_by}:",
                    options,
                    0,
                    False
                )
                if ok and item:
                    filter_val = item
                else:
                    return

        self._update_path_label_text(parent)
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

    def _show_shortcuts_cheat_sheet(self, parent) -> None:
        mb = QMessageBox(parent)
        mb.setWindowTitle("Keyboard shortcuts")
        mb.setIcon(QMessageBox.Icon.Information)
        mb.setTextFormat(Qt.TextFormat.RichText)
        mb.setText(
            "<p style='margin-bottom:10px'><b>Toolbar / main window</b></p>"
            "<table cellspacing='6'>"
            "<tr><td>Open configuration…</td><td><b>Ctrl+O</b></td></tr>"
            "<tr><td>Save configuration</td><td><b>Ctrl+S</b></td></tr>"
            "<tr><td>Generate schedules</td><td><b>Ctrl+G</b></td></tr>"
            "<tr><td>Refresh schedule grid</td><td><b>F5</b></td></tr>"
            "<tr><td>Import schedules</td><td><b>Ctrl+Shift+I</b></td></tr>"
            "<tr><td>Export schedules</td><td><b>Ctrl+Shift+E</b></td></tr>"
            "<tr><td>Configuration summary</td><td><b>F2</b></td></tr>"
            "<tr><td>Send assistant message</td><td><b>Ctrl+Enter</b> "
            "(or Enter in the message field)</td></tr>"
            "</table>"
        )
        mb.exec()

    #=================================================================================
    """Config Handlers:"""
    #=================================================================================

    def save_as(self, parent):
        """'Save As' functionality for exporting the current config state."""
        p, _ = QFileDialog.getSaveFileName(parent, "Save JSON", "", "*.json")
        if p:
            self.config_mgr.filepath = p
            self.config_mgr.save(parent)
            self._update_path_label_text(parent)
            self._sync_detail_view(parent)

    def handle_change_path(self, parent):
        """Opens dialog to update the configuration file path."""
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "Select Configuration File", "config/", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_mgr.filepath = file_path
            try:
                self.config_mgr.load(parent)
                self._update_path_label_text(parent)
                self._sync_detail_view(parent)
                QMessageBox.information(parent, "Success", "Configuration File changed.")
                
            except Exception as e:
                QMessageBox.warning(parent, "Load Warning", str(e))

    def handle_import_schedule(self, parent):
        """
        Delegates JSON parsing to ConfigManager and updates the UI with the result.
        """

        imported_data = self.config_mgr.import_schedule_from_json(parent=parent)

        if imported_data:

            parent.schedules = imported_data
            parent.current_schedule_index = 0
            #Updates filepath displayed for imported schedules
            parent.cfg_panel.update_title(parent.cfg_panel, self.config_mgr.import_file)
            self.update_schedule_display(parent)

            try:
                QMessageBox.information(
                    parent,
                    "Import Successful",
                    f"Successfully loaded {len(imported_data)} schedule(s)."
                )
            except:
                QMessageBox.critical(parent, "Error", "Import failed.")

    def handle_export_schedule(self, parent):
        """Delegates schedule export with selectable output mode."""
        if not (hasattr(parent, "schedules") and parent.schedules):
            QMessageBox.warning(
                parent, 
                "Export Error", 
                "There are no schedules currently loaded to export. "
                "Please generate schedules first."
            )
            return

        options = [
            "Full schedules (JSON)",
            "Full schedules (PDF)",
            "By room/lab postings (PDF printable)",
            "By faculty postings (PDF printable)",
        ]
        choice, ok = QInputDialog.getItem(
            parent,
            "Export Schedules",
            "Export format:",
            options,
            0,
            False,
        )
        if not ok:
            return

        if choice == options[0]:
            self.config_mgr.export_schedule_to_json(parent.schedules, parent)
        elif choice == options[1]:
            self.config_mgr.export_schedule_to_pdf(parent.schedules, parent)
        elif choice == options[2]:
            self.config_mgr.export_grouped_printable(parent.schedules, parent, "room_lab")
        else:
            self.config_mgr.export_grouped_printable(parent.schedules, parent, "faculty")

    def handle_clear_schedule(self, parent) -> None:
        """Removes all the currently generated schedules."""
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