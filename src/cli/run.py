"""
File    : run.py
Author  : Tyler Strohl & Shane del Villar
Desc    : Run the scheduler task & display schedule task.
"""

from __future__ import annotations

import sys
import csv
import json
from pathlib import Path
from typing import Any, List, Optional

from common import prompt, prompt_int

src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir))
from config import ConfigManager


class Run:
    """Run/display schedule submenu: configure and run scheduler or display schedule."""

    def __init__(self, default_config_path: Path) -> None:
        self.default_config_path = default_config_path
        self.config_path: Optional[Path] = None
        self.limit: int = 2
        self.output_format: str = "json"
        self.output_path: Optional[Path] = None
        self.optimize: bool = True

    def specify_config(self) -> None:
        raw = prompt("Config file path", str(self.default_config_path)).strip()
        if not raw:
            self.config_path = self.default_config_path
        else:
            self.config_path = Path(raw)
        try:
            mgr = ConfigManager(self.config_path)
            mgr.load()
            print(f"Loaded config from {self.config_path}")
        except FileNotFoundError as e:
            print(e)

    def specify_limit(self) -> None:
        self.limit = prompt_int("Limit (number of schedules to generate)", self.limit)

    def specify_format(self) -> None:
        while True:
            raw = prompt("Output format [CSV] or [JSON]", self.output_format).strip().lower()
            if not raw:
                break
            if raw in ("csv", "json"):
                self.output_format = raw
                break
            print("Invalid choice. Please enter CSV or JSON.")

    def specify_output(self) -> None:
        raw = prompt("Output file path", "").strip()
        self.output_path = Path(raw) if raw else None

    def specify_optimize(self) -> None:
        while True:
            raw = prompt("Optimize schedules? [yes]/no", "yes").strip().lower()
            if not raw or raw == "yes":
                self.optimize = True
                break
            if raw == "no":
                self.optimize = False
                break
            print("Invalid choice. Please enter yes or no.")

    def _run_scheduler_impl(self) -> None:
        
        """Call course-constraint-scheduler if available."""
        try:
            from scheduler import Scheduler, load_config_from_file  # type: ignore
            from scheduler.config import CombinedConfig  # type: ignore
        except ImportError as e:
            print(
                "Scheduler package not available. Install dependencies and run with the project venv:\n"
                "  From project root:  uv sync\n"
                "  Then run the CLI with:  uv run python src/main.py path/to/config.json\n"
                "  Or activate the venv and run:  python src/main.py path/to/config.json"
            )
            return
        path = self.config_path or self.default_config_path
        if not path.exists():
            print(f"Config file not found: {path}. Choose option 1 to set config path.")
            return
        path_str = str(path.resolve())
        try:
            config = load_config_from_file(CombinedConfig, path_str)
        except Exception as e:
            print(f"Failed to load config: {e}")
            return
        scheduler = Scheduler(config)
        out_path = self.output_path
        if out_path and not out_path.is_absolute():
            out_path = path.parent / out_path
        schedules = []
        try:
            for i, schedule in enumerate(scheduler.get_models()):
                if i >= self.limit:
                    break
                schedules.append(schedule)
            if not schedules:
                print("No schedules generated.")
                return
        except Exception as e:
            print(f"Scheduler error: {e}")
            return
        # Output
        def course_to_dict(c: Any) -> Any:
            if hasattr(c, "model_dump"):
                return c.model_dump()
            if hasattr(c, "as_dict"):
                return c.as_dict()
            if hasattr(c, "__dict__"):
                return c.__dict__
            return str(c)

        if out_path:
            out_path = Path(out_path)
            if self.output_format == "json":
                out_data = [[course_to_dict(c) for c in sched] for sched in schedules]
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(out_data, f, indent=2)
            else:
                with open(out_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    for idx, sched in enumerate(schedules):
                        if idx > 0:
                            f.write("\n")
                        for course in sched:
                            if hasattr(course, "as_csv"):
                                f.write(course.as_csv() + "\n")
                            else:
                                writer.writerow([str(course)])
            print(f"Wrote {len(schedules)} schedule(s) to {out_path}")
        else:
            for idx, sched in enumerate(schedules):
                print(f"\n--- Schedule {idx + 1} ---")
                for course in sched:
                    print(getattr(course, "as_csv", lambda c=course: str(c))())

    def display_schedule(self) -> None:
        
        """Display schedule (e.g. from last run or current config)."""
        path = self.config_path or self.default_config_path
        if not path.exists():
            print(f"Config file not found: {path}. Choose option 1 to set config path.")
            return
        try:
            mgr = ConfigManager(path)
            mgr.load()
            mgr.display_human_summary()
        except FileNotFoundError as e:
            print(e)
        print("\n(To see a generated schedule, run the scheduler first and open the output file.)")

    def _load_schedule_from_file(self, path: Path) -> Optional[List[dict[str, Any]]]:
        """Load schedule from CSV or JSON; return list of {course_id, day, time} or None."""
        path = Path(path)
        if not path.exists():
            print(f"File not found: {path}")
            return None
        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list) or not data:
                    return [] if data == [] else None
                first = data[0]
                if isinstance(first, dict):
                    out = []
                    for item in data:
                        cid, day, t = item.get("course_id"), item.get("day"), item.get("time")
                        if cid is not None and day is not None and t is not None:
                            out.append({"course_id": str(cid), "day": str(day), "time": str(t)})
                    return out
                if isinstance(first, list):
                    out = []
                    for item in first:
                        if not isinstance(item, dict):
                            continue
                        cid, day, t = item.get("course_id"), item.get("day"), item.get("time")
                        if cid is not None and day is not None and t is not None:
                            out.append({"course_id": str(cid), "day": str(day), "time": str(t)})
                    return out
                return None
            if suffix == ".csv":
                days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
                out = []
                with open(path, encoding="utf-8", newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if not header:
                        return []
                    time_col = 0
                    day_cols = {}
                    for i, cell in enumerate(header):
                        cell = (cell or "").strip()
                        if i == 0 and cell.upper() == "TIME":
                            continue
                        if cell in days:
                            day_cols[i] = cell
                    if not day_cols and len(header) >= 6:
                        for j, d in enumerate(days):
                            if j + 1 < len(header):
                                day_cols[j + 1] = d
                    for row in reader:
                        if not row:
                            continue
                        time_slot = row[time_col].strip() if time_col < len(row) else ""
                        for col_idx, day in day_cols.items():
                            if col_idx < len(row) and row[col_idx].strip():
                                out.append({
                                    "course_id": row[col_idx].strip(),
                                    "day": day,
                                    "time": time_slot,
                                })
                return out
        except Exception as e:
            print(f"Import error: {e}")
            return None
        print("Unsupported format. Use .csv or .json.")
        return None

    def import_schedule(self) -> None:
        """Prompt for a schedule file path and print the imported schedule."""
        raw = prompt("Schedule file path (CSV or JSON)", "").strip()
        if not raw:
            return
        path = Path(raw)
        if not path.is_absolute() and (self.config_path or self.default_config_path).exists():
            path = (self.config_path or self.default_config_path).parent / path
        schedule = self._load_schedule_from_file(path)
        if schedule is None:
            print("Could not load schedule from file.")
            return
        if not schedule:
            print("No assignments found in file.")
            return
        print(f"\n--- Imported schedule ({len(schedule)} assignment(s)) ---")
        for a in schedule:
            print(f"  {a['course_id']}  {a['day']}  {a['time']}")
        print("---")

    def run_scheduler_menu(self) -> None:
        """Show Run/display schedule submenu. Does not return a dirty flag."""
        while True:
            print(
                "\n--- Run / Display Schedule ---\n"
                "1) Specify configuration file\n"
                "2) Specify limit (number of schedules to generate)\n"
                "3) Specify output format (CSV or JSON)\n"
                "4) Specify output file\n"
                "5) Specify whether to optimize schedules\n"
                "6) Run scheduler\n"
                "7) Display schedule / config summary\n"
                "8) Import schedule from file (CSV or JSON)\n"
                "9) Back to main menu\n"
            )
            choice = prompt("Choose an option", "")
            if choice == "1":
                self.specify_config()
            elif choice == "2":
                self.specify_limit()
            elif choice == "3":
                self.specify_format()
            elif choice == "4":
                self.specify_output()
            elif choice == "5":
                self.specify_optimize()
            elif choice == "6":
                self._run_scheduler_impl()
            elif choice == "7":
                self.display_schedule()
            elif choice == "8":
                self.import_schedule()
            elif choice == "9":
                return
            else:
                print("Invalid choice. Please enter 1–9.")
