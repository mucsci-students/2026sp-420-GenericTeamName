"""
main_window.py
==============
The primary entry point for the Scheduler Program GUI.

The Design-Patterns implemented here are as follows:
    -Command
    -Singleton
    -Proxy

:date: 04/17/2026
:authors: Kyle Smith, Tyler Strohl, Chayse Altland, & Shane del Villar
:class: CMSC 420
"""
#Note: The """ comment blocks are important for the documentation (see docs folder).
#TODO: Reformat comments so auto-documentation picks up more files across program.

import json
import os
import copy
from collections.abc import Callable
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
    QMessageBox, QDialog, QPlainTextEdit, QLabel,
    QMenuBar, QLineEdit, QTableWidget, QHeaderView, 
    QTableWidgetItem, QToolBar, QToolButton,
    )
from PyQt6.QtCore import Qt, QCoreApplication, QSize
from PyQt6.QtGui import QAction, QFont, QColor, QBrush, QKeySequence
from PyQt6.QtWidgets import QInputDialog

from .menu_widgets import ContentPanel
from .proxy_manager import ProxyManager
from themes.themes import THEME_PRESETS, apply_main_window_theme

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
        self._update_path_label_text()

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
            "Example: “Add room Roddy 201”, “List faculty”, “Set schedule limit to 5”…"
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
        """One-click access to common actions + shortcuts (fewer menu dives)."""
        tb = QToolBar("Actions")
        tb.setObjectName("quickToolBar")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        def add_action(
            text: str,
            slot,
            tip: str,
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
            self.handle_change_path,
            "Choose a different JSON configuration file (Ctrl+O)",
            QKeySequence.StandardKey.Open,
        )
        add_action(
            "Save",
            lambda: self.config_mgr.save(self),
            "Save configuration to disk (Ctrl+S)",
            QKeySequence.StandardKey.Save,
        )
        tb.addSeparator()
        add_action(
            "Generate",
            lambda: self.gen_manager.run_scheduler(self),
            "Run schedule generation (Ctrl+G)",
            QKeySequence("Ctrl+G"),
        )
        add_action(
            "Refresh grid",
            lambda: self.viewer_mgr.update_schedule_display(self, "all"),
            "Redraw the schedule table (F5)",
            QKeySequence("F5"),
        )
        tb.addSeparator()
        add_action(
            "Import",
            self.handle_import_schedule,
            "Import schedule JSON (Ctrl+Shift+I)",
            QKeySequence("Ctrl+Shift+I"),
        )
        add_action(
            "Export",
            self.handle_export_schedule,
            "Export schedules (Ctrl+Shift+E)",
            QKeySequence("Ctrl+Shift+E"),
        )
        tb.addSeparator()
        add_action(
            "Summary",
            lambda: self.viewer_mgr.handle_view_summary(self),
            "View configuration summary (F2)",
            QKeySequence("F2"),
        )
        add_action(
            "Undo",
            self.undo,
            "Undo last config change (Ctrl+Z)",
            QKeySequence("Ctrl+Z"),
        )
        add_action(
            "Redo",
            self.redo,
            "Redo last undone config change (Ctrl+Y)",
            QKeySequence("Ctrl+Y"),
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
        self._setup_theme_menu(menubar)

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
        help_menu.addAction("Keyboard shortcuts…", self._show_shortcuts_cheat_sheet)

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

    def _setup_theme_menu(self, menubar):
        """
        Configures the theme selection button in the corner of the menubar.
        
        :param menubar: The QMenuBar instance to attach the widget to.
        """
        self.theme_btn = QPushButton(self.current_theme)
        self.theme_btn.setMaximumWidth(180)
        theme_menu = QMenu(self)
        for name in self.theme_colors:
            theme_menu.addAction(name).triggered.connect(
                lambda chk, n=name: self.set_theme(n)
            )
        self.theme_btn.setMenu(theme_menu)
        menubar.setCornerWidget(self.theme_btn, Qt.Corner.TopLeftCorner)

    def _bind_file_commands(self, menu):
        """Binds file-related operations."""
        menu.addAction("Change Config File").triggered.connect(self.handle_change_path)
        menu.addAction("View Summary").triggered.connect(lambda: self.viewer_mgr.handle_view_summary(self))
        menu.addAction("Save configuration").triggered.connect(lambda: self.config_mgr.save(self))
        menu.addAction("Save configuration as…").triggered.connect(self.save_config_to_file)
    
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
        menu.addAction("Limit # Of Schedules").triggered.connect(lambda: self.gen_manager.set_limit(self))
        menu.addAction("Toggle Optimization").triggered.connect(lambda: self.gen_manager.set_optimize(self))
        menu.addAction("Generate Schedules").triggered.connect(lambda: self.gen_manager.run_scheduler(self))

    def _bind_viewer_commands(self, menu):
        """Binds schedule viewing and I/O operations."""
        menu.addAction("View Schedules").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "all"))
        menu.addAction("View by Faculty").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "faculty"))
        menu.addAction("View by Room").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "room"))
        menu.addAction("View by Lab").triggered.connect(lambda: self.viewer_mgr.update_schedule_display(self, "lab"))
        menu.addAction("Export Schedules").triggered.connect(self.handle_export_schedule)
        menu.addAction("Import Schedules").triggered.connect(self.handle_import_schedule)
        menu.addAction("Clear Schedules").triggered.connect(lambda: self.viewer_mgr.handle_clear_schedule(self))

    #=================================================================================
    """
    Theme: palette and QSS are applied in ``themes.themes.apply_main_window_theme``.
    """
    #=================================================================================

    def apply_theme(self) -> None:
        apply_main_window_theme(self)

    def _update_path_label_text(self) -> None:
        if not hasattr(self, "path_label"):
            return
        fp = (getattr(self.config_mgr, "filepath", None) or "").strip()
        if fp:
            self.path_label.setText(f"Config: {os.path.basename(fp)}")
            self.path_label.setToolTip(fp)
        else:
            self.path_label.setText("Config: (unsaved or unknown path)")
            self.path_label.setToolTip("")

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

    #TODO: Move this function to Viewer class.   
    def _show_shortcuts_cheat_sheet(self) -> None:
        mb = QMessageBox(self)
        mb.setWindowTitle("Keyboard shortcuts")
        mb.setIcon(QMessageBox.Icon.Information)
        mb.setTextFormat(Qt.TextFormat.RichText)
        mb.setText(
            "<p style='margin-bottom:10px'><b>Toolbar / main window</b></p>"
            "<table cellspacing='6'>"
            "<tr><td>Open configuration…</td><td><b>Ctrl+O</b></td></tr>"
            "<tr><td>Save configuration</td><td><b>Ctrl+S</b></td></tr>"
            "<tr><td>Generate schedules</td><td><b>Ctrl+G</b></td></tr>"
            "<tr><td>Refresh schedule grid</td><td><b>F5</b></td></tr>"
            "<tr><td>Import schedules</td><td><b>Ctrl+Shift+I</b></td></tr>"
            "<tr><td>Export schedules</td><td><b>Ctrl+Shift+E</b></td></tr>"
            "<tr><td>Configuration summary</td><td><b>F2</b></td></tr>"
            "<tr><td>Send assistant message</td><td><b>Ctrl+Enter</b> "
            "(or Enter in the message field)</td></tr>"
            "</table>"
        )
        mb.exec()

    #TODO: Move this function over to config_mgr
    def handle_change_path(self):
        """Opens dialog to update the configuration file path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Configuration File", "config/", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_mgr.filepath = file_path
            try:
                self.config_mgr.load(self)
                self._update_path_label_text()
                self.viewer_mgr._sync_detail_view(self)
                QMessageBox.information(self, "Success", "Configuration File changed.")
                
            except Exception as e:
                QMessageBox.warning(self, "Load Warning", str(e))



    #TODO: Move the following functions to a new class:
    #DO THIS BEFORE MOVING MORE FUNCTIONS TO CONFIG_MGR
    #---------------------------------------------------------
    #THESE FUNCTIONS NEED TO BE MOVED TO A NEW VIEWER CLASS
    #---------------------------------------------------------
    def handle_import_schedule(self):
        """
        Delegates JSON parsing to ConfigManager and updates the UI with the result.
        """

        imported_data = self.config_mgr.import_schedule_from_json(parent=self)

        if imported_data:

            self.schedules = imported_data
            self.current_schedule_index = 0
            #Updates filepath displayed for imported schedules
            self.cfg_panel.update_title(self.cfg_panel, self.config_mgr.import_file)
            self.viewer_mgr.update_schedule_display(self)

            try:
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Successfully loaded {len(imported_data)} schedule(s)."
                )
            except:
                QMessageBox.critical(self, "Error", "Import failed.")

    def handle_export_schedule(self):
        """
        Delegates schedule export with selectable output mode.
        """
        if not (hasattr(self, "schedules") and self.schedules):
            QMessageBox.warning(
                self, 
                "Export Error", 
                "There are no schedules currently loaded to export. "
                "Please generate schedules first."
            )
            return

        options = [
            "Full schedules (JSON)",
            "Full schedules (PDF)",
            "By room/lab postings (PDF printable)",
            "By faculty postings (PDF printable)",
        ]
        choice, ok = QInputDialog.getItem(
            self,
            "Export Schedules",
            "Export format:",
            options,
            0,
            False,
        )
        if not ok:
            return

        if choice == options[0]:
            self.config_mgr.export_schedule_to_json(self.schedules, self)
        elif choice == options[1]:
            self.config_mgr.export_schedule_to_pdf(self.schedules, self)
        elif choice == options[2]:
            self.config_mgr.export_grouped_printable(self.schedules, self, "room_lab")
        else:
            self.config_mgr.export_grouped_printable(self.schedules, self, "faculty")

    #---------------------------------------------------------
    #End of functions that should be moved to viewer (see them above)
    #---------------------------------------------------------

    #TODO: Move this function to config_mgr
    def save_config_to_file(self):
        """'Save As' functionality for exporting the current config state."""
        p, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "*.json")
        if p:
            self.config_mgr.filepath = p
            self.config_mgr.save(self)
            self._update_path_label_text()
            self.viewer_mgr._sync_detail_view(self)

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
            self._update_path_label_text()

    def undo(self):
        if not self.undo_stack:
            QMessageBox.information(self, "Undo", "Nothing to undo.")
            return

        current = copy.deepcopy(self.config_mgr.data)
        self.redo_stack.append(current)
        self.config_mgr.data = self.undo_stack.pop()
        self.config_mgr.save(self)
        self.viewer_mgr._sync_detail_view(self)
        self._update_path_label_text()

    def redo(self):
        if not self.redo_stack:
            QMessageBox.information(self, "Redo", "Nothing to redo.")
            return

        current = copy.deepcopy(self.config_mgr.data)
        self.undo_stack.append(current)
        self.config_mgr.data = self.redo_stack.pop()
        self.config_mgr.save(self)
        self.viewer_mgr._sync_detail_view(self)
        self._update_path_label_text()