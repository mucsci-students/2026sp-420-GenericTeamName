'''
    File: config_mgr.py
    Date: 04/03/2026
    Author: Chayse Altland
    Class: CMSC 420
    Description: Implements saving, loading and displaying a class meeting pattern for the scheduler.
'''
from __future__ import annotations

from PyQt6.QtWidgets import QInputDialog, QMessageBox


class MeetingPatternEditor:
    DAY_MAP = {
        "Monday": "MON",
        "Tuesday": "TUE",
        "Wednesday": "WED",
        "Thursday": "THU",
        "Friday": "FRI",
    }

    REVERSE_DAY_MAP = {v: k for k, v in DAY_MAP.items()}

    def __init__(self, config_mgr):
        self.config_mgr = config_mgr

    def _get_patterns(self) -> list:
        config = self.config_mgr.data.setdefault("config", {})
        gui_patterns = config.get("meeting_patterns")

        if gui_patterns:
            return gui_patterns

        # Fallback from scheduler format
        scheduler_cfg = self.config_mgr.data.get("time_slot_config", {})
        scheduler_patterns = scheduler_cfg.get("classes", [])

        converted = []
        for pattern in scheduler_patterns:
            meetings = []
            for meeting in pattern.get("meetings", []):
                day = self.REVERSE_DAY_MAP.get(meeting.get("day"), meeting.get("day"))
                meetings.append({
                    "day": day,
                    "duration": meeting.get("duration", 50),
                    "lab": bool(meeting.get("lab", False)),
                })

            converted.append({
                "credits": pattern.get("credits", 3),
                "meetings": meetings,
                "start_time": pattern.get("start_time", ""),
                "disabled": bool(pattern.get("disabled", False)),
            })

        config["meeting_patterns"] = converted
        return config["meeting_patterns"]

    def _sync_time_slot_config_classes(self) -> None:
        gui_patterns = self._get_patterns()

        classes = []
        for pattern in gui_patterns:
            meetings = []
            for meeting in pattern.get("meetings", []):
                short_day = self.DAY_MAP.get(meeting.get("day"))
                if not short_day:
                    continue

                sched_meeting = {
                    "day": short_day,
                    "duration": int(meeting.get("duration", 50)),
                }
                if meeting.get("lab", False):
                    sched_meeting["lab"] = True

                meetings.append(sched_meeting)

            if not meetings:
                continue

            sched_pattern = {
                "credits": int(pattern.get("credits", 3)),
                "meetings": meetings,
            }

            start_time = str(pattern.get("start_time", "")).strip()
            if start_time:
                sched_pattern["start_time"] = start_time

            if pattern.get("disabled", False):
                sched_pattern["disabled"] = True

            classes.append(sched_pattern)

        top = self.config_mgr.data.setdefault("time_slot_config", {})
        top.setdefault("times", {})
        top["classes"] = classes

    def _prompt_yes_no(self, parent, title: str, label: str, default: bool = False) -> bool | None:
        value, ok = QInputDialog.getItem(
            parent,
            title,
            label,
            ["False", "True"],
            1 if default else 0,
            False,
        )
        if not ok:
            return None
        return value == "True"

    def _prompt_for_meetings(self, parent, existing: list | None = None) -> list | None:
        existing = existing or []
        meetings = []

        count, ok = QInputDialog.getInt(
            parent,
            "Meetings",
            "Number of meetings in this pattern:",
            value=max(1, len(existing)) if existing else 1,
            min=1,
            max=5,
        )
        if not ok:
            return None

        weekday_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

        for i in range(count):
            prev = existing[i] if i < len(existing) else {}

            day_default = prev.get("day", "Monday")
            day_index = weekday_options.index(day_default) if day_default in weekday_options else 0

            day, ok = QInputDialog.getItem(
                parent,
                "Meeting Day",
                f"Meeting {i + 1} day:",
                weekday_options,
                day_index,
                False,
            )
            if not ok:
                return None

            duration, ok = QInputDialog.getInt(
                parent,
                "Meeting Duration",
                f"Meeting {i + 1} duration (minutes):",
                value=int(prev.get("duration", 50)),
                min=1,
                max=500,
            )
            if not ok:
                return None

            lab_value = self._prompt_yes_no(
                parent,
                "Lab Meeting",
                f"Is meeting {i + 1} a lab?",
                default=bool(prev.get("lab", False)),
            )
            if lab_value is None:
                return None

            meetings.append({
                "day": day,
                "duration": duration,
                "lab": lab_value,
            })

        return meetings

    def _prompt_for_pattern(self, parent, existing: dict | None = None) -> dict | None:
        existing = existing or {}

        credits, ok = QInputDialog.getInt(
            parent,
            "Pattern Credits",
            "Credits:",
            value=int(existing.get("credits", 3)),
            min=1,
            max=10,
        )
        if not ok:
            return None

        meetings = self._prompt_for_meetings(parent, existing.get("meetings", []))
        if meetings is None:
            return None

        start_time, ok = QInputDialog.getText(
            parent,
            "Fixed Start Time",
            "Fixed start time (HH:MM, leave blank for none):",
            text=str(existing.get("start_time", "")),
        )
        if not ok:
            return None

        disabled = self._prompt_yes_no(
            parent,
            "Disable Pattern",
            "Disable this pattern?",
            default=bool(existing.get("disabled", False)),
        )
        if disabled is None:
            return None

        return {
            "credits": credits,
            "meetings": meetings,
            "start_time": start_time.strip(),
            "disabled": disabled,
        }

    def _pattern_label(self, pattern: dict, index: int) -> str:
        meetings_str = ", ".join(
            f"{m.get('day', '?')} {m.get('duration', '?')}{' lab' if m.get('lab') else ''}"
            for m in pattern.get("meetings", [])
        )
        start_str = f", start={pattern.get('start_time')}" if pattern.get("start_time") else ""
        disabled_str = ", disabled" if pattern.get("disabled") else ""
        return f"Pattern {index + 1}: {pattern.get('credits', '?')} cr | {meetings_str}{start_str}{disabled_str}"

    def add_meeting_pattern(self, parent):
        patterns = self._get_patterns()
        new_pattern = self._prompt_for_pattern(parent)
        if new_pattern is None:
            return

        try:
            patterns.append(new_pattern)
            self._sync_time_slot_config_classes()
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Saved", "Meeting pattern added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add meeting pattern: {e}")

    def modify_meeting_pattern(self, parent):
        patterns = self._get_patterns()

        if not patterns:
            QMessageBox.warning(parent, "No Data", "No meeting patterns exist yet.")
            return

        labels = [self._pattern_label(p, i) for i, p in enumerate(patterns)]

        selected, ok = QInputDialog.getItem(
            parent,
            "Modify Meeting Pattern",
            "Select pattern:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        index = labels.index(selected)
        updated = self._prompt_for_pattern(parent, patterns[index])
        if updated is None:
            return

        try:
            patterns[index] = updated
            self._sync_time_slot_config_classes()
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Updated", "Meeting pattern updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to modify meeting pattern: {e}")

    def delete_meeting_pattern(self, parent):
        patterns = self._get_patterns()

        if not patterns:
            QMessageBox.warning(parent, "No Data", "No meeting patterns exist yet.")
            return

        labels = [self._pattern_label(p, i) for i, p in enumerate(patterns)]

        selected, ok = QInputDialog.getItem(
            parent,
            "Delete Meeting Pattern",
            "Select pattern:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        index = labels.index(selected)

        confirm = QMessageBox.question(
            parent,
            "Confirm Delete",
            f"Delete {selected}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            del patterns[index]
            self._sync_time_slot_config_classes()
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Deleted", "Meeting pattern deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete meeting pattern: {e}")