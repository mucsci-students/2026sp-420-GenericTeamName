'''
    File: roon_gui.py
    Date: 3/1/2026
    Author: Chayse Altland
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
    """

    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self._config_data: Dict[str, Any] = {}

    # -----------------------------
    # Internal Helpers
    # -----------------------------

    def _ensure_config_loaded(self, parent: QWidget) -> bool:
        """
        Use the config file selected via the Change Config File button.
        """
        config_mgr = getattr(parent, "config_mgr", None)
        if config_mgr is None or not getattr(config_mgr, "filepath", None):
            QMessageBox.warning(
                parent,
                "No Config",
                "Please select a config file first using the Change Config File button."
            )
            return False
        try:
            config_mgr.load()
        except Exception as e:
            QMessageBox.critical(
                parent,
                "Config Error",
                f"Could not load config:\n{e}",
            )
            return False
        self.config_path = Path(config_mgr.filepath)
        self._config_data = config_mgr.data
        return True

    def _get_rooms_list(self) -> List[str]:
        cfg = self._config_data.setdefault("config", {})
        rooms = cfg.setdefault("rooms", [])
        if not isinstance(rooms, list):
            cfg["rooms"] = []
        return cfg["rooms"]

    def _save(self, parent: QWidget) -> None:
        if self.config_path is None:
            return
        try:
            self.config_path.write_text(
                json.dumps(self._config_data, indent=2),
                encoding="utf-8"
            )
        except OSError as e:
                QMessageBox.critical(
                    parent,
                    "Save failed",
                    f"Failed to save config:\n{e}",
                )
                return

        QMessageBox.information(
            parent,
            "Config saved",
            "Configuration saved.",
        )

    def _select_room(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
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

        index = rooms.index(item)
        return index, item

    # -----------------------------
    # Public CRUD Methods
    # -----------------------------

    def add_room_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
        self._save(parent)

    def modify_room_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
        self._save(parent)

    def delete_room_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
        self._save(parent)