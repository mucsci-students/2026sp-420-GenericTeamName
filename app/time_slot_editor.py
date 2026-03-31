# from PyQt6.QtWidgets import (
#     QWidget,
#     QVBoxLayout,
#     QHBoxLayout,
#     QLabel,
#     QComboBox,
#     QTimeEdit,
#     QSpinBox,
#     QPushButton,
#     QListWidget,
#     QMessageBox,
# )
# from PyQt6.QtCore import QTime

# from app.schedule_config_manager import ScheduleConfigManager


# class TimeSlotEditor(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.manager = ScheduleConfigManager()

#         self.setWindowTitle("Time Slot Editor")
#         self.resize(500, 400)

#         self.days = [
#             "Monday",
#             "Tuesday",
#             "Wednesday",
#             "Thursday",
#             "Friday",
#             "Saturday",
#             "Sunday",
#         ]

#         self.setup_ui()

#     def setup_ui(self):
#         main_layout = QVBoxLayout()

#         # Day selector
#         day_layout = QHBoxLayout()
#         day_label = QLabel("Day:")
#         self.day_combo = QComboBox()
#         self.day_combo.addItems(self.days)
#         self.day_combo.currentTextChanged.connect(self.load_day_config)
#         day_layout.addWidget(day_label)
#         day_layout.addWidget(self.day_combo)

#         # Start time
#         start_layout = QHBoxLayout()
#         start_label = QLabel("Start Time:")
#         self.start_time_edit = QTimeEdit()
#         self.start_time_edit.setDisplayFormat("HH:mm")
#         self.start_time_edit.setTime(QTime(8, 0))
#         start_layout.addWidget(start_label)
#         start_layout.addWidget(self.start_time_edit)

#         # End time
#         end_layout = QHBoxLayout()
#         end_label = QLabel("End Time:")
#         self.end_time_edit = QTimeEdit()
#         self.end_time_edit.setDisplayFormat("HH:mm")
#         self.end_time_edit.setTime(QTime(17, 0))
#         end_layout.addWidget(end_label)
#         end_layout.addWidget(self.end_time_edit)

#         # Spacing
#         spacing_layout = QHBoxLayout()
#         spacing_label = QLabel("Spacing (minutes):")
#         self.spacing_spin = QSpinBox()
#         self.spacing_spin.setRange(1, 300)
#         self.spacing_spin.setValue(60)
#         spacing_layout.addWidget(spacing_label)
#         spacing_layout.addWidget(self.spacing_spin)

#         # Buttons
#         button_layout = QHBoxLayout()
#         self.generate_button = QPushButton("Generate Slots")
#         self.save_button = QPushButton("Save")
#         button_layout.addWidget(self.generate_button)
#         button_layout.addWidget(self.save_button)

#         self.generate_button.clicked.connect(self.generate_slots_preview)
#         self.save_button.clicked.connect(self.save_day_config)

#         # Slot list
#         slots_label = QLabel("Generated Time Slots:")
#         self.slot_list = QListWidget()

#         main_layout.addLayout(day_layout)
#         main_layout.addLayout(start_layout)
#         main_layout.addLayout(end_layout)
#         main_layout.addLayout(spacing_layout)
#         main_layout.addLayout(button_layout)
#         main_layout.addWidget(slots_label)
#         main_layout.addWidget(self.slot_list)

#         self.setLayout(main_layout)

#         # Load the first day on startup
#         self.load_day_config(self.day_combo.currentText())

#     def load_day_config(self, day):
#         self.slot_list.clear()

#         time_slots = self.manager.config.get("time_slots", {})
#         day_config = time_slots.get(day)

#         if day_config:
#             start_time = day_config.get("start_time", "08:00")
#             end_time = day_config.get("end_time", "17:00")
#             spacing = day_config.get("spacing_minutes", 60)
#             slots = day_config.get("slots", [])

#             self.start_time_edit.setTime(QTime.fromString(start_time, "HH:mm"))
#             self.end_time_edit.setTime(QTime.fromString(end_time, "HH:mm"))
#             self.spacing_spin.setValue(spacing)

#             for slot in slots:
#                 self.slot_list.addItem(slot)
#         else:
#             self.start_time_edit.setTime(QTime(8, 0))
#             self.end_time_edit.setTime(QTime(17, 0))
#             self.spacing_spin.setValue(60)

#     def generate_slots_preview(self):
#         self.slot_list.clear()

#         start_time = self.start_time_edit.time().toString("HH:mm")
#         end_time = self.end_time_edit.time().toString("HH:mm")
#         spacing = self.spacing_spin.value()

#         if start_time >= end_time:
#             QMessageBox.warning(self, "Invalid Input", "Start time must be before end time.")
#             return

#         slots = self.manager.generate_time_slots(start_time, end_time, spacing)

#         for slot in slots:
#             self.slot_list.addItem(slot)

#     def save_day_config(self):
#         day = self.day_combo.currentText()
#         start_time = self.start_time_edit.time().toString("HH:mm")
#         end_time = self.end_time_edit.time().toString("HH:mm")
#         spacing = self.spacing_spin.value()

#         if start_time >= end_time:
#             QMessageBox.warning(self, "Invalid Input", "Start time must be before end time.")
#             return

#         self.manager.set_day_config(day, start_time, end_time, spacing)
#         self.manager.save_config()

#         self.generate_slots_preview()

#         QMessageBox.information(self, "Saved", f"{day} time slots saved successfully.")

from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtWidgets import QInputDialog, QMessageBox


class TimeSlotEditor:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr

    def _get_timeslots(self) -> dict:
        config = self.config_mgr.data.setdefault("config", {})
        return config.setdefault("time_slots", {})

    def _generate_slots(self, start_time: str, end_time: str, spacing: int) -> list[str]:
        slots = []
        current = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")

        while current < end:
            slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=spacing)

        return slots

    def add_time_slot(self, parent):
        time_slots = self._get_timeslots()

        day, ok = QInputDialog.getItem(
            parent,
            "Add Timeslot",
            "Select day:",
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            0,
            False,
        )
        if not ok:
            return

        start_time, ok = QInputDialog.getText(parent, "Add Timeslot", "Start time (HH:MM):")
        if not ok or not start_time.strip():
            return

        end_time, ok = QInputDialog.getText(parent, "Add Timeslot", "End time (HH:MM):")
        if not ok or not end_time.strip():
            return

        spacing, ok = QInputDialog.getInt(parent, "Add Timeslot", "Spacing (minutes):", 60, 1, 300)
        if not ok:
            return

        if start_time >= end_time:
            QMessageBox.warning(parent, "Invalid Input", "Start time must be before end time.")
            return

        try:
            time_slots[day] = {
                "enabled": True,
                "start_time": start_time,
                "end_time": end_time,
                "spacing_minutes": spacing,
                "slots": self._generate_slots(start_time, end_time, spacing),
            }
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Saved", f"{day} timeslots added successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to add timeslots: {e}")

    def modify_time_slot(self, parent):
        time_slots = self._get_timeslots()

        if not time_slots:
            QMessageBox.warning(parent, "No Data", "No timeslots exist yet.")
            return

        day, ok = QInputDialog.getItem(
            parent,
            "Modify Timeslot",
            "Select day:",
            list(time_slots.keys()),
            0,
            False,
        )
        if not ok:
            return

        current = time_slots[day]

        start_time, ok = QInputDialog.getText(
            parent,
            "Modify Timeslot",
            "Start time (HH:MM):",
            text=current.get("start_time", "08:00"),
        )
        if not ok or not start_time.strip():
            return

        end_time, ok = QInputDialog.getText(
            parent,
            "Modify Timeslot",
            "End time (HH:MM):",
            text=current.get("end_time", "17:00"),
        )
        if not ok or not end_time.strip():
            return

        spacing, ok = QInputDialog.getInt(
            parent,
            "Modify Timeslot",
            "Spacing (minutes):",
            current.get("spacing_minutes", 60),
            1,
            300,
        )
        if not ok:
            return

        if start_time >= end_time:
            QMessageBox.warning(parent, "Invalid Input", "Start time must be before end time.")
            return

        try:
            time_slots[day] = {
                "enabled": True,
                "start_time": start_time,
                "end_time": end_time,
                "spacing_minutes": spacing,
                "slots": self._generate_slots(start_time, end_time, spacing),
            }
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Updated", f"{day} timeslots updated successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to modify timeslots: {e}")

    def delete_time_slot(self, parent):
        time_slots = self._get_timeslots()

        if not time_slots:
            QMessageBox.warning(parent, "No Data", "No timeslots exist yet.")
            return

        day, ok = QInputDialog.getItem(
            parent,
            "Delete Timeslot",
            "Select day:",
            list(time_slots.keys()),
            0,
            False,
        )
        if not ok:
            return

        confirm = QMessageBox.question(
            parent,
            "Confirm Delete",
            f"Delete timeslots for {day}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            del time_slots[day]
            self.config_mgr.save(parent)
            QMessageBox.information(parent, "Deleted", f"{day} timeslots deleted successfully.")
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to delete timeslots: {e}")