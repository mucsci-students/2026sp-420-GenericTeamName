'''
    File: main_window.py
    Date: 03/03/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: The main window of the GUI.
'''

from PyQt6.QtWidgets import QMainWindow, QSplitter, QMenu, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont
from .menu_widgets import ContentPanel
from .course_gui import CourseConfigManager
from .room_gui import RoomConfigManager
from config.config_mgr import ConfigManager
from .lab_gui import LabConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scheduler Program - GenericTeamName")
        self.resize(900, 600)

        # Initialize with a default
        self.config_mgr = ConfigManager("config/config.json")

        
        #Management helpers:
        #---------------------------------------------------------------------------
        self.course_manager = CourseConfigManager()
        self.room_manager = RoomConfigManager()
        self.lab_manager = LabConfigManager()
        
        #---------------------------------------------------------------------------
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

        self.left_panel = ContentPanel("Config Editor", "#ecf0f1")
        self.mid_panel = ContentPanel("Schedule Generator", "#ffffff")
        self.right_panel = ContentPanel("Schedule Viewer", "#f4f7f6")
        
        #----------------------------------------------------------
        #Left-Panel (Config Editor)
        #----------------------------------------------------------
        self.faculty_btn = QPushButton("Faculty")
        self.course_btn = QPushButton("Courses")
        self.room_btn = QPushButton("Rooms")
        self.lab_btn = QPushButton("Labs")
        self.change_path_btn = QPushButton("Change Config File")
        self.config_btn_layout.insertWidget(4, self.change_path_btn) #would like to look at this further. could reduce lines of code?
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
            #note: 
            # lambdas in here are placeholders.
            # plz replace with the correct functions.

        #-------------------------------------------
        #triggers for left panel (config editor)
        #faculty:
        add_faculty_ac.triggered.connect(lambda: print("Add Faculty clicked"))
        mod_faculty_ac.triggered.connect(lambda: print("Modify Faculty clicked"))
        del_faculty_ac.triggered.connect(lambda: print("Delete Faculty clicked"))
        ed_faculty_times_ac.triggered.connect(lambda: print("Edit Faculty Available Times clicked"))
        ed_faculty_pref_ac.triggered.connect(lambda: print("Edit Faculty Preferences clicked"))

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

        self.limit_btn.clicked.connect(lambda: print("Set Limit clicked"))
        self.optimize_btn.clicked.connect(lambda: print("Toggle Optimization clicked"))
        self.generate_sc_btn.clicked.connect(lambda: print("Generate Schedules clicked"))
        #-------------------------------------------
        #triggers for right panel (schedule viewer)

        self.view_sc_btn.clicked.connect(self.handle_view_schedule)
        self.export_sc_btn.clicked.connect(self.handle_export_schedule)
        self.import_sc_btn.clicked.connect(lambda: print("Import Schedules clicked"))

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
        # TODO: CHANGE THIS TO TAKE INPUT FROM SCHEDULE GEN
        mock_schedule = [
            {'course_id': 'CMSC420', 'day': 'Mon', 'time': '09:00'},
            {'course_id': 'CMSC420', 'day': 'Wed', 'time': '09:00'},
            {'course_id': 'MATH101', 'day': 'Tue', 'time': '10:00'},
            {'course_id': 'CS202', 'day': 'Thu', 'time': '13:00'},
        ]

        spreadsheet = self.config_mgr.get_schedule_spreadsheet(mock_schedule)

        msg = QMessageBox(self)
        msg.setWindowTitle("Weekly Schedule Spreadsheet")
        msg.setText(spreadsheet)

        mono_font = QFont("Courier New", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        msg.setFont(mono_font)

        msg.setStyleSheet("QLabel{min-width: 800px;}")
        msg.exec()

    def handle_export_schedule(self):
        """Triggers the CSV export via a file dialog."""
        # TODO: CHANGE THIS TO TAKE INPUT FROM SCHEDULE GEN
        mock_schedule = [
            {'course_id': 'CMSC420', 'day': 'Mon', 'time': '09:00'},
            {'course_id': 'CMSC420', 'day': 'Wed', 'time': '09:00'},
            {'course_id': 'MATH101', 'day': 'Tue', 'time': '10:00'},
        ]

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Schedule", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'

            success = self.config_mgr.export_schedule_to_csv(mock_schedule, file_path)

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


