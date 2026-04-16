# Copyright (C) 2025-2026 SparkLost
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

import heapq
import importlib.util
import re

import emoji

from endcord.deprecated.input_assist import (
    search_app_commands as deprecated_search_app_commands,
    search_usernames_roles as deprecated_search_usernames_roles,
)

COMMAND_OPT_TYPE = ("subcommand", "group", "string", "integer", "True/False", "user ID", "channel ID", "role ID", "mentionable ID", "number", "attachment")


def fuzzy_match_score_single(query, candidate):
    """
    Calculates score for fuzzy matching of single query word.
    Consecutive matches will have larger score.
    Matches closer to the start of the candidate string will have larger score.
    Score is not limited.
    """
    query_lower, candidate_lower = query.lower(), candidate.lower()
    qlen, clen = len(query), len(candidate)
    qpos, cpos = 0, 0
    score = 0
    last_match_pos = -1
    while qpos < qlen and cpos < clen:
        if query_lower[qpos] == candidate_lower[cpos]:
            if last_match_pos == cpos - 1:
                score += 10   # consecutive match adds more score
            else:
                score += 1   # match after some gap
            last_match_pos = cpos
            qpos += 1
        cpos += 1
    if qpos == qlen:
        # bonus for match starting early in candidate
        score += max(0, 10 - last_match_pos)
        return score
    return 0


def fuzzy_match_score(query, candidate):
    """
    Calculate score for fuzzy matching of query containing one or multiple words.
    Consecutive matches will have larger score.
    Matches closer to the start of the candidate string will have larger score.
    Score is not limited.
    """
    total_score = 0
    for word in query.split():
        score = fuzzy_match_score_single(word, candidate)
        if score == 0:
            return 0
        total_score += score
    return total_score


# use cython if available, ~6.7 times faster
if importlib.util.find_spec("endcord_cython") and importlib.util.find_spec("endcord_cython.search"):
    from endcord_cython.search import fuzzy_match_score


def search_options(options, query, prompt, limit=50, score_cutoff=15):
    """Generic search for options"""
    results = []
    worst_score = score_cutoff

    for option in options:
        score = fuzzy_match_score(query, option)
        if score < worst_score and query:
            continue
        heapq.heappush(results, (option, prompt + " " + option, score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_channels_guild(channels, query, limit=50, score_cutoff=15):
    """Search for channels in one guild"""
    results = []
    worst_score = score_cutoff

    for channel in channels:
        # skip categories (type 4)
        if channel["permitted"] and channel["type"] != 4:
            formatted = channel["name"]
            if channel["type"] == 2:
                formatted += " - voice"
            elif channel["type"] in (11, 12):
                formatted += " - thread"
            elif channel["type"] == 15:
                formatted += " - forum"
            elif channel["type"] == 16:
                formatted += " - imageboard"

            score = fuzzy_match_score(query, formatted)
            if score < worst_score:
                continue
            heapq.heappush(results, (formatted, channel["id"], score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_channels_all(guilds, dms, query, full_input, recent=None, read_state=None, limit=50, score_cutoff=15):
    """Search for guilds/categories/channels/DMs"""
    results = []
    worst_score = score_cutoff
    if read_state:
        mentions = {ch_id for ch_id, channel in read_state.items() if channel.get("mentions")}
    else:
        mentions = set()

    for dm in dms:
        bonus_score = 0
        if recent:
            if dm["id"] in recent:
                bonus_score = score_cutoff
            elif not query:
                continue
        if mentions and dm["id"] in mentions:
            if bonus_score:
                bonus_score += 1
            else:
                bonus_score = score_cutoff
        formatted = f"{dm["name"]} (DM)"
        score = fuzzy_match_score(query, formatted) * 4 + bonus_score   # dms get more score so they are on top
        if score < worst_score * 4:
            continue
        if recent:
            completion = f"goto <#{dm["id"]}>"
        else:
            completion = dm["id"]
        heapq.heappush(results, (formatted, completion, score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    if (full_input.startswith("toggle_mute") or full_input.startswith("mark_as_read") or full_input.startswith("goto")) and (not recent or query):
        full = True   # include guilds and categories
    else:
        full = False
    for guild in guilds:
        if full:
            formatted = f"{guild["name"]} - server"
            score = fuzzy_match_score(query, formatted) * 2   # guilds get more score so they are on top
            if score >= worst_score:
                heapq.heappush(results, (formatted, guild["guild_id"], score))
                if len(results) > limit:
                    heapq.heappop(results)
                    worst_score = results[0][2]

        for channel in guild["channels"]:
            bonus_score = 0
            if recent:
                if channel["id"] in recent:
                    bonus_score = score_cutoff
                elif not query:
                    continue
            if mentions and dm["id"] in mentions:
                if bonus_score:
                    bonus_score += 1
                else:
                    bonus_score = score_cutoff
            if channel["permitted"]:
                formatted = channel["name"]
                if channel["type"] == 2:
                    formatted += " - voice"
                elif full and channel["type"] == 4:
                    formatted += " - category"
                elif channel["type"] in (11, 12):
                    formatted += " - thread"
                elif channel["type"] == 15:
                    formatted += " - forum"
                elif channel["type"] == 16:
                    formatted += " - imageboard"
                formatted += f" ({guild["name"]})"
                score = fuzzy_match_score(query, formatted) + bonus_score
                if score < worst_score:
                    continue
                if recent:
                    completion = f"goto <#{channel["id"]}>"
                else:
                    completion = channel["id"]
                heapq.heappush(results, (formatted, completion, score))
                if len(results) > limit:
                    heapq.heappop(results)
                    worst_score = results[0][2]

    results = sorted(results, key=lambda x: x[2], reverse=True)
    if recent and not query:
        order = {ch_id: i for i, ch_id in enumerate(recent)}
        results.sort(key=lambda t: order.get(t[1], len(order)), reverse=True)

    return results


def search_usernames_roles(roles, query_results, guild_id, gateway, query, presences=[], limit=50, score_cutoff=15):
    """Compatibility wrapper for the deprecated mention helper search."""
    return deprecated_search_usernames_roles(roles, query_results, guild_id, gateway, query, presences, limit, score_cutoff)


def search_emojis(all_emojis, premium, guild_id, query, safe_emoji=False, limit=50, score_cutoff=15):
    """Search for emoji"""
    results = []
    worst_score = score_cutoff

    # guild emoji
    if premium:
        emojis = all_emojis
    else:
        for guild in all_emojis:
            if guild["guild_id"] == guild_id:
                emojis = [guild]
                break
        else:
            emojis = []

    for guild in emojis:
        guild_name = guild["guild_name"]
        for guild_emoji in guild["emojis"]:
            formatted = f"{guild_emoji["name"]} ({guild_name})"
            score = fuzzy_match_score(query, formatted)
            if score < worst_score:
                continue
            heapq.heappush(results, (formatted, f"<:{guild_emoji["name"]}:{guild_emoji["id"]}>", score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]

    # standard emoji
    if len(results) < limit:
        for key, item in emoji.EMOJI_DATA.items():
            if item["status"] > 2:   # skip unqualified and minimally qualified emoji
                continue
            # emoji.EMOJI_DATA = {emoji: {"en": ":emoji_name:", "status": 2, "E": 3}...}
            # using only qualified emojis (status: 2)
            if safe_emoji:
                formatted = item["en"]
            else:
                formatted = f"{item["en"]} - {key}"
            score = fuzzy_match_score(query, formatted)
            if score < worst_score:
                continue
            heapq.heappush(results, (formatted, item["en"], score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_stickers(all_stickers, default_stickers, premium, guild_id, query, limit=50, score_cutoff=15):
    """Search for stickers"""
    results = []
    worst_score = score_cutoff

    if premium:
        stickers = all_stickers
    else:
        for pack in all_stickers:
            if pack["pack_id"] == guild_id:
                stickers = [pack]
                break
        else:
            stickers = []

    for pack in stickers + default_stickers:
        pack_name = pack["pack_name"]
        for sticker in pack["stickers"]:
            formatted = f"{sticker["name"]} ({pack_name})"
            score = fuzzy_match_score(query, formatted)
            if score < worst_score:
                continue
            heapq.heappush(results, (formatted, sticker["id"], score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_settings(config, query, limit=50, score_cutoff=15):
    """Search for settings"""
    results = []
    worst_score = score_cutoff

    for key, value in config.items():
        formatted = f"{key} = {value}"
        score = fuzzy_match_score(query, formatted)
        if score < worst_score:
            continue
        heapq.heappush(results, (formatted, f"set {key} = {value}", score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_string_selects(message, query_in, limit=50, score_cutoff=15):
    """Search for string selects"""
    results = []
    worst_score = score_cutoff
    query = query_in.lower()
    num = query.split(" ")[1]

    try:
        num = max(int(num)-1, 0)
        query_words = query.split(" ")[2:]
    except (ValueError, IndexError):
        num = 0
        query_words = query.split(" ")[1:]
    try:
        string_select = message["component_info"]["string_selects"][num]
    except IndexError:
        string_select = None
    # allow executing command if space is at the end
    if string_select and not (query.endswith(" ") and not all(not x for x in query_words)):
        for option in string_select["options"]:
            score = fuzzy_match_score(query, option["label"])
            if score < worst_score:
                continue
            description = option.get("description", "")
            if description:
                formatted = f"{option["label"]}{description}"
            else:
                formatted = option["label"]
            heapq.heappush(results, (formatted, f"string_select {num+1} {option["value"]}", score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_set_notifications(guilds, dms, guild_id, channel_id, ping_options, query_in, score_cutoff=15):
    """Search for notification settings"""
    options = []
    query = query_in.lower()
    query_words = query.split(" ")

    if guild_id:   # channel/category
        channel = None
        for guild in guilds:
            if guild["guild_id"] == guild_id:
                for channel in guild["channels"]:
                    if channel["id"] == channel_id:
                        break
                break
        if channel:
            message_notifications = channel.get("message_notifications", 0)
            if channel["type"] == 4:
                default_val = guild["message_notifications"]
            else:
                for category in guild["channels"]:
                    if category["type"] == 4 and category["id"] == channel["parent_id"]:
                        default_val = category["message_notifications"]
                        default_val = default_val - 10 if default_val >= 10 else default_val
                        break
                else:
                    default_val = 2
            default = "default" + f" ({"server" if channel["type"] == 4 else "category"}: {ping_options[default_val]})"
            message_notifications = 3 if message_notifications >= 10 else message_notifications
            for num, option in enumerate(ping_options[:-1] + [default]):
                if num == message_notifications:
                    options.append((f"* {option}", query_words[0] + " " + option.split(" ")[0]))
                else:
                    options.append((option, query_words[0] + " " + option.split(" ")[0]))
    else:
        for dm in dms:
            if dm["id"] == channel_id:
                options.append(("No notification settings for DM", None))
                return options
        else:   # guild
            guild = None
            for guild in guilds:
                if guild["guild_id"] == channel_id:
                    break
            if guild:
                message_notifications = guild.get("message_notifications", 0)
                for num, option in enumerate(ping_options):
                    if num == message_notifications:
                        options.append((f"* {option}", f"{" ".join(query_words[:2])}{option}"))
                    else:
                        options.append((option, f"{" ".join(query_words[:2])}{option}"))
                options.append((f"suppress_everyone = {guild.get("suppress_everyone", False)}", f"{" ".join(query_words[:2])}suppress_everyone"))
                options.append((f"suppress_roles = {guild.get("suppress_roles", False)}", f"{" ".join(query_words[:2])}suppress_roles"))

    results = []
    for option in options:
        score = fuzzy_match_score(query_words[1], option[0].replace("*", " ").strip())
        if query_words[1] and score < score_cutoff:
            continue
        results.append((option[0], option[1], score))

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_client_commands(commands, query, limit=50, score_cutoff=15):
    """Search for client commands"""
    results = []
    worst_score = score_cutoff

    for command in commands:
        score = fuzzy_match_score(query, command[1])
        if score < worst_score:
            continue
        heapq.heappush(results, (*command, score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_games(games, blacklist, query, limit=50, score_cutoff=15):
    """Search for settings"""
    results = []
    worst_score = score_cutoff

    for game_id, game_name in games:
        if game_id in blacklist:
            formatted = game_name + " (blacklisted)"
        else:
            formatted = game_name
        score = fuzzy_match_score(query, formatted)
        if score < worst_score and query:
            continue
        heapq.heappush(results, (formatted, f"game_detection_blacklist {game_name}", score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_tabs(tabs, query, limit=50, score_cutoff=15):
    """Search for tabs"""
    results = []
    worst_score = score_cutoff

    for num, tab in enumerate(tabs):
        formatted = f"{num + 1} - {tab["channel_name"]} ({tab["guild_name"]})"
        score = fuzzy_match_score(query, formatted)
        if score < worst_score and query:
            continue
        heapq.heappush(results, (formatted, f"switch_tab {num + 1}", score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_app_commands(guild_apps, guild_commands, my_apps, my_commands, depth, guild_commands_permitted, dm, assist_skip_app_command, match_command_arguments, query, limit=50, score_cutoff=15):
    """Compatibility wrapper for the deprecated slash-command assist search."""
    return deprecated_search_app_commands(
        guild_apps,
        guild_commands,
        my_apps,
        my_commands,
        depth,
        guild_commands_permitted,
        dm,
        assist_skip_app_command,
        match_command_arguments,
        query,
        limit,
        score_cutoff,
    )
