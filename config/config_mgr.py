'''
    File: config_mgr.py
    Date: 04/02/2026
    Author: Kyle Smith, Shane del Villar, Chayse Altland, & Tyler Strohl
    Class: CMSC 420
    Description: Implements saving, loading and displaying a config for the scheduler.
    Implements displaying the schedule in a tabulated format and saving as a JSON.
'''

import json
import os
import csv
from PyQt6.QtWidgets import QMessageBox, QWidget


class ConfigManager:
    def __init__(self, filepath="config.json"):
        self.filepath = filepath
        self.data = {
            "config": {
                "rooms": [],
                "labs": [],
                "courses": [],
                "faculty": [],
                "time_slots": {},
                "meeting_patterns": [],
            },
            "time_slot_config": {
                "times": {},
                "classes": [],
            },
            "limit": 2,
            "optimizer_flags": [],
        }

    def load(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Config file not found: {self.filepath}")
        with open(self.filepath, "r") as f:
            self.data = json.load(f)
        return self.data

    def save(self, parent: QWidget):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.data, f, indent=4)
                QMessageBox.information(parent, "Success", f"Saved to: {self.filepath}")
        except Exception as e:
            QMessageBox.critical(parent, "Save Error", f"Failed to save: {str(e)}")

    def get_summary_text(self):
        if not self.data:
            return "No data loaded."

        c = self.data.get("config", {})
        courses = c.get("courses", [])
        lines = []

        max_id_len = 15
        if courses:
            max_id_len = max([len(str(course.get("course_id", ""))) for course in courses] + [15])

        id_col_width = max_id_len + 2

        header = f"{'COURSE ID':<{id_col_width}} | {'CREDITS':<8} | {'OTHER ATTRIBUTES'}"
        lines.append(header)
        lines.append("-" * len(header))

        for course in courses:
            cid = course.get("course_id", "N/A")
            creds = str(course.get("credits", "0"))
            others = " | ".join([f"{k}: {v}" for k, v in course.items() if k not in ["course_id", "credits"]])
            lines.append(f"{cid:<{id_col_width}} | {creds:<8} | {others}")

        if not courses:
            lines.append(f"{' (No courses defined) ':-^{len(header)}}")

        return "\n".join(lines)

    def get_schedule_spreadsheet(self, schedule_data):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]

        col_width = 15
        time_width = 8

        header = f"{' TIME':<{time_width}} |"
        for day in days:
            header += f" {day:^{col_width}} |"

        divider = "-" * len(header)
        lines = [divider, header, divider]

        for t in times:
            row = f" {t:<{time_width-1}} |"
            for d in days:
                entry = next((s for s in schedule_data if s['day'] == d and s['time'] == t), None)
                cell_text = entry['course_id'] if entry else ""
                row += f" {cell_text:^{col_width}} |"
            lines.append(row)
            lines.append(divider)

        return "\n".join(lines)

    def get_grouped_schedule_text(self, schedule_data, group_by_key="faculty"):
        if not schedule_data:
            return "No schedule data to display."

        labels = {
            "faculty": "FACULTY",
            "room": "ROOM",
            "lab": "LAB/EQUIP"
        }
        display_label = labels.get(group_by_key, group_by_key.upper())

        sorted_data = sorted(schedule_data, key=lambda x: str(x.get(group_by_key, 'Unassigned')))

        max_group_len = max([len(str(x.get(group_by_key, 'Unassigned'))) for x in sorted_data] + [len(display_label)])
        max_c_len = max([len(str(x.get('course_id', 'N/A'))) for x in sorted_data] + [12])

        g_width = max_group_len + 2
        c_width = max_c_len + 2

        header = f"{display_label:<{g_width}} | {'COURSE ID':<{c_width}} | {'DAY':<6} | {'TIME':<8}"
        divider = "-" * len(header)
        lines = [divider, header, divider]

        for item in sorted_data:
            group_val = item.get(group_by_key, 'Unassigned')
            cid = item.get('course_id', 'N/A')
            day = item.get('day', 'N/A')
            time = item.get('time', 'N/A')
            lines.append(f"{group_val:<{g_width}} | {cid:<{c_width}} | {day:<6} | {time:<8}")

        lines.append(divider)
        return "\n".join(lines)

    def export_schedule_to_csv(self, all_schedules, parent: QWidget):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        if not all_schedules:
            QMessageBox.warning(parent, "Export Error", "No schedule data available.")
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Save All Generated Schedules",
            "generated_schedules.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return False

        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]

        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                if all_schedules and isinstance(all_schedules[0], dict):
                    data_to_export = [all_schedules]
                else:
                    data_to_export = all_schedules

                for i, schedule_data in enumerate(data_to_export):
                    writer.writerow([f"--- SCHEDULE OPTION {i+1} ---"])
                    writer.writerow(["TIME"] + days)

                    for t in times:
                        row = [t]
                        for d in days:
                            entry = next((s for s in schedule_data if s['day'] == d and s['time'] == t), None)
                            row.append(entry['course_id'] if entry else "")
                        writer.writerow(row)

                    writer.writerow([])

            QMessageBox.information(parent, "Success", f"Exported {len(data_to_export)} schedule(s) to:\n{file_path}")
            return True

        except Exception as e:
            QMessageBox.critical(parent, "Export Error", f"Failed to save CSV: {str(e)}")
            return False

    def import_schedule_from_csv(self, filename=None, parent: QWidget = None):
        from PyQt6.QtWidgets import QFileDialog

        if not filename:
            filename, _ = QFileDialog.getOpenFileName(
                parent, "Import Schedule CSV", "", "CSV Files (*.csv);;All Files (*)"
            )

        if not filename:
            return None

        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        try:
            all_schedules = []
            current_schedule = []

            with open(filename, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)

                day_cols = {}
                time_col = 0

                for row in reader:
                    if not row or not any(field.strip() for field in row):
                        continue

                    if row[0].startswith("---"):
                        if current_schedule:
                            all_schedules.append(current_schedule)
                        current_schedule = []
                        day_cols = {}
                        continue

                    if row[0].strip().upper() == "TIME":
                        day_cols = {i: cell.strip() for i, cell in enumerate(row) if cell.strip() in days}
                        continue

                    if day_cols:
                        time_slot = row[time_col].strip()
                        for col_idx, day_name in day_cols.items():
                            if col_idx < len(row) and row[col_idx].strip():
                                current_schedule.append({
                                    "course_id": row[col_idx].strip(),
                                    "day": day_name,
                                    "time": time_slot,
                                })

                if current_schedule:
                    all_schedules.append(current_schedule)

            return all_schedules

        except Exception as e:
            print(f"CSV Import Error: {e}")
            if parent:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(parent, "Import Error", f"Failed to load CSV: {str(e)}")
            return None

    def scheduler_output_to_viewer_format(self, schedule_list):
        days_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri"}
        result = []
        for item in schedule_list:
            if not isinstance(item, dict):
                continue

            cid = item.get("course_id") or item.get("course_str") or "Unknown"
            section = item.get("section")

            if section is not None:
                sec_str = str(section)
                full_name = f"{cid}.{sec_str}" if not sec_str.startswith('.') else f"{cid}{sec_str}"
            else:
                full_name = str(cid)

            for t in item.get("times", []):
                day_num = t.get("day")
                start_mins = t.get("start", 0)
                if day_num:
                    result.append({
                        "course_id": full_name,
                        "day": days_map.get(day_num, "Mon"),
                        "time": f"{start_mins // 60:02d}:{start_mins % 60:02d}"
                    })
        return result

    def import_schedule_from_json(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None
            if not data:
                return []
            first = data[0]
            if isinstance(first, dict):
                result = []
                for item in data:
                    cid = item.get("course_id")
                    day = item.get("day")
                    time_val = item.get("time")
                    if cid is not None and day is not None and time_val is not None:
                        result.append({"course_id": str(cid), "day": str(day), "time": str(time_val)})
                return result
            if isinstance(first, list):
                schedule = first
                first_item = schedule[0] if schedule else {}
                if isinstance(first_item, dict) and "course_str" in first_item and "times" in first_item:
                    return self.scheduler_output_to_viewer_format(schedule)
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

    def get_schedule_grid_data(self, schedule_data, filter_type="all", filter_value=None):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = [f"{h:02d}:00" for h in range(24)]
        grid = [["" for _ in range(len(days))] for _ in range(len(times))]

        master_courses = self.data.get("config", {}).get("courses", [])

        for entry in schedule_data:
            if filter_type != "all" and filter_value:
                entry_val = entry.get(filter_type)

                if entry_val is None:
                    base_id = entry.get('course_id', '').split('.')[0]
                    course_info = next((c for c in master_courses if c.get('course_id') == base_id), {})
                    entry_val = course_info.get(filter_type, [])

                if isinstance(entry_val, list):
                    if str(filter_value) not in [str(v) for v in entry_val]:
                        continue
                else:
                    if str(entry_val) != str(filter_value):
                        continue

            day = entry.get('day')
            time = entry.get('time')
            course = entry.get('course_id', '')

            if day in days and time in times:
                row = times.index(time)
                col = days.index(day)
                if grid[row][col]:
                    grid[row][col] += f"\n{course}"
                else:
                    grid[row][col] = course

        return days, times, grid