'''
    File: config_mgr.py
    Date: 02/28/2026
    Author: Kyle Smith
    Class: CMSC 420
    Description: Implements saving, loading and displaying a config for the scheduler.
'''

import json
import os

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
