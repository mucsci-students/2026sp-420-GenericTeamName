'''
    File: config_mgr.py
    Date: 02/28/2026
    Author: Kyle Smith & Shane del Villar
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

    def get_grouped_schedule_text(self, schedule_data, group_by_key="faculty"):
        """
        Returns a tabulated string of the schedule sorted by a specific attribute.
        group_by_key: 'faculty', 'room', or 'lab'
        """
        if not schedule_data:
            return "No schedule data to display."

        # Label mapping for headers
        labels = {
            "faculty": "FACULTY",
            "room": "ROOM",
            "lab": "LAB/EQUIP"
        }
        display_label = labels.get(group_by_key, group_by_key.upper())

        # Sort the data by the chosen key
        sorted_data = sorted(schedule_data, key=lambda x: str(x.get(group_by_key, 'Unassigned')))

        # Calculate dynamic widths
        max_group_len = max([len(str(x.get(group_by_key, 'Unassigned'))) for x in sorted_data] + [len(display_label)])
        max_c_len = max([len(str(x.get('course_id', 'N/A'))) for x in sorted_data] + [12])

        g_width = max_group_len + 2
        c_width = max_c_len + 2

        # Build Header
        header = f"{display_label:<{g_width}} | {'COURSE ID':<{c_width}} | {'DAY':<6} | {'TIME':<8}"
        divider = "-" * len(header)
        lines = [divider, header, divider]

        # Build Rows
        for item in sorted_data:
            group_val = item.get(group_by_key, 'Unassigned')
            cid = item.get('course_id', 'N/A')
            day = item.get('day', 'N/A')
            time = item.get('time', 'N/A')

            lines.append(f"{group_val:<{g_width}} | {cid:<{c_width}} | {day:<6} | {time:<8}")

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

    def import_schedule_from_csv(self, filename):
        """
        Imports schedule from a CSV file (same format as export_schedule_to_csv).
        Returns list of dicts [{'course_id': str, 'day': str, 'time': str}, ...] or None on error.
        """
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        try:
            schedule_data = []
            with open(filename, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return None
                # Header: TIME, Mon, Tue, Wed, Thu, Fri (or similar)
                time_col = 0
                day_cols = {}
                for i, cell in enumerate(header):
                    cell = (cell or "").strip()
                    if i == 0 and cell.upper() == "TIME":
                        time_col = 0
                        continue
                    if cell in days:
                        day_cols[i] = cell
                if not day_cols:
                    # Fallback: assume columns 1..5 are Mon..Fri
                    for j, d in enumerate(days):
                        if j + 1 < len(header):
                            day_cols[j + 1] = d
                for row in reader:
                    if not row:
                        continue
                    time_slot = row[time_col].strip() if time_col < len(row) else ""
                    for col_idx, day in day_cols.items():
                        if col_idx < len(row) and row[col_idx].strip():
                            schedule_data.append({
                                "course_id": row[col_idx].strip(),
                                "day": day,
                                "time": time_slot,
                            })
            return schedule_data
        except Exception as e:
            print(f"CSV Import Error: {e}")
            return None

    def import_schedule_from_json(self, filename):
        """
        Imports schedule from a JSON file.
        Accepts:
          - List of assignments: [{"course_id": "...", "day": "...", "time": "..."}, ...]
          - List of schedules (CLI-style): [[{...}, ...], ...] — uses first schedule and normalizes keys.
        Returns list of dicts [{'course_id', 'day', 'time'}, ...] or None on error.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None
            if not data:
                return []
            first = data[0]
            # Single schedule: list of assignment dicts
            if isinstance(first, dict):
                result = []
                for item in data:
                    cid = item.get("course_id")
                    day = item.get("day")
                    time_val = item.get("time")
                    if cid is not None and day is not None and time_val is not None:
                        result.append({"course_id": str(cid), "day": str(day), "time": str(time_val)})
                return result
            # List of schedules (CLI export): list of lists of course dicts
            if isinstance(first, list):
                schedule = first
                result = []
                for item in schedule:
                    if not isinstance(item, dict):
                        continue
                    cid = item.get("course_id")
                    day = item.get("day")
                    time_val = item.get("time")
                    if cid is not None and day is not None and time_val is not None:
                        result.append({"course_id": str(cid), "day": str(day), "time": str(time_val)})
                return result
            return None
        except Exception as e:
            print(f"JSON Import Error: {e}")
            return None
