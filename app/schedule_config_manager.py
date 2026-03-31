import json
from pathlib import Path


class ScheduleConfigManager:
    def __init__(self, filepath="config/schedule_config.json"):
        self.filepath = Path(filepath)
        self.config = self.load_config()

    def load_config(self):
        if self.filepath.exists():
            with open(self.filepath, "r") as f:
                return json.load(f)
        return {
            "time_slots": {},
            "meeting_patterns": []
        }

    def save_config(self):
        with open(self.filepath, "w") as f:
            json.dump(self.config, f, indent=4)

    # ---------- TIME SLOTS ----------
    def set_day_config(self, day, start_time, end_time, spacing):
        self.config["time_slots"][day] = {
            "enabled": True,
            "start_time": start_time,
            "end_time": end_time,
            "spacing_minutes": spacing,
            "slots": self.generate_time_slots(start_time, end_time, spacing)
        }

    def generate_time_slots(self, start_time, end_time, spacing):
        from datetime import datetime, timedelta

        slots = []
        current = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        while current < end:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=spacing)

        return slots

    # ---------- MEETING PATTERNS ----------
    def add_meeting_pattern(self, pattern):
        self.config["meeting_patterns"].append(pattern)

    def remove_meeting_pattern(self, name):
        self.config["meeting_patterns"] = [
            p for p in self.config["meeting_patterns"] if p["name"] != name
        ]