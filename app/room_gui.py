'''
    File: roon_gui.py
    Date: 04/16/2026
    Author: Chayse Altland & Tyler Strohl
    Class: CMSC 420
    Description: Room management dialogs and helpers for the GUI.
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


class RoomConfigManager:
    """
    Helper to load, modify, and save room entries in a scheduler config JSON file.
    Rooms are stored as a list of strings:
        "rooms": ["Roddy 140", "Roddy 147", ...]

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

    def _get_rooms_list(self) -> List[str]:
        """Retrieve the list of rooms from the config file."""
        return self.config_mgr.data["config"]["rooms"]

    def _select_room(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
        """Retrieves a specific room from list of rooms."""
        rooms = self._get_rooms_list()

        if not rooms:
            QMessageBox.information(parent, "No rooms", "No rooms found in the config.")
            return None, None

        item, ok = QInputDialog.getItem(
            parent,
            "Select Room",
            "Room:",
            rooms,
            0,
            False,
        )

        if not ok or not item:
            return None, None

        return rooms.index(item), item

    # -----------------------------
    # Public CRUD Methods
    # -----------------------------

    def add_room_via_dialog(self, parent: QWidget) -> None:
        """Add a new room to config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        text, ok = QInputDialog.getText(
            parent,
            "Add Room",
            "Room name:"
        )

        if not ok or not text.strip():
            return

        rooms = self._get_rooms_list()
        rooms.append(text.strip())
        self.config_mgr.save(parent)

    def modify_room_via_dialog(self, parent: QWidget) -> None:
        """Modify a room in the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        index, existing = self._select_room(parent)
        if index is None or existing is None:
            return

        text, ok = QInputDialog.getText(
            parent,
            "Modify Room",
            "Room name:",
            text=existing
        )

        if not ok or not text.strip():
            return

        rooms = self._get_rooms_list()
        rooms[index] = text.strip()
        self.config_mgr.save(parent)

    def delete_room_via_dialog(self, parent: QWidget) -> None:
        """Remove a room from the config file."""
        if not self.config_mgr.data:
            QMessageBox.warning(parent, "No Config", "Please load a config first.")
            return

        index, existing = self._select_room(parent)
        if index is None or existing is None:
            return

        reply = QMessageBox.question(
            parent,
            "Confirm delete",
            f"Delete room '{existing}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        rooms = self._get_rooms_list()
        del rooms[index]
        self.config_mgr.save(parent)