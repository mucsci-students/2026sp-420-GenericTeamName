"""
test_themes.py
==============
Coverage tests for ``themes.themes`` utility functions.

:date: 04/25/2026
:author: Shane del Villar
:class: CMSC 420
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from themes.themes import (
    THEME_PRESETS,
    _apply_editor_panels_theme,
    apply_main_window_theme,
    darken,
    is_dark,
    lighten,
)


def _fake_main_window(theme_color: str = "#eef1f6") -> SimpleNamespace:
    mw = SimpleNamespace()
    mw.theme_color = theme_color
    mw.current_theme = "Light"
    mw.setStyleSheet = MagicMock()
    mw.theme_btn = MagicMock()
    mw.inspect_panel = MagicMock()
    mw.cfg_panel = MagicMock()
    mw.assistant_panel = MagicMock()
    mw.ai_chat_log = MagicMock()
    mw.ai_input = MagicMock()
    mw.detail_view = MagicMock()
    mw.inspect_caption = MagicMock()
    mw.ai_caption = MagicMock()
    mw.path_label = MagicMock()
    mw.counter_label = MagicMock()
    mw._update_path_label_text = MagicMock()
    return mw


def test_theme_presets_exposes_known_keys():
    assert "Light" in THEME_PRESETS
    assert "Dark" in THEME_PRESETS
    assert THEME_PRESETS["Light"].startswith("#")


def test_is_dark_detects_light_and_dark():
    assert is_dark("#000000") is True
    assert is_dark("#ffffff") is False


def test_darken_and_lighten_bounds():
    assert darken("#ffffff", 1.0) == "#000000"
    assert lighten("#000000", 1.0) == "#ffffff"


@patch("themes.themes.SchedulerStyles.editor_panels")
def test_apply_editor_panels_theme_no_ai_widgets_short_circuit(mock_editor):
    mw = SimpleNamespace()
    _apply_editor_panels_theme(mw, "#111", "#eee", "#222", "#888")
    mock_editor.assert_not_called()


@patch("themes.themes.SchedulerStyles.editor_panels")
def test_apply_editor_panels_theme_sets_all_widget_styles(mock_editor):
    mock_editor.return_value = ("chat-qss", "line-qss", "detail-qss")
    mw = _fake_main_window()

    _apply_editor_panels_theme(mw, "#111111", "#eeeeee", "#222222", "#999999")

    mw.ai_chat_log.setStyleSheet.assert_called_once_with("chat-qss")
    mw.ai_input.setStyleSheet.assert_called_once_with("line-qss")
    mw.detail_view.setStyleSheet.assert_called_once_with("detail-qss")
    mw.path_label.setStyleSheet.assert_called_once_with("color: #999999;")
    mw.counter_label.setStyleSheet.assert_called_once_with("color: #eeeeee;")


@patch("themes.themes._apply_editor_panels_theme")
@patch("themes.themes.SchedulerStyles.theme_corner_button", return_value="btn-qss")
@patch("themes.themes.SchedulerStyles.main_window", return_value="main-qss")
def test_apply_main_window_theme_light_path(mock_main, mock_corner, mock_editor_apply):
    mw = _fake_main_window("#eef1f6")

    apply_main_window_theme(mw)

    mw.setStyleSheet.assert_called_once_with("main-qss")
    mw.theme_btn.setStyleSheet.assert_called_once_with("btn-qss")
    mw.theme_btn.setText.assert_called_once_with("Light")
    mw.inspect_panel.set_color.assert_called_once()
    mw.cfg_panel.set_color.assert_called_once()
    mw.assistant_panel.set_color.assert_called_once()
    mw._update_path_label_text.assert_called_once()
    mock_editor_apply.assert_called_once()


@patch("themes.themes._apply_editor_panels_theme")
@patch("themes.themes.SchedulerStyles.theme_corner_button", return_value="btn-qss")
@patch("themes.themes.SchedulerStyles.main_window", return_value="main-qss")
def test_apply_main_window_theme_dark_without_update_path(
    mock_main, mock_corner, mock_editor_apply
):
    mw = _fake_main_window("#18181b")
    delattr(mw, "_update_path_label_text")

    apply_main_window_theme(mw)

    kwargs = mock_main.call_args.kwargs
    assert kwargs["theme_color"] == "#18181b"
    assert kwargs["text_color"] == "#f4f4f5"
    assert kwargs["table_bg"] == "#27272a"
    assert kwargs["primary"] == "#3b82f6"
