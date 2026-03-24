'''
    File: main_window.py
    Date: 03/23/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: The main window of the GUI.
'''

import random
import copy
import json
import csv
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton, 
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, 
    QMessageBox, QDialog, QPlainTextEdit, QLabel,
    QMenuBar
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scheduler Program - GenericTeamName")
        self.resize(900, 600)
        self.theme_colors = {
            "Light": "#f3f4f6",
            "Dark": "#1f1f24",
            "Autumn": "#8a5a44",
            "Crimson": "#8b2e3c",
            "Marathon": "#c2fe0b",
            "Summer": "#f4c95d",
            "Spring": "#98c379",
            "Winter": "#cfddeb",
            "Ocean": "#1f6f8b",
            "Land": "#6b8f71",
            "Sky": "#7fb7e6",
        }
        self.current_theme = "Light"
        self.theme_color = self.theme_colors[self.current_theme]

        # Initialize with a default
        self.config_mgr = ConfigManager("config/config.json")
        try:
            self.config_mgr.load()
        except Exception:
            pass
        self.imported_schedule = None  # list of {course_id, day, time} or None
        
        #Management helpers:
        #---------------------------------------------------------------------------
        self.course_manager = CourseConfigManager()
        self.room_manager = RoomConfigManager()
        self.faculty_manager = FacultyManager()
        self.gen_manager = GenConfigManager()
        self.lab_manager = LabConfigManager()
        
        #---------------------------------------------------------------------------
        # schedules: list of schedules; each schedule is list of {course_id, day, time}
        self.schedules = []
        self.current_schedule_index = 0

        #most important function, along with "menu_widgets.py" class.
        self.init_menus()
        self.apply_theme()

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

#__init__ ends here ------------------------------------------------------------------

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

    def reset_layout(self):
        total_width = sum(self.splitter.sizes())
        third = total_width // 3
        self.splitter.setSizes([third, third, total_width - (2 * third)])

    def init_menus(self):

        #TODO: Implement a design pattern to improve this code.
        #see some functions at bottom of class.

        menubar = self.menuBar()

        self.theme_btn = QPushButton(self.current_theme)
        self.theme_btn.setMaximumWidth(180)
        self.theme_btn.setMaximumHeight(28)
        self.theme_btn.setFont(QFont("", 9))
        theme_menu = QMenu(self)
        for theme_name in self.theme_colors:
            theme_menu.addAction(theme_name).triggered.connect(
                lambda checked=False, name=theme_name: self.set_theme(name)
            )
        self.theme_btn.setMenu(theme_menu)

        menubar.setCornerWidget(self.theme_btn, Qt.Corner.TopLeftCorner)

        #--------------------------------------------
        #Config Editor, Schedule Generator & Viewer MENU-BAR Options:
        #Menus & Actions: [note: only applies to buttons with sub-menus]

        #these are the menubar tabs that display.
        file_menu = menubar.addMenu("File")

        edit_menu = menubar.addMenu("Edit")

        #tabs will be moved under edit_menu
        faculty_menu = menubar.addMenu("Faculty")
        courses_menu = menubar.addMenu("Courses")
        rooms_menu = menubar.addMenu("Rooms")
        labs_menu = menubar.addMenu("Labs")


        gen_menu = menubar.addMenu("Generator")
        viewer_menu = menubar.addMenu("Viewer")
        #-------------------------------------------
        #actions for menubar tabs.
        #file:
        change_file_ac = file_menu.addAction("Change Config File")
        view_sum_ac = file_menu.addAction("View Summary")
        save_config_ac = file_menu.addAction("Save Config")
        save_config_as_ac = file_menu.addAction("Save Config As")

        #faculty:
        add_faculty_ac = faculty_menu.addAction("Add Faculty")
        mod_faculty_ac = faculty_menu.addAction("Modify Faculty")
        del_faculty_ac = faculty_menu.addAction("Delete Faculty")
        ed_faculty_times_ac = faculty_menu.addAction("Edit Faculty Available Times")
        ed_faculty_pref_ac = faculty_menu.addAction("Edit Faculty Preferences")

        #courses:
        add_courses_ac = courses_menu.addAction("Add Courses")
        mod_courses_ac = courses_menu.addAction("Modify Courses")
        del_courses_ac = courses_menu.addAction("Delete Courses")

        #rooms:
        add_rooms_ac = rooms_menu.addAction("Add Rooms")
        mod_rooms_ac = rooms_menu.addAction("Modify Rooms")
        del_rooms_ac = rooms_menu.addAction("Delete Rooms")

        #labs:
        add_labs_ac = labs_menu.addAction("Add Labs")
        mod_labs_ac = labs_menu.addAction("Modify Labs")
        del_labs_ac = labs_menu.addAction("Delete Labs")

        #generator:
        limit_ac = gen_menu.addAction("Limit # Of Schedules")
        optimize_ac = gen_menu.addAction("Toggle Optimization")
        generate_sc_ac = gen_menu.addAction("Generate Schedules")

        #viewer:
        view_sc_ac = viewer_menu.addAction("View Schedules")
        view_sc_fac_ac = viewer_menu.addAction("View by Faculty")
        view_sc_room_ac = viewer_menu.addAction("View by Room")
        view_sc_lab_ac = viewer_menu.addAction("View by Lab")
        export_sc_ac = viewer_menu.addAction("Export Schedules")
        import_sc_ac = viewer_menu.addAction("Import Schedules")

        #--------------------------------------------

        #box-layout for buttons
        self.sc_generator_layout = QVBoxLayout()
        self.config_btn_layout = QHBoxLayout()
        self.sc_viewer_layout = QVBoxLayout()
        #splitter for panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_panel = ContentPanel("Schedule Generator", "#1a1a1a")
        self.mid_panel = ContentPanel(f"Active Config: <b>{self.config_mgr.filepath}</b>", "#000000")
        #self.right_panel = ContentPanel("Schedule Viewer", "#1a1a1a")
        
        #TODO: TEMPORARY, FIX OR MOVE LATER:
        #------------------------------------------------------------
        
        self.right_panel = ContentPanel("Viewer & Inspector", "#1a1a1a")
        self.detail_view = QPlainTextEdit()
        self.save_cfg_btn = QPushButton("Apply JSON Changes")
        self.save_cfg_btn.clicked.connect(self.save_inspector_changes)
        self.right_panel.layout.addWidget(self.detail_view)
        self.right_panel.layout.addWidget(self.save_cfg_btn)

        #------------------------------------------------------------

        #----------------------------------------------------------
        #Left-Panel (currently unused)
        #----------------------------------------------------------

        self.sc_generator_layout.addStretch()

        #----------------------------------------------------------
        #Mid-Panel (Config Editor)
        #----------------------------------------------------------

        self.config_btn_layout.addStretch()

        #----------------------------------------------------------
        #Right-Panel (currently unused)
        #----------------------------------------------------------

        #----------------------------------------------------------
        #Splitter for 3 Main Panels:
        #----------------------------------------------------------
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        #sizes in order of declarations above ^^
        self.splitter.setSizes([100, 400, 100])
        self.left_panel.layout.insertLayout(1, self.sc_generator_layout)
        self.mid_panel.layout.insertLayout(1, self.config_btn_layout)
        self.right_panel.layout.insertLayout(1, self.sc_viewer_layout)
        
        self.setCentralWidget(self.splitter)

        self.splitter.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.splitter.customContextMenuRequested.connect(self.show_context_menu)

  
        #----------------------------------------------------------
        #Action triggers:

        #btn.clicked.connect = one button click
        #ac.triggered.connect = drop-down option clicked

        #-------------------------------------------
        #triggers for left panel (currently unused)
        
        #-------------------------------------------

        #-------------------------------------------
        #triggers for mid panel (live config/schedules will display here)
        
        #-------------------------------------------
        #triggers for menubar
        #file:
        change_file_ac.triggered.connect(self.handle_change_path)
        view_sum_ac.triggered.connect(self.handle_view_summary)
        save_config_ac.triggered.connect(lambda: self.config_mgr.save(self))
        save_config_as_ac.triggered.connect(lambda: self.save_config_to_file())
        
        #faculty:
        add_faculty_ac.triggered.connect(lambda: self.faculty_manager.add_faculty_via_dialog(self))
        mod_faculty_ac.triggered.connect(lambda: self.faculty_manager.modify_faculty_via_dialog(self))
        del_faculty_ac.triggered.connect(lambda: self.faculty_manager.delete_faculty_via_dialog(self))
        ed_faculty_times_ac.triggered.connect(lambda: self.faculty_manager.faculty_time_via_dialog(self))
        ed_faculty_pref_ac.triggered.connect(lambda: self.faculty_manager.faculty_preference(self))

        #courses:
        add_courses_ac.triggered.connect(lambda: self.course_manager.add_course_via_dialog(self))
        mod_courses_ac.triggered.connect(lambda: self.course_manager.modify_course_via_dialog(self))
        del_courses_ac.triggered.connect(lambda: self.course_manager.delete_course_via_dialog(self))

        #rooms:
        add_rooms_ac.triggered.connect(lambda: self.room_manager.add_room_via_dialog(self))
        mod_rooms_ac.triggered.connect(lambda: self.room_manager.modify_room_via_dialog(self))
        del_rooms_ac.triggered.connect(lambda: self.room_manager.delete_room_via_dialog(self))

        #labs:
        add_labs_ac.triggered.connect(lambda: self.lab_manager.add_lab_via_dialog(self))
        mod_labs_ac.triggered.connect(lambda: self.lab_manager.modify_lab_via_dialog(self))
        del_labs_ac.triggered.connect(lambda: self.lab_manager.delete_lab_via_dialog(self))
        
        #generator
        limit_ac.triggered.connect(lambda: self.gen_manager.set_limit(self))
        optimize_ac.triggered.connect(lambda: self.gen_manager.set_optimize(self))
        generate_sc_ac.triggered.connect(lambda: self.gen_manager.run_scheduler(self))

        #viewer:
        view_sc_ac.triggered.connect(lambda: self.open_schedule_viewer("all"))
        view_sc_fac_ac.triggered.connect(lambda: self.open_schedule_viewer("faculty"))
        view_sc_room_ac.triggered.connect(lambda: self.open_schedule_viewer("room"))
        view_sc_lab_ac.triggered.connect(lambda: self.open_schedule_viewer("lab"))
        export_sc_ac.triggered.connect(lambda: self.handle_export_schedule())
        import_sc_ac.triggered.connect(lambda: self.handle_import_schedule())

        #-------------------------------------------
        #triggers for right panel (currently unused)
        
        #-------------------------------------------

    #----------------------------------------------------------
    # Config management handlers (GUI)
    #----------------------------------------------------------

    def handle_change_path(self):
        """Opens a file dialog to choose or create a config JSON."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Configuration File",
            "config/",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            self.config_mgr.filepath = file_path
            try:
                self.config_mgr.load()
                self.mid_panel.update_title(file_path)
                QMessageBox.information(self, "Path Changed", f"Now using: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Load Warning", f"File selected, but could not load data: {e}")

    def handle_view_summary(self):
        """Displays summary with the current file path in the title."""
        summary_text = self.config_mgr.get_summary_text()

        msg = QMessageBox(self)
        msg.setWindowTitle(f"Summary: {self.config_mgr.filepath.split('/')[-1]}")
        msg.setText(summary_text)

        # Use Monospace for tabulation
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        msg.setFont(font)

        msg.exec()

    def handle_import_schedule(self):
        """Opens a file dialog to import a schedule from CSV or JSON. Schedule is viewable in Schedule Viewer."""
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self,
            "Import Schedule",
            "",
            "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return
        schedule_data = None
        if file_path.lower().endswith(".json"):
            schedule_data = self.config_mgr.import_schedule_from_json(file_path)
        else:
            schedule_data = self.config_mgr.import_schedule_from_csv(file_path)
        if schedule_data is not None:
            self.imported_schedule = schedule_data
            self.schedules.append(schedule_data)
            self.current_schedule_index = len(self.schedules) - 1
            QMessageBox.information(
                self,
                "Import Success",
                f"Imported {len(schedule_data)} assignment(s) from:\n{file_path}\nView in Schedule Viewer."
            )
        else:
            QMessageBox.warning(
                self,
                "Import Failed",
                "Could not read a valid schedule from the selected file."
            )

    def handle_export_schedule(self):
        """Triggers the CSV export via a file dialog. Exports the currently viewed schedule."""
        schedule = None
        if self.schedules and 0 <= self.current_schedule_index < len(self.schedules):
            schedule = self.schedules[self.current_schedule_index]
        if not schedule or not isinstance(schedule, list):
            QMessageBox.warning(
                self,
                "No Schedule",
                "No schedule to export. Generate or import a schedule first, then use Schedule Viewer to select which one to export."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Schedule", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            success = self.config_mgr.export_schedule_to_csv(schedule, file_path)

            if success:
                QMessageBox.information(self, "Export Success", f"Schedule exported to:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "Could not write to the selected file.")

    def _show_tabulated_msg(self, title, text):
        """Private helper to ensure monospaced font is used for all tables."""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        mono_font = QFont("Courier New", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        msg.setFont(mono_font)
        msg.exec()

    #----------------------------------------------------------
    # Schedule Viewer Functions
    #----------------------------------------------------------

    #TODO: Make schedules look nicer, & do more with the faculty/room/lab options.
    def open_schedule_viewer(self, grouping):

        if not self.schedules:
            QMessageBox.warning(self, "No schedules", "No schedules to view. Generate or import one first.")
            return

        self.viewer = QDialog(self)
        self.viewer.setWindowTitle(f"Schedule Viewer - {grouping.capitalize()}")
        self.viewer.resize(900, 500)
        layout = QVBoxLayout(self.viewer)

        self.schedule_display = QPlainTextEdit()
        self.schedule_display.setReadOnly(True)
        self.schedule_display.setFont(QFont("Courier New", 10))
        self.schedule_display.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0;")
        layout.addWidget(self.schedule_display)

        if grouping == "all":

            def refresh_display():
                self._refresh_schedule_display()

            nav_layout = QHBoxLayout()
            prev_btn = QPushButton("Previous")
            next_btn = QPushButton("Next")
            
            prev_btn.clicked.connect(lambda: (self.show_prev_schedule(), refresh_display()))
            next_btn.clicked.connect(lambda: (self.show_next_schedule(), refresh_display()))
            
            nav_layout.addWidget(prev_btn)
            nav_layout.addWidget(next_btn)
            layout.addLayout(nav_layout)
            
            self._refresh_schedule_display()

        else:

            config_data = self.config_mgr.data.get("config", {})
            
            data_map = {
                "faculty": config_data.get("faculty", "No Faculty found"),
                "room": config_data.get("rooms", "No Rooms found"),
                "lab": config_data.get("labs", "No Labs found")
            }
            
            content = data_map.get(grouping)
            self.schedule_display.setPlainText(json.dumps(content, indent=4))


        self.viewer.exec()

    def _refresh_schedule_display(self):
        if not self.schedules or not (0 <= self.current_schedule_index < len(self.schedules)):
            return
        schedule = self.schedules[self.current_schedule_index]
        schedule_data = schedule if isinstance(schedule, list) and schedule else []
        if schedule_data and isinstance(schedule_data[0], dict):
            text = self.config_mgr.get_schedule_spreadsheet(schedule_data)
        else:
            text = str(schedule)
        if hasattr(self, "schedule_display"):
            self.schedule_display.setPlainText(text)
        if hasattr(self, "viewer") and self.viewer is not None:
            self.viewer.setWindowTitle(f"Schedule Viewer ({self.current_schedule_index + 1}/{len(self.schedules)})")

    def show_current_schedule(self):
        if not self.schedules:
            return
        self._refresh_schedule_display()


    def show_next_schedule(self):
        if not self.schedules:
            return

        self.current_schedule_index = (
            self.current_schedule_index + 1
        ) % len(self.schedules)

        self.show_current_schedule()


    def show_prev_schedule(self):
        if not self.schedules:
            return

        self.current_schedule_index = (
            self.current_schedule_index - 1
        ) % len(self.schedules)

        self.show_current_schedule()

    #This function is used to "save as" a config file
    def save_config_to_file(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "*.json")
        if p:
            with open(p, 'w') as f: json.dump(self.config_mgr.data, f, indent=4)

    ######

    #TODO: Finish the below function idea.
    #use this concept to make function calls more dynamic,
    #needs more work however. maybe adding a function to each manager class?
    """
    def open_manager_gui(self, manager):
        
        #Safely opens a manager's sub-window.

        #Args:
            #manager: An instance of a ConfigManager (Course, Room, or Faculty).
        
        if hasattr(manager, 'show'): 
            manager.show()
        elif hasattr(manager, 'gui'): 
            manager.gui.show()
    """

    def save_inspector_changes(self):
            try:
                it = self.config_tree.currentItem()
                if not it: return
                self.config_mgr.data[it.text(0).upper()] = json.loads(self.detail_view.toPlainText())
                QMessageBox.information(self, "Success", "Configuration applied.")
            except: QMessageBox.critical(self, "Error", "Invalid JSON.")
