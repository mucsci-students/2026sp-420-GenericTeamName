'''
    File: config_mgr.py
    Date: 04/02/2026
    Author: Kyle Smith, Shane del Villar, Chayse Altland, & Tyler Strohl
    Class: CMSC 420
    Description: Implements saving, loading and displaying a config for the scheduler.
    Implements displaying the schedule in a tabulated format and saving as JSON or PDF.
'''

import json
import os

from fpdf import FPDF
from PyQt6.QtWidgets import QMessageBox, QWidget, QFileDialog

class ConfigManager:
    #May need to add viewer class in as second param.
    def __init__(self, filepath="config.json", import_file = ""):
        #filepath is used for a config file
        self.filepath = filepath
        #import_file is used for an imported schedules file
        self.import_file = import_file
        self.data = {
            "config": {
                "rooms": [],
                "labs": [],
                "courses": [],
                "faculty": [],
                "time_slots": {},
                "meeting_patterns": []
            },
            "time_slot_config": {
                "times": {},
                "classes": []
            }
        }

    def load(self, parent: QWidget):
        """Load JSON data from file."""
        
        #First check if the file exists
        if not os.path.exists(self.filepath):
            QMessageBox.critical(parent, "Load Error", f"Config file not found: {self.filepath}")
            return None
        
        #If file exists, open it, if unsuccessful, return no data.
        try:
            with open(self.filepath, "r") as f:
                self.data = json.load(f)
            return self.data
        except Exception as e:
            QMessageBox.critical(parent, "Load Error", f"Failed to parse JSON:\n{str(e)}")
            return None

    def save(self, parent: QWidget):
        """Save JSON data with 4 space indent."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.data, f, indent=4)
                QMessageBox.information(parent, "Success", f"Saved to: {self.filepath}")
        except Exception as e:
            QMessageBox.critical(parent, "Save Error", f"Failed to save: {str(e)}")

    def get_summary_text(self):
        """Returns a string formatted as a table with dynamic padding."""
        # Only return "No data" if the dictionary is empty
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

    #Used as helper to change which schedule is being displayed.   
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

    @staticmethod
    def _export_format_from_path_and_filter(file_path: str, selected_filter: str) -> str:
        """Return 'json' or 'pdf' from extension, else from the dialog filter."""
        lower = file_path.lower()
        if lower.endswith(".pdf"):
            return "pdf"
        if lower.endswith(".json"):
            return "json"
        sf = (selected_filter or "").upper()
        if "PDF" in sf and "JSON" not in sf:
            return "pdf"
        return "json"

    @staticmethod
    def _trim_schedule_grid_for_export(days, times, grid):
        """
        Drop leading/trailing empty time rows; if the grid is empty, show a typical day window.
        """
        row_has_content = [any(str(c).strip() for c in row) for row in grid]
        if not any(row_has_content):
            try:
                lo = next(i for i, t in enumerate(times) if t >= "08:00")
            except StopIteration:
                lo = 0
            try:
                hi = next(i for i in range(len(times) - 1, -1, -1) if times[i] <= "17:00")
            except StopIteration:
                hi = len(times) - 1
        else:
            indices = [i for i, has in enumerate(row_has_content) if has]
            lo, hi = min(indices), max(indices)
            lo = max(0, lo - 1)
            hi = min(len(times) - 1, hi + 1)
        return days, times[lo : hi + 1], grid[lo : hi + 1]

    @staticmethod
    def _pdf_cell_text(cell) -> str:
        if not cell:
            return ""
        return " / ".join(str(cell).splitlines())

    def _write_schedules_pdf(self, file_path: str, data_to_export: list) -> None:
        pdf = FPDF(orientation="L", unit="mm", format="Letter")
        pdf.set_margins(10, 10, 10)
        pdf.set_auto_page_break(True, margin=15)

        for i, schedule_data in enumerate(data_to_export):
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(text=f"Schedule option {i + 1}")
            pdf.ln(10)

            days, times_full, grid_full = self.get_schedule_grid_data(
                schedule_data, filter_type="all", filter_value=None
            )
            days, times_trim, grid_trim = self._trim_schedule_grid_for_export(
                days, times_full, grid_full
            )

            # Time column slightly narrower than day columns.
            col_widths = (1,) + tuple(2 for _ in days)
            pdf.set_font("Helvetica", size=8)
            with pdf.table(
                col_widths=col_widths,
                text_align="C",
                line_height=6,
                first_row_as_headings=True,
            ) as table:
                table.row(["Time", *[str(d) for d in days]])
                for ti, t in enumerate(times_trim):
                    row_cells = [str(t)]
                    for d in range(len(days)):
                        cell = (
                            grid_trim[ti][d]
                            if ti < len(grid_trim) and d < len(grid_trim[ti])
                            else ""
                        )
                        row_cells.append(self._pdf_cell_text(cell))
                    table.row(row_cells)

        pdf.output(file_path)

    def export_schedule_to_json(self, all_schedules, parent: QWidget):
        """
        Handles the Save As dialog and writes all schedules to one JSON or PDF file.
        """
        if not all_schedules:
            QMessageBox.warning(parent, "Export Error", "No schedule data available.")
            return False

        file_path, selected_filter = QFileDialog.getSaveFileName(
            parent,
            "Export Schedules",
            "generated_schedules",
            "JSON (*.json);;PDF (*.pdf);;All Files (*)",
        )

        if not file_path:
            return False

        fmt = self._export_format_from_path_and_filter(file_path, selected_filter)
        if fmt == "pdf" and not file_path.lower().endswith(".pdf"):
            file_path = file_path + ".pdf"
        elif fmt == "json" and not file_path.lower().endswith(".json"):
            file_path = file_path + ".json"

        data_to_export = (
            all_schedules if isinstance(all_schedules, list) else [all_schedules]
        )

        if fmt == "pdf":
            try:
                self._write_schedules_pdf(file_path, data_to_export)
                QMessageBox.information(parent, "Success", f"Exported to:\n{file_path}")
                return True
            except Exception as e:
                QMessageBox.critical(
                    parent, "Export Error", f"Failed to save PDF: {str(e)}"
                )
                return False

        try:
            self.write_schedules_json_file(file_path, data_to_export)
            QMessageBox.information(parent, "Success", f"Exported to:\n{file_path}")
            return True

        except Exception as e:
            QMessageBox.critical(parent, "Export Error", f"Failed to save JSON: {str(e)}")
            return False

    def write_schedules_json_file(self, file_path: str, data_to_export: list) -> None:
        """Write all schedule options to one JSON file (same grid layout as Export Schedules JSON)."""
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
        final_output = []
        for i, schedule_data in enumerate(data_to_export):
            grid = []
            grid.append([f"--- SCHEDULE OPTION {i+1} ---"])
            grid.append(["TIME"] + days)

            for t in times:
                row = [t]
                for d in days:
                    entry = next(
                        (
                            s
                            for s in schedule_data
                            if s["day"] == d and s["time"] == t
                        ),
                        None,
                    )
                    row.append(entry["course_id"] if entry else "")
                grid.append(row)

            final_output.append(grid)

        with open(file_path, mode="w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=4)

    def scheduler_output_to_viewer_format(self, schedule_list):
        """
        Standardizes raw scheduler dicts into viewer format.
        Explicitly combines 'course_id' and 'section' (e.g., CMSC 161.01).
        """
        days_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri"}
        result = []
        for item in schedule_list:
            if not isinstance(item, dict): continue

            # Get base ID and Section
            cid = item.get("course_id") or item.get("course_str") or "Unknown"
            section = item.get("section")

            # Courses are formatted as: CMSC 161.01
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

    def import_schedule_from_json(self, filename=None, parent: QWidget = None):
        """
        Imports a JSON file of schedules to view.
        """
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(
                parent, "Import Schedule JSON", "", "JSON Files (*.json);;All Files (*)"
            )

        if not filename:
            return None

        #Store the imported JSON filepath
        self.import_file = filename

        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        try:
            with open(filename, mode='r', encoding='utf-8') as f:
                imported_data = json.load(f)

            all_schedules = []
            for grid in imported_data:
                current_schedule = []
                day_cols = {}

                for row in grid:
                    if not row or not any(str(field).strip() for field in row):
                        continue

                    if str(row[0]).strip().upper() == "TIME":
                        day_cols = {i: cell.strip() for i, cell in enumerate(row) if cell.strip() in days}
                        continue

                    if day_cols:
                        time_slot = str(row[0]).strip()
                        for col_idx, day_name in day_cols.items():
                            if col_idx < len(row) and str(row[col_idx]).strip():
                                current_schedule.append({
                                    "course_id": str(row[col_idx]).strip(),
                                    "day": day_name,
                                    "time": time_slot,
                                })

                if current_schedule:
                    all_schedules.append(current_schedule)

            return all_schedules

        except Exception as e:
            print(f"JSON Import Error: {e}")
            if parent:
                QMessageBox.critical(parent, "Import Error", f"Failed to load JSON: {str(e)}")
            return None

    #NEW SCHEDULE VIEWER GRID [As seen in cfg panel]:
    def get_schedule_grid_data(self, schedule_data, filter_type="all", filter_value=None):
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        times = [f"{h:02d}:00" for h in range(24)]
        grid = [["" for _ in range(len(days))] for _ in range(len(times))]
        
        # Access the master course list from config to look up missing attributes
        master_courses = self.data.get("config", {}).get("courses", [])

        for entry in schedule_data:
  
            if filter_type != "all" and filter_value:
                # Get value from entry (CSV import style) or from master config (JSON style)
                entry_val = entry.get(filter_type)
                
                # If the attribute (like 'room') isn't in the schedule entry, 
                # find the course in the master config and check its attributes there.
                if entry_val is None:
                    # Strip section numbers (e.g., 'CMSC 161.01' -> 'CMSC 161') to match master list
                    base_id = entry.get('course_id', '').split('.')[0]
                    course_info = next((c for c in master_courses if c.get('course_id') == base_id), {})
                    entry_val = course_info.get(filter_type, [])

                # JSON stores rooms/faculty as lists
                # Check if the filter_value (string) is in the entry_val (list or string)
                if isinstance(entry_val, list):
                    if str(filter_value) not in [str(v) for v in entry_val]:
                        continue
                else:
                    if str(entry_val) != str(filter_value):
                        continue

            # 2. Placement Logic
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
