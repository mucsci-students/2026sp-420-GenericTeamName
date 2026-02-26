'''
    File: main_window.py
    Date: 02/26/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: The main window of the GUI.
'''

from PyQt6.QtWidgets import QMainWindow, QSplitter, QMenu, QPushButton, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from .menu_widgets import ContentPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scheduler Program - GenericTeamName")
        self.resize(900, 600)

        #box-layout for buttons
        self.config_btn_layout = QVBoxLayout()
        self.sc_generator_layout = QVBoxLayout()
        self.sc_viewer_layout = QVBoxLayout()
        #splitter for panels
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_panel = ContentPanel("Config Editor", "#ecf0f1")
        self.mid_panel = ContentPanel("Schedule Generator", "#ffffff")
        self.right_panel = ContentPanel("Schedule Viewer", "#f4f7f6")

        #Left-Panel
        #----------------------------------------------------------
        self.faculty_btn = QPushButton("Faculty")
        self.course_btn = QPushButton("Courses")
        self.room_btn = QPushButton("Rooms")
        self.lab_btn = QPushButton("Labs")
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
        #Mid-Panel
        #----------------------------------------------------------

        self.limit_btn = QPushButton("Set Limit (# Of Schedules)")
        self.optimize_btn = QPushButton("Toggle Optimization")
        self.generate_sc_btn = QPushButton("Generate Schedules")

        self.sc_generator_layout.addWidget(self.limit_btn)
        self.sc_generator_layout.addWidget(self.optimize_btn)
        self.sc_generator_layout.addWidget(self.generate_sc_btn)
        #----------------------------------------------------------
        #Right-Panel
        #----------------------------------------------------------

        self.view_sc_btn = QPushButton("View Schedules")
        self.export_sc_btn = QPushButton("Export Schedules")
        self.import_sc_btn = QPushButton("Import Schedules")

        self.sc_viewer_layout.addWidget(self.view_sc_btn)
        self.sc_viewer_layout.addWidget(self.export_sc_btn)
        self.sc_viewer_layout.addWidget(self.import_sc_btn)

        #----------------------------------------------------------

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        #sizes in order of declarations above ^^
        self.splitter.setSizes([300, 300, 300])
        self.left_panel.layout.insertLayout(1, self.config_btn_layout)
        self.mid_panel.layout.insertLayout(1, self.sc_generator_layout)
        self.right_panel.layout.insertLayout(1, self.sc_viewer_layout)
        
        #container = QWidget()
        #master_layout = QVBoxLayout(container)
        #master_layout.addLayout(self.config_btn_layout)
        #self.left_panel.setLayout(self.config_btn_layout)
        #master_layout.addWidget(self.splitter)
        self.setCentralWidget(self.splitter)

        self.splitter.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.splitter.customContextMenuRequested.connect(self.show_context_menu)

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

        #menus:
        #-------------------------------------------
        #menus for left panel (config editor)
        faculty_menu = QMenu(self)
        courses_menu = QMenu(self)
        rooms_menu = QMenu(self)
        labs_menu = QMenu(self)
        view_sum_menu = QMenu(self)
        save_config_menu = QMenu(self)

        #menus for mid panel (schedule generator)
        limit_menu = QMenu(self)
        optimize_menu = QMenu(self)
        generate_sc_menu = QMenu(self)

        #menus for right panel (schedule viewer)
        view_sc_menu = QMenu(self)
        export_sc_menu = QMenu(self)
        import_sc_menu = QMenu(self)
        #-------------------------------------------

        #menu actions:
        #-------------------------------------------
        #actions for left panel (config editor)
        #faculty:
        add_faculty_ac = faculty_menu.addAction("Add Faculty")
        mod_faculty_ac = faculty_menu.addAction("Modify Faculty")
        del_faculty_ac = faculty_menu.addAction("Delete Faculty")
        ed_faculty_times_ac = faculty_menu.addAction("Edit Faculty Available Times")
        add_faculty_pref_ac = faculty_menu.addAction("Add Faculty Preferences")

        #courses:
        add_courses_ac = faculty_menu.addAction("Add Courses")
        mod_courses_ac = faculty_menu.addAction("Modify Courses")
        del_courses_ac = faculty_menu.addAction("Delete Courses")

        #rooms:
        add_rooms_ac = faculty_menu.addAction("Add Rooms")
        mod_rooms_ac = faculty_menu.addAction("Modify Rooms")
        del_rooms_ac = faculty_menu.addAction("Delete Rooms")

        #labs:
        add_labs_ac = faculty_menu.addAction("Add Labs")
        mod_labs_ac = faculty_menu.addAction("Modify Labs")
        del_labs_ac = faculty_menu.addAction("Delete Labs")



        #[MORE NEEDS TO BE FILLED IN ABOVE] ^^^

        #action triggers:
        #-------------------------------------------

        #note: 
        # lambdas in here are placeholders.
        # plz replace with the correct functions.

        add_faculty_ac.triggered.connect(lambda: print("Add Faculty clicked"))
        self.faculty_btn.setMenu(faculty_menu)
