'''
    File: config_mgr.py
    Date: 04/02/2026
    Author: Kyle Smith, Shane del Villar, Chayse Altland, & Tyler Strohl
    Class: CMSC 420
    Description: Implements saving, loading and displaying a config for the scheduler.
    Implements displaying the schedule in a tabulated format and saving schedules as JSON or PDF (separate export flows).
'''

import copy
import json
import math
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

    def save(self, parent: QWidget, *, silent: bool = False):
        """Save JSON data with 4 space indent. ``silent`` skips the success popup (e.g. auto-save from undo)."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.data, f, indent=4)
                if not silent:
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

            days, times_full, grid_full, spans_full = self.get_schedule_grid_data(
                schedule_data, filter_type="all", filter_value=None
            )
            pdf_grid = copy.deepcopy(grid_full)
            self._inflate_spanned_cells_for_export(pdf_grid, spans_full)
            days, times_trim, grid_trim = self._trim_schedule_grid_for_export(
                days, times_full, pdf_grid
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

    @staticmethod
    def _time_sort_key(time_str: str):
        try:
            hh, mm = str(time_str).split(":")
            return (int(hh), int(mm))
        except (ValueError, AttributeError):
            return (99, 99)

    @staticmethod
    def _parse_time_minutes(raw) -> int | None:
        try:
            p = str(raw).strip().split(":")
            h = int(p[0])
            m = int(p[1]) if len(p) > 1 else 0
            return h * 60 + m
        except (ValueError, TypeError, IndexError):
            return None

    @staticmethod
    def _minutes_to_hhmm(total: int) -> str:
        t = total % (24 * 60)
        return f"{t // 60:02d}:{t % 60:02d}"

    @staticmethod
    def _coerce_optional_str_list(attr) -> list | None:
        """
        Normalize faculty/room/lab from solver entries (often a single string).
        Empty / missing values yield None so we fall back to config lists.
        """
        if attr is None:
            return None
        if isinstance(attr, list):
            parts = []
            for x in attr:
                if x is None:
                    continue
                if isinstance(x, dict):
                    name = str(x.get("name") or x.get("id") or "").strip()
                    if name:
                        parts.append(name)
                    continue
                s = str(x).strip()
                if s:
                    parts.append(s)
            return parts or None
        s = str(attr).strip()
        return [s] if s else None

    @staticmethod
    def _scheduler_day_index(day_raw) -> int | None:
        """Normalize Day enums or ints from ``model_dump`` / JSON to 1-based weekday ints."""
        if day_raw is None:
            return None
        try:
            if hasattr(day_raw, "value"):  # IntEnum etc.
                return int(day_raw.value)
        except (TypeError, ValueError):
            pass
        try:
            return int(day_raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _scheduler_start_minutes(raw) -> int | None:
        if raw is None:
            return None
        try:
            if hasattr(raw, "value"):
                raw = raw.value
            return int(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_faculty_suffix(faculty_val) -> str:
        """Return a comma-separated instructor line from list or scalar."""
        if faculty_val is None:
            return ""
        if isinstance(faculty_val, list):
            names = ", ".join(str(x).strip() for x in faculty_val if str(x).strip())
        else:
            s = str(faculty_val).strip()
            names = s
        return names

    @staticmethod
    def _schedule_cell_lines(course_id: str, faculty_suffix: str) -> str:
        course_id = str(course_id or "").strip() or "(unknown)"
        faculty_suffix = (faculty_suffix or "").strip()
        if faculty_suffix:
            return f"{course_id}\n{faculty_suffix}"
        return course_id

    @staticmethod
    def _inflate_spanned_cells_for_export(grid: list, spans: list) -> None:
        """Duplicate top-of-span cell text across covered rows so trim/PDF stays aligned."""
        for r, c, rs, _colspan in spans:
            if rs <= 1:
                continue
            text = grid[r][c]
            if not str(text).strip():
                continue
            for dr in range(1, rs):
                rr = r + dr
                if rr >= len(grid):
                    break
                if not str(grid[rr][c]).strip():
                    grid[rr][c] = text

    def _course_lookup_by_base_id(self) -> dict:
        lookup = {}
        for c in self.data.get("config", {}).get("courses", []):
            cid = str(c.get("course_id", "")).strip()
            if cid:
                lookup.setdefault(cid, []).append(c)
        return lookup

    def _values_for_group(self, entry: dict, group_mode: str, course_lookup: dict) -> list:
        base_id = str(entry.get("course_id", "")).split(".")[0]
        course_infos = course_lookup.get(base_id, [])

        def as_list(v):
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            if v is None:
                return []
            s = str(v).strip()
            return [s] if s else []

        def unique_preserve(items):
            out = []
            seen = set()
            for v in items:
                if v not in seen:
                    seen.add(v)
                    out.append(v)
            return out

        if group_mode == "faculty":
            direct = as_list(entry.get("faculty"))
            fallback = []
            for ci in course_infos:
                fallback.extend(as_list(ci.get("faculty")))
            fallback = unique_preserve(fallback)
            vals = direct or fallback
        else:
            fallback_room = []
            fallback_lab = []
            for ci in course_infos:
                fallback_room.extend(as_list(ci.get("room")))
                fallback_lab.extend(as_list(ci.get("lab")))
            fallback_room = unique_preserve(fallback_room)
            fallback_lab = unique_preserve(fallback_lab)

            room_vals = as_list(entry.get("room")) or fallback_room
            lab_vals = as_list(entry.get("lab")) or fallback_lab
            vals = room_vals + lab_vals

        return vals or ["Unassigned"]

    def _build_grouped_schedule_rows(self, schedule_data: list, group_mode: str) -> dict:
        grouped = {}
        course_lookup = self._course_lookup_by_base_id()
        for entry in schedule_data:
            day = str(entry.get("day", "N/A"))
            time = str(entry.get("time", "N/A"))
            course_id = str(entry.get("course_id", "N/A"))
            for label in self._values_for_group(entry, group_mode, course_lookup):
                grouped.setdefault(label, []).append(
                    {"course_id": course_id, "day": day, "time": time}
                )

        day_order = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4}
        for label in grouped:
            grouped[label].sort(
                key=lambda r: (
                    day_order.get(r["day"], 99),
                    self._time_sort_key(r["time"]),
                    r["course_id"],
                )
            )
        return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))

    def _write_grouped_printable_pdf(
        self, file_path: str, data_to_export: list, group_mode: str
    ) -> None:
        title = "By Faculty" if group_mode == "faculty" else "By Room/Lab"
        label = "Faculty" if group_mode == "faculty" else "Room/Lab"

        pdf = FPDF(orientation="P", unit="mm", format="Letter")
        pdf.set_margins(10, 10, 10)
        pdf.set_auto_page_break(True, margin=12)

        for i, schedule_data in enumerate(data_to_export):
            grouped = self._build_grouped_schedule_rows(schedule_data, group_mode)
            if not grouped:
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(text=f"Schedule option {i + 1}: {title}")
                pdf.ln(8)
                pdf.set_font("Helvetica", size=10)
                pdf.cell(text="No data.")
                continue

            if group_mode == "faculty":
                # One printable page per faculty member.
                for group_name, rows in grouped.items():
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.cell(text=f"Schedule option {i + 1}: Faculty posting")
                    pdf.ln(8)
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(text=f"Faculty: {group_name}")
                    pdf.ln(6)
                    pdf.set_font("Helvetica", size=9)
                    with pdf.table(
                        col_widths=(3, 1.2, 1.2),
                        text_align="L",
                        line_height=5.2,
                        first_row_as_headings=True,
                    ) as table:
                        table.row(["Course ID", "Day", "Time"])
                        for r in rows:
                            table.row([r["course_id"], r["day"], r["time"]])
            else:
                # One printable page per room/lab.
                for group_name, rows in grouped.items():
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.cell(text=f"Schedule option {i + 1}: Room/Lab posting")
                    pdf.ln(8)
                    pdf.set_font("Helvetica", "B", 12)
                    pdf.cell(text=f"Room/Lab: {group_name}")
                    pdf.ln(6)
                    pdf.set_font("Helvetica", size=9)
                    with pdf.table(
                        col_widths=(3, 1.2, 1.2),
                        text_align="L",
                        line_height=5.2,
                        first_row_as_headings=True,
                    ) as table:
                        table.row(["Course ID", "Day", "Time"])
                        for r in rows:
                            table.row([r["course_id"], r["day"], r["time"]])

        pdf.output(file_path)

    def export_grouped_printable(self, all_schedules, parent: QWidget, group_mode: str) -> bool:
        if not all_schedules:
            QMessageBox.warning(parent, "Export Error", "No schedule data available.")
            return False

        default_stem = "faculty_postings" if group_mode == "faculty" else "room_lab_postings"
        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Export Printable Grouped Schedules",
            default_stem + ".pdf",
            "PDF (*.pdf);;All Files (*)",
        )
        if not file_path:
            return False

        lower = file_path.lower()
        if not lower.endswith(".pdf"):
            file_path += ".pdf"

        data_to_export = self._enrich_schedules(all_schedules)
        try:
            self._write_grouped_printable_pdf(file_path, data_to_export, group_mode)
            QMessageBox.information(parent, "Success", f"Exported to:\n{file_path}")
            return True
        except Exception as e:
            QMessageBox.critical(parent, "Export Error", f"Failed to export printable file: {str(e)}")
            return False

    def export_schedule_to_json(self, all_schedules, parent: QWidget):
        """
        Export schedules in a self-contained format so imported filters work.
        """
        if not all_schedules:
            QMessageBox.warning(parent, "Export Error", "No schedule data available.")
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Save All Generated Schedules",
            "generated_schedules.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if not file_path:
            return False

        try:
            payload = {
                 "format": "entry_schedules_v2",
                 "schedules": self._enrich_schedules(all_schedules),
             }
 
            with open(file_path, mode="w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
 
            QMessageBox.information(parent, "Success", f"Exported to:\n{file_path}")
            return True

        except Exception as e:
            QMessageBox.critical(parent, "Export Error", f"Failed to save JSON: {str(e)}")
            return False

    def export_schedule_to_pdf(self, all_schedules, parent: QWidget):
        """
        Save As dialog for PDF only: writes all schedule options to one PDF (full grid).
        """
        if not all_schedules:
            QMessageBox.warning(parent, "Export Error", "No schedule data available.")
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Export Schedules (PDF)",
            "generated_schedules.pdf",
            "PDF (*.pdf);;All Files (*)",
        )

        if not file_path:
            return False

        if not file_path.lower().endswith(".pdf"):
            file_path = file_path + ".pdf"

        data_to_export = self._enrich_schedules(all_schedules)

        try:
            self._write_schedules_pdf(file_path, data_to_export)
            QMessageBox.information(parent, "Success", f"Exported to:\n{file_path}")
            return True
        except Exception as e:
            QMessageBox.critical(
                parent, "Export Error", f"Failed to save PDF: {str(e)}"
            )
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
        Understands pydantic ``CourseInstance.model_dump()`` shape: ``course`` or
        ``course_str``, string ``faculty`` / ``room`` / ``lab``, plus ``times``
        instances with ints or enums.
        """
        days_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri"}
        result = []
        for item in schedule_list:
            if not isinstance(item, dict):
                continue

            cid = (
                item.get("course")
                or item.get("course_str")
                or item.get("course_id")
                or ""
            )

            section = item.get("section")
            cid_s = str(cid).strip() if cid else ""

            full_name_from_parts = ""
            if section is not None and cid_s and "." not in cid_s:
                sec_str = str(section)
                full_name_from_parts = (
                    f"{cid_s}.{sec_str}" if not sec_str.startswith(".") else f"{cid_s}{sec_str}"
                )

            if full_name_from_parts and ("." not in cid_s):
                full_name = full_name_from_parts
            elif cid_s:
                full_name = cid_s
            else:
                full_name = full_name_from_parts or "Unknown"

            solver_faculty = self._coerce_optional_str_list(item.get("faculty"))
            solver_room = self._coerce_optional_str_list(item.get("room"))
            solver_lab = self._coerce_optional_str_list(item.get("lab"))

            for t in item.get("times", []):
                if not isinstance(t, dict):
                    continue
                day_num = self._scheduler_day_index(t.get("day"))

                start_mins = self._scheduler_start_minutes(t.get("start"))
                if start_mins is None:
                    start_mins = 0

                if day_num is None:
                    continue

                hhmm = self._minutes_to_hhmm(start_mins)
                entry = {
                    "course_id": full_name,
                    "day": days_map.get(day_num, "Mon"),
                    "time": hhmm,
                }
                raw_dur = t.get("duration")
                if raw_dur is None:
                    raw_dur = t.get("duration_minutes")
                if raw_dur is None:
                    raw_dur = t.get("length")
                try:
                    if hasattr(raw_dur, "value"):
                        raw_dur = raw_dur.value
                    if raw_dur is not None:
                        entry["duration_minutes"] = max(1, int(raw_dur))
                except (TypeError, ValueError):
                    pass

                if solver_faculty is not None:
                    entry["faculty"] = solver_faculty
                if solver_room is not None:
                    entry["room"] = solver_room
                if solver_lab is not None:
                    entry["lab"] = solver_lab

                result.append(self._enrich_schedule_entry(entry))
        return result

    def import_schedule_from_json(self, filename=None, parent: QWidget = None):
        """
        Import schedules from either:
        - new entry_schedules_v2 format
        - old grid format
        """
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(
                parent, "Import Schedule JSON", "", "JSON Files (*.json);;All Files (*)"
            )

        if not filename:
            return None

        self.import_file = filename
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]

        try:
            with open(filename, mode="r", encoding="utf-8") as f:
                imported_data = json.load(f)

            # New format
            if isinstance(imported_data, dict) and imported_data.get("format") == "entry_schedules_v2":
                schedules = imported_data.get("schedules", [])
                return [
                    [
                        {
                            "course_id": str(entry.get("course_id", "")).strip(),
                            "day": str(entry.get("day", "")).strip(),
                            "time": str(entry.get("time", "")).strip(),
                            "faculty": list(entry.get("faculty", []) or []),
                            "room": list(entry.get("room", []) or []),
                            "lab": list(entry.get("lab", []) or []),
                        }
                        for entry in schedule
                        if isinstance(entry, dict)
                    ]
                    for schedule in schedules
                    if isinstance(schedule, list)
                ]

            # Old grid format fallback
            master_courses = self.data.get("config", {}).get("courses", [])
            all_schedules = []

            for grid in imported_data:
                current_schedule = []
                day_cols = {}

                for row in grid:
                    if not row or not any(str(field).strip() for field in row):
                        continue

                    if str(row[0]).strip().upper() == "TIME":
                        day_cols = {
                            i: cell.strip()
                            for i, cell in enumerate(row)
                            if isinstance(cell, str) and cell.strip() in days
                        }
                        continue

                    if day_cols:
                        time_slot = str(row[0]).strip()

                        for col_idx, day_name in day_cols.items():
                            if col_idx < len(row) and str(row[col_idx]).strip():
                                full_course_id = str(row[col_idx]).strip()
                                base_id = full_course_id.split(".")[0].strip()

                                course_info = next(
                                    (
                                        c for c in master_courses
                                        if str(c.get("course_id", "")).strip() == full_course_id
                                    ),
                                    None
                                )

                                if course_info is None:
                                    course_info = next(
                                        (
                                            c for c in master_courses
                                            if str(c.get("course_id", "")).strip() == base_id
                                        ),
                                        {}
                                    )

                                current_schedule.append({
                                    "course_id": full_course_id,
                                    "day": day_name,
                                    "time": time_slot,
                                    "faculty": list(course_info.get("faculty", []) or []),
                                    "room": list(course_info.get("room", []) or []),
                                    "lab": list(course_info.get("lab", []) or []),
                                })

                if current_schedule:
                    all_schedules.append(current_schedule)

            return all_schedules

        except Exception as e:
            print(f"JSON Import Error: {e}")
            if parent:
                QMessageBox.critical(parent, "Import Error", f"Failed to load JSON: {str(e)}")
            return None

    # NEW SCHEDULE VIEWER GRID (Outlook-style granularity + faculty rows)
    def get_schedule_grid_data(self, schedule_data, filter_type="all", filter_value=None):
        """
        Builds a weekday grid using 15-minute rows between the first and last meetings
        (+ padding). Cells show course plus faculty underneath; vertical spans mimic
        block length when there is no collision in that column.
        Returns spans as (row, column, rowspan, colspan) tuples for Qt setSpan().
        """
        slot_minutes = 15
        default_duration = 55

        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        spans: list[tuple[int, int, int, int]] = []
        master_courses = self.data.get("config", {}).get("courses", [])
        enriched: list[dict] = []
        if schedule_data:
            for raw in schedule_data:
                if isinstance(raw, dict):
                    enriched.append(self._enrich_schedule_entry(dict(raw)))

        visible: list[dict] = []
        for entry in enriched:
            if filter_type != "all" and filter_value:
                entry_val = entry.get(filter_type)

                if entry_val is None:
                    base_id = entry.get("course_id", "").split(".")[0]
                    course_info = next(
                        (c for c in master_courses if c.get("course_id") == base_id),
                        {},
                    )
                    entry_val = course_info.get(filter_type, [])

                if isinstance(entry_val, list):
                    if str(filter_value) not in [str(v) for v in entry_val]:
                        continue
                elif str(entry_val) != str(filter_value):
                    continue

            visible.append(entry)

        if not visible:
            grid_start = 8 * 60
            grid_end = 18 * 60
            slots = []
            t = grid_start
            while t <= grid_end:
                slots.append(self._minutes_to_hhmm(t))
                t += slot_minutes
            n_slots = len(slots)
            grid = [["" for _ in range(len(days))] for _ in range(n_slots)]
            return days, slots, grid, spans

        start_mins: list[int] = []
        end_mins: list[int] = []

        for entry in visible:
            sm = self._parse_time_minutes(entry.get("time"))
            if sm is None:
                continue
            dm = entry.get("duration_minutes")
            try:
                dur = (
                    max(slot_minutes, int(dm))
                    if dm is not None
                    else default_duration
                )
            except (TypeError, ValueError):
                dur = default_duration
            start_mins.append(sm)
            end_mins.append(sm + dur)

        if not start_mins:
            slots = []
            ss = 8 * 60
            ee = 18 * 60
            tt = ss
            while tt <= ee:
                slots.append(self._minutes_to_hhmm(tt))
                tt += slot_minutes
            return days, slots, [["" for _ in range(len(days))] for _ in range(len(slots))], spans

        earliest = min(start_mins)
        latest = max(end_mins)

        pad = slot_minutes
        grid_start = max(0, (earliest // slot_minutes) * slot_minutes - pad)
        grid_end_min = math.ceil(latest / slot_minutes) * slot_minutes + pad
        n_slots = max(1, (grid_end_min - grid_start) // slot_minutes)
        times_seq = [
            self._minutes_to_hhmm(grid_start + i * slot_minutes) for i in range(n_slots)
        ]
        grid = [["" for _ in range(len(days))] for _ in range(n_slots)]
        occupied: dict[int, set[int]] = {}

        def _sort_key(ent: dict) -> tuple:
            d_raw = ent.get("day")
            dv = (
                days.index(d_raw)
                if d_raw in days
                else 999
            )
            tm_raw = ent.get("time")
            tm = self._parse_time_minutes(tm_raw)
            return (dv, tm if tm is not None else 9999, str(ent.get("course_id", "")))

        ordered = sorted(visible, key=_sort_key)

        for entry in ordered:
            day_raw = entry.get("day")
            if day_raw not in days:
                continue
            col = days.index(day_raw)
            sm = self._parse_time_minutes(entry.get("time"))
            if sm is None:
                continue

            dm = entry.get("duration_minutes")
            try:
                dur_min = (
                    max(slot_minutes, int(dm))
                    if dm is not None
                    else default_duration
                )
            except (TypeError, ValueError):
                dur_min = default_duration

            r0 = (sm - grid_start) // slot_minutes
            if r0 >= n_slots:
                continue
            r0 = max(0, min(r0, n_slots - 1))
            rowspan = max(1, math.ceil(dur_min / slot_minutes))
            rowspan = min(rowspan, n_slots - r0)

            label = self._schedule_cell_lines(
                str(entry.get("course_id", "")),
                self._format_faculty_suffix(entry.get("faculty")),
            )

            occ = occupied.setdefault(col, set())
            span_rows = range(r0, r0 + rowspan)
            conflict = False
            for rr in span_rows:
                if rr >= n_slots:
                    conflict = True
                    break
                if rr in occ or str(grid[rr][col]).strip():
                    conflict = True
                    break

            if conflict:
                prior = grid[r0][col]
                sep = "\n" if prior else ""
                grid[r0][col] = prior + sep + label
                occ.add(r0)
            else:
                grid[r0][col] = label
                for rr in span_rows:
                    if rr < n_slots:
                        occ.add(rr)
                if rowspan > 1:
                    spans.append((r0, col, rowspan, 1))

        return days, times_seq, grid, spans

    # Enrich schedules so exported file includes metadata for filtering
    def _enrich_schedule_entry(self, entry: dict) -> dict:
        full_course_id = str(entry.get("course_id", "")).strip()
        base_id = full_course_id.split(".")[0].strip()

        master_courses = self.data.get("config", {}).get("courses", [])

        course_info = next(
            (c for c in master_courses if str(c.get("course_id", "")).strip() == full_course_id),
            None
        )

        if course_info is None:
            course_info = next(
                (c for c in master_courses if str(c.get("course_id", "")).strip() == base_id),
                {}
            )

        enriched = dict(entry)
        ef = self._coerce_optional_str_list(entry.get("faculty"))
        er = self._coerce_optional_str_list(entry.get("room"))
        el = self._coerce_optional_str_list(entry.get("lab"))

        cfg_fac = course_info.get("faculty", []) if course_info else []
        cfg_rm = course_info.get("room", []) if course_info else []
        cfg_lb = course_info.get("lab", []) if course_info else []

        enriched["faculty"] = list(
            ef
            if ef is not None
            else (cfg_fac if isinstance(cfg_fac, list) else [])
        )
        enriched["room"] = list(
            er
            if er is not None
            else (cfg_rm if isinstance(cfg_rm, list) else [])
        )
        enriched["lab"] = list(
            el if el is not None else (cfg_lb if isinstance(cfg_lb, list) else [])
        )
        dm = entry.get("duration_minutes")
        if dm is not None:
            try:
                enriched["duration_minutes"] = max(1, int(dm))
            except (TypeError, ValueError):
                pass
        return enriched

    """
    Apply enrichment to every entry in all schedules.
    Ensures exported schedules contain full metadata needed for filtering.
    """
    def _enrich_schedules(self, all_schedules) -> list:
        data_to_export = all_schedules if isinstance(all_schedules, list) else [all_schedules]
        return [
            [self._enrich_schedule_entry(entry) for entry in schedule]
            for schedule in data_to_export
        ]
