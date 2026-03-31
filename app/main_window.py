"""
main_window.py
==============
The primary entry point for the Scheduler Program GUI.

The Design-Patterns implemented here are as follows:
    -Command
    -Singleton

:date: 03/31/2026
:authors: Kyle Smith, Tyler Strohl, & Shane del Villar
:class: CMSC 420
"""
#Note: The """ comment blocks are important for the documentation (see docs folder).
#TODO: Reformat comments so auto-documentation picks up more files across program.

import json
import csv
import os
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
    QMessageBox, QDialog, QPlainTextEdit, QLabel,
    QMenuBar, QLineEdit,
    )
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont

from .menu_widgets import ContentPanel
from .ai_assistant import (
    AssistantChatWorker, OPENAI_MODEL, SYSTEM_PROMPT,
    default_api_key, execute_tool,
)
from .course_gui import CourseConfigManager
from .room_gui import RoomConfigManager
from .faculty_gui import FacultyManager
from config.config_mgr import ConfigManager
from .generator_gui import GenConfigManager
from .lab_gui import LabConfigManager
from .time_slot_editor import TimeSlotEditor

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
        self.setWindowTitle("Scheduler Program - GenericTeamName")
        self.resize(900, 600)

        #Theme Configuration
        self.theme_colors = {
            "Light": "#f3f4f6", "Dark": "#1f1f24", "Autumn": "#8a5a44",
            "Crimson": "#8b2e3c", "Marathon": "#c2fe0b", "Summer": "#f4c95d",
            "Spring": "#98c379", "Winter": "#cfddeb", "Ocean": "#1f6f8b",
            "Land": "#6b8f71", "Sky": "#7fb7e6",
        }
        #Default theme on startup
        self.current_theme = "Light"
        self.theme_color = self.theme_colors[self.current_theme]

        #Domain Logic Managers
        self.config_mgr = ConfigManager("config/config.json")
        self._load_config()

        self.faculty_manager = FacultyManager()
        self.course_manager = CourseConfigManager()
        self.room_manager = RoomConfigManager()
        self.gen_manager = GenConfigManager()
        self.lab_manager = LabConfigManager()
        self.time_slot_editor = TimeSlotEditor(self.config_mgr)

        #State Management
        self.schedules = []
        self.current_schedule_index = 0
        self.imported_schedule = None

        #AI Chatbot Setup
        self.assistant_messages: list = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._assistant_worker: AssistantChatWorker | None = None
          
        #UI Setup (see functions below)
        self._setup_ui_components()
        self.init_menus()
        self.apply_theme()
#=================================================================================
"""
UI Setup Functions:
"""
#=================================================================================
    
    def _setup_ui_components(self):
        """
        Initializes the structural layout components of the window.
        """
        #Splitter organizes our panels.
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.cfg_panel = ContentPanel(f"Active Config: <b>{self.config_mgr.filepath}</b>", "#000000")
        self.right_panel = ContentPanel("Inspector & Assistant", "#1a1a1a", stretch_middle=False)
        
        self.detail_view = QPlainTextEdit()    
        self.right_panel.layout.addWidget(self.detail_view)

        #Panels are displayed in widgets.
        self.splitter.addWidget(self.cfg_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([800, 200])
        self.setCentralWidget(self.splitter)
        
        #Remaining function code sets up the AI Chatbot panels:
        inspect_box = QWidget()
        inspect_layout = QVBoxLayout(inspect_box)
        inspect_layout.setContentsMargins(0, 0, 0, 0)
        inspect_layout.addWidget(self.detail_view, 1)
        inspect_layout.addWidget(self.save_cfg_btn)

        self.ai_chat_log = QPlainTextEdit()
        self.ai_chat_log.setReadOnly(True)
        self.ai_chat_log.setPlaceholderText("Ask the assistant to change rooms, faculty, courses, run generation, etc.")
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Message the assistant…")
        self.ai_input.returnPressed.connect(self.send_assistant_message)
        self.ai_send_btn = QPushButton("Send")
        self.ai_send_btn.clicked.connect(self.send_assistant_message)
        ai_row = QHBoxLayout()
        ai_row.addWidget(self.ai_input, 1)
        ai_row.addWidget(self.ai_send_btn)

        assistant_box = QWidget()
        assistant_layout = QVBoxLayout(assistant_box)
        assistant_layout.setContentsMargins(0, 0, 0, 0)
        assistant_layout.addWidget(QLabel("AI assistant"), 0)
        assistant_layout.addWidget(self.ai_chat_log, 1)
        assistant_layout.addLayout(ai_row)

        #Embed a vertical splitter into existing right panel
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.addWidget(inspect_box)
        self.right_splitter.addWidget(assistant_box)
        self.right_splitter.setStretchFactor(0, 2)
        self.right_splitter.setStretchFactor(1, 3)
        self.right_panel.layout.addWidget(self.right_splitter, 1)

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
        menu.addAction("View Summary").triggered.connect(self.handle_view_summary)
        menu.addAction("Save Config").triggered.connect(lambda: self.config_mgr.save(self))
        menu.addAction("Save Config As").triggered.connect(self.save_config_to_file)
    
    def _bind_faculty_commands(self, menu):
        """Binds faculty management operations."""
        menu.addAction("Add Faculty").triggered.connect(lambda: self.faculty_manager.add_faculty_via_dialog(self))
        menu.addAction("Modify Faculty").triggered.connect(lambda: self.faculty_manager.modify_faculty_via_dialog(self))
        menu.addAction("Delete Faculty").triggered.connect(lambda: self.faculty_manager.delete_faculty_via_dialog(self))

    def _bind_meeting_pattern_commands(self, menu):
        """Binds dummy meeting pattern operations."""
        menu.addAction("Add Meeting Pattern").triggered.connect(lambda: print("Add Meeting Patterns clicked."))
        menu.addAction("Modify Meeting Pattern").triggered.connect(lambda: print("Modify Meeting Patterns clicked."))
        menu.addAction("Delete Meeting Pattern").triggered.connect(lambda: print("Delete Meeting Patterns clicked."))

    def _bind_timeslot_commands(self, menu):
        """Binds dummy timeslot operations."""
        menu.addAction("Add Timeslot").triggered.connect(lambda: self.time_slot_editor.add_time_slot(self))
        menu.addAction("Modify Timeslot").triggered.connect(lambda: self.time_slot_editor.modify_time_slot(self))
        menu.addAction("Delete Timeslot").triggered.connect(lambda: self.time_slot_editor.delete_time_slot(self))

    def _bind_course_commands(self, menu):
        """Binds course management operations."""
        menu.addAction("Add Courses").triggered.connect(lambda: self.course_manager.add_course_via_dialog(self))
        menu.addAction("Modify Courses").triggered.connect(lambda: self.course_manager.modify_course_via_dialog(self))
        menu.addAction("Delete Courses").triggered.connect(lambda: self.course_manager.delete_course_via_dialog(self))

    def _bind_room_commands(self, menu):
        """Binds room management operations."""
        menu.addAction("Add Rooms").triggered.connect(lambda: self.room_manager.add_room_via_dialog(self))
        menu.addAction("Modify Rooms").triggered.connect(lambda: self.room_manager.modify_room_via_dialog(self))
        menu.addAction("Delete Rooms").triggered.connect(lambda: self.room_manager.delete_room_via_dialog(self))

    def _bind_lab_commands(self, menu):
        """Binds lab management operations."""
        menu.addAction("Add Labs").triggered.connect(lambda: self.lab_manager.add_lab_via_dialog(self))
        menu.addAction("Modify Labs").triggered.connect(lambda: self.lab_manager.modify_lab_via_dialog(self))
        menu.addAction("Delete Labs").triggered.connect(lambda: self.lab_manager.delete_lab_via_dialog(self))

    def _bind_generator_commands(self, menu):
        """Binds schedule generation operations."""
        menu.addAction("Limit # Of Schedules").triggered.connect(lambda: self.gen_manager.set_limit(self))
        menu.addAction("Toggle Optimization").triggered.connect(lambda: self.gen_manager.set_optimize(self))
        menu.addAction("Generate Schedules").triggered.connect(lambda: self.gen_manager.run_scheduler(self))

    def _bind_viewer_commands(self, menu):
        """Binds schedule viewing and I/O operations."""
        menu.addAction("View Schedules").triggered.connect(lambda: self.open_schedule_viewer("all"))
        menu.addAction("View by Faculty").triggered.connect(lambda: self.open_schedule_viewer("faculty"))
        menu.addAction("View by Room").triggered.connect(lambda: self.open_schedule_viewer("room"))
        menu.addAction("View by Lab").triggered.connect(lambda: self.open_schedule_viewer("lab"))
        menu.addAction("Export Schedules").triggered.connect(self.handle_export_schedule)
        menu.addAction("Import Schedules").triggered.connect(self.handle_import_schedule)
        menu.addAction("Clear Schedules").triggered.connect(self.handle_clear_schedule)

#=================================================================================
"""
Theme Functions:
"""
#=================================================================================
        
    def _is_dark(self, hex_color: str) -> bool:
        """Return True if color is dark (use light text)."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5

    def apply_theme(self) -> None:
        dark = self._is_dark(self.theme_color)
        text_color = "#e0e0e0" if dark else "#333333"
        btn_bg = self._darken(self.theme_color, 0.15) if dark else self._lighten(self.theme_color, 0.1)
        btn_hover = self._darken(self.theme_color, 0.1) if dark else self._lighten(self.theme_color, 0.05)
        btn_disabled = self._darken(self.theme_color, 0.25) if dark else self._lighten(self.theme_color, 0.2)
        btn_border = self._lighten(self.theme_color, 0.22) if dark else self._darken(self.theme_color, 0.18)
        panel_border = self._lighten(self.theme_color, 0.16) if dark else self._darken(self.theme_color, 0.12)

        self.setStyleSheet(
            f"QMainWindow, QWidget {{ background-color: {self.theme_color}; }} "
            f"QPushButton {{ background-color: {btn_bg}; color: {text_color}; border: 1px solid {btn_border}; }} "
            f"QPushButton:hover {{ background-color: {btn_hover}; }} "
            f"QPushButton:disabled {{ background-color: {btn_disabled}; color: #888; }} "
        )
        text_c = "#e0e0e0" if dark else "#333333"
        self.theme_btn.setStyleSheet(
            f"background-color: {self.theme_color}; color: {text_c}; border: 2px solid {btn_border};"
        )
        self.theme_btn.setText(self.current_theme)
        for panel in (self.left_panel, self.mid_panel, self.right_panel):
            panel.set_color(self.theme_color, panel_border)
        self._apply_ai_chat_theme()

    def _apply_ai_chat_theme(self) -> None:
        if not hasattr(self, "ai_chat_log"):
            return
        dark = self._is_dark(self.theme_color)
        bg = "#2b2b2b" if dark else "#ffffff"
        fg = "#e0e0e0" if dark else "#222222"
        border = "#555" if dark else "#ccc"
        sheet = (
            f"QPlainTextEdit, QLineEdit {{ background-color: {bg}; color: {fg}; "
            f"border: 1px solid {border}; }}"
        )
        self.ai_chat_log.setStyleSheet(sheet)
        self.ai_input.setStyleSheet(sheet)

    def _darken(self, hex_color: str, amount: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = max(0, int(int(hex_color[0:2], 16) * (1 - amount)))
        g = max(0, int(int(hex_color[2:4], 16) * (1 - amount)))
        b = max(0, int(int(hex_color[4:6], 16) * (1 - amount)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _lighten(self, hex_color: str, amount: float) -> str:
        hex_color = hex_color.lstrip("#")
        r = min(255, int(int(hex_color[0:2], 16) + 255 * amount))
        g = min(255, int(int(hex_color[2:4], 16) + 255 * amount))
        b = min(255, int(int(hex_color[4:6], 16) + 255 * amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Reset Layout").triggered.connect(self.reset_layout)
        menu.exec(self.splitter.mapToGlobal(position))

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
        
    def handle_change_path(self):
        """Opens dialog to update the configuration file path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Configuration File", "config/", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_mgr.filepath = file_path
            try:
                self.config_mgr.load()
                self.cfg_panel.update_title(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Load Warning", str(e))

    def handle_import_schedule(self):
        """
        Delegates CSV parsing to ConfigManager and updates the UI with the result.
        """
        # ConfigManager opens the Open File dialog and parses the CSV into a list of lists
        imported_data = self.config_mgr.import_schedule_from_csv(parent=self)

        if imported_data:
            # Replace current session with imported data
            self.schedules = imported_data
            self.current_schedule_index = 0

            # Trigger your UI update logic
            # (Assuming you have a method like update_viewer_text() or similar)
            if hasattr(self, 'update_schedule_display'):
                self.update_schedule_display()

            QMessageBox.information(
                self,
                "Import Successful",
                f"Successfully loaded {len(imported_data)} schedule(s)."
            )

    def handle_export_schedule(self):
        """
        Delegates the export process to the ConfigManager.
        The ConfigManager will handle the 'Save As' dialog and CSV formatting.
        """
        # 1. Check if we actually have schedules to export
        # We pass self.schedules (the full list of generated options)
        if hasattr(self, 'schedules') and self.schedules:
            # Pass 'self' as the second argument so the ConfigManager 
            # can use this window as the parent for its file dialog.
            success = self.config_mgr.export_schedule_to_csv(self.schedules, self)
            
            if success:
                # Optional: log to status bar if you have one
                # self.statusBar().showMessage("Schedules exported successfully.", 5000)
                pass
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, 
                "Export Error", 
                "There are no schedules currently loaded to export. "
                "Please generate schedules first."
            )

    def handle_clear_schedule(self) -> None:

        """
        Removes all the currently generated schedules.
        """
        if not self.schedules or not (0 <= self.current_schedule_index < len(self.schedules)):
            QMessageBox.warning(self, "No Data", "No schedules to clear.")
            return
        else:
            try:
                self.schedules.clear()
                QMessageBox.information(self, "Success", "Schedule/s have been cleared.")
            except:
                QMessageBox.critical(self, "Error", "Clear failed.")

    def show_context_menu(self, position) -> None:
        """
        Displays a context menu for the splitter to reset the layout.
        """
        menu = QMenu(self)
        menu.addAction("Reset Layout").triggered.connect(self.reset_layout)
        menu.exec(self.splitter.mapToGlobal(position))

    def reset_layout(self) -> None:
        """
        Resets the splitter panels to an even distribution.
        """
        width = sum(self.splitter.sizes())
        self.splitter.setSizes([width // 2, width // 2])

    def handle_view_summary(self):
        """Displays a summary of the current configuration in a monospaced dialog."""
        summary = self.config_mgr.get_summary_text()
        self._show_tabulated_msg(f"Summary: {self.config_mgr.filepath}", summary)

    def _show_tabulated_msg(self, title, text):
        """Helper for monospaced message boxes."""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setFont(QFont("Courier New", 10))
        msg.exec()

    #TODO: Revisit this function, i do not think it is finished.
    def open_schedule_viewer(self, grouping: str):
        """
        Opens the schedule viewing strategy.
        
        :param grouping: How to group the data ('all', 'faculty', 'room', 'lab').
        """
        if not self.schedules:
            QMessageBox.warning(self, "No schedules", "Generate or import one first.")
            return

        self.viewer = QDialog(self)
        self.viewer.setWindowTitle(f"Viewer - {grouping.capitalize()}")
        self.viewer.resize(900, 500)
        layout = QVBoxLayout(self.viewer)

        self.schedule_display = QPlainTextEdit()
        self.schedule_display.setReadOnly(True)
        self.schedule_display.setFont(QFont("Courier New", 10))
        layout.addWidget(self.schedule_display)

        if grouping == "all":
            self._setup_viewer_navigation(layout)
            self._refresh_schedule_display()
        else:
            # Viewer Strategy: Logic for specific data maps
            config_data = self.config_mgr.data.get("config", {})
            data_map = {
                "faculty": config_data.get("faculty", "N/A"),
                "room": config_data.get("rooms", "N/A"),
                "lab": config_data.get("labs", "N/A")
            }
            self.schedule_display.setPlainText(json.dumps(data_map.get(grouping), indent=4))

        self.viewer.exec()

    def _setup_viewer_navigation(self, layout):
        """Adds navigation buttons for cycling through multiple schedules."""
        nav_layout = QHBoxLayout()
        prev_btn, next_btn = QPushButton("Previous"), QPushButton("Next")
        prev_btn.clicked.connect(lambda: (self.show_prev_schedule(), self._refresh_schedule_display()))
        next_btn.clicked.connect(lambda: (self.show_next_schedule(), self._refresh_schedule_display()))
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        layout.addLayout(nav_layout)

    def _refresh_schedule_display(self):
        """Updates the viewer text based on the current schedule index."""
        if not self.schedules: return
        schedule = self.schedules[self.current_schedule_index]
        text = self.config_mgr.get_schedule_spreadsheet(schedule) if isinstance(schedule, list) else str(schedule)
        self.schedule_display.setPlainText(text)
        self.viewer.setWindowTitle(f"Schedule Viewer ({self.current_schedule_index + 1}/{len(self.schedules)})")

    def show_next_schedule(self):
        """Increments schedule index with wrap-around."""
        if self.schedules:
            self.current_schedule_index = (self.current_schedule_index + 1) % len(self.schedules)

    def show_prev_schedule(self):
        """Decrements schedule index with wrap-around."""
        if self.schedules:
            self.current_schedule_index = (self.current_schedule_index - 1) % len(self.schedules)

    def save_config_to_file(self):
        """'Save As' functionality for exporting the current config state."""
        p, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "*.json")
        if p:
            with open(p, 'w') as f:
                json.dump(self.config_mgr.data, f, indent=4)

    def refresh_config_views_after_mutation(self) -> None:
        """Reload config from disk and refresh read-only views after AI (or other) tools wrote the file."""
        path = getattr(self.config_mgr, "filepath", None)
        if path and os.path.isfile(path):
            try:
                self.config_mgr.load()
            except Exception:
                pass
        if hasattr(self, "detail_view"):
            self.detail_view.setPlainText(json.dumps(self.config_mgr.data, indent=2))

    def _append_ai_chat(self, who: str, text: str) -> None:
        self.ai_chat_log.appendPlainText(f"{who}: {text}\n")

    def send_assistant_message(self) -> None:
        if self._assistant_worker is not None and self._assistant_worker.isRunning():
            return
        user_text = self.ai_input.text().strip()
        if not user_text:
            return
        key = default_api_key()
        if not key:
            QMessageBox.warning(
                self,
                "OpenAI API key",
                "Set your key in app/ai_assistant.py (OPENAI_API_KEY_IN_CODE), "
                "or put it in config/openai_key.txt, or set OPENAI_API_KEY in the environment.",
            )
            return
        self.ai_input.clear()
        self._append_ai_chat("You", user_text)
        self.assistant_messages.append({"role": "user", "content": user_text})
        self.ai_send_btn.setEnabled(False)
        self.ai_input.setEnabled(False)

        msgs = copy.deepcopy(self.assistant_messages)
        w = AssistantChatWorker(key, OPENAI_MODEL, msgs)
        self._assistant_worker = w
        w.need_tools.connect(self._on_assistant_need_tools)
        w.finished_reply.connect(self._on_assistant_finished)
        w.failed.connect(self._on_assistant_failed)
        # finished_reply can run before the native thread has fully stopped; never destroy
        # the QThread until QThread.finished (or Qt aborts in ~QThread).
        w.finished.connect(lambda worker=w: self._dispose_assistant_chat_worker(worker))
        w.start()

    def _on_assistant_need_tools(self, tool_calls: list) -> None:
        results = []
        for tc in tool_calls:
            try:
                args = json.loads(tc.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            out = execute_tool(self, tc["name"], args)
            results.append({"id": tc["id"], "content": out})
        self.refresh_config_views_after_mutation()
        w = self._assistant_worker
        if w is not None:
            w.deliver_tool_results(results)

    def _dispose_assistant_chat_worker(self, worker: AssistantChatWorker) -> None:
        if self._assistant_worker is worker:
            self._assistant_worker = None
        worker.deleteLater()

    def _on_assistant_finished(self, text: str) -> None:
        self._append_ai_chat("Assistant", text)
        if self._assistant_worker is not None:
            self.assistant_messages = self._assistant_worker.out_messages
        self.ai_send_btn.setEnabled(True)
        self.ai_input.setEnabled(True)

    def _on_assistant_failed(self, err: str) -> None:
        self._append_ai_chat("Assistant", f"(Error) {err}")
        self.ai_send_btn.setEnabled(True)
        self.ai_input.setEnabled(True)
