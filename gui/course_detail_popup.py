'''
   File: course_detail_popup.py
   Date: 04/16/2026
   Author: Mohamed Mussa
   Class: CMSC 420
   Descrption: Popup dialog displayed when a user clicks a course block in the schedule grid.
   
'''
   

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QWidget,
)


class CourseDetailPopup(QDialog):
    """
    Frameless popup card shown near the clicked schedule cell.

    :param course_data: A dict representing one course section from the schedule.
    :param parent: Parent widget (MainWindow).
    """

    def __init__(self, course_data: dict, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._course = course_data
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QDialog  { background: transparent; }

            #card {
                background: #1e293b;
                border: 1.5px solid #3b82f6;
                border-radius: 12px;
            }
            #header {
                background: #2563eb;
                border-radius: 10px 10px 0 0;
                padding: 10px 14px;
            }
            #course_id_lbl {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            #section_lbl {
                color: rgba(255,255,255,0.75);
                font-size: 12px;
            }
            #close_btn {
                background: rgba(255,255,255,0.15);
                border: none;
                color: white;
                border-radius: 9px;
                font-size: 13px;
                padding: 1px 6px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
            }
            #close_btn:hover { background: rgba(255,255,255,0.30); }

            #body { padding: 12px 14px 14px 14px; }

            .field_label {
                color: #94a3b8;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            .field_value {
                color: #e2e8f0;
                font-size: 12px;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 8, 8)   # shadow offset

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("header")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 10, 10)
        h_layout.setSpacing(8)

        titles = QVBoxLayout()
        titles.setSpacing(2)

        course_id = self._course.get("course_id", "Unknown")
        section   = self._course.get("section", "")

        lbl_id = QLabel(course_id)
        lbl_id.setObjectName("course_id_lbl")

        lbl_sec = QLabel(f"Section {section}" if section else "")
        lbl_sec.setObjectName("section_lbl")

        titles.addWidget(lbl_id)
        if section:
            titles.addWidget(lbl_sec)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self.close)

        h_layout.addLayout(titles, 1)
        h_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        card_layout.addWidget(header)

        # ── Body ──────────────────────────────────────────────────────
        body = QFrame()
        body.setObjectName("body")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(14, 12, 14, 14)
        b_layout.setSpacing(0)

        def add_field(label: str, value: str) -> None:
            """Adds a label/value pair to the body."""
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(
                "color: #94a3b8; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
            )
            val = QLabel(value or "—")
            val.setStyleSheet("color: #e2e8f0; font-size: 12px; margin-bottom: 8px;")
            val.setWordWrap(True)
            b_layout.addWidget(lbl)
            b_layout.addWidget(val)

        # Faculty
        faculty_raw = self._course.get("faculty", [])
        if isinstance(faculty_raw, list):
            faculty_str = ", ".join(
                f.get("name", str(f)) if isinstance(f, dict) else str(f)
                for f in faculty_raw
            ) or "TBA"
        else:
            faculty_str = str(faculty_raw) if faculty_raw else "TBA"
        add_field("Faculty", faculty_str)

        # Days & Time — try multiple key shapes produced by the scheduler
        time_str = self._resolve_time_string()
        add_field("Days & Time", time_str)

        # Room
        rooms = self._course.get("room", self._course.get("rooms", []))
        if isinstance(rooms, list):
            room_str = ", ".join(str(r) for r in rooms) or "TBA"
        else:
            room_str = str(rooms) if rooms else "TBA"
        add_field("Room", room_str)

        # Lab
        labs = self._course.get("lab", self._course.get("labs", []))
        if isinstance(labs, list):
            lab_str = ", ".join(str(r) for r in labs) if labs else "None"
        else:
            lab_str = str(labs) if labs else "None"
        add_field("Lab", lab_str)

        # Credits (optional but useful)
        credits = self._course.get("credits")
        if credits is not None:
            add_field("Credits", str(credits))

        card_layout.addWidget(body)
        outer.addWidget(card)
        self.setMinimumWidth(270)

    # ------------------------------------------------------------------
    def _resolve_time_string(self) -> str:
        """
        Builds a human-readable days/time string regardless of which
        key shape the scheduler used (meeting_pattern list, flat day/time, etc.).
        """
        # Shape 1: list of meeting_pattern dicts
        patterns = self._course.get("meeting_pattern", [])
        if patterns and isinstance(patterns, list):
            parts = []
            for mp in patterns:
                days  = " ".join(mp.get("days", []))
                start = mp.get("start_time", "")
                end   = mp.get("end_time", "")
                if days and start:
                    parts.append(f"{days}  {start}–{end}" if end else f"{days}  {start}")
                elif start:
                    parts.append(f"{start}–{end}" if end else start)
            return "\n".join(parts) if parts else "TBA"

        # Shape 2: flat keys
        days      = self._course.get("days", [])
        start     = self._course.get("start_time", "")
        end       = self._course.get("end_time", "")
        time_slot = self._course.get("time_slot", "")

        day_str = " ".join(days) if isinstance(days, list) else str(days)
        if day_str and start:
            return f"{day_str}  {start}–{end}" if end else f"{day_str}  {start}"
        if day_str and time_slot:
            return f"{day_str}  {time_slot}"
        if time_slot:
            return time_slot
        return "TBA"

    # ------------------------------------------------------------------
    def show_near(self, global_pos: QPoint) -> None:
        """
        Positions and shows the popup near *global_pos*, nudging it
        back onto the screen if it would overflow.
        """
        self.adjustSize()
        x = global_pos.x() + 12
        y = global_pos.y() + 12

        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            if x + self.width()  > geo.right():
                x = global_pos.x() - self.width()  - 4
            if y + self.height() > geo.bottom():
                y = global_pos.y() - self.height() - 4

        self.move(x, y)
        self.show()
