'''
    File: main_window.py
    Date: 03/03/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: The main window of the GUI.
'''

from PyQt6.QtWidgets import QMainWindow, QSplitter, QMenu, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QMessageBox, QDialog, QPlainTextEdit
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
        # Dark theme
        self.setStyleSheet(
            "QMainWindow, QWidget { background-color: #000000; } "
            "QPushButton { background-color: #333; color: #e0e0e0; border: 1px solid #555; } "
            "QPushButton:hover { background-color: #444; } "
            "QPushButton:disabled { background-color: #222; color: #888; } "
        )

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


#__init__ ends here ------------------------------------------------------------------

    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Reset Layout").triggered.connect(self.reset_layout)
        menu.exec(self.splitter.mapToGlobal(position))

    def reset_layout(self):
        total_width = sum(self.splitter.sizes())
        third = total_width // 3
        self.splitter.setSizes([third, third, total_width - (2 * third)])

    def init_menus(self):

        #can maybe turn some of these things into a loop & arrays.

        #----------------------------------------------------------
        #box-layout for buttons
        self.config_btn_layout = QVBoxLayout()
        self.sc_generator_layout = QVBoxLayout()
        self.sc_viewer_layout = QVBoxLayout()
        #splitter for panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_panel = ContentPanel("Config Editor", "#1a1a1a")
        self.mid_panel = ContentPanel("Schedule Generator", "#000000")
        self.right_panel = ContentPanel("Schedule Viewer", "#1a1a1a")
        
        #----------------------------------------------------------
        #Left-Panel (Config Editor)
        #----------------------------------------------------------
        self.faculty_btn = QPushButton("Faculty")
        self.course_btn = QPushButton("Courses")
        self.room_btn = QPushButton("Rooms")
        self.lab_btn = QPushButton("Labs")
        self.change_path_btn = QPushButton("Change Config File")
        self.config_btn_layout.addWidget(self.change_path_btn)
        self.view_sum_btn = QPushButton("View Config Summary")
        self.save_config_btn = QPushButton("Save Config")

        #above panels & buttons are displayed in widgets.
        self.config_btn_layout.addWidget(self.faculty_btn)
        self.config_btn_layout.addWidget(self.course_btn)
        self.config_btn_layout.addWidget(self.room_btn)
        self.config_btn_layout.addWidget(self.lab_btn)
        self.config_btn_layout.addWidget(self.view_sum_btn)
        self.config_btn_layout.addWidget(self.save_config_btn)
        self.config_btn_layout.addStretch()

        #----------------------------------------------------------
        #Mid-Panel (Schedule Generator)
        #----------------------------------------------------------

        self.limit_btn = QPushButton("Set Limit (# Of Schedules)")
        self.optimize_btn = QPushButton("Toggle Optimization")
        self.generate_sc_btn = QPushButton("Generate Schedules")

        self.sc_generator_layout.addWidget(self.limit_btn)
        self.sc_generator_layout.addWidget(self.optimize_btn)
        self.sc_generator_layout.addWidget(self.generate_sc_btn)
        self.sc_generator_layout.addStretch()
        #----------------------------------------------------------
        #Right-Panel (Schedule Viewer)
        #----------------------------------------------------------

        self.view_sc_btn = QPushButton("View Schedules")
        self.export_sc_btn = QPushButton("Export Schedules")
        self.import_sc_btn = QPushButton("Import Schedules")

        self.sc_viewer_layout.addWidget(self.view_sc_btn)
        self.sc_viewer_layout.addWidget(self.export_sc_btn)
        self.sc_viewer_layout.addWidget(self.import_sc_btn)
        self.sc_viewer_layout.addStretch()

        #----------------------------------------------------------
        #Splitter for 3 Main Panels:
        #----------------------------------------------------------
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        #sizes in order of declarations above ^^
        self.splitter.setSizes([300, 300, 300])
        self.left_panel.layout.insertLayout(1, self.config_btn_layout)
        self.mid_panel.layout.insertLayout(1, self.sc_generator_layout)
        self.right_panel.layout.insertLayout(1, self.sc_viewer_layout)
        
        self.setCentralWidget(self.splitter)

        self.splitter.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.splitter.customContextMenuRequested.connect(self.show_context_menu)

        #----------------------------------------------------------
        #Menus & Actions: [note: only applies to buttons with sub-menus]
        #-------------------------------------------
        #menus for left panel (config editor)
        faculty_menu = QMenu(self)
        courses_menu = QMenu(self)
        rooms_menu = QMenu(self)
        labs_menu = QMenu(self)

        self.faculty_btn.setMenu(faculty_menu)
        self.course_btn.setMenu(courses_menu)
        self.room_btn.setMenu(rooms_menu)
        self.lab_btn.setMenu(labs_menu)

        #-------------------------------------------
        #actions for left panel (config editor)
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

        #----------------------------------------------------------
        #Action triggers:
        #-------------------------------------------
        #triggers for left panel (config editor)
        #faculty:
        add_faculty_ac.triggered.connect(lambda: self.faculty_manager.add_faculty_via_dialog(self))
        mod_faculty_ac.triggered.connect(lambda: self.faculty_manager.modify_faculty_via_dialog(self))
        del_faculty_ac.triggered.connect(lambda: self.faculty_manager.delete_faculty_via_dialog(self))
        ed_faculty_times_ac.triggered.connect(lambda: self.faculty_manager.faculty_time_via_dialog(self))
        ed_faculty_pref_ac.triggered.connect(lambda: self.faculty_manager.faculty_preference(self))

        #courses:
        add_courses_ac.triggered.connect(self.handle_add_course)
        mod_courses_ac.triggered.connect(self.handle_modify_course)
        del_courses_ac.triggered.connect(self.handle_delete_course)

        #rooms:
        add_rooms_ac.triggered.connect(lambda: self.room_manager.add_room_via_dialog(self))
        mod_rooms_ac.triggered.connect(lambda: self.room_manager.modify_room_via_dialog(self))
        del_rooms_ac.triggered.connect(lambda: self.room_manager.delete_room_via_dialog(self))

        #labs:
        add_labs_ac.triggered.connect(lambda: self.lab_manager.add_lab_via_dialog(self))
        mod_labs_ac.triggered.connect(lambda: self.lab_manager.modify_lab_via_dialog(self))
        del_labs_ac.triggered.connect(lambda: self.lab_manager.delete_lab_via_dialog(self))

        #config-management:
        self.change_path_btn.clicked.connect(self.handle_change_path)
        self.view_sum_btn.clicked.connect(self.handle_view_summary)
        self.save_config_btn.clicked.connect(self.handle_save_config)
        
        #-------------------------------------------
        #triggers for mid panel (schedule generator)

        self.limit_btn.clicked.connect(lambda: self.gen_manager.set_limit(self))
        self.optimize_btn.clicked.connect(lambda: self.gen_manager.set_optimize(self))
        self.generate_sc_btn.clicked.connect(lambda: self.gen_manager.run_scheduler(self))
        #-------------------------------------------
        #triggers for right panel (schedule viewer)
        self.view_sc_btn.clicked.connect(self.open_schedule_viewer)
        self.export_sc_btn.clicked.connect(self.handle_export_schedule)
        self.import_sc_btn.clicked.connect(self.handle_import_schedule)

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
                QMessageBox.information(self, "Path Changed", f"Now using: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Load Warning", f"File selected, but could not load data: {e}")

    def handle_save_config(self):
        """Saves to the currently selected path."""
        try:
            self.config_mgr.save()
            QMessageBox.information(self, "Success", f"Saved to: {self.config_mgr.filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save: {str(e)}")

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

    def handle_view_schedule(self):
        """Fetches generated schedule and displays it as a spreadsheet."""
        schedule = self.imported_schedule
        if not schedule:
            schedule = [
                {'course_id': 'CMSC420', 'day': 'Mon', 'time': '09:00'},
                {'course_id': 'CMSC420', 'day': 'Wed', 'time': '09:00'},
                {'course_id': 'MATH101', 'day': 'Tue', 'time': '10:00'},
                {'course_id': 'CS202', 'day': 'Thu', 'time': '13:00'},
            ]

        spreadsheet = self.config_mgr.get_schedule_spreadsheet(schedule)

        msg = QMessageBox(self)
        msg.setWindowTitle("Weekly Schedule Spreadsheet")
        msg.setText(spreadsheet)

        mono_font = QFont("Courier New", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        msg.setFont(mono_font)

        msg.setStyleSheet("QLabel{min-width: 800px;}")
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

    #----------------------------------------------------------
    # Course management handlers (GUI)
    #----------------------------------------------------------

    def handle_add_course(self):
        """Add a new course via dialog and save to config."""
        self.course_manager.add_course_via_dialog(self)

    def handle_modify_course(self):
        """Modify an existing course via dialogs."""
        self.course_manager.modify_course_via_dialog(self)

    def handle_delete_course(self):
        """Delete an existing course via dialogs."""
        self.course_manager.delete_course_via_dialog(self)

    #----------------------------------------------------------
    # Schedule Viewer Functions
    #----------------------------------------------------------

    def open_schedule_viewer(self):
        if not self.schedules:
            QMessageBox.warning(
                self,
                "No schedules",
                "No schedules to view. Generate schedules or import a schedule first."
            )
            return

        self.viewer = QDialog(self)
        self.viewer.setWindowTitle("Schedule Viewer")
        self.viewer.resize(900, 500)
        layout = QVBoxLayout(self.viewer)
        self.schedule_display = QPlainTextEdit()
        self.schedule_display.setReadOnly(True)
        self.schedule_display.setFont(QFont("Courier New", 10))
        self.schedule_display.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0;")

        def refresh_display():
            self._refresh_schedule_display()

        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("Previous")
        next_btn = QPushButton("Next")
        prev_btn.clicked.connect(lambda: (self.show_prev_schedule(), refresh_display()))
        next_btn.clicked.connect(lambda: (self.show_next_schedule(), refresh_display()))
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        layout.addWidget(self.schedule_display)
        layout.addLayout(nav_layout)
        self._refresh_schedule_display()
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

