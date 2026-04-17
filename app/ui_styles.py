"""
   File: ui_styles.py
   Date: 04/17/2026
   Author: Shane del Villar
   Class: CMSC 420
   Description: Central Qt stylesheets for the scheduler application.
"""

from __future__ import annotations

from typing import Tuple

from PyQt6.QtWidgets import QDialog, QScrollArea, QWidget


class SchedulerStyles:
    """Factory for application QSS strings and small helpers."""

    # Shared high-contrast modal (course/faculty forms) — white surface, black text.
    _HIGH_CONTRAST_MODAL = """
QDialog {
    background-color: #ffffff;
    color: #000000;
}
QScrollArea {
    background-color: #ffffff;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #ffffff;
}
QLabel {
    color: #000000;
    background-color: transparent;
}
QGroupBox {
    color: #000000;
    background-color: #ffffff;
    border: 2px solid #000000;
    border-radius: 6px;
    margin-top: 16px;
    padding-top: 14px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    color: #000000;
    background-color: #ffffff;
}
QListWidget {
    background-color: #ffffff;
    color: #000000;
    border: 2px solid #000000;
    border-radius: 4px;
    outline: none;
}
QListWidget::item {
    color: #000000;
    padding: 4px;
}
QListWidget::item:selected {
    background-color: #000000;
    color: #ffffff;
}
QLineEdit, QSpinBox {
    background-color: #ffffff;
    color: #000000;
    border: 2px solid #000000;
    border-radius: 4px;
    padding: 6px 8px;
    selection-background-color: #000000;
    selection-color: #ffffff;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #f0f0f0;
    border: 1px solid #000000;
    width: 18px;
}
QDialogButtonBox QPushButton {
    background-color: #ffffff;
    color: #000000;
    border: 2px solid #000000;
    border-radius: 4px;
    padding: 8px 18px;
    font-weight: 600;
    min-width: 80px;
}
QDialogButtonBox QPushButton:hover {
    background-color: #f0f0f0;
}
QDialogButtonBox QPushButton:pressed {
    background-color: #000000;
    color: #ffffff;
}
"""

    @classmethod
    def high_contrast_modal_form(cls) -> str:
        """Stylesheet for course/faculty detail dialogs (independent of main theme)."""
        return cls._HIGH_CONTRAST_MODAL.strip()

    @classmethod
    def apply_high_contrast_shell(
        cls,
        dialog: QDialog,
        inner: QWidget,
        scroll: QScrollArea,
    ) -> None:
        """Apply modal form QSS plus white scroll viewport/inner backgrounds."""
        dialog.setStyleSheet(cls.high_contrast_modal_form())
        inner.setStyleSheet("background-color: #ffffff;")
        scroll.viewport().setStyleSheet("background-color: #ffffff;")

    @classmethod
    def main_window(
        cls,
        *,
        theme_color: str,
        text_color: str,
        btn_bg: str,
        btn_hover: str,
        btn_disabled: str,
        btn_border: str,
        panel_border: str,
        splitter_handle: str,
        table_bg: str,
        table_alt: str,
        header_bg: str,
        grid: str,
        primary: str,
        primary_hover: str,
    ) -> str:
        """Full QMainWindow + global widget styles (menus, toolbar, tables, buttons)."""
        return f"""
            QMainWindow {{ background-color: {theme_color}; }}
            QWidget {{ color: {text_color}; font-family: "Segoe UI", "SF Pro Text", sans-serif; }}
            QMenuBar {{
                background-color: {theme_color};
                border-bottom: 1px solid {panel_border};
                padding: 4px 2px;
                spacing: 8px;
            }}
            QMenuBar::item {{ padding: 6px 12px; border-radius: 6px; }}
            QMenuBar::item:selected {{ background-color: {btn_hover}; }}
            QToolBar {{
                background-color: {theme_color};
                border: none;
                border-bottom: 1px solid {panel_border};
                padding: 6px 8px;
                spacing: 10px;
            }}
            QToolButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {btn_border};
                border-radius: 8px;
                padding: 6px 12px;
                margin: 2px;
                font-weight: 500;
            }}
            QToolButton:hover {{ background-color: {btn_hover}; }}
            QMenu {{ background-color: {table_bg}; border: 1px solid {btn_border}; padding: 4px; }}
            QMenu::item {{ padding: 8px 28px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {btn_hover}; }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid {btn_border};
                border-radius: 8px;
                padding: 8px 14px;
                min-height: 22px;
            }}
            QPushButton:hover {{ background-color: {btn_hover}; }}
            QPushButton:disabled {{ background-color: {btn_disabled}; color: #888888; }}
            QPushButton#primaryButton {{
                background-color: {primary};
                color: #ffffff;
                border: 1px solid {primary};
                font-weight: 600;
            }}
            QPushButton#primaryButton:hover {{ background-color: {primary_hover}; border-color: {primary_hover}; }}
            QSplitter::handle {{
                background-color: {splitter_handle};
            }}
            QTableWidget {{
                background-color: {table_bg};
                alternate-background-color: {table_alt};
                gridline-color: {grid};
                border: none;
                border-radius: 8px;
            }}
            QTableCornerButton::section {{ background-color: {header_bg}; }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {text_color};
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid {grid};
                font-weight: 600;
            }}
            QTableWidget::item:selected {{
                background-color: {primary};
                color: #ffffff;
            }}
            """

    @classmethod
    def theme_corner_button(
        cls,
        *,
        btn_bg: str,
        text_color: str,
        btn_border: str,
    ) -> str:
        return (
            f"background-color: {btn_bg}; color: {text_color}; "
            f"border: 1px solid {btn_border}; border-radius: 8px; padding: 6px 12px; font-weight: 600;"
        )

    @classmethod
    def editor_panels(
        cls,
        *,
        surface: str,
        fg: str,
        border: str,
    ) -> Tuple[str, str, str]:
        """Returns (chat_plaintext_and_lineedit, lineedit_only, detail_monospace)."""
        chat_sheet = (
            f"QPlainTextEdit, QLineEdit {{ background-color: {surface}; color: {fg}; "
            f"border: 1px solid {border}; border-radius: 8px; padding: 8px; selection-background-color: #2563eb; }}"
        )
        line_sheet = (
            f"QLineEdit {{ background-color: {surface}; color: {fg}; "
            f"border: 1px solid {border}; border-radius: 8px; padding: 8px; selection-background-color: #2563eb; }}"
        )
        detail_sheet = (
            f"QPlainTextEdit {{ background-color: {surface}; color: {fg}; "
            f"border: 1px solid {border}; border-radius: 8px; padding: 8px; selection-background-color: #2563eb; "
            f"font-family: Consolas, 'Cascadia Mono', 'SF Mono', Menlo, monospace; font-size: 11px; }}"
        )
        return chat_sheet, line_sheet, detail_sheet
