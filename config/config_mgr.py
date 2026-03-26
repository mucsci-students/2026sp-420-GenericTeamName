"""
:file: config/config_mgr.py
:author: Kyle Smith & Shane del Villar
:date: 03/25/2026
:class: CMSC 420
:synopsis: Singleton management for configuration data and tabulated schedule displays.
"""

import json
import os
import csv
from PyQt6.QtWidgets import QMessageBox, QWidget

class ConfigManager:
    """
    Singleton class to manage JSON/CSV configuration and schedule formatting.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, filepath="config/config.json"):
        if not getattr(self, '_initialized', False):
            self.filepath = filepath
            self.data = {"config": {"rooms": [], "labs": [], "courses": [], "faculty": []}}
            self._initialized = True

    @classmethod
    def get_instance(cls):
        """Provides global access to the Singleton instance."""
        if cls._instance is None:
            cls._instance = ConfigManager()
        return cls._instance

    def load(self):
        """Loads data from the JSON file."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Config file not found: {self.filepath}")
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        return self.data

    def save(self, parent: QWidget):
        """Saves current state to JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.data, f, indent=4)
                QMessageBox.information(parent, "Success", f"Saved to: {self.filepath}")
        except Exception as e:
            QMessageBox.critical(parent, "Save Error", f"Failed to save: {str(e)}")

    def get_summary_text(self):
        """Returns a string formatted as a table with dynamic padding for courses."""
        if not self.data: return "No data loaded."
        c = self.data.get("config", {})
        courses = c.get("courses", [])
        
        max_id_len = max([len(str(course.get("course_id", ""))) for course in courses] + [15]) if courses else 15
        id_col_width = max_id_len + 2

        header = f"{'COURSE ID':<{id_col_width}} | {'CREDITS':<8} | {'OTHER ATTRIBUTES'}"
        lines = [header, "-" * len(header)]

        for course in courses:
            cid = course.get("course_id", "N/A")
            creds = str(course.get("credits", "0"))
            others = " | ".join([f"{k}: {v}" for k, v in course.items() if k not in ["course_id", "credits"]])
            lines.append(f"{cid:<{id_col_width}} | {creds:<8} | {others}")

        if not courses:
            lines.append(f"{' (No courses defined) ':-^{len(header)}}")
        return "\n".join(lines)
        
    def scheduler_output_to_viewer_format(self, raw_schedules):
        """
        Converts raw scheduler output into a standardized list of dictionaries 
        for the GUI viewer strategies.
        
        :param raw_schedules: Raw data (list of dicts or objects) from the generator.
        :return: A list of formatted dictionaries.
        """
        formatted_list = []
        
        # If raw_schedules is a single schedule, wrap it in a list
        if isinstance(raw_schedules, dict):
            raw_schedules = [raw_schedules]

        for item in raw_schedules:
            # Standardize keys to ensure the Viewer doesn't crash on missing data
            entry = {
                "course": item.get("course_name") or item.get("course", "Unknown"),
                "faculty": item.get("instructor") or item.get("faculty", "Unassigned"),
                "room": item.get("room_id") or item.get("room", "TBD"),
                "day": item.get("day", "Monday"),
                "time": item.get("start_time") or item.get("time", "08:00")
            }
            formatted_list.append(entry)
            
        return formatted_list
        
    def get_schedule_spreadsheet(self, schedule_data):
        """Formats schedule data into an ASCII spreadsheet grid."""
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
        col_width, time_width = 15, 8

        header = f"{' TIME':<{time_width}} |" + "".join([f" {day:^{col_width}} |" for day in days])
        divider = "-" * len(header)
        lines = [divider, header, divider]

        for t in times:
            row = f" {t:<{time_width-1}} |"
            for d in days:
                entry = next((s for s in schedule_data if s['day'] == d and s['time'] == t), None)
                row += f" {entry['course_id'] if entry else '':^{col_width}} |"
            lines.append(row); lines.append(divider)
        return "\n".join(lines)

    def export_schedule_to_csv(self, schedule_data, filename):
        """Exports the schedule grid to a CSV file."""
        days, times = ["Mon", "Tue", "Wed", "Thu", "Fri"], ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
        try:
            with open(filename, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["TIME"] + days)
                for t in times:
                    row = [t] + [next((s['course_id'] for s in schedule_data if s['day'] == d and s['time'] == t), "") for d in days]
                    writer.writerow(row)
            return True
        except Exception: return False
