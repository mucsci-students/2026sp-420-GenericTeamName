"""
File    : run.py
Author  : Tyler Strohl
Desc    : Run the scheduler task.
"""

import json
import csv

from cli.common import prompt, prompt_int, prompt_list
from pathlib import Path

class Run:

    """Considering putting the display schedule feature in here too."""


    def specify_config(self) -> None:

        """Placeholder."""

    def specify_limit(self) -> None:

        """Placeholder."""

    def specify_format(self) -> None:

        """Placeholder."""

    def specify_output(self) -> None:

        """Placeholder."""

    def specify_optimize(self) -> None:

        """Placeholder."""

    def run_scheduler(self) -> None:

        dirty = False
        while True:
            print(
            "\n--- Run the scheduler ---\n"
            "1) Specify a configuration file\n"
            "2) Specify a limit (number of schedules to generate)\n"
            "3) Specify a format (csv or json)\n"
            "4) Specify an output file\n"
            "5) Specify whether to optimize the schedules\n"
            "6) Back to main menu\n"
        )
        choice = prompt("Choose an option", "")
        if choice == "1":
            specify_config()
            dirty = True
        elif choice == "2":
            specify_limit()
            dirty = True
        elif choice == "3":
            specify_format()
            dirty = True
        elif choice == "4":
            specify_output()
            dirty = True
        elif choice == "5":
            specify_optimize()
            dirty = True
        elif choice == "6":
            return dirty
        else:
            print("Invalid choice. Please enter 1–4.")
    