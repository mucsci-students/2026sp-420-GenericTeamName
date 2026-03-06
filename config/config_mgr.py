'''
    File: config_mgr.py
    Date: 02/28/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Implements saving, loading and displaying a config for the scheduler.
    Implements displaying the schedule in a tabulated format and saving as a CSV.
'''

import json
import os
import csv

class ConfigManager:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        self.data = {"config": {"rooms": [], "labs": [], "courses": [], "faculty": []}}

    def load(self):
        """Load data from the JSON file."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Config file not found: {self.filepath}")
        with open(self.filepath, 'r') as f:
            self.data = json.load(f)
        return self.data

    def save(self):
        """Save JSON data with 4 space indent."""
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_summary_text(self):
        """Returns a string formatted as a table with dynamic padding."""
        # Only return "No data" if the dictionary is literally empty
        if not self.data:
            return "No data loaded."

        # Safely get the config dictionary
        c = self.data.get("config", {})
        
        # Ensure 'courses' is a list even if 'config' key was missing
        courses = c.get("courses", [])
        lines = []

        # Determine dynamic width (minimum 15 for the header)
        # We handle the case where courses might be empty to avoid max() errors
        max_id_len = 15
        if courses:
            max_id_len = max([len(str(course.get("course_id", ""))) for course in courses] + [15])
        
        id_col_width = max_id_len + 2

        # Table Header (Always printed if self.data exists)
        header = f"{'COURSE ID':<{id_col_width}} | {'CREDITS':<8} | {'OTHER ATTRIBUTES'}"
        lines.append(header)
        lines.append("-" * len(header))

        # Table Rows
        for course in courses:
            cid = course.get("course_id", "N/A")
            creds = str(course.get("credits", "0"))
            others = " | ".join([f"{k}: {v}" for k, v in course.items() if k not in ["course_id", "credits"]])
            lines.append(f"{cid:<{id_col_width}} | {creds:<8} | {others}")

        if not courses:
            lines.append(f"{' (No courses defined) ':-^{len(header)}}")

        return "\n".join(lines)

    def get_schedule_spreadsheet(self, schedule_data):
        """
        Formats schedule data into an ASCII spreadsheet grid.
        schedule_data: List of dicts e.g. [{'course_id': 'CS101', 'day': 'Mon', 'time': '09:00'}, ...]
        """
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        # Define standard time slots
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]

        col_width = 15
        time_width = 8

        # Create the Header
        header = f"{' TIME':<{time_width}} |"
        for day in days:
            header += f" {day:^{col_width}} |"

        divider = "-" * len(header)
        lines = [divider, header, divider]

        # Build Rows
        for t in times:
            row = f" {t:<{time_width-1}} |"
            for d in days:
                # Find course assigned to this day and time
                entry = next((s for s in schedule_data if s['day'] == d and s['time'] == t), None)
                cell_text = entry['course_id'] if entry else ""
                row += f" {cell_text:^{col_width}} |"
            lines.append(row)
            lines.append(divider)

        return "\n".join(lines)

    def export_schedule_to_csv(self, schedule_data, filename="schedule.csv"):
        """Exports the schedule grid to a CSV file."""
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]

        try:
            with open(filename, mode='w', newline='') as f:
                writer = csv.writer(f)
                # Header row
                writer.writerow(["TIME"] + days)

                # Data rows
                for t in times:
                    row = [t]
                    for d in days:
                        entry = next((s for s in schedule_data if s['day'] == d and s['time'] == t), None)
                        row.append(entry['course_id'] if entry else "")
                    writer.writerow(row)
            return True
        except Exception as e:
            print(f"CSV Export Error: {e}")
            return False
