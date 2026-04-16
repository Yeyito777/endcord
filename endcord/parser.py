# Copyright (C) 2025-2026 SparkLost
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

import logging
import re
import time
from datetime import datetime, timedelta, timezone

from endcord.deprecated.command_mode import (
    command_string as deprecated_command_string,
    split_command_binding as deprecated_split_command_binding,
)
from endcord.deprecated.input_assist import (
    app_command_string as deprecated_app_command_string,
    check_start_command as deprecated_check_start_command,
)

logger = logging.getLogger(__name__)
DISCORD_EPOCH_MS = 1420070400000
STATUS_STRINGS = ("online", "idle", "dnd", "invisible")
TIME_FORMATS = ("%Y-%m-%d", "%Y-%m-%d-%H-%M", "%H:%M:%S", "%H:%M")
TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
NOTIFICATION_VALUES = ("all", "mentions", "nothing", "default", "suppress_everyone", "suppress_roles")

match_from = re.compile(r"from:<@\d*>")
match_mentions = re.compile(r"mentions:<@\d*>")
match_has = re.compile(r"has:(?:link|embed|file|video|image|sound|sticker)")
match_before = re.compile(r"before:\d{4}-\d{2}-\d{2}")
match_after = re.compile(r"after:\d{4}-\d{2}-\d{2}")
match_in = re.compile(r"in:<#\d*>")
match_pinned = re.compile(r"pinned:(?:true|false)")

match_setting = re.compile(r"(\w+) ?= ?(.+)")
match_channel = re.compile(r"<#(\d*)>")
match_profile = re.compile(r"<@(\d*)>")

match_command_arguments = re.compile(r"--(\S+)=(\w+|\"[^\"]+\")?")

match_string_select = re.compile(r"string_select(?: (\d+))?\s+(.+)")
match_time_with_unit = re.compile(r"(\d+)([wdhms])")


def date_to_snowflake(date, end=False):
    """Convert date to discord snowflake, rounded to day start, if end=True then is rounded to day end"""
    try:
        time_obj = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        time_obj = datetime.now()
        time_obj = time_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    # timestamp cant be larger than now
    if int(time_obj.timestamp()) > time.time():
        time_obj = datetime.now()
        time_obj = time_obj.replace(hour=0, minute=0, second=0, microsecond=0)
        time_obj = time_obj.replace(tzinfo=timezone.utc)
    if end:
        time_obj += timedelta(days=1)
    return (int(time_obj.timestamp()) * 1000 - DISCORD_EPOCH_MS) << 22


def date_to_timestamp(date):
    """Convert date to discord snowflake, rounded to day start, if end=True then is rounded to day end"""
    time_obj = None
    # try various time formats
    for time_format in TIME_FORMATS:
        try:
            time_obj = datetime.strptime(date, time_format)
        except ValueError:
            continue

    if not time_obj:
        time_obj = datetime.now()
        time_obj = time_obj.replace(hour=0, minute=0, second=0, microsecond=0)

    # set current date if its unset
    if time_obj.year == 1900:
        now = datetime.now()
        time_obj = time_obj.replace(year=now.year, month=now.month, day=now.day)

    return int(time_obj.timestamp())


def time_string_seconds(time_str):
    """Convert time string to seconds.Strings: 1w, 2d, 3h, 4m, 5s"""
    try:
        return int(time_str)
    except ValueError:
        pass
    total = 0
    for value, unit in re.findall(match_time_with_unit, time_str.lower()):
        total += int(value) * TIME_UNITS[unit]
    if not total:
        return 0
    return total


def read_value(text, idx):
    """Read quited and unquoted value from string index"""
    length = len(text)
    # quoted value
    if idx < length and text[idx] == '"':
        idx += 1
        start = idx
        while idx < length and text[idx] != '"':
            idx += 1
        value = text[start:idx]
        return value, idx + 1

    # unquoted value
    start = idx
    while idx < length and text[idx] != " ":
        idx += 1
    return text[start:idx], idx



def search_string(text):
    """
    Parse search string.
    from:[<@ID>]
    mentions:[<@ID>]
    has:[link|embed|file|video|image|sound|sticker]
    before:[2015-01-01]
    after:[2015-01-01]
    in:[<#ID>]
    pinned:[true|false]
    """
    author_id = []
    for match in re.findall(match_from, text):
        text = text.replace(match, "")
        author_id.append(match[7:-1])
    mentions = []
    for match in re.findall(match_mentions, text):
        text = text.replace(match, "")
        author_id.append(match[11:-1])
    has = []
    for match in re.findall(match_has, text):
        text = text.replace(match, "")
        has.append(match[4:])
    max_id = []
    for match in re.findall(match_before, text):
        text = text.replace(match, "")
        max_id.append(date_to_snowflake(match[7:]))
    min_id = []
    for match in re.findall(match_after, text):
        text = text.replace(match, "")
        min_id.append(date_to_snowflake(match[6:], end=True))
    channel_id = []
    for match in re.findall(match_in, text):
        text = text.replace(match, "")
        channel_id.append(match[5:-1])
    pinned = []
    for match in re.findall(match_pinned, text):
        text = text.replace(match, "")
        pinned.append(match[7:])
    text = text.strip()
    return text, channel_id, author_id, mentions, has, max_id, min_id, pinned


def check_start_command(text, my_commands, guild_commands, permitted_guild_commands):
    """Compatibility wrapper for the deprecated slash-command start checker."""
    return deprecated_check_start_command(text, my_commands, guild_commands, permitted_guild_commands)


def app_command_string(text, my_commands, guild_commands, permitted_guild_commands, roles, channels, dm, autocomplete):
    """Compatibility wrapper for the deprecated slash-command parser."""
    return deprecated_app_command_string(text, my_commands, guild_commands, permitted_guild_commands, roles, channels, dm, autocomplete)


def split_command_binding(text):
    """Compatibility wrapper for the deprecated command-binding parser."""
    return deprecated_split_command_binding(text)


def command_string(text):
    """Compatibility wrapper for the deprecated client command parser."""
    return deprecated_command_string(text)
