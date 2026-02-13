#
# File: config_mgr.py
# Author: Kyle Smith
# Description: Contains loading, saving, and printing config files.
#

import json
import os

class ConfigManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = {}

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

    def get_pretty_json(self):
        """Return JSON as pretty-print."""
        return json.dumps(self.data, indent=4)

    def display_human_summary(self):
        """Print readable summary of config."""
        if not self.data:
            print("No configuration data available.")
            return

        c = self.data.get("config", {})
        print(f"{'='*10} SYSTEM CONFIGURATION {'='*10}")
        print(f"Rooms Available: {', '.join(c.get('rooms', []))}")
        print(f"Labs Available:  {', '.join(c.get('labs', []))}")
        
        print(f"\nCourses ({len(c.get('courses', []))}):")
        for course in c.get("courses", []):
            print(f" - {course['course_id']} (Credits: {course['credits']})")
            
        print(f"\nFaculty ({len(c.get('faculty', []))}):")
        for f in c.get("faculty", []):
            print(f" - {f['name']} (Limit: {f['unique_course_limit']} courses)")
        print(f"{'='*42}")
