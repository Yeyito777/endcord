# Copyright (C) 2025-2026 SparkLost
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

"""Archived legacy command palette / command-binding implementation.

This module preserves the old client-command parser and assist metadata after
those UI entry points were deprecated from the live application.
"""

import re
from datetime import datetime

STATUS_STRINGS = ("online", "idle", "dnd", "invisible")
TIME_FORMATS = ("%Y-%m-%d", "%Y-%m-%d-%H-%M", "%H:%M:%S", "%H:%M")
TIME_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
NOTIFICATION_VALUES = ("all", "mentions", "nothing", "default", "suppress_everyone", "suppress_roles")

match_setting = re.compile(r"(\w+) ?= ?(.+)")
match_channel = re.compile(r"<#(\d*)>")
match_profile = re.compile(r"<@(\d*)>")
match_command_arguments = re.compile(r'--(\S+)=(\w+|"[^"]+")?')
match_string_select = re.compile(r"string_select(?: (\d+))?\s+(.+)")
match_time_with_unit = re.compile(r"(\d+)([wdhms])")

DEFAULT_COMMAND_BINDINGS = {
    "552": "switch_tab prev",
    "567": "switch_tab next",
    "11": "command_palette; type 'goto '",
    "336": "tree_select server; collapse_all_except selected",
    "337": "tree_select server prev; collapse_all_except selected",
    "25-259": "resize_extra_window +1",
    "25-258": "resize_extra_window -1",
}

COMMAND_PALETTE_KEYBINDINGS = {
    "standard": 31,
    "vim": ":",
    "windows": 28,
}

COMMAND_ASSISTS = (
    ("goto <#[channel_id]> - go to specified channel/server/category/DM", "goto"),
    ("view_pfp *<@[user_id]> - view specified or selected users pfp", "view_pfp"),
    ("react *[reaction] - show prompt or react to message", "react"),
    ("status *[type] - change your status 1/online, 2/idle, 3/dnd, 4/invisible", "status"),
    ("open_link *[num] - open selected link or specify index if multiple are on same line", "open_link"),
    ("copy_link *[num] - copy selected link to clipboard or specify index if multiple are on same line", "copy_link"),
    ("download *[num] - download selected attachment", "download"),
    ("play *[num] - play selected attachment", "play"),
    ("search *[query] - prompt for message search or search provided string", "search"),
    ("gif *[query] - prompt for gif search or search provided string", "gif"),
    ("record / record cancel - start/stop/cancel recording voice message", "record"),
    ("upload *[path] - prompt to upload attachment or use provided path", "upload"),
    ("profile *<@[user_id]> - view profile of selected or specified user", "profile"),
    ("channel *<#[channel_id]> - view info of selected or specified channel", "channel"),
    ("summaries *<#[channel_id]> - view summaries of selected or specified channel", "summaries"),
    ("hide *<#[channel_id]> - view info of selected or specified channel", "hide"),
    ("toggle_mute *<#[channel_id]> - toggle mute state of selected or specified channel", "toggle_mute"),
    ("mark_as_read *<#[channel_id]> - mark selected or specified channel/server/category/DM/* as read", "mark_as_read"),
    ("mark_as_unread - mark selected message as unread", "mark_as_unread"),
    ("copy_message - copy selected message text", "copy_message"),
    ("spoil - reveal one by one spoiler in selected message", "spoil"),
    ("link_channel *<#[channel_id]> - store channel link in clipboard", "link_channel"),
    ("link_message - store selected message link in clipboard", "link_message"),
    ("goto_mention *[num] - go to channel/message mention in selected message", "goto_mention"),
    ("cancel *[download/1/upload/2/attachment/3] - cancel all downloads and/or uploads", "cancel"),
    ("external_edit - open external editor to type message in it", "external_edit"),
    ("toggle_member_list - toggle member list", "toggle_member_list"),
    ("toggle_tree - toggle channel tree", "toggle_tree"),
    ("toggle_thread - join/leave currently open thread", "toggle_thread"),
    ("toggle_thread_tree - join/leave selected thread in tree", "toggle_thread_tree"),
    ("bottom - go to chat bottom", "bottom"),
    ("goto_reply - go to message that selected message is replying to", "goto_reply"),
    ("show_reactions - show reactions details for selected message", "show_reactions"),
    ("show_pinned - show pinned messages for current channel", "show_pinned"),
    ("pin_message - pin selected message to current channel", "pin_message"),
    ("push_button [num/name] - push button on interactive app message", "push_button"),
    ("string_select [string] - select string on interactive app message", "string_select"),
    ("toggle_tab - toggle tabbed (pinned) state of current channel", "toggle_tab"),
    ("switch_tab [num/next/prev] - switch to specified tab by its number", "switch_tab"),
    ("remove_all_tabs - remove all tabbed channels", "remove_all_tabs"),
    ("vote [num] - vote for specified answer index on active poll message", "vote"),
    ("paste - paste image or file as attachment or text from clipboard", "paste"),
    ("insert_timestamp YYYY-MM-DD-HH-mm / YYYY-MM-DD / HH:mm / HH:mm:SS - insert timestamp", "insert_timestamp"),
    ("set_notifications *<#[channel_id]> ... - show and modify server/channel notification settings", "set_notifications"),
    ("check_standing - check account standing, anything non-100 is concerning", "check_standing"),
    ("custom_status [string] - set custom status text", "custom_status"),
    ("custom_status_emoji [emoji] - set custom status emoji", "custom_status_emoji"),
    ("custom_status_remove - remove custom status", "custom_status_remove"),
    ("toggle_afk - toggle afk state; if afk, mobile devices will receive notifications", "toggle_afk"),
    ("block *ignore <@[user_id]> - block/ignore user", "block"),
    ("unblock *ignore <@[user_id]> - unblock/unignore user", "unblock"),
    ("toggle_blocked_messages - toggle showing messages from blocked users in chat", "toggle_blocked_messages"),
    ("view_emoji *[emoji/num] - download specified custom emoji and show it in media player", "view_emoji"),
    ("voice_start_call - start voice call in currently open DM", "voice_start_call"),
    ("voice_accept_call - accept incoming voice call", "voice_accept_call"),
    ("voice_leave_call - leave current voice call", "voice_leave_call"),
    ("voice_reject_call - silence incoming call or cancel outgoing call", "voice_reject_call"),
    ("voice_list_call - show all call participants and their states in an updated list", "voice_list_call"),
    ("voice_set_volume_input [0-100] - change volume for input devices in voice call", "voice_set_volume_input"),
    ("voice_set_volume_output [0-100] - change volume for output devices in voice call", "voice_set_volume_output"),
    ("generate_invite *[duration] *[limit] - generate invite to current server, default is 7 days", "generate_invite"),
    ("rename_folder [name] - locally rename currently selected folder in tree", "rename_folder"),
    ("resize_extra_window [num/-1/+1] - resize extra window", "resize_extra_window"),
    ("collapse_all_except *[option] - collapse all servers in tree except specific [option]", "collapse_all_except"),
    ("tree_select *[server/channel], *[next/prev] - select next or previous server or channel in tree", "tree_select"),
    ("send_message * - see commands documentation for options", "send_message"),
    ("redraw - redraw UI if it ever gets messed up", "redraw"),
    ("check_for_updates *open - check endcord and extensions for updates and open gh release", "check_for_updates"),
    ("search_extensions - search all endcord extensions on GitHub", "search_extensions"),
    ("install_extension *[url] - install extension from specified git url or update all", "install_extension"),
    ("open_config_dir - open config directory with system file manager", "open_config_dir"),
    ("show_log - show live log", "show_log"),
    ("show_stats - show current client stats", "show_stats"),
    ("dump_chat - dump current chat to unique json file", "dump_chat"),
    ("dump_roles - dump current server roles to unique json file", "dump_roles"),
    ("game_detection_blacklist [game] - toggle blacklist for games detected in past 7 days", "game_detection_blacklist"),
    ("set [key] = [value] - change settings and save them.", "set"),
    ("quit - quit endcord", "quit"),
)

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

def split_command_binding(text):
    """Split string into multiple strings on ";" and ignore whitespace and newline"""
    # Using null chaacter as placeholder
    parts = text.replace("\\;", "\x00").split(";")
    return [p.replace("\x00", ";").strip() for p in parts]


def command_string(text):
    """Parse command string"""

    # 0 - UNKNOWN
    cmd_type = 0
    cmd_args = {}
    text_lower = text.lower()

    # 1 - SET
    if text_lower.startswith("set "):
        # "set [key] = [value]" / "set [key]=[value]"
        cmd_type = 1
        match = re.search(match_setting, text)
        if match:
            key = match.group(1)
            value = match.group(2)
            if not (key and value):
                cmd_type = 0
        else:
            cmd_type = 0
        cmd_args = {
            "key": key,
            "value": value,
        }

    # 2 - BOTTOM
    elif text_lower.startswith("bottom"):
        cmd_type = 2

    # 3 - GOTO_REPLY
    elif text_lower.startswith("goto_reply"):
        cmd_type = 3

    # 4 - DOWNLOAD
    elif text_lower.startswith("download"):
        cmd_type = 4
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            pass

    # 5 - OPEN_LINK
    elif text_lower.startswith("open_link"):
        cmd_type = 5
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            pass

    # 6 - PLAY
    elif text_lower.startswith("play"):
        cmd_type = 6
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            pass

    # 7 - CANCEL
    elif text_lower.startswith("cancel"):
        cmd_type = 7
        value_part = text_lower[7:]
        cmd_args = {"type": 0}
        if "download" in value_part or "1" in value_part:
            cmd_args = {"type": 1}
        if "upload" in value_part or "2" in value_part:
            cmd_args = {"type": 2}
        if "attachment" in value_part or "3" in value_part:
            cmd_args = {"type": 3}

    # 8 - COPY_MESSAGE
    elif text_lower.startswith("copy_message"):
        cmd_type = 8

    # 9 - UPLOAD
    elif text_lower.startswith("upload"):
        cmd_type = 9
        cmd_args = {"path": text[7:]}

    # 10 - SPOIL
    elif text_lower.startswith("spoil"):
        cmd_type = 10
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            pass

    # 11 - TOGGLE_THREAD_TREE
    elif text_lower.startswith("toggle_thread_tree"):
        cmd_type = 11

    # 12 - PROFILE
    elif text_lower.startswith("profile"):
        cmd_type = 12
        match = re.search(match_profile, text)
        if match:
            cmd_args = {"user_id": match.group(1)}

    # 13 - CHANNEL
    elif text_lower.startswith("channel"):
        cmd_type = 13
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}

    # 14 - SUMMARIES
    elif text_lower.startswith("summaries"):
        cmd_type = 14
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}

    # 15 - HIDE
    elif text_lower.startswith("hide"):
        cmd_type = 15
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}

    # 16 - SEARCH
    elif text_lower.startswith("search "):
        cmd_type = 16
        search_text = text[7:].strip(" ")
        cmd_args = {"search_text": search_text}

    # 17 - LINK_CHANNEL
    elif text_lower.startswith("link_channel"):
        cmd_type = 17
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}

    # 18 - LINK_MESSAGE
    elif text_lower.startswith("link_message"):
        cmd_type = 18

    # 19 - GOTO_MENTION
    elif text_lower.startswith("goto_mention"):
        cmd_type = 19
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            pass

    # 20 - STATUS
    elif text_lower.startswith("status"):
        cmd_type = 20
        text += " "
        if text.split(" ")[1].lower() in STATUS_STRINGS:
            cmd_args = {"status": text.split(" ")[1].lower()}
        else:
            try:
                num = int(text.split(" ")[1].lower()) - 1
                if num < len(STATUS_STRINGS):
                    cmd_args = {"status": STATUS_STRINGS[num]}
            except ValueError:
                pass

    # 21 - RECORD
    elif text_lower.startswith("record"):
        cmd_type = 21
        text += " "
        cmd_args = {"cancel": text.split(" ")[1].lower() == "cancel"}

    # 22 - TOGGLE_MEMBER_LIST
    elif text_lower.startswith("toggle_member_list"):
        cmd_type = 22

    # 23 - REACT
    elif text_lower.startswith("react"):
        cmd_type = 23
        react_text = text[6:].strip(" ")
        cmd_args = {"react_text": react_text}

    # 24 - SHOW_REACTIONS
    elif text_lower.startswith("show_reactions"):
        cmd_type = 24

    # 25 - GOTO
    elif text_lower.startswith(("goto", "xyzzy")):
        cmd_type = 25
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}
        elif text_lower.startswith("xyzzy"):
            cmd_args = {"channel_id": "special"}
        else:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 26 - VIEW_PFP
    elif text_lower.startswith("view_pfp"):
        cmd_type = 26
        match = re.search(match_profile, text)
        if match:
            cmd_args = {"user_id": match.group(1)}

    # 27 - CHECK_STANDING
    elif text_lower.startswith("check_standing"):
        cmd_type = 27

    # 28 - PASTE
    elif text_lower.startswith("paste"):
        cmd_type = 28

    # 29 - TOGGLE_MUTE
    elif text_lower.startswith("toggle_mute"):
        cmd_type = 29
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}

    # 30 - TOGGLE_TAB
    elif text_lower.startswith("toggle_tab"):
        cmd_type = 30

    # 31 - SWITCH_TAB
    elif text_lower.startswith("switch_tab"):
        cmd_type = 31
        value_part = text_lower[11:]
        if "next" in value_part:
            cmd_args = {"num": "next"}
        elif "prev" in value_part:
            cmd_args = {"num": "prev"}
        else:
            try:
                num = int(text.split(" ")[1]) - 1
                cmd_args = {"num": num}
            except (IndexError, ValueError):
                cmd_type = 0

    # 32 - MARK_AS_READ
    elif text_lower.startswith("mark_as_read"):
        cmd_type = 32
        match = re.search(match_channel, text)
        if match:
            cmd_args = {"channel_id": match.group(1)}
        elif text.split(" ")[1] == "*":
            cmd_args = {"channel_id": "*"}

    # 33 - INSERT_TIMESTAMP
    elif text_lower.startswith("insert_timestamp"):
        cmd_type = 33
        try:
            date_string = text.split(" ")[1]
            timestamp = date_to_timestamp(date_string)
            cmd_args = {"timestamp": timestamp}
        except (IndexError, ValueError):
            cmd_type = 0
            cmd_args = {"value": 1}

    # 34 - VOTE
    elif text_lower.startswith("vote"):
        cmd_type = 34
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            cmd_type = 0
            cmd_args = {"value": 1}

    # 35 - SHOW_PINNED
    elif text_lower.startswith("show_pinned"):
        cmd_type = 35

    # 36 - PIN_MESSAGE
    elif text_lower.startswith("pin_message"):
        cmd_type = 36

    # 37 - PUSH_BUTTON
    elif text_lower.startswith("push_button"):
        cmd_type = 37
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except ValueError:
            name = text.split(" ")[1]
            cmd_args = {"name": name}
        except IndexError:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 38 - STRING_SELECT
    elif text_lower.startswith("string_select"):
        cmd_type = 38
        match = re.search(match_string_select, text_lower)
        if match:
            num = match.group(1)
            string = match.group(2)
            cmd_args = {"num": num, "text": string}
        else:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 39 - DUMP_CHAT
    elif text_lower.startswith("dump_chat"):
        cmd_type = 39

    # 40 - SET_NOTIFICATIONS
    elif text_lower.startswith("set_notifications"):
        cmd_type = 40
        cmd_split = text.split(" ")
        have_id = False
        cmd_args = {"id": None, "setting": ""}
        if len(cmd_split) > 1:
            match = re.search(match_channel, cmd_split[1])
            if match:
                cmd_args["channel_id"] = match.group(1)
                have_id = True
        if len(cmd_split) > 1 + have_id:
            if cmd_split[1 + have_id].lower() in NOTIFICATION_VALUES:
                cmd_args["setting"] = cmd_split[1 + have_id].lower()
            else:
                cmd_type = 0
                cmd_args = {"value": 1}

    # 41 - GIF
    elif text_lower.startswith("gif"):
        cmd_type = 41
        search_text = text[4:].strip(" ")
        cmd_args = {"search_text": search_text}

    # 42 - REDRAW
    elif text_lower.startswith("redraw"):
        cmd_type = 42

    # 43 - EXTERNAL_EDIT
    elif text_lower.startswith("external_edit"):
        cmd_type = 43

    # 44 - CUSTOM_STATUS/EMOJI/REMOVE
    elif text_lower.startswith("custom_status"):
        cmd_type = 44
        if text_lower.startswith("custom_status_emoji"):
            cmd_args = {"emoji": text[20:]}
            if len(text) <= 20:
                cmd_type = 0
                cmd_args = {"value": 1}
        elif text_lower.startswith("custom_status_remove"):
            pass
        else:
            cmd_args = {"text": text[14:]}
            if len(text) <= 14:
                cmd_type = 0
                cmd_args = {"value": 1}

    # 45 - BLOCK
    elif text_lower.startswith("block"):
        cmd_type = 45
        match = re.search(match_profile, text)
        if match:
            cmd_args = {
                "user_id": match.group(1),
                "ignore": "ignore" in text_lower,
            }
        else:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 46 - UNBLOCK
    elif text_lower.startswith("unblock"):
        cmd_type = 46
        match = re.search(match_profile, text)
        if match:
            cmd_args = {
                "user_id": match.group(1),
                "ignore": "ignore" in text_lower,
            }
        else:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 47 - TOGGLE_BLOCKED_MESSGAES
    elif text_lower.startswith("toggle_blocked_messages"):
        cmd_type = 47

    # 48 - VOICE_START_CALL
    elif text_lower.startswith("voice_start_call"):
        cmd_type = 48

    # 49 - VOICE_ACCEPT_CALL
    elif text_lower.startswith("voice_accept_call"):
        cmd_type = 49

    # 50 - VOICE_LEAVE_VALL
    elif text_lower.startswith("voice_leave_call"):
        cmd_type = 50

    # 51 - VOICE_REJECT_CALL
    elif text_lower.startswith("voice_reject_call"):
        cmd_type = 51

    # 52 - VOICE_SET_VOLUME_INPUT
    elif text_lower.startswith("voice_set_volume_input"):
        cmd_type = 52
        try:
            num_piece = text.split(" ")[1]
            num = abs(int(num_piece))
            increment = 0
            if "+" in num_piece:
                increment = 1
            if "-" in num_piece:
                increment = -1
            cmd_args = {"value": num, "increment": increment}
        except (IndexError, ValueError):
            cmd_type = 0
            cmd_args = {"value": 1}

    # 53 - VOICE_SET_VOLUME_OUTPUT
    elif text_lower.startswith("voice_set_volume_output"):
        cmd_type = 53
        try:
            num_piece = text.split(" ")[1]
            num = abs(int(num_piece))
            increment = 0
            if "+" in num_piece:
                increment = 1
            if "-" in num_piece:
                increment = -1
            cmd_args = {"value": num, "increment": increment}
        except (IndexError, ValueError):
            cmd_type = 0
            cmd_args = {"value": 1}

    # 54 - VOICE_LIST_CALL
    elif text_lower.startswith("voice_list_call"):
        cmd_type = 54

    # 55 - SHOW_LOG
    elif text_lower.startswith("show_log"):
        cmd_type = 55

    # 56 - RENAME_FOLDER
    elif text_lower.startswith("rename_folder"):
        cmd_type = 56
        name = text[14:].strip(" ")
        if name:
            cmd_args = {"name": name}
        else:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 57 - VIEW_EMOJI
    elif text_lower.startswith("view_emoji"):
        cmd_type = 57
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            name = text[11:].strip(" ")
            cmd_args = {"name": name}

    # 58 - QUIT
    elif text_lower.split(" ")[0] == "quit":
        cmd_type = 58

    # 59 - MARK_AS_UNREAD
    elif text_lower.split(" ")[0] == "mark_as_unread":
        cmd_type = 59

    # 60 - TOGGLE_THREAD
    elif text_lower.split(" ")[0] == "toggle_thread":
        cmd_type = 60

    # 61 - GAME_DETECTION_BLACKLIST
    elif text_lower.split(" ")[0] == "game_detection_blacklist":
        cmd_type = 61
        name = text[25:].strip(" ")
        if name:
            cmd_args = {"name": name}
        else:
            cmd_type = 0
            cmd_args = {"value": 1}

    # 62 - OPEN_CONFIG_DIR
    elif text_lower.split(" ")[0] == "open_config_dir":
        cmd_type = 62

    # 63 - SEND_MESSAGE
    elif text_lower.split(" ")[0] == "send_message":
        cmd_type = 63
        channel_id = None
        reply_id = None
        ping = True
        attachments = []
        length = len(text_lower)
        i = 13
        while i < length and text[i] == " ":   # skip spaces
            i += 1
        while i < length:
            if text.startswith("--channel_id=", i):
                i += len("--channel_id=")
                value, i = read_value(text, i)
                try:
                    int(value)
                    channel_id = value
                except ValueError:
                    match = re.search(match_channel, value)
                    if match:
                        channel_id = match.group(1)
            elif text.startswith("--reply_id=", i):
                i += len("--reply_id=")
                reply_id, i = read_value(text, i)
            elif text.startswith("--ping=", i):
                i += len("--ping=")
                value, i = read_value(text, i)
                ping = value.lower() == "true"
            elif text.startswith("--attachment=", i):
                i += len("--attachment=")
                value, i = read_value(text, i)
                attachments.append(value)
            else:
                break
            while i < length and text[i] == " ":   # skip spaces
                i += 1
        content = text[i:].lstrip()
        cmd_args = {
            "content": content,
            "channel_id": channel_id,
            "reply_id": reply_id,
            "ping": ping,
            "attachments": attachments,
        }

    # 64 - COPY_LINK
    elif text_lower.startswith("copy_link"):
        cmd_type = 64
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"num": num}
        except (IndexError, ValueError):
            pass

    # 65 - TOGGLE_AFK
    elif text_lower.startswith("toggle_afk"):
        cmd_type = 65

    # 66 - 666
    elif text_lower.startswith("666"):
        cmd_type = 66

    # 67 - TOGGLE_SNOW
    elif text_lower.startswith("toggle_snow"):
        cmd_type = 67

    # 68 - REMOVE_ALL_TABS
    elif text_lower.startswith("remove_all_tabs"):
        cmd_type = 68

    # 69 - COLLAPSE_ALL_EXCEPT
    elif text_lower.startswith("collapse_all_except"):
        cmd_type = 69
        value_part = text_lower[20:].strip(" ")
        if value_part == "current":
            cmd_args = {"value": 2}
        elif value_part == "selected":
            cmd_args = {"value": 0}
        elif value_part == "above":
            cmd_args = {"value": 1}
        elif value_part == "bellow":
            cmd_args = {"value": -1}

    # 70 - TREE_SELECT
    elif text_lower.startswith("tree_select"):
        cmd_type = 70
        all_args = text_lower[12:].strip(" ").split(" ")
        cmd_args = {
            "type": "server" in all_args,
            "value": "prev" in all_args,
        }

    # 71 - CHECK_FOR_UPDATES
    elif text_lower.startswith("check_for_updates"):
        cmd_type = 71
        cmd_args = {"open": "open" in text_lower}

    # 72 - INSTALL_EXTENSION
    elif text_lower.startswith("install_extension"):
        cmd_type = 72
        cmd_args = {"text": text[18:]}

    # 73 - SEARCH_EXTENSIONS
    elif text_lower.startswith("search_extensions"):
        cmd_type = 73

    # 74 - RESIZE_EXTRA_WINDOW
    elif text_lower.startswith("resize_extra_window"):
        cmd_type = 74
        try:
            num = int(text.split(" ")[1])
            cmd_args = {"value": num}
        except (IndexError, ValueError):
            cmd_type = 0
            cmd_args = {"value": 1}

    # 75 - DUMP_ROLES
    elif text_lower.startswith("dump_roles"):
        cmd_type = 75

    # 76 - SHOW_STATS
    elif text_lower.startswith("show_stats"):
        cmd_type = 76

    # 77 - TOGGLE_TREE
    elif text_lower.startswith("toggle_tree"):
        cmd_type = 77

    # 78 - GENERATE_INVITE
    elif text_lower.startswith("generate_invite"):
        cmd_type = 78
        max_age = 604800
        max_uses = 0
        text_split = text_lower.split(" ")
        text_split = list(filter(None, text_split))
        if len(text_split) >= 2:
            new_max_age = time_string_seconds(text_split[1])
            if new_max_age is not None:
                max_age = new_max_age
        if len(text_split) >= 3:
            try:
                max_uses = int(text_split[2])
            except ValueError:
                pass

        cmd_args = {
            "max_age": max_age,
            "max_uses": max_uses,
        }

    return cmd_type, cmd_args
