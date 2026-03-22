"""
    File: main_window.py
    Date: 03/22/2026
    Author: Kyle Smith & Tyler Strohl
    Class: CMSC 420
    Description: Primary GUI controller for the Scheduler Pro system. 
    Handles event loops, theme switching, and data visualization.
"""

import random
import copy
import json
import csv
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QMenu, QPushButton, QVBoxLayout, 
    QHBoxLayout, QWidget, QFileDialog, QMessageBox, QTableWidget, 
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QMenuBar, 
    QStatusBar, QHeaderView, QPlainTextEdit, QAbstractItemView, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QPainter
from PyQt6.QtPrintSupport import QPrinter

from .menu_widgets import ContentPanel
from config.config_mgr import ConfigManager
from .course_gui import CourseConfigManager
from .room_gui import RoomConfigManager
from .faculty_gui import FacultyManager
from .generator_gui import GenConfigManager
from .lab_gui import LabConfigManager

class MainWindow(QMainWindow):
    """
    Main application window for Scheduler Pro.

    This class manages the lifecycle of the GUI, coordinates between 
    different configuration managers, and provides the interface for 
    generating and exporting academic schedules.

    Attributes:
        is_dark_mode (bool): Tracks the current theme state.
        schedules (list): Stores generated schedule result sets.
        history_stack (list): Stores previous states for Undo functionality.
        view_mode (str): Current grid perspective (DAY, ROOM, FACULTY, or LAB).
    """

    def __init__(self):
        """Initializes the MainWindow, managers, and UI components."""
        super().__init__()
        self.setWindowTitle("Scheduler Pro v4.3 - GenericTeamName")
        self.resize(1400, 900) 

        # State Initialization
        self.is_dark_mode = True
        self.schedules = []
        self.history_stack = [] 
        self.view_mode = "DAY" 
        self.color_cache = {}

        # Core Logic Managers
        self.config_mgr = ConfigManager("config/config.json")
        try: 
            self.config_mgr.load()
        except Exception: 
            pass

        self.course_manager = CourseConfigManager()
        self.room_manager = RoomConfigManager()
        self.faculty_manager = FacultyManager()
        self.gen_manager = GenConfigManager()
        self.lab_manager = LabConfigManager()
        
        self.init_ui()
        self.create_menus()
        self.apply_global_theme()
        self.render_config_tree()

    def init_ui(self):
        """Constructs the primary layout including the Explorer, Grid, and Inspector."""
        self.setStatusBar(QStatusBar())
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Data Explorer Panel
        self.left_panel = ContentPanel("Data Explorer", "#1a1a1a")
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search items...")
        self.search_bar.textChanged.connect(self.filter_tree)
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabel("Configuration Hierarchy")
        self.config_tree.itemClicked.connect(self.handle_tree_selection)
        self.left_panel.layout.addWidget(self.search_bar)
        self.left_panel.layout.addWidget(self.config_tree)

        # Weekly Schedule Grid Panel
        self.mid_panel = ContentPanel("Schedule Grid", "#000000")
        grid_ctrl = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.undo_move)
        self.undo_btn.setEnabled(False)
        
        self.view_btn = QPushButton("View Mode: Day")
        self.view_menu = QMenu(self)
        for m in ["DAY", "ROOM", "FACULTY", "LAB"]:
            self.view_menu.addAction(f"{m.title()} View").triggered.connect(
                lambda chk, mode=m: self.set_view_mode(mode)
            )
        self.view_btn.setMenu(self.view_menu)
        
        self.theme_btn = QPushButton("Switch Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        grid_ctrl.addWidget(self.undo_btn)
        grid_ctrl.addWidget(self.view_btn)
        grid_ctrl.addWidget(self.theme_btn)
        grid_ctrl.addStretch()
        
        self.sched_table = QTableWidget()
        self.sched_table.model().dataChanged.connect(self.handle_manual_move)
        
        self.mid_panel.layout.addLayout(grid_ctrl)
        self.mid_panel.layout.addWidget(self.sched_table)

        # Object Inspector Panel
        self.right_panel = ContentPanel("Inspector & Limits", "#1a1a1a")
        self.detail_view = QPlainTextEdit()
        self.save_cfg_btn = QPushButton("Apply JSON Changes")
        self.save_cfg_btn.clicked.connect(self.save_inspector_changes)
        self.right_panel.layout.addWidget(self.detail_view)
        self.right_panel.layout.addWidget(self.save_cfg_btn)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([300, 800, 300])
        self.setCentralWidget(self.splitter)

    def open_manager_gui(self, manager):
        """
        Safely opens a manager's sub-window.

        Args:
            manager: An instance of a ConfigManager (Course, Room, or Faculty).
        """
        if hasattr(manager, 'show'): 
            manager.show()
        elif hasattr(manager, 'gui'): 
            manager.gui.show()

    def run_generation_and_render(self):
        """Executes the scheduling algorithm and updates the table view."""
        self.gen_manager.run_scheduler(self)
        if self.schedules:
            self.render_schedule_table(self.schedules[0])
            self.statusBar().showMessage("Generation Complete", 3000)

    def render_schedule_table(self, schedule):
        """
        Populates the QTableWidget based on the current view mode and schedule data.

        Args:
            schedule (list): A list of dictionaries representing scheduled courses.
        """
        self.sched_table.blockSignals(True)
        self.sched_table.setRowCount(0)
        
        if not schedule:
            self.sched_table.setColumnCount(0)
            self.sched_table.blockSignals(False)
            return

        slots = sorted(list(set(i['time'] for i in schedule)))
        self.sched_table.setRowCount(len(slots))
        
        view_map = {
            "DAY": ("day", ["Mon", "Tue", "Wed", "Thu", "Fri"]),
            "ROOM": ("room", sorted(list(set(i.get('room', 'N/A') for i in schedule)))),
            "FACULTY": ("faculty", sorted(list(set(i.get('faculty', 'TBD') for i in schedule)))),
            "LAB": ("lab", sorted(list(set(i.get('lab', 'None') for i in schedule))))
        }
        key, cols = view_map.get(self.view_mode, view_map["DAY"])
        
        self.sched_table.setColumnCount(len(cols) + 1)
        self.sched_table.setHorizontalHeaderLabels(["Time"] + cols)
        
        for row, t in enumerate(slots):
            self.sched_table.setItem(row, 0, QTableWidgetItem(t))
            for entry in schedule:
                if entry['time'] == t:
                    try:
                        col_val = entry.get(key)
                        if col_val in cols:
                            c_idx = cols.index(col_val) + 1
                            cell = QTableWidgetItem(f"{entry['course_id']}\n{entry.get('faculty','TBD')}")
                            cell.setBackground(QBrush(self.get_color_for_id(entry.get('faculty'))))
                            cell.setData(Qt.ItemDataRole.UserRole, entry)
                            self.sched_table.setItem(row, c_idx, cell)
                    except (ValueError, KeyError): 
                        continue

        self.sched_table.resizeRowsToContents()
        self.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sched_table.blockSignals(False)

    def apply_global_theme(self):
        """Updates the application stylesheet to handle light/dark mode transitions."""
        if self.is_dark_mode:
            bg, panel, text, border = "#1f1f24", "#1a1a1a", "#ffffff", "#444444"
        else:
            bg, panel, text, border = "#f0f2f5", "#ffffff", "#1a1a1a", "#bbbbbb"

        self.left_panel.update_theme(panel, self.is_dark_mode)
        self.mid_panel.update_theme(panel if self.is_dark_mode else "#ffffff", self.is_dark_mode)
        self.right_panel.update_theme(panel, self.is_dark_mode)

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {bg}; }}
            QMenuBar {{ background-color: {panel}; color: {text}; border-bottom: 1px solid {border}; }}
            QTableWidget, QTreeWidget, QPlainTextEdit, QLineEdit {{ 
                background-color: {panel}; color: {text}; border: 1px solid {border}; 
            }}
            QTreeWidget::viewport, QTableWidget::viewport {{ background-color: transparent; }}
            QHeaderView::section {{ background-color: {panel}; color: {text}; border: 1px solid {border}; }}
            QPushButton {{ background-color: {panel}; color: {text}; border: 1px solid {border}; padding: 4px 12px; }}
            QPushButton:hover {{ background-color: {border}; }}
        """)

    def create_menus(self):
        """Defines the menu bar structure and connects actions to functions."""
        menubar = self.menuBar()
        menubar.clear()
        
        file = menubar.addMenu("&File")
        file.addAction("Import Config").triggered.connect(self.import_config)
        file.addAction("Save Config").triggered.connect(self.save_config_to_file)
        file.addSeparator()
        file.addAction("Export CSV").triggered.connect(self.handle_export_schedule)
        file.addAction("Export PDF").triggered.connect(self.export_to_pdf)

        cfg = menubar.addMenu("&Configure")
        cfg.addAction("Manage Courses").triggered.connect(lambda: self.open_manager_gui(self.course_manager))
        cfg.addAction("Manage Rooms").triggered.connect(lambda: self.open_manager_gui(self.room_manager))
        cfg.addAction("Manage Faculty").triggered.connect(lambda: self.open_manager_gui(self.faculty_manager))

        build = menubar.addMenu("&Build")
        build.addAction("Run Generator").triggered.connect(self.run_generation_and_render)
        build.addAction("Clear Results").triggered.connect(self.confirm_clear_schedule)

    def get_color_for_id(self, uid):
        """Retrieves or generates a unique QColor for a given faculty/item ID."""
        if uid not in self.color_cache:
            self.color_cache[uid] = QColor.fromHsvF(random.random(), 0.3, 0.9 if self.is_dark_mode else 0.8)
        return self.color_cache[uid]

    def render_config_tree(self):
        """Recursively renders the configuration JSON into the Explorer tree."""
        self.config_tree.clear()
        data = self.config_mgr.data if hasattr(self.config_mgr, 'data') else {}
        for cat, content in data.items():
            parent = QTreeWidgetItem(self.config_tree, [str(cat).upper()])
            parent.setData(0, Qt.ItemDataRole.UserRole, content)
            if isinstance(content, list):
                for item in content:
                    name = item.get('course_id') or item.get('name') or "Item" if isinstance(item, dict) else str(item)
                    child = QTreeWidgetItem(parent, [str(name)])
                    child.setData(0, Qt.ItemDataRole.UserRole, item)
        self.config_tree.expandAll()

    def handle_tree_selection(self, item):
        """Displays the selected item's raw JSON in the Inspector."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is not None: 
            self.detail_view.setPlainText(json.dumps(data, indent=4))

    def filter_tree(self, query):
        """Filters tree items based on the search bar input."""
        q = query.lower()
        for i in range(self.config_tree.topLevelItemCount()):
            parent = self.config_tree.topLevelItem(i)
            hit = False
            for j in range(parent.childCount()):
                child = parent.child(j)
                match = q in child.text(0).lower()
                child.setHidden(not match)
                if match: hit = True
            parent.setHidden(not hit and q != "")

    # Boilerplate / Navigation handlers
    def import_config(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open JSON", "", "*.json")
        if p:
            with open(p, 'r') as f: self.config_mgr.data = json.load(f)
            self.render_config_tree()

    def save_config_to_file(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "*.json")
        if p:
            with open(p, 'w') as f: json.dump(self.config_mgr.data, f, indent=4)

    def set_view_mode(self, m):
        self.view_mode = m
        self.view_btn.setText(f"View Mode: {m.title()}")
        if self.schedules: self.render_schedule_table(self.schedules[0])

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_global_theme()
        if self.schedules: self.render_schedule_table(self.schedules[0])

    def handle_export_schedule(self):
        if not self.schedules: return
        p, _ = QFileDialog.getSaveFileName(self, "CSV", "", "*.csv")
        if p:
            with open(p, 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=self.schedules[0][0].keys())
                w.writeheader(); w.writerows(self.schedules[0])

    def export_to_pdf(self):
        p, _ = QFileDialog.getSaveFileName(self, "PDF", "", "*.pdf")
        if p:
            pr = QPrinter(QPrinter.PrinterMode.HighResolution)
            pr.setOutputFileName(p)
            painter = QPainter(pr)
            self.sched_table.render(painter)
            painter.end()

    def confirm_clear_schedule(self): 
        if QMessageBox.question(self, "Clear", "Clear results?") == QMessageBox.StandardButton.Yes:
            self.schedules = []; self.render_schedule_table([])

    def undo_move(self):
        if self.history_stack:
            self.schedules[0] = self.history_stack.pop()
            self.render_schedule_table(self.schedules[0])
            self.undo_btn.setEnabled(len(self.history_stack) > 0)

    def handle_manual_move(self):
        if self.schedules:
            self.history_stack.append(copy.deepcopy(self.schedules[0]))
            self.undo_btn.setEnabled(True)

    def save_inspector_changes(self):
        try:
            it = self.config_tree.currentItem()
            if not it: return
            self.config_mgr.data[it.text(0).upper()] = json.loads(self.detail_view.toPlainText())
            QMessageBox.information(self, "Success", "Configuration applied.")
        except: QMessageBox.critical(self, "Error", "Invalid JSON.")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.sched_table.columnCount() > 0:
            self.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
