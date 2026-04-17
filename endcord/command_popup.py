# Copyright (C) 2025-2026 SparkLost
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

"""Pure helpers for the prompt-local slash-command popup."""

from dataclasses import dataclass

POPUP_MIN_WIDTH = 4
POPUP_MIN_NAME_WIDTH = 20
POPUP_MAX_NAME_WIDTH = 40
POPUP_MIN_DESC_WIDTH = 24
POPUP_MAX_DESC_WIDTH = 48


@dataclass(frozen=True)
class PopupLayout:
    """Geometry and formatted row metadata for the slash-command popup."""

    height: int
    width: int
    y: int
    x: int
    rows: list[tuple[str, str]]
    name_width: int
    desc_width: int


def split_completion_item(item):
    """Split a slash-command completion display string into name/description."""
    display = item[0]
    if " - " in display:
        return display.split(" - ", 1)
    return display, ""


def format_popup_column(text, width):
    """Pad or truncate popup column text to a fixed width."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[:width - 3] + "..."


def build_layout(items, chat_h, chat_w, chat_y, chat_x):
    """Return popup geometry and column sizing for the current chat area."""
    if not items or chat_h <= 0 or chat_w <= 2:
        return None

    rows = [split_completion_item(item) for item in items]
    max_name = max(len(name) for name, _ in rows)
    max_desc = max(len(desc) for _, desc in rows)
    max_popup_width = max(POPUP_MIN_WIDTH, chat_w - 2)

    if max_desc:
        max_name_width = min(max_name + 1, max(POPUP_MIN_NAME_WIDTH, min(max_popup_width // 2, POPUP_MAX_NAME_WIDTH)))
        max_desc_width = min(max_desc, max(POPUP_MIN_DESC_WIDTH, min(max_popup_width // 3, POPUP_MAX_DESC_WIDTH)))
    else:
        max_name_width = min(max_name + 1, max_popup_width - 2)
        max_desc_width = 0

    popup_width = min(max_name_width + max_desc_width + 2, max_popup_width)
    popup_width = max(POPUP_MIN_WIDTH, popup_width)
    name_width = min(max_name_width, max(1, popup_width - 2))
    desc_width = max(0, popup_width - name_width - 2)
    height = min(len(rows), chat_h)
    y = chat_y + chat_h - height
    return PopupLayout(height, popup_width, y, chat_x, rows, name_width, desc_width)


def clamp_scroll(scroll, active_index, win_size, total):
    """Keep the active row visible while only scrolling once it leaves view."""
    max_scroll = max(0, total - win_size)
    scroll = min(max(0, scroll), max_scroll)
    if active_index >= 0:
        if active_index < scroll:
            scroll = active_index
        elif active_index >= scroll + win_size:
            scroll = active_index - win_size + 1
    return min(max(0, scroll), max_scroll)
