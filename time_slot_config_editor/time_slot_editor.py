'''
    File: time_slot_editor.py
    Date: 04/01/2026
    Author: Chayse Altland & Mohamed Musa
    Class: CMSC 420
    Description: Implements adding, modifying, and deleting time slots for specified days
'''
from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtWidgets import QInputDialog, QMessageBox

print("DEBUG: loaded app/time_slot_editor.py from schedule-config-editor")
class TimeSlotEditor:
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

    def _generate_slots(self, start_time: str, end_time: str, spacing: int) -> list[str]:
        slots = []
        current = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        while current < end:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=spacing)

        return slots

    def _normalize_day_entry(self, day_entry: dict) -> dict:
        """
        Backward compatibility:
        old shape:
        {
            "enabled": True,
            "start_time": "...",
            "end_time": "...",
            "spacing_minutes": 60,
            "slots": [...]
        }

        new shape:
        {
            "enabled": True,
            "blocks": [
                {
                    "start_time": "...",
                    "end_time": "...",
                    "spacing_minutes": 60,
                    "slots": [...]
                }
            ]
        }
        """
        if "blocks" in day_entry:
            return day_entry

        if {"start_time", "end_time", "spacing_minutes"} <= set(day_entry.keys()):
            return {
                "enabled": day_entry.get("enabled", True),
                "blocks": [
                    {
                        "start_time": day_entry["start_time"],
                        "end_time": day_entry["end_time"],
                        "spacing_minutes": day_entry["spacing_minutes"],
                        "slots": day_entry.get(
                            "slots",
                            self._generate_slots(
                                day_entry["start_time"],
                                day_entry["end_time"],
                                day_entry["spacing_minutes"],
                            ),
                        ),
                    }
                ],
            }

        return {
            "enabled": day_entry.get("enabled", True),
            "blocks": [],
        }

    def _get_timeslots(self) -> dict:
        config = self.config_mgr.data.setdefault("config", {})
        time_slots = config.get("time_slots")

        if time_slots:
            normalized = {}
            for day, entry in time_slots.items():
                normalized[day] = self._normalize_day_entry(entry)
            config["time_slots"] = normalized
            return config["time_slots"]

        # Fallback: build GUI format from scheduler format
        scheduler_cfg = self.config_mgr.data.get("time_slot_config", {})
        scheduler_times = scheduler_cfg.get("times", {})

        converted = {}
        for short_day, blocks in scheduler_times.items():
            long_day = self.REVERSE_DAY_MAP.get(short_day)
            if not long_day:
                continue

            converted_blocks = []
            for block in blocks:
                start_time = block.get("start", "08:00")
                end_time = block.get("end", "17:00")
                spacing = block.get("spacing", 60)

                converted_blocks.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "spacing_minutes": spacing,
                    "slots": self._generate_slots(start_time, end_time, spacing),
                })

            converted[long_day] = {
                "enabled": True,
                "blocks": converted_blocks,
            }

        config["time_slots"] = converted
        return config["time_slots"]

    def _sync_time_slot_config(self) -> None:
        ui_slots = self._get_timeslots()

        times = {}
        for day, day_entry in ui_slots.items():
            if not day_entry.get("enabled", True):
                continue

            short_day = self.DAY_MAP.get(day)
            if not short_day:
                continue

            blocks = []
            for block in day_entry.get("blocks", []):
                blocks.append({
                    "start": block["start_time"],
                    "end": block["end_time"],
                    "spacing": block["spacing_minutes"],
                })

            times[short_day] = blocks

        top = self.config_mgr.data.setdefault("time_slot_config", {})
        top["times"] = times
        top.setdefault("classes", [])

    def _prompt_for_block(self, parent, title: str, existing: dict | None = None) -> dict | None:
        existing = existing or {}

        start_time, ok = QInputDialog.getText(
            parent,
            title,
            "Start time (HH:MM):",
            text=existing.get("start_time", "08:00"),
        )
        if not ok or not start_time.strip():
            return None

        end_time, ok = QInputDialog.getText(
            parent,
            title,
            "End time (HH:MM):",
            text=existing.get("end_time", "17:00"),
        )
        if not ok or not end_time.strip():
            return None

        spacing, ok = QInputDialog.getInt(
            parent,
            title,
            "Spacing (minutes):",
            existing.get("spacing_minutes", 60),
            1,
            300,
        )
        if not ok:
            return None

        if start_time >= end_time:
            QMessageBox.warning(parent, "Invalid Input", "Start time must be before end time.")
            return None

        return {
            "start_time": start_time,
            "end_time": end_time,
            "spacing_minutes": spacing,
            "slots": self._generate_slots(start_time, end_time, spacing),
        }

    def add_time_slot(self, parent):
        time_slots = self._get_timeslots()

        day, ok = QInputDialog.getItem(
            parent,
            "Add Timeslot",
            "Select day:",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            0,
            False,
        )
        if not ok:
            return

        block = self._prompt_for_block(parent, f"Add Timeslot for {day}")
        if block is None:
            return

        try:
            day_entry = self._normalize_day_entry(time_slots.get(day, {"enabled": True, "blocks": []}))
            day_entry.setdefault("blocks", []).append(block)
            day_entry["enabled"] = True
            time_slots[day] = day_entry

            self._sync_time_slot_config()
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Saved", f"Timeslot block added for {day}.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add timeslot: {e}")

    def modify_time_slot(self, parent):
        time_slots = self._get_timeslots()

        available_days = [day for day, entry in time_slots.items() if entry.get("blocks")]
        if not available_days:
            QMessageBox.warning(parent, "No Data", "No timeslots exist yet.")
            return

        day, ok = QInputDialog.getItem(
            parent,
            "Modify Timeslot",
            "Select day:",
            available_days,
            0,
            False,
        )
        if not ok:
            return

        day_entry = self._normalize_day_entry(time_slots[day])
        blocks = day_entry.get("blocks", [])
        if not blocks:
            QMessageBox.warning(parent, "No Data", f"No timeslot blocks exist for {day}.")
            return

        labels = [
            f"Block {i + 1}: {b['start_time']} - {b['end_time']} every {b['spacing_minutes']} min"
            for i, b in enumerate(blocks)
        ]

        selected_label, ok = QInputDialog.getItem(
            parent,
            "Modify Timeslot",
            "Select block:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        block_index = labels.index(selected_label)
        updated_block = self._prompt_for_block(
            parent,
            f"Modify Timeslot for {day}",
            existing=blocks[block_index],
        )
        if updated_block is None:
            return

        try:
            blocks[block_index] = updated_block
            time_slots[day] = day_entry

            self._sync_time_slot_config()
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Updated", f"Timeslot block updated for {day}.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to modify timeslot: {e}")

    def delete_time_slot(self, parent):
        time_slots = self._get_timeslots()

        available_days = [day for day, entry in time_slots.items() if entry.get("blocks")]
        if not available_days:
            QMessageBox.warning(parent, "No Data", "No timeslots exist yet.")
            return

        day, ok = QInputDialog.getItem(
            parent,
            "Delete Timeslot",
            "Select day:",
            available_days,
            0,
            False,
        )
        if not ok:
            return

        day_entry = self._normalize_day_entry(time_slots[day])
        blocks = day_entry.get("blocks", [])
        if not blocks:
            QMessageBox.warning(parent, "No Data", f"No timeslot blocks exist for {day}.")
            return

        labels = [
            f"Block {i + 1}: {b['start_time']} - {b['end_time']} every {b['spacing_minutes']} min"
            for i, b in enumerate(blocks)
        ]

        selected_label, ok = QInputDialog.getItem(
            parent,
            "Delete Timeslot",
            "Select block to delete:",
            labels,
            0,
            False,
        )
        if not ok:
            return

        block_index = labels.index(selected_label)

        confirm = QMessageBox.question(
            parent,
            "Confirm Delete",
            f"Delete {selected_label} for {day}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            del blocks[block_index]

            if not blocks:
                del time_slots[day]
            else:
                time_slots[day] = day_entry

            self._sync_time_slot_config()
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Deleted", f"Timeslot block deleted for {day}.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete timeslot: {e}")