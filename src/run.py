"""
File    : run.py
Author  : Tyler Strohl
Desc    : Run the scheduler task & display schedule task.
"""

import json
import csv
import sys

from cli.common import prompt, prompt_int, prompt_list
from pathlib import Path
from config import config_mgr

class Run:

    """Considering putting the display schedule feature in here too."""


    def specify_config(self) -> None:

        filepath = prompt("Please specify the filepath: ", Path(sys.argv[0]))
        config_obj = config_mgr.ConfigManager(filepath)
        config_obj.load

    def specify_limit(self) -> None:

        """Please ensure this value gets updated in config."""
        limit = prompt_int("Please specify the limit (number of schedules to generate): ", 2)

    def specify_format(self) -> None:

        format = prompt("Please specify either [CSV] or [JSON] format: ", "")

        if format.lower() != "csv" and format.lower() != "json":
            print("Invalid choice. Please enter [CSV] or [JSON]")
            format = ""
            return

    def specify_output(self) -> None:

        filepath = prompt("Please specify the filepath: ", Path(sys.argv[0]))
        config_obj = config_mgr.ConfigManager(filepath)
        config_obj.save

    def specify_optimize(self) -> None:

        optimize = prompt("Optimize Schedules? ", "")

        if optimize.lower() != "yes" and optimize.lower() != "no":
            print("Invalid choice. Please enter [Yes] or [No]")
            optimize = ""
            return


    def display_schedule(self) -> None:

        """Display schedule in csv in this function."""

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
    