'''
    File: lab_gui.py
    Date: 04/16/2026
    Author: Mohamed Mussa & Tyler Strohl
    Class: CMSC 420
    Description: Lab management dialogs and helpers for the GUI.
'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QWidget,
)


class LabConfigManager:
    """
    Helper to load, modify, and save lab entries in a scheduler config JSON file.
    Labs are stored as a list of strings:
        "labs": ["Linux", "Mac", ...]

    This class implements the following design patterns:
        -Dependency Injection
        -Delegation
        -Model-View-Controller (controller)
        -Facade
        -Template Logic
    """

    def __init__(self, config_mgr):
        self.config_mgr = config_mgr

    # -----------------------------
    # Internal Helpers
    # -----------------------------

    def _get_labs_list(self) -> List[str]:
        """Retrieve the list of labs from the config file."""
        return self.config_mgr.data["config"]["labs"]

    def _select_lab(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
        """Retrieves a specific lab from list of labs."""
        labs = self._get_labs_list()

        if not labs:
            QMessageBox.information(parent, "No labs", "No labs found in the config.")
            return None, None

        item, ok = QInputDialog.getItem(
            parent,
            "Select Lab",
            "Lab:",
            labs,
            0,
            False,
        )

        if not ok or not item:
            return None, None

        return labs.index(item), item

    # -----------------------------
    # Public CRUD Methods
    # -----------------------------

    def add_lab_via_dialog(self, parent: QWidget) -> None:
        """Add a new lab to config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        text, ok = QInputDialog.getText(
            parent,
            "Add Lab",
            "Lab name:"
        )

        if not ok or not text.strip():
            return

        labs = self._get_labs_list()
        labs.append(text.strip())
        self.config_mgr.save(parent)

    def modify_lab_via_dialog(self, parent: QWidget) -> None:
        """Modify a lab in the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        index, existing = self._select_lab(parent)
        if index is None or existing is None:
            return

        text, ok = QInputDialog.getText(
            parent,
            "Modify Lab",
            "Lab name:",
            text=existing
        )

        if not ok or not text.strip():
            return

        labs = self._get_labs_list()
        labs[index] = text.strip()
        self.config_mgr.save(parent)

    def delete_lab_via_dialog(self, parent: QWidget) -> None:
        """Remove a lab from the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        index, existing = self._select_lab(parent)
        if index is None or existing is None:
            return

        reply = QMessageBox.question(
            parent,
            "Confirm delete",
            f"Delete lab '{existing}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        labs = self._get_labs_list()
        del labs[index]
        self.config_mgr.save(parent)