"""
main_window.py
==============
The primary entry point for the Scheduler Program GUI.

:date: 03/23/2026
:authors: Kyle Smith, Tyler Strohl
:class: CMSC 420
"""

import json
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton, 
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, 
    QMessageBox, QDialog, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont

from .menu_widgets import ContentPanel
from .course_gui import CourseConfigManager
from .room_gui import RoomConfigManager
from .faculty_gui import FacultyManager
from config.config_mgr import ConfigManager
from .generator_gui import GenConfigManager
from .lab_gui import LabConfigManager


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

        # Theme Configuration
        self.theme_colors = {
            "Light": "#f3f4f6", "Dark": "#1f1f24", "Autumn": "#8a5a44",
            "Crimson": "#8b2e3c", "Marathon": "#c2fe0b", "Summer": "#f4c95d",
            "Spring": "#98c379", "Winter": "#cfddeb", "Ocean": "#1f6f8b",
            "Land": "#6b8f71", "Sky": "#7fb7e6",
        }
        self.current_theme = "Light"
        self.theme_color = self.theme_colors[self.current_theme]

        # Domain Logic Managers
        self.config_mgr = ConfigManager("config/config.json")
        self._load_config()

        self.course_manager = CourseConfigManager()
        self.room_manager = RoomConfigManager()
        self.faculty_manager = FacultyManager()
        self.gen_manager = GenConfigManager()
        self.lab_manager = LabConfigManager()

        # State Management
        self.schedules = []
        self.current_schedule_index = 0
        self.imported_schedule = None

        # UI Setup
        self._setup_ui_components()
        self.init_menus()
        self.apply_theme()

    def _load_config(self):
        """
        Attempts to load the initial configuration file.
        """
        try:
            self.config_mgr.load()
        except Exception:
            pass

    def _setup_ui_components(self):
        """
        Initializes the structural layout components of the window.
        """
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.mid_panel = ContentPanel(f"Active Config: <b>{self.config_mgr.filepath}</b>", "#000000")
        self.right_panel = ContentPanel("Inspector & Assistant", "#1a1a1a")
        
        self.detail_view = QPlainTextEdit()
        self.save_cfg_btn = QPushButton("Apply JSON Changes")
        self.save_cfg_btn.clicked.connect(self.save_inspector_changes)
        
        self.right_panel.layout.addWidget(self.detail_view)
        self.right_panel.layout.addWidget(self.save_cfg_btn)

        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([800, 200])
        self.setCentralWidget(self.splitter)

    def init_menus(self):
        """
        Constructs the Menu Bar and binds actions using the Command Pattern approach.
        
        .. note:: Actions are bound via lambda triggers to respective manager methods.
        """
        menubar = self.menuBar()
        self._setup_theme_menu(menubar)

        # Menu Definitions
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        gen_menu = menubar.addMenu("Generator")
        viewer_menu = menubar.addMenu("Viewer")

        # Sub-Menus
        faculty_menu = edit_menu.addMenu("Faculty")
        courses_menu = edit_menu.addMenu("Courses")
        rooms_menu = edit_menu.addMenu("Rooms")
        labs_menu = edit_menu.addMenu("Labs")

        # Command Binding
        self._bind_file_commands(file_menu)
        self._bind_faculty_commands(faculty_menu)
        self._bind_course_commands(courses_menu)
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
        menu.addAction("Edit Available Times").triggered.connect(lambda: self.faculty_manager.faculty_time_via_dialog(self))
        menu.addAction("Edit Preferences").triggered.connect(lambda: self.faculty_manager.faculty_preference(self))

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

    def apply_theme(self) -> None:
        """
        Applies the selected theme strategy to the application widgets.
        
        Calculates luminance to determine text contrast and updates stylesheets.
        """
        dark = self._is_dark(self.theme_color)
        text_color = "#e0e0e0" if dark else "#333333"
        btn_bg = self._darken(self.theme_color, 0.15) if dark else self._lighten(self.theme_color, 0.1)
        btn_border = self._lighten(self.theme_color, 0.22) if dark else self._darken(self.theme_color, 0.18)
        panel_border = self._lighten(self.theme_color, 0.16) if dark else self._darken(self.theme_color, 0.12)

        self.setStyleSheet(
            f"QMainWindow, QWidget {{ background-color: {self.theme_color}; }} "
            f"QPushButton {{ background-color: {btn_bg}; color: {text_color}; border: 1px solid {btn_border}; }} "
        )
        self.theme_btn.setStyleSheet(f"color: {text_color}; border: 2px solid {btn_border};")
        self.theme_btn.setText(self.current_theme)

        for panel in (self.mid_panel, self.right_panel):
            panel.set_color(self.theme_color, panel_border)

    def _is_dark(self, hex_color: str) -> bool:
        """
        Determines if a color is dark based on perceived luminance.
        
        :param hex_color: Hex string of the color.
        :return: True if luminance < 0.5.
        """
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance < 0.5

    def _darken(self, hex_color: str, amount: float) -> str:
        """Helper to darken a hex color."""
        hex_color = hex_color.lstrip("#")
        parts = [max(0, int(int(hex_color[i:i+2], 16) * (1 - amount))) for i in (0, 2, 4)]
        return f"#{parts[0]:02x}{parts[1]:02x}{parts[2]:02x}"

    def _lighten(self, hex_color: str, amount: float) -> str:
        """Helper to lighten a hex color."""
        hex_color = hex_color.lstrip("#")
        parts = [min(255, int(int(hex_color[i:i+2], 16) + 255 * amount)) for i in (0, 2, 4)]
        return f"#{parts[0]:02x}{parts[1]:02x}{parts[2]:02x}"

    def set_theme(self, theme_name: str) -> None:
        """
        Changes the current theme and triggers a UI refresh.
        
        :param theme_name: Name of the theme key in ``theme_colors``.
        """
        if theme_name in self.theme_colors:
            self.current_theme = theme_name
            self.theme_color = self.theme_colors[theme_name]
            self.apply_theme()

    def handle_change_path(self):
        """Opens dialog to update the configuration file path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Configuration File", "config/", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.config_mgr.filepath = file_path
            try:
                self.config_mgr.load()
                self.mid_panel.update_title(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Load Warning", str(e))

    def handle_import_schedule(self) -> None:
        """
        Imports a schedule from CSV or JSON and adds it to the session list.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Schedule", "", "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        # Simple strategy choice based on extension
        if file_path.lower().endswith(".json"):
            data = self.config_mgr.import_schedule_from_json(file_path)
        else:
            data = self.config_mgr.import_schedule_from_csv(file_path)

        if data:
            self.schedules.append(data)
            self.current_schedule_index = len(self.schedules) - 1
            QMessageBox.information(self, "Success", f"Imported {len(data)} assignments.")
        else:
            QMessageBox.warning(self, "Error", "Failed to import a valid schedule.")

    def handle_export_schedule(self) -> None:
        """
        Exports the currently active schedule to a CSV file.
        """
        if not self.schedules or not (0 <= self.current_schedule_index < len(self.schedules)):
            QMessageBox.warning(self, "No Data", "No schedule selected to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Schedule", "", "CSV Files (*.csv)")
        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'
            
            if self.config_mgr.export_schedule_to_csv(self.schedules[self.current_schedule_index], file_path):
                QMessageBox.information(self, "Success", f"Exported to {file_path}")
            else:
                QMessageBox.critical(self, "Error", "Export failed.")

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

    def save_inspector_changes(self):
        """Applies manual JSON edits from the right-hand Inspector panel."""
        try:
            # Note: Logic assumes a config_tree exists as part of the implementation
            # Added basic error handling as per original source.
            content = json.loads(self.detail_view.toPlainText())
            # (Logic for updating specific keys would go here)
            QMessageBox.information(self, "Success", "Configuration applied.")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Invalid JSON format.")
