"""
main_window.py
==============
The primary entry point for the Scheduler Program GUI.

The Design-Patterns implemented here are as follows:
    -Command
    -Singleton
    -Proxy

:date: 04/25/2026
:authors: Kyle Smith, Tyler Strohl, Chayse Altland, Shane del Villar, & Mohamed Mussa
:class: CMSC 420
"""
# Note: Module docstrings feed Sphinx autodoc; add new public modules in docs/source/api.rst.

import json
import os
import re
import copy
from collections.abc import Callable
from functools import partial
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
    QMessageBox, QDialog, QPlainTextEdit, QLabel,
    QLineEdit, QTableWidget, QHeaderView, 
    QTableWidgetItem, QToolBar, QToolButton,
    )
from PyQt6.QtCore import Qt, QCoreApplication, QSize
from PyQt6.QtGui import QAction, QFont, QColor, QBrush, QKeySequence
from PyQt6.QtWidgets import QInputDialog

from .menu_widgets import ContentPanel
from .proxy_manager import ProxyManager
from .course_detail_popup import CourseDetailPopup
from .toast import show_toast
from themes.themes import THEME_PRESETS, apply_main_window_theme
from config.config_mgr import ConfigManager

#=================================================================================
class MainWindow(QMainWindow):
    """
    Main Window for the Scheduler Application.
    
    This class serves as the 'Invoker' in the Command Pattern and 
    the 'Context' for various UI strategies.
    
    :ivar theme_colors: Dictionary of available UI color themes.
    :vartype theme_colors: dict
    """
    def __init__(self):
        """
        Initializes the MainWindow, managers, and UI components.
        """
        super().__init__()
        self.setWindowTitle("Schedule Builder · GenericTeamName")
        self.resize(1280, 720)
        self.setMinimumSize(960, 520)

        #Theme Configuration (window chrome; panels use slightly elevated surfaces)
        self.theme_colors = THEME_PRESETS
        #Default theme on startup
        self.current_theme = "Light"
        self.theme_color = self.theme_colors[self.current_theme]

        #Domain Logic Managers
        #--------------------------------------------------------------
        self.proxy = ProxyManager(self)
        
        self.config_mgr = self.proxy.config_mgr
        self.config_mgr.load(self)
        self.viewer_mgr = self.proxy.viewer_mgr

        self.faculty_manager = self.proxy.faculty_manager
        self.course_manager = self.proxy.course_manager
        self.room_manager = self.proxy.room_manager
        self.lab_manager = self.proxy.lab_manager
        self.gen_manager = self.proxy.gen_manager
        self.time_slot_editor = self.proxy.time_slot_editor
        self.meeting_pattern_editor = self.proxy.meeting_pattern_editor
        
        self.ai_viewer_mgr = self.proxy.ai_viewer_mgr
        #--------------------------------------------------------------

        #State Management
        self.schedules = []
        self.current_schedule_index = 0
        self.imported_schedule = None

        #UI Setup (see functions below)
        self._setup_ui_components()
        self._setup_quick_toolbar()
        self.init_menus()
        self.apply_theme()
        self.viewer_mgr._sync_detail_view(self)

        #Undo and redo
        self.undo_stack = []
        self.redo_stack = []
    #=================================================================================
    """
    UI Setup Functions:
    """
    #=================================================================================

    def _setup_ui_components(self):
        """
        Initializes the structural layout components of the window.
        Three columns: configuration JSON | schedule grid | AI assistant.
        """
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setChildrenCollapsible(False)

        # --- Left: inspector (JSON) ---
        self.inspect_panel = ContentPanel("Configuration", "#f1f5f9", add_bottom_stretch=False)
        self.detail_view = QPlainTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setPlaceholderText("Loaded config JSON appears here…")

        self.inspect_caption = QLabel("Active configuration (read-only)")
        self.inspect_caption.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))

        self.save_cfg_btn = QPushButton("Save configuration")
        self.save_cfg_btn.setObjectName("primaryButton")
        self.save_cfg_btn.setToolTip("Write changes to the active JSON file (Ctrl+S)")
        self.save_cfg_btn.clicked.connect(lambda: self.config_mgr.save(self))

        inspect_inner = QWidget()
        inspect_layout = QVBoxLayout(inspect_inner)
        inspect_layout.setContentsMargins(0, 0, 0, 0)
        inspect_layout.setSpacing(6)
        inspect_layout.addWidget(self.inspect_caption, 0)
        inspect_layout.addWidget(self.detail_view, 1)
        inspect_layout.addWidget(self.save_cfg_btn, 0)
        self.inspect_panel.layout.addWidget(inspect_inner, 1)

        # --- Center: schedule ---
        self.cfg_panel = ContentPanel("Schedule", "#f1f5f9", add_bottom_stretch=False)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(8)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 4, 4, 8)
        header_layout.setSpacing(6)

        self.counter_label = QLabel(
            "No schedules yet — use Generate on the toolbar, or Import (Ctrl+Shift+I)"
        )
        self.counter_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label.setWordWrap(True)

        self.path_label = QLabel()
        self.path_label.setFont(QFont("Segoe UI", 9))
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setWordWrap(True)
        self.viewer_mgr._update_path_label_text(self)

        header_layout.addWidget(self.counter_label)
        header_layout.addWidget(self.path_label)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setSpacing(8)
        self.prev_dashboard_btn = QPushButton("← Previous")
        self.next_dashboard_btn = QPushButton("Next →")
        self.prev_dashboard_btn.setToolTip("Show the previous generated schedule")
        self.next_dashboard_btn.setToolTip("Show the next generated schedule")
        self.prev_dashboard_btn.clicked.connect(
            lambda: (self.viewer_mgr.show_prev_schedule(self), self.viewer_mgr.update_schedule_display(self))
        )
        self.next_dashboard_btn.clicked.connect(
            lambda: (self.viewer_mgr.show_next_schedule(self), self.viewer_mgr.update_schedule_display(self))
        )
        nav_layout.addWidget(self.prev_dashboard_btn)
        nav_layout.addWidget(self.next_dashboard_btn)

        self.calendar_view = QTableWidget()
        self.calendar_view.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.calendar_view.setAlternatingRowColors(True)
        self.calendar_view.setShowGrid(True)
        self.calendar_view.verticalHeader().setDefaultSectionSize(28)
        self.calendar_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.calendar_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.calendar_view.cellClicked.connect(self._on_schedule_cell_clicked)

        inner_layout.addWidget(header_widget, 0)
        inner_layout.addWidget(nav_widget, 0)
        inner_layout.addWidget(self.calendar_view, 1)
        self.cfg_panel.layout.addWidget(inner, 1)

        # --- Right: assistant (full height) ---
        self.assistant_panel = ContentPanel("Assistant", "#f1f5f9", add_bottom_stretch=False)
        self.ai_caption = QLabel("Ask the assistant to edit your config or run tasks")
        self.ai_caption.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        self.ai_caption.setWordWrap(True)

        self.ai_chat_log = QPlainTextEdit()
        self.ai_chat_log.setReadOnly(True)
        self.ai_chat_log.setPlaceholderText(
            "Example: “Add room Roddy 210”, “List faculty”, “Set schedule limit to 5”…"
        )
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Message… (Enter to send)")
        self.ai_input.returnPressed.connect(self.send_assistant_message)
        self.ai_send_btn = QPushButton("Send")
        self.ai_send_btn.setObjectName("primaryButton")
        self.ai_send_btn.setToolTip("Send message (Ctrl+Enter)")
        self.ai_send_btn.clicked.connect(self.send_assistant_message)
        ai_row = QHBoxLayout()
        ai_row.setSpacing(8)
        ai_row.addWidget(self.ai_input, 1)
        ai_row.addWidget(self.ai_send_btn)

        assistant_inner = QWidget()
        assistant_layout = QVBoxLayout(assistant_inner)
        assistant_layout.setContentsMargins(0, 0, 0, 0)
        assistant_layout.setSpacing(6)
        assistant_layout.addWidget(self.ai_caption, 0)
        assistant_layout.addWidget(self.ai_chat_log, 1)
        assistant_layout.addLayout(ai_row)
        self.assistant_panel.layout.addWidget(assistant_inner, 1)

        self.main_splitter.addWidget(self.inspect_panel)
        self.main_splitter.addWidget(self.cfg_panel)
        self.main_splitter.addWidget(self.assistant_panel)
        self.main_splitter.setSizes([160, 760, 360])

        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(12, 10, 12, 10)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self.main_splitter)
        self.setCentralWidget(shell)

    def _setup_quick_toolbar(self) -> None:
        """
        One-click access to common actions + shortcuts (fewer menu dives).
        Also created due to menubar differences for Mac OS users.
        """
        tb = QToolBar("Actions")
        tb.setObjectName("quickToolBar")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        theme_menu = QMenu(self)
        theme_menu.setToolTipsVisible(True)
        for theme_name in self.theme_colors:
            theme_menu.addAction(theme_name).triggered.connect(partial(self.set_theme, theme_name))

        self.theme_btn = QToolButton(self)
        self.theme_btn.setObjectName("themeToolButton")
        self.theme_btn.setText(f"{self.current_theme} ▾")
        self.theme_btn.setToolTip("Color theme (macOS-safe; also under Help → Theme)")
        self.theme_btn.setMenu(theme_menu)
        self.theme_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tb.addWidget(self.theme_btn)
        tb.addSeparator()

        def add_action(
            text: str, slot, tip: str,
            shortcut: QKeySequence | None = None,
        ) -> QAction:
            act = QAction(text, self)
            act.setToolTip(tip)
            if shortcut is not None:
                act.setShortcut(shortcut)
            act.triggered.connect(slot)
            tb.addAction(act)
            self.addAction(act)
            return act

        add_action(
            "Open…",
            lambda: self.run_with_undo(lambda: self.viewer_mgr.handle_change_path(self)),
            "Choose a different JSON configuration file (Ctrl+O)",
            QKeySequence.StandardKey.Open,
        )
        add_action(
            "Save", lambda: self.config_mgr.save(self),
            "Save configuration to disk (Ctrl+S)", QKeySequence.StandardKey.Save,
        )
        tb.addSeparator()
        add_action(
            "Generate", lambda: self.gen_manager.run_scheduler(self),
            "Run schedule generation (Ctrl+G)", QKeySequence("Ctrl+G"),
        )
        add_action(
            "Refresh grid", lambda: self.viewer_mgr.update_schedule_display(self, "all"),
            "Redraw the schedule table (F5)", QKeySequence("F5"),
        )
        tb.addSeparator()
        add_action(
            "Import", lambda: self.viewer_mgr.handle_import_schedule(self),
            "Import schedule JSON (Ctrl+Shift+I)", QKeySequence("Ctrl+Shift+I"),
        )
        add_action(
            "Export", lambda: self.viewer_mgr.handle_export_schedule(self),
            "Export schedules (Ctrl+Shift+E)", QKeySequence("Ctrl+Shift+E"),
        )
        tb.addSeparator()
        add_action(
            "Summary", lambda: self.viewer_mgr.handle_view_summary(self),
            "View configuration summary (F2)", QKeySequence("F2"),
        )
        add_action("Undo", self.undo, "Undo last config change (Ctrl+Z)", QKeySequence("Ctrl+Z"),
        )
        add_action("Redo", self.redo, "Redo last undone config change (Ctrl+Y)", QKeySequence("Ctrl+Y"),
        )

        send_act = QAction("Send assistant message", self)
        send_act.setShortcut(QKeySequence("Ctrl+Return"))
        send_act.triggered.connect(self.send_assistant_message)
        self.addAction(send_act)
        tb.addSeparator()

        def _menu_btn(text: str, tip: str, entries: list[tuple[str, Callable[[], None]]]) -> QToolButton:
            m = QMenu(self)
            m.setToolTipsVisible(True)
            for label, fn in entries:
                m.addAction(label).triggered.connect(fn)
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setMenu(m)
            b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            return b

        add_entries = [
            ("Faculty…", lambda: self.run_with_undo(lambda: self.faculty_manager.add_faculty_via_dialog(self))),
            ("Course…", lambda: self.run_with_undo(lambda: self.course_manager.add_course_via_dialog(self))),
            ("Room…", lambda: self.run_with_undo(lambda: self.room_manager.add_room_via_dialog(self))),
            ("Lab…", lambda: self.run_with_undo(lambda: self.lab_manager.add_lab_via_dialog(self))),
        ]

        modify_entries = [
            ("Faculty…", lambda: self.run_with_undo(lambda: self.faculty_manager.modify_faculty_via_dialog(self))),
            ("Course…", lambda: self.run_with_undo(lambda: self.course_manager.modify_course_via_dialog(self))),
            ("Room…", lambda: self.run_with_undo(lambda: self.room_manager.modify_room_via_dialog(self))),
            ("Lab…", lambda: self.run_with_undo(lambda: self.lab_manager.modify_lab_via_dialog(self))),
        ]

        delete_entries = [
            ("Faculty…", lambda: self.run_with_undo(lambda: self.faculty_manager.delete_faculty_via_dialog(self))),
            ("Course…", lambda: self.run_with_undo(lambda: self.course_manager.delete_course_via_dialog(self))),
            ("Room…", lambda: self.run_with_undo(lambda: self.room_manager.delete_room_via_dialog(self))),
            ("Lab…", lambda: self.run_with_undo(lambda: self.lab_manager.delete_lab_via_dialog(self))),
        ]
        
        tb.addWidget(_menu_btn("Add ▾", "Add faculty, course, room, or lab", add_entries))
        tb.addWidget(_menu_btn("Modify ▾", "Change an existing entry", modify_entries))
        tb.addWidget(_menu_btn("Delete ▾", "Remove an entry from the config", delete_entries))

    def init_menus(self):
        """
        Constructs the Menu Bar and binds actions using the Command Pattern approach.
        
        .. note:: Actions are bound via lambda triggers to respective manager methods.
        """
        menubar = self.menuBar()

        # Menubar tab definitions:
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")

        # Tabs under edit:
        faculty_menu = edit_menu.addMenu("Faculty")
        courses_menu = edit_menu.addMenu("Courses")
        rooms_menu = edit_menu.addMenu("Rooms")
        labs_menu = edit_menu.addMenu("Labs")

        # Timeslot config editor option, underneath Edit->Courses
        timeslot_menu = courses_menu.addMenu("Timeslots")
        # Timeslot sub-options:
        meet_pat_menu = timeslot_menu.addMenu("Class Meeting Patterns")
        ed_timeslot_menu = timeslot_menu.addMenu("Edit Timeslots")

        # Remaining two menubar tabs:
        gen_menu = menubar.addMenu("Generator")
        viewer_menu = menubar.addMenu("Viewer")
        help_menu = menubar.addMenu("Help")
        theme_help = help_menu.addMenu("Theme")
        for theme_name in self.theme_colors:
            theme_help.addAction(theme_name).triggered.connect(partial(self.set_theme, theme_name))
        help_menu.addSeparator()
        help_menu.addAction("Keyboard shortcuts…", lambda: self.viewer_mgr._show_shortcuts_cheat_sheet(self))

        # Command Bindings
        self._bind_file_commands(file_menu)
        self._bind_faculty_commands(faculty_menu)
        self._bind_course_commands(courses_menu)
        
        # New Bindings for the nested Timeslot menus
        self._bind_meeting_pattern_commands(meet_pat_menu)
        self._bind_timeslot_commands(ed_timeslot_menu)
        
        self._bind_room_commands(rooms_menu)
        self._bind_lab_commands(labs_menu)
        self._bind_generator_commands(gen_menu)
        self._bind_viewer_commands(viewer_menu)

        edit_menu.addSeparator()
        edit_menu.addAction("Undo").triggered.connect(self.undo)
        edit_menu.addAction("Redo").triggered.connect(self.redo)

    def _bind_file_commands(self, menu):
        """Binds file-related operations."""
        menu.addAction("Change Config File").triggered.connect(
            lambda: self.run_with_undo(lambda: self.viewer_mgr.handle_change_path(self))
        )
        menu.addAction("View Summary").triggered.connect(lambda: self.viewer_mgr.handle_view_summary(self))
        menu.addAction("Save Config").triggered.connect(lambda: self.config_mgr.save(self))
        menu.addAction("Save Config As").triggered.connect(
            lambda: self.run_with_undo(lambda: self.viewer_mgr.save_as(self))
        )
    
    def _bind_faculty_commands(self, menu):
        """Binds faculty management operations."""
        menu.addAction("Add Faculty").triggered.connect(lambda: self.run_with_undo(lambda: self.faculty_manager.add_faculty_via_dialog(self)))
        menu.addAction("Modify Faculty").triggered.connect(lambda: self.run_with_undo(lambda: self.faculty_manager.modify_faculty_via_dialog(self)))
        menu.addAction("Delete Faculty").triggered.connect(lambda: self.run_with_undo(lambda: self.faculty_manager.delete_faculty_via_dialog(self)))

    def _bind_meeting_pattern_commands(self, menu):
        """Binds class meeting pattern operations."""
        menu.addAction("Add Meeting Pattern").triggered.connect(lambda: self.run_with_undo(lambda: self.meeting_pattern_editor.add_meeting_pattern(self)))
        menu.addAction("Modify Meeting Pattern").triggered.connect(lambda: self.run_with_undo(lambda: self.meeting_pattern_editor.modify_meeting_pattern(self)))
        menu.addAction("Delete Meeting Pattern").triggered.connect(lambda: self.run_with_undo(lambda: self.meeting_pattern_editor.delete_meeting_pattern(self)))

    def _bind_timeslot_commands(self, menu):
        """Binds dummy timeslot operations."""
        menu.addAction("Add Timeslot").triggered.connect(lambda: self.run_with_undo(lambda: self.time_slot_editor.add_time_slot(self)))
        menu.addAction("Modify Timeslot").triggered.connect(lambda: self.run_with_undo(lambda: self.time_slot_editor.modify_time_slot(self)))
        menu.addAction("Delete Timeslot").triggered.connect(lambda: self.run_with_undo(lambda: self.time_slot_editor.delete_time_slot(self)))

    def _bind_course_commands(self, menu):
        """Binds course management operations."""
        menu.addAction("Add Courses").triggered.connect(lambda: self.run_with_undo(lambda: self.course_manager.add_course_via_dialog(self)))
        menu.addAction("Modify Courses").triggered.connect(lambda: self.run_with_undo(lambda: self.course_manager.modify_course_via_dialog(self)))
        menu.addAction("Delete Courses").triggered.connect(lambda: self.run_with_undo(lambda: self.course_manager.delete_course_via_dialog(self)))

    def _bind_room_commands(self, menu):
        """Binds room management operations."""
        menu.addAction("Add Rooms").triggered.connect(lambda: self.run_with_undo(lambda: self.room_manager.add_room_via_dialog(self)))
        menu.addAction("Modify Rooms").triggered.connect(lambda: self.run_with_undo(lambda: self.room_manager.modify_room_via_dialog(self)))
        menu.addAction("Delete Rooms").triggered.connect(lambda: self.run_with_undo(lambda: self.room_manager.delete_room_via_dialog(self)))

    def _bind_lab_commands(self, menu):
        """Binds lab management operations."""
        menu.addAction("Add Labs").triggered.connect(lambda: self.run_with_undo(lambda: self.lab_manager.add_lab_via_dialog(self)))
        menu.addAction("Modify Labs").triggered.connect(lambda: self.run_with_undo(lambda: self.lab_manager.modify_lab_via_dialog(self)))
        menu.addAction("Delete Labs").triggered.connect(lambda: self.run_with_undo(lambda: self.lab_manager.delete_lab_via_dialog(self)))

    def _bind_generator_commands(self, menu):
        """Binds schedule generation operations."""
        menu.addAction("Limit # Of Schedules").triggered.connect(
            lambda: self.run_with_undo(lambda: self.gen_manager.set_limit(self))
        )
        menu.addAction("Toggle Optimization").triggered.connect(
            lambda: self.run_with_undo(lambda: self.gen_manager.set_optimize(self))
        )
        menu.addAction("Generate Schedules").triggered.connect(lambda: self.gen_manager.run_scheduler(self))

    def _bind_viewer_commands(self, menu):
        """Binds schedule viewing and I/O operations."""
        menu.addAction("View Schedules").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "all"))
        menu.addAction("View by Faculty").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "faculty"))
        menu.addAction("View by Room").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "room"))
        menu.addAction("View by Lab").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "lab"))
        menu.addAction("Export Schedules").triggered.connect(lambda: self.viewer_mgr.handle_export_schedule(self))
        menu.addAction("Import Schedules").triggered.connect(lambda: self.viewer_mgr.handle_import_schedule(self))
        menu.addAction("Clear Schedules").triggered.connect(lambda: self.viewer_mgr.handle_clear_schedule(self))

    #=================================================================================
    """
    Theme: palette and QSS are applied in ``themes.themes.apply_main_window_theme``.
    """
    #=================================================================================

    def apply_theme(self) -> None:
        apply_main_window_theme(self)

    def set_theme(self, theme_name: str) -> None:
        if theme_name not in self.theme_colors:
            return
        self.current_theme = theme_name
        self.theme_color = self.theme_colors[theme_name]
        self.apply_theme()
        
    #=================================================================================
    """
    Handler Functions:
    """
    #=================================================================================    
    # Course-detail helpers stay on MainWindow because they need ``calendar_view`` and config.
    #-------------------------------------------
    def _on_schedule_cell_clicked(self, row: int, col: int) -> None:
        """
        Slot: when the user clicks a cell in the schedule grid, find the
        matching course and show the CourseDetailPopup near the cursor.
        """
        anchor_row, anchor_col, cell_text = self._calendar_anchor_cell(row, col)
        if not cell_text.strip():
            return

        payloads = self._all_course_popup_payloads(anchor_row, anchor_col, cell_text)
        if not payloads:
            return

        from PyQt6.QtGui import QCursor
        popup = CourseDetailPopup(payloads, self)
        popup.show_near(QCursor.pos())

    def _calendar_anchor_cell(self, row: int, col: int) -> tuple[int, int, str]:
        """
        Row spans store ``QTableWidgetItem`` text only on the top-left row.
        """
        it = self.calendar_view.item(row, col)
        if it is not None and str(it.text()).strip():
            return row, col, str(it.text())
        for rr in range(row, -1, -1):
            it2 = self.calendar_view.item(rr, col)
            if it2 is not None and str(it2.text()).strip():
                return rr, col, str(it2.text())
        return row, col, ""

    @staticmethod
    def _guess_course_ids_from_cell_text(cell_text: str) -> list[str]:
        """Lines resembling ``SUBJECT NUMBER`` where *NUMBER* starts with a digit."""
        found: list[str] = []
        seen: set[str] = set()
        for raw in cell_text.splitlines():
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            if parts[0].lower().startswith(("dr.", "prof", "prof.")):
                continue
            if not re.match(r"^\d", parts[1]):
                continue
            cand = f"{parts[0]} {parts[1]}".strip()
            if cand and cand not in seen:
                seen.add(cand)
                found.append(cand)
        return found

    def _meetings_at_grid_day_time(self, day: str, time_label: str) -> list[dict]:
        if not self.schedules or not (0 <= self.current_schedule_index < len(self.schedules)):
            return []
        sched = self.schedules[self.current_schedule_index]
        if not isinstance(sched, list):
            return []

        tgt_min = ConfigManager._parse_time_minutes(time_label)
        day_s = day.strip()
        time_s = str(time_label).strip()
        out: list[dict] = []
        for e in sched:
            if not isinstance(e, dict):
                continue
            if str(e.get("day", "")).strip() != day_s:
                continue
            em = ConfigManager._parse_time_minutes(e.get("time"))
            if tgt_min is not None and em is not None and em == tgt_min:
                out.append(e)
            elif time_s and str(e.get("time", "")).strip() == time_s:
                out.append(e)
        return out

    def _ordered_unique_course_ids(self, meetings: list[dict]) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for e in meetings:
            cid = str(e.get("course_id", "")).strip()
            if cid and cid not in seen:
                seen.add(cid)
                ids.append(cid)
        return ids

    def _all_course_popup_payloads(
        self,
        anchor_row: int,
        anchor_col: int,
        cell_text: str,
    ) -> list[dict]:
        payloads: list[dict] = []
        hci = self.calendar_view.horizontalHeaderItem(anchor_col)
        vhi = self.calendar_view.verticalHeaderItem(anchor_row)

        if hci is not None and vhi is not None:
            meetings = self._meetings_at_grid_day_time(hci.text().strip(), vhi.text().strip())
            for cid in self._ordered_unique_course_ids(meetings):
                p = self._popup_payload_for_course_id(cid)
                if p:
                    payloads.append(p)

        if payloads:
            return payloads

        guessed: set[str] = set()
        for cid in self._guess_course_ids_from_cell_text(cell_text):
            if cid in guessed:
                continue
            guessed.add(cid)
            p = self._popup_payload_for_course_id(cid)
            if p:
                payloads.append(p)
        return payloads

    def _popup_payload_for_course_id(self, target_id: str) -> dict | None:
        """
        Combine every meeting slice for ``target_id`` with config fallback fields.
        """
        if not self.schedules or not (0 <= self.current_schedule_index < len(self.schedules)):
            return None

        schedule = self.schedules[self.current_schedule_index]
        if not isinstance(schedule, list):
            return None

        tid = target_id.strip()
        if not tid:
            return None

        meetings = [
            e for e in schedule
            if isinstance(e, dict) and str(e.get("course_id", "")).strip() == tid
        ]
        if not meetings:
            return None

        days = [m.get("day", "") for m in meetings if m.get("day")]
        times = sorted({m.get("time", "") for m in meetings if m.get("time")})

        base_id = tid.split(".")[0].strip()
        config_courses = (
            self.config_mgr.data.get("config", {}).get("courses", [])
            if hasattr(self, "config_mgr") else []
        )
        cfg_full = next(
            (
                c for c in config_courses
                if isinstance(c, dict) and str(c.get("course_id", "")).strip() == tid
            ),
            None,
        )
        base_course = cfg_full or next(
            (
                c for c in config_courses
                if isinstance(c, dict) and str(c.get("course_id", "")).strip() == base_id
            ),
            {},
        )

        def _collect_from_meetings(key: str) -> list:
            out, seen = [], set()
            for m in meetings:
                if not isinstance(m, dict):
                    continue
                val = m.get(key)
                chunk: list[str] = []
                if isinstance(val, list):
                    for v in val:
                        if isinstance(v, dict):
                            nm = str(v.get("name") or v.get("id") or "").strip()
                            if nm:
                                chunk.append(nm)
                        elif v is not None and str(v).strip():
                            chunk.append(str(v).strip())
                elif val is not None and str(val).strip():
                    chunk.append(str(val).strip())
                for s in chunk:
                    if s not in seen:
                        seen.add(s)
                        out.append(s)
            return out

        mf = _collect_from_meetings("faculty")
        mr = _collect_from_meetings("room")
        ml = _collect_from_meetings("lab")

        def _cfg_list(key: str) -> list:
            v = base_course.get(key, []) if isinstance(base_course, dict) else []
            if isinstance(v, list):
                return v
            return [v] if v not in (None, "") else []

        section = ""
        course_id_display = tid
        if "." in tid:
            course_id_display, section = tid.split(".", 1)
            course_id_display = course_id_display.strip()
            section = section.strip()

        return {
            "course_id": course_id_display or tid,
            "section": section,
            "faculty": mf or _cfg_list("faculty"),
            "room": mr or _cfg_list("room"),
            "lab": ml or _cfg_list("lab"),
            "credits": base_course.get("credits") if isinstance(base_course, dict) else None,
            "days": days,
            "time_slot": ", ".join(times) if times else "",
        }
    #-------------------------------------------

    def send_assistant_message(self) -> None:
        self.ai_viewer_mgr.send_assistant_message()

    #Undo redo methods

    def run_with_undo(self, action):
        before = copy.deepcopy(self.config_mgr.data)
        action()
        after = self.config_mgr.data

        if after != before:
            self.undo_stack.append(before)
            self.redo_stack.clear()
            self.viewer_mgr._sync_detail_view(self)
            self.viewer_mgr._update_path_label_text(self)

    def _show_toast(self, message: str) -> None:
        host = self.centralWidget()
        if host is not None:
            show_toast(host, message)

    def undo(self):
        if not self.undo_stack:
            self._show_toast("Nothing to undo.")
            return

        current = copy.deepcopy(self.config_mgr.data)
        self.redo_stack.append(current)
        self.config_mgr.data = self.undo_stack.pop()
        self.config_mgr.save(self, silent=True)
        self.viewer_mgr._sync_detail_view(self)
        self.viewer_mgr._update_path_label_text(self)
        self._show_toast("Undid the last configuration change.")

    def redo(self):
        if not self.redo_stack:
            self._show_toast("Nothing to redo.")
            return

        current = copy.deepcopy(self.config_mgr.data)
        self.undo_stack.append(current)
        self.config_mgr.data = self.redo_stack.pop()
        self.config_mgr.save(self, silent=True)
        self.viewer_mgr._sync_detail_view(self)
        self.viewer_mgr._update_path_label_text(self)
        self._show_toast("Redid the last configuration change.")
