"""
themes.py
================
Main window theming: color utilities and QSS application via SchedulerStyles.
:date: 04/24/2026
:author: Shane del Villar
:class: CMSC 420
"""

from __future__ import annotations

from typing import Any

from gui.ui_styles import SchedulerStyles

# Window chrome (panels use slightly elevated surfaces in ContentPanel)
THEME_PRESETS: dict[str, str] = {
    "Light": "#eef1f6",
    "Dark": "#18181b",
    "Autumn": "#8a5a44",
    "Crimson": "#8b2e3c",
    "Marathon": "#c2fe0b",
    "Summer": "#f4c95d",
    "Spring": "#98c379",
    "Winter": "#cfddeb",
    "Ocean": "#1f6f8b",
    "Land": "#6b8f71",
    "Sky": "#7fb7e6",
}


def is_dark(hex_color: str) -> bool:
    """Return True if color is dark (use light text)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5


def darken(hex_color: str, amount: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = max(0, int(int(hex_color[0:2], 16) * (1 - amount)))
    g = max(0, int(int(hex_color[2:4], 16) * (1 - amount)))
    b = max(0, int(int(hex_color[4:6], 16) * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten(hex_color: str, amount: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = min(255, int(int(hex_color[0:2], 16) + 255 * amount))
    g = min(255, int(int(hex_color[2:4], 16) + 255 * amount))
    b = min(255, int(int(hex_color[4:6], 16) + 255 * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def _apply_editor_panels_theme(
    mw: Any,
    surface: str,
    fg: str,
    border: str,
    muted: str,
) -> None:
    if not hasattr(mw, "ai_chat_log"):
        return
    sheet, line_sheet, detail_sheet = SchedulerStyles.editor_panels(
        surface=surface, fg=fg, border=border
    )
    mw.ai_chat_log.setStyleSheet(sheet)
    mw.ai_input.setStyleSheet(line_sheet)
    mw.detail_view.setStyleSheet(detail_sheet)
    cap = f"color: {muted}; padding: 0 2px;"
    mw.inspect_caption.setStyleSheet(cap)
    mw.ai_caption.setStyleSheet(cap)
    mw.path_label.setStyleSheet(f"color: {muted};")
    mw.counter_label.setStyleSheet(f"color: {fg};")


def apply_main_window_theme(mw: Any) -> None:
    """
    Apply palette derived from ``mw.theme_color`` and refresh panel chrome + editor QSS.
    Expects: theme_color, current_theme, theme_btn, inspect/cfg/assistant panels, paths used by _update_path_label_text.
    """
    dark = is_dark(mw.theme_color)
    text_color = "#f4f4f5" if dark else "#1e293b"
    muted = "#a1a1aa" if dark else "#64748b"
    btn_bg = darken(mw.theme_color, 0.12) if dark else lighten(mw.theme_color, 0.12)
    btn_hover = darken(mw.theme_color, 0.06) if dark else lighten(mw.theme_color, 0.06)
    btn_disabled = darken(mw.theme_color, 0.22) if dark else lighten(mw.theme_color, 0.18)
    btn_border = lighten(mw.theme_color, 0.2) if dark else darken(mw.theme_color, 0.14)
    panel_border = lighten(mw.theme_color, 0.14) if dark else darken(mw.theme_color, 0.1)
    splitter_handle = "#3f3f46" if dark else "#d4d4d8"
    table_bg = "#27272a" if dark else "#ffffff"
    table_alt = "#2e2e33" if dark else "#f8fafc"
    header_bg = "#3f3f46" if dark else "#f1f5f9"
    grid = "#52525b" if dark else "#e2e8f0"
    primary = "#2563eb" if not dark else "#3b82f6"
    primary_hover = "#1d4ed8" if not dark else "#2563eb"

    mw.setStyleSheet(
        SchedulerStyles.main_window(
            theme_color=mw.theme_color,
            text_color=text_color,
            btn_bg=btn_bg,
            btn_hover=btn_hover,
            btn_disabled=btn_disabled,
            btn_border=btn_border,
            panel_border=panel_border,
            splitter_handle=splitter_handle,
            table_bg=table_bg,
            table_alt=table_alt,
            header_bg=header_bg,
            grid=grid,
            primary=primary,
            primary_hover=primary_hover,
        )
    )
    mw.theme_btn.setStyleSheet(
        SchedulerStyles.theme_corner_button(
            btn_bg=btn_bg, text_color=text_color, btn_border=btn_border
        )
    )
    mw.theme_btn.setText(f"{mw.current_theme} ▾")
    for panel in (mw.inspect_panel, mw.cfg_panel, mw.assistant_panel):
        panel.set_color(mw.theme_color, panel_border)
    _apply_editor_panels_theme(mw, table_bg, text_color, btn_border, muted)
    if hasattr(mw, "_update_path_label_text"):
        mw._update_path_label_text()
