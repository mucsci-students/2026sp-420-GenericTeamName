'''
   File: course_detail_popup.py
   Date: 04/16/2026
   Author: Mohamed Mussa
   Class: CMSC 420
   Descrption: Popup dialog displayed when a user clicks a course block in the schedule grid.

'''

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CourseDetailPopup(QDialog):
    """
    Frameless popup card shown near the clicked schedule cell.

    ``course_data`` may be one course mapping or a sequence of mappings when multiple
    sections share the same visible calendar cell.
    """

    def __init__(
        self,
        course_data: Mapping | Sequence[Mapping],
        parent: QWidget | None = None,
    ):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if isinstance(course_data, Mapping):
            self._courses: list[Mapping] = [course_data]
        elif isinstance(course_data, Sequence):
            seq = list(course_data)
            self._courses = seq if seq else [{"course_id": "Unknown"}]
        else:
            self._courses = [{"course_id": "Unknown"}]

        self._setup_ui()

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
            #subpanel_head {
                color: #f8fafc;
                font-weight: bold;
                font-size: 13px;
                margin-top: 4px;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 8, 8)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 10, 10)
        h_layout.setSpacing(8)

        titles = QVBoxLayout()
        titles.setSpacing(2)

        if len(self._courses) == 1:
            c0 = self._courses[0]
            course_id = c0.get("course_id", "Unknown")
            section = c0.get("section", "")

            lbl_id = QLabel(str(course_id))
            lbl_id.setObjectName("course_id_lbl")

            lbl_sec = QLabel(f"Section {section}" if section else "")
            lbl_sec.setObjectName("section_lbl")

            titles.addWidget(lbl_id)
            if section:
                titles.addWidget(lbl_sec)
        else:
            lbl_banner = QLabel("Multiple classes · one time slot")
            lbl_banner.setObjectName("section_lbl")
            lbl_banner.setWordWrap(True)
            lbl_detail = QLabel(
                f"This cell lists {len(self._courses)} different sections. Scroll to compare."
            )
            lbl_detail.setObjectName("section_lbl")
            lbl_detail.setWordWrap(True)
            titles.addWidget(lbl_banner)
            titles.addWidget(lbl_detail)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self.close)

        h_layout.addLayout(titles, 1)
        h_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        card_layout.addWidget(header)

        body = QFrame()
        body.setObjectName("body")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(14, 12, 14, 14)
        b_layout.setSpacing(8)

        if len(self._courses) == 1:
            self._add_course_fields_block(b_layout, self._courses[0])
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
            scroll.setMaximumHeight(420)

            inner = QWidget()
            inner_l = QVBoxLayout(inner)
            inner_l.setSpacing(14)
            inner_l.setContentsMargins(0, 0, 0, 4)

            last_i = len(self._courses) - 1
            for i, crs in enumerate(self._courses):
                sub = QFrame()
                sub_l = QVBoxLayout(sub)
                sub_l.setSpacing(6)
                sub_l.setContentsMargins(0, 0, 0, 10)
                if i != last_i:
                    sub.setStyleSheet(
                        "QFrame { border-bottom: 1px solid rgba(148,163,184,0.35); }"
                    )

                head = QLabel()
                cid = str(crs.get("course_id", "Unknown")).strip()
                sec = crs.get("section", "")
                if sec:
                    head.setText(f"{cid} · Section {sec}")
                else:
                    head.setText(cid)
                head.setObjectName("subpanel_head")
                font = head.font()
                font.setBold(True)
                font.setPointSize(12)
                head.setFont(font)
                sub_l.addWidget(head)

                self._add_course_fields_block(sub_l, crs)

                inner_l.addWidget(sub)

            inner_l.addStretch(1)
            scroll.setWidget(inner)
            b_layout.addWidget(scroll)

        card_layout.addWidget(body)

        outer.addWidget(card)
        min_w = 320 if len(self._courses) > 1 else 270
        self.setMinimumWidth(min_w)

    @staticmethod
    def _resolve_time_string(course: Mapping) -> str:
        patterns = course.get("meeting_pattern", [])
        if patterns and isinstance(patterns, list):
            parts = []
            for mp in patterns:
                days_txt = " ".join(mp.get("days", []))
                start = mp.get("start_time", "")
                end = mp.get("end_time", "")
                if days_txt and start:
                    parts.append(f"{days_txt}  {start}–{end}" if end else f"{days_txt}  {start}")
                elif start:
                    parts.append(f"{start}–{end}" if end else start)
            return "\n".join(parts) if parts else "TBA"

        days_raw = course.get("days", [])
        start_t = course.get("start_time", "")
        end_t = course.get("end_time", "")
        time_slot = course.get("time_slot", "")
        day_str = " ".join(days_raw) if isinstance(days_raw, list) else str(days_raw)

        if day_str and start_t:
            return f"{day_str}  {start_t}–{end_t}" if end_t else f"{day_str}  {start_t}"
        if day_str and time_slot:
            return f"{day_str}  {time_slot}"
        if time_slot:
            return str(time_slot)
        return "TBA"

    def _add_course_fields_block(self, target: QVBoxLayout, course: Mapping) -> None:
        def add_field(label: str, value: str) -> None:
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(
                "color: #94a3b8; font-size: 10px; font-weight: bold; letter-spacing: 1px;"
            )
            val = QLabel(value or "—")
            val.setStyleSheet("color: #e2e8f0; font-size: 12px; margin-bottom: 8px;")
            val.setWordWrap(True)
            target.addWidget(lbl)
            target.addWidget(val)

        faculty_raw = course.get("faculty", [])
        if isinstance(faculty_raw, list):
            faculty_str = ", ".join(
                f.get("name", str(f)) if isinstance(f, dict) else str(f)
                for f in faculty_raw
            ) or "TBA"
        else:
            faculty_str = str(faculty_raw) if faculty_raw else "TBA"

        add_field("Faculty", faculty_str)

        add_field("Days & Time", self._resolve_time_string(course))

        rooms = course.get("room", course.get("rooms", []))
        if isinstance(rooms, list):
            room_str = ", ".join(str(r) for r in rooms) or "TBA"
        else:
            room_str = str(rooms) if rooms else "TBA"
        add_field("Room", room_str)

        labs = course.get("lab", course.get("labs", []))
        if isinstance(labs, list):
            lab_str = ", ".join(str(r) for r in labs) if labs else "None"
        else:
            lab_str = str(labs) if labs else "None"
        add_field("Lab", lab_str)

        credits = course.get("credits")
        if credits is not None:
            add_field("Credits", str(credits))

    # ------------------------------------------------------------------
    def show_near(self, global_pos) -> None:
        self.adjustSize()
        x = global_pos.x() + 12
        y = global_pos.y() + 12

        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            if x + self.width() > geo.right():
                x = global_pos.x() - self.width() - 4
            if y + self.height() > geo.bottom():
                y = global_pos.y() - self.height() - 4

        self.move(x, y)
        self.show()
