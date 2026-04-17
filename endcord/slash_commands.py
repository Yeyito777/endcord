# Copyright (C) 2025-2026 SparkLost
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

"""Live slash-command helpers for the Endcord prompt.

This module powers the new Exocortex-style local command UX:
- direct `/command` entry in the main prompt
- live autocomplete suggestions
- light inline highlighting for recognized commands / args
- submit-time routing to the existing local command executor

It intentionally reuses the archived legacy command corpus so Endcord keeps the
same client-side capabilities while the UI is rebuilt around prompt-first slash
commands instead of the deprecated command palette.
"""

import re

from endcord import discord, parser, search
from endcord.assist_data import COMMAND_ASSISTS

HELP_COMMAND = ("help - show available local slash commands", "help")
BASE_COMMAND_ASSISTS = (HELP_COMMAND,) + tuple(COMMAND_ASSISTS)
KNOWN_COMMANDS = frozenset(command for _, command in BASE_COMMAND_ASSISTS)
STATUS_OPTIONS = ("online", "idle", "dnd", "invisible")
CANCEL_OPTIONS = ("download", "upload", "attachment")
RECORD_OPTIONS = ("cancel", )
COLLAPSE_ALL_EXCEPT_OPTIONS = ("current", "selected", "above", "bellow")
TREE_SELECT_TARGETS = ("server", "channel")
TREE_SELECT_DIRECTIONS = ("next", "prev")
SWITCH_TAB_OPTIONS = ("next", "prev")

COMMAND_SPAN_RE = re.compile(r"(^|[ \t])(\/\S+(?:[ \t]+\S+)*)")
WORD_RE = re.compile(r"\S+")

STATIC_ARG_REGISTRY = {
    "/status": set(STATUS_OPTIONS),
    "/cancel": set(CANCEL_OPTIONS),
    "/record": set(RECORD_OPTIONS),
    "/collapse_all_except": set(COLLAPSE_ALL_EXCEPT_OPTIONS),
    "/tree_select": set(TREE_SELECT_TARGETS),
    "/tree_select server": set(TREE_SELECT_DIRECTIONS),
    "/tree_select channel": set(TREE_SELECT_DIRECTIONS),
    "/switch_tab": set(SWITCH_TAB_OPTIONS),
}


def is_slash_command_text(text):
    """Return True when the input should be treated as live local slash-command text."""
    return bool(text) and text.startswith("/") and "\n" not in text


def get_base_command(text):
    """Extract the leading slash command token, lower-cased."""
    if not is_slash_command_text(text):
        return None
    match = re.match(r"^/(\S+)", text)
    if not match:
        return ""
    return match.group(1).lower()


def is_known_slash_command(text):
    """Check whether the prompt begins with a known local slash command."""
    base_command = get_base_command(text)
    return bool(base_command) and base_command in KNOWN_COMMANDS


def to_legacy_command_text(text):
    """Convert a live `/command` prompt string to the archived legacy command syntax."""
    if not is_known_slash_command(text):
        return None
    return text[1:]


def _format_base_completion(item):
    label, insert = item[:2]
    score = item[2] if len(item) > 2 else None
    display = f"/{label}"
    completion = (display, f"/{insert}")
    if score is not None:
        completion += (score, )
    return completion


def _format_dynamic_completion(label, insert, score=None):
    display = f"/{insert}"
    if label and label not in insert:
        display = f"/{insert} - {label}"
    completion = (display, f"/{insert}")
    if score is not None:
        completion += (score, )
    return completion


def _search_base_commands(query, limit=50, score_cutoff=15):
    if query:
        results = search.search_client_commands(
            BASE_COMMAND_ASSISTS,
            query,
            limit=limit,
            score_cutoff=score_cutoff,
        )
    else:
        results = BASE_COMMAND_ASSISTS
    return [_format_base_completion(item) for item in results]


def _format_dynamic_results(results):
    formatted = []
    for item in results:
        label, insert = item[:2]
        score = item[2] if len(item) > 2 else None
        formatted.append(_format_dynamic_completion(label, insert, score))
    return formatted


def get_help_lines():
    """Return human-readable slash-command help lines."""
    return [f"/{label}" for label, _ in BASE_COMMAND_ASSISTS]


def get_highlight_ranges(text, config_keys=None):
    """Return [start, end] ranges for recognized slash command spans in prompt text."""
    if not is_slash_command_text(text):
        return []

    config_keys = set(config_keys or ())
    spans = []
    for match in COMMAND_SPAN_RE.finditer(text):
        full = match.group(2)
        span_start = match.start(2)
        words = [(word.group(0), word.start(), word.end()) for word in WORD_RE.finditer(full)]
        if not words:
            continue
        base_token = words[0][0].lower()
        if base_token[1:] not in KNOWN_COMMANDS:
            continue
        span_end = span_start + words[0][2]
        key = base_token
        for word, _, word_end in words[1:]:
            lower_word = word.lower()
            valid_words = STATIC_ARG_REGISTRY.get(key)
            if valid_words and lower_word in valid_words:
                span_end = span_start + word_end
                key = f"{key} {lower_word}"
                continue
            if key == "/set" and word in config_keys:
                span_end = span_start + word_end
                break
            break
        spans.append([span_start, span_end])
    return spans


def get_matches(app, text):
    """Build autocomplete matches for prompt-local slash commands."""
    if not is_slash_command_text(text):
        return []

    legacy_text = text[1:]
    query = legacy_text.lower()
    if not legacy_text:
        return _search_base_commands("", limit=app.assist_limit, score_cutoff=app.assist_score_cutoff)

    if query.startswith("set "):
        setting_query = legacy_text[4:]
        if setting_query:
            return _format_dynamic_results(search.search_settings(
                app.config,
                setting_query,
                limit=app.assist_limit,
                score_cutoff=app.assist_score_cutoff,
            ))
        return [
            _format_dynamic_completion(f"{key} = {value}", f"set {key} = {value}")
            for key, value in app.config.items()
        ]

    if query.startswith("string_select "):
        chat_sel, _ = app.tui.get_chat_selected()
        msg_index = app.lines_to_msg(chat_sel)
        if msg_index is not None:
            message = app.messages[msg_index]
            if "component_info" in message and message["component_info"]["buttons"]:
                return _format_dynamic_results(search.search_string_selects(
                    message,
                    legacy_text[14:],
                    limit=app.assist_limit,
                    score_cutoff=app.assist_score_cutoff,
                ))
        return []

    if query.startswith("set_notifications "):
        query_words = legacy_text.split(" ")
        channel_id = None
        if len(query_words) > 1:
            match = re.search(parser.match_channel, query_words[1])
            if match:
                channel_id = match.group(1)
        if channel_id:
            _, _, guild_id, _, _ = app.find_parents_from_id(channel_id)
        else:
            tree_sel = app.tui.get_tree_selected()
            channel_id = app.tree_metadata[tree_sel]["id"]
            guild_id = app.find_parents_from_tree(tree_sel)[0]
        if legacy_text.endswith(" ") and not all(not x for x in query_words[1:]):
            guild_id = None
            channel_id = None
        else:
            return _format_dynamic_results(search.search_set_notifications(
                app.guilds,
                app.dms,
                guild_id,
                channel_id,
                discord.PING_OPTIONS,
                legacy_text,
                score_cutoff=app.assist_score_cutoff,
            ))
        return []

    if query.startswith("game_detection_blacklist ") and app.enable_game_detection and app.game_detection.run:
        return _format_dynamic_results(search.search_games(
            app.game_detection.get_detected(),
            app.state["games_blacklist"],
            legacy_text[25:],
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))

    if query.startswith("switch_tab "):
        tab_query = legacy_text[11:]
        dynamic = _format_dynamic_results(search.search_tabs(
            app.tabs_names,
            tab_query,
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))
        option_matches = _format_dynamic_results(search.search_options(
            SWITCH_TAB_OPTIONS,
            tab_query,
            "switch_tab",
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))
        return dynamic + option_matches

    if query.startswith("goto "):
        return _format_dynamic_results(search.search_channels_all(
            app.guilds,
            app.dms,
            legacy_text[5:],
            app.tui.input_buffer,
            recent=app.state["recent_channels"][:-1],
            read_state=app.read_state,
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))

    if query.startswith("collapse_all_except "):
        return _format_dynamic_results(search.search_options(
            COLLAPSE_ALL_EXCEPT_OPTIONS,
            legacy_text[20:],
            "collapse_all_except",
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))

    if query.startswith("status "):
        return _format_dynamic_results(search.search_options(
            STATUS_OPTIONS,
            legacy_text[7:],
            "status",
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))

    if query.startswith("cancel "):
        return _format_dynamic_results(search.search_options(
            CANCEL_OPTIONS,
            legacy_text[7:],
            "cancel",
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))

    if query.startswith("record "):
        return _format_dynamic_results(search.search_options(
            RECORD_OPTIONS,
            legacy_text[7:],
            "record",
            limit=app.assist_limit,
            score_cutoff=app.assist_score_cutoff,
        ))

    if query.startswith("tree_select "):
        parts = legacy_text.split(" ")
        if len(parts) <= 2:
            return _format_dynamic_results(search.search_options(
                TREE_SELECT_TARGETS,
                legacy_text[12:],
                "tree_select",
                limit=app.assist_limit,
                score_cutoff=app.assist_score_cutoff,
            ))
        if parts[1] in TREE_SELECT_TARGETS:
            prefix = f"tree_select {parts[1]}"
            suffix = legacy_text[len(prefix) + 1:]
            return _format_dynamic_results(search.search_options(
                TREE_SELECT_DIRECTIONS,
                suffix,
                prefix,
                limit=app.assist_limit,
                score_cutoff=app.assist_score_cutoff,
            ))

    return _search_base_commands(
        legacy_text,
        limit=app.assist_limit,
        score_cutoff=app.assist_score_cutoff,
    )
