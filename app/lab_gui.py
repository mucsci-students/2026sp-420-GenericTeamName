'''
    File: lab_gui.py
    Date: 3/3/2026
    Author: Mohamed Mussa
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
        "labs": ["Roddy Lab A", "Roddy Lab B", ...]
    """

    def __init__(self) -> None:
        self.config_path: Optional[Path] = None
        self._config_data: Dict[str, Any] = {}

    # -----------------------------
    # Internal Helpers
    # -----------------------------

    def _ensure_config_loaded(self, parent: QWidget) -> bool:
        """
        Ensure a config file is loaded.
        If none is loaded yet, prompt the user to choose one.
        """
        if self.config_path is None:
            filename, _ = QFileDialog.getOpenFileName(
                parent,
                "Select Scheduler Config JSON",
                "",
                "JSON Files (*.json);;All Files (*)",
            )
            if not filename:
                return False
            self.config_path = Path(filename)

        if not self._config_data:
            try:
                text = self.config_path.read_text(encoding="utf-8")
                self._config_data = json.loads(text)
            except FileNotFoundError:
                QMessageBox.critical(
                    parent,
                    "Config not found",
                    f"Config file not found:\n{self.config_path}",
                )
                self.config_path = None
                self._config_data = {}
                return False
            except json.JSONDecodeError as e:
                QMessageBox.critical(
                    parent,
                    "Invalid JSON",
                    f"Failed to parse JSON:\n{e}",
                )
                self.config_path = None
                self._config_data = {}
                return False

        return True

    def _get_labs_list(self) -> List[str]:
        cfg = self._config_data.setdefault("config", {})
        labs = cfg.setdefault("labs", [])
        if not isinstance(labs, list):
            cfg["labs"] = []
        return cfg["labs"]

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
            f"Configuration saved to:\n{self.config_path}",
        )

    def _select_lab(self, parent: QWidget) -> Tuple[Optional[int], Optional[str]]:
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

        index = labs.index(item)
        return index, item

    # -----------------------------
    # Public CRUD Methods
    # -----------------------------

    def add_lab_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
        self._save(parent)

    def modify_lab_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
        self._save(parent)

    def delete_lab_via_dialog(self, parent: QWidget) -> None:
        if not self._ensure_config_loaded(parent):
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
        self._save(parent)