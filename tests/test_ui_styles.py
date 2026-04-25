"""
test_ui_styles.py
=================
Coverage tests for ``gui.ui_styles`` helpers and QSS factories.

:date: 04/25/2026
:author: Shane del Villar
:class: CMSC 420
"""

from __future__ import annotations

from unittest.mock import MagicMock

from gui.ui_styles import SchedulerStyles


def test_high_contrast_modal_form_contains_core_rules():
    qss = SchedulerStyles.high_contrast_modal_form()
    assert "QDialog" in qss
    assert "QDialogButtonBox QPushButton:pressed" in qss
    assert qss.startswith("QDialog")


def test_apply_high_contrast_shell_sets_dialog_inner_and_viewport_styles():
    dialog = MagicMock()
    inner = MagicMock()
    scroll = MagicMock()
    viewport = MagicMock()
    scroll.viewport.return_value = viewport

    SchedulerStyles.apply_high_contrast_shell(dialog, inner, scroll)

    dialog.setStyleSheet.assert_called_once()
    inner.setStyleSheet.assert_called_once_with("background-color: #ffffff;")
    viewport.setStyleSheet.assert_called_once_with("background-color: #ffffff;")


def test_apply_high_contrast_dialog_flat_sets_style():
    dialog = MagicMock()
    SchedulerStyles.apply_high_contrast_dialog_flat(dialog)
    dialog.setStyleSheet.assert_called_once()


def test_main_window_qss_embeds_dynamic_colors():
    qss = SchedulerStyles.main_window(
        theme_color="#111111",
        text_color="#eeeeee",
        btn_bg="#222222",
        btn_hover="#333333",
        btn_disabled="#444444",
        btn_border="#555555",
        panel_border="#666666",
        splitter_handle="#777777",
        table_bg="#888888",
        table_alt="#999999",
        header_bg="#aaaaaa",
        grid="#bbbbbb",
        primary="#123456",
        primary_hover="#654321",
    )
    assert "QMainWindow { background-color: #111111; }" in qss
    assert "QPushButton#primaryButton" in qss
    assert "#654321" in qss


def test_theme_corner_button_contains_all_tokens():
    qss = SchedulerStyles.theme_corner_button(
        btn_bg="#111111", text_color="#222222", btn_border="#333333"
    )
    assert "background-color: #111111" in qss
    assert "color: #222222" in qss
    assert "border: 1px solid #333333" in qss


def test_editor_panels_returns_three_distinct_styles():
    chat_sheet, line_sheet, detail_sheet = SchedulerStyles.editor_panels(
        surface="#111111", fg="#efefef", border="#333333"
    )
    assert "QPlainTextEdit, QLineEdit" in chat_sheet
    assert "QLineEdit {" in line_sheet
    assert "font-family: Consolas" in detail_sheet
