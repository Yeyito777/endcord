# Copyright (C) 2025-2026 SparkLost
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.

"""Archived compose-time assist implementations.

This preserves the legacy #channel, @mention/@role, :emoji, and ;sticker;
helper searches plus the old slash/app-command compose parser/search while
those entry points are deprecated in the live client.
"""

import heapq
import importlib.util
import re

import emoji

LEGACY_ASSIST_TRIGGERS = ("#", "@", ":", ";")
LEGACY_APP_COMMAND_ASSIST_TRIGGER = "/"

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

match_channel = re.compile(r"<#(\d*)>")
match_profile = re.compile(r"<@(\d*)>")
match_command_arguments = re.compile(r"--(\S+)=(\w+|\"[^\"]+\")?")

def check_start_command(text, my_commands, guild_commands, permitted_guild_commands):
    """Check if string is valid start of command"""
    app_name = text.split(" ")[0][1:].lower()
    if not app_name:
        return False
    for command in my_commands:
        if command["app_name"].lower().replace(" ", "_") == app_name:
            return True
    for num, command in enumerate(guild_commands):
        if permitted_guild_commands[num] and command["app_name"].lower().replace(" ", "_") == app_name:
            return True
    return False

def verify_option_type(option_value, option_type, roles, channels):
    """Check if option value is of correct type"""
    if option_type in (1, 2):   # SUB_COMMAND and SUB_COMMAND_GROUP
        if not option_value:
            return False   # skip subcommands
    if option_type == 3:   # STRING
        return not (
            bool(re.search(match_profile, option_value)) or
            bool(re.search(match_channel, option_value))
        )
    if option_type == 4:   # INTEGER
        try:
            int(option_value)
            return True
        except ValueError:
            pass
    elif option_type == 5:   # BOOLEAN
        try:
            bool(option_value)
            return True
        except ValueError:
            pass
    elif option_type == 6:   # USER
        return bool(re.search(match_profile, option_value))
    elif option_type == 7:   # CHANNEL
        match = re.search(match_channel, option_value)
        if match:
            channel_id = match.group(1)
            for channel in channels:
                if channel["id"] == channel_id:
                    return True
    elif option_type == 8:   # ROLE
        match = re.search(match_profile, option_value)
        if match:
            role_id = match.group(1)
            for role in roles:
                if role["id"] == role_id:
                    return True
    elif option_type == 9:   # MENTIONABLE
        return bool(re.search(match_profile, option_value))
    elif option_type == 10:   # NUMBER
        try:
            float(option_value)
            return True
        except ValueError:
            pass
    elif option_type == 11:   # ATTACHMENT
        if option_value == 0:
            return True
    return False

def app_command_string(text, my_commands, guild_commands, permitted_guild_commands, roles, channels, dm, autocomplete):
    """Parse app command string and prepare data payload"""
    app_name = text.split(" ")[0][1:].lower()
    if not app_name:
        return None, None, None

    #  verify command
    command_name = text.split(" ")[1]
    if command_name.startswith("--"):
        return None, None, None
    for num, command in enumerate(guild_commands):
        if permitted_guild_commands[num] and command["name"] == command_name and command["app_name"].lower().replace(" ", "_") == app_name:
            app_id = command["app_id"]
            break
    else:
        for command in my_commands:
            if command["name"] == command_name and command["app_name"].lower().replace(" ", "_") == app_name:
                if dm and not command.get("dm"):
                    return None, None, None   # command not allowed in dm
                app_id = command["app_id"]
                break
        else:
            return None, None, None

    # get subcommands
    try:
        subcommand_group_name = text.split(" ")[2]
        if subcommand_group_name.startswith("--"):
            subcommand_group_name = None
    except IndexError:
        subcommand_group_name = None
    if subcommand_group_name:
        try:
            subcommand_name = text.split(" ")[3]
            if subcommand_name.startswith("--"):
                subcommand_name = None
        except IndexError:
            subcommand_name = None
    else:
        subcommand_name = None

    command_options = []
    for match in re.finditer(match_command_arguments, text):
        if len(match.groups()) == 2:
            value = match.group(2)
        else:
            value = 0
        command_options.append((match.group(1), value))   # (name, value)
    context_options = command.get("options", [])

    # verify subcommands and groups
    subcommand = None
    subcommand_group = None
    if subcommand_group_name:
        for subcmd in context_options:
            if subcmd["type"] == 1 and subcmd["name"] == subcommand_group_name:   # subcommand
                subcommand = subcmd
                context_options = subcmd.get("options", [])
                break
            elif subcmd["type"] == 2 and subcmd["name"] == subcommand_group_name:   # group
                subcommand_group = subcmd
                break
    if subcommand_group and subcommand_name:   # subcommand after group
        for subcmd in subcommand_group.get("options", []):
            if subcmd["type"] == 1 and subcmd["name"] == subcommand_name:
                subcommand = subcmd
                context_options = subcmd.get("options", [])
                break

    # add and verify options
    need_attachment = False
    options = []
    required = True
    for num, (option_name, option_value) in enumerate(command_options):
        for option in context_options:
            if option["name"] == option_name:
                break
        option_value_clean = option_value
        if option["type"] == 11:
            need_attachment = True
            option_value_clean = 0
        if not autocomplete and not (option_value_clean and verify_option_type(option_value_clean, option["type"], roles, channels)):
            return None, None, None
        option_dict = {
            "type": option["type"],
            "name": option["name"],
            "value": option_value_clean,
        }
        if autocomplete and num == len(command_options) - 1:   # if its last option
            option_dict["focused"] = True   # what "focused" means ?
        options.append(option_dict)

    # check for required
    for option in context_options:
        if option.get("required"):
            for option_name, _ in command_options:
                if option["name"] == option_name:
                    break
            else:
                return None, None, None   # missing required option

    # dont allow command with options but none is set
    if not options and not subcommand_group_name and context_options and required:
        return None, None, None

    # add subcommands and groups
    if subcommand:
        options = [{
            "type": subcommand["type"],
            "name": subcommand["name"],
            "options": options,
        }]
        if not options[0]["options"]:
            options[0].pop("options")
    if subcommand_group:
        options = [{
            "type": subcommand_group["type"],
            "name": subcommand_group["name"],
            "options": options,
        }]
        if not options[0]["options"]:
            options[0].pop("options")
            return None, None, None   # cant have group without subcommand

    command_data = {
        "version": command["version"],
        "id": command["id"],
        "name": command["name"],
        "type": 1,   # only slash commands
        "options": options,
        "attachments": [],
    }
    return command_data, app_id, need_attachment

def search_channels_guild(channels, query, limit=50, score_cutoff=15):
    """Search channels for the archived #channel compose helper."""
    results = []
    worst_score = score_cutoff

    for channel in channels:
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


def search_usernames_roles(roles, query_results, guild_id, gateway, query, presences=[], limit=50, score_cutoff=15):
    """Search for usernames and roles"""
    results = []
    worst_score = score_cutoff

    # roles first
    for role in roles:
        formatted = f"{role["name"]} - role"
        score = fuzzy_match_score(query, formatted)
        if score < worst_score:
            continue
        heapq.heappush(results, (formatted, f"&{role["id"]}", score))
        if len(results) > limit:
            heapq.heappop(results)
            worst_score = results[0][2]

    if query_results:
        for member in query_results:
            formatted = f"{member["username"]} {member["name"]}"
            score = fuzzy_match_score(query, formatted)
            if score < worst_score:
                continue
            if member["name"]:
                member_name = f" ({member["name"]})"
            else:
                member_name = ""
            formatted = f"{member["username"]}{member_name}"
            for presence in presences:
                if presence["id"] == member["id"]:
                    status = presence["status"].capitalize().replace("Dnd", "DnD")
                    formatted += f" - {status}"
                    break
            heapq.heappush(results, (formatted, member["id"], score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]
    else:
        gateway.request_members(
            guild_id,
            None,
            query=query,
            limit=10,
        )

    return sorted(results, key=lambda x: x[2], reverse=True)


def search_emojis(all_emojis, premium, guild_id, query, safe_emoji=False, limit=50, score_cutoff=15):
    """Search emoji for the archived compose-time emoji assist."""
    results = []
    worst_score = score_cutoff

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

    if len(results) < limit:
        for key, item in emoji.EMOJI_DATA.items():
            if item["status"] > 2:
                continue
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
    """Search stickers for the archived ;sticker; compose helper."""
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


def search_app_commands(guild_apps, guild_commands, my_apps, my_commands, depth, guild_commands_permitted, dm, assist_skip_app_command, match_command_arguments, query, limit=50, score_cutoff=15):
    """Search for app commands"""
    results = []
    worst_score = score_cutoff
    query_words = query.split(" ")
    autocomplete = False
    if depth == 1 and assist_skip_app_command:
        depth = 2   # skip app assist on depth 1

    if depth == 1:   # app
        assist_app = query_words[0].replace("_", " ")
        # list apps
        for app in guild_apps:
            score = fuzzy_match_score(assist_app, app["name"])
            if score < worst_score and assist_app:   # show all if no text is typed
                continue
            clean_name = app["name"].lower().replace(" ", "_")
            heapq.heappush(results, (f"{clean_name} - guild app", f"/{clean_name}", score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]
        for app in my_apps:
            score = fuzzy_match_score(assist_app, app["name"])
            if score < worst_score and assist_app:
                continue
            clean_name = app["name"].lower().replace(" ", "_")
            heapq.heappush(results, (f"{clean_name} - user app", f"/{clean_name}", score))
            if len(results) > limit:
                heapq.heappop(results)
                worst_score = results[0][2]

    elif depth == 2:   # command
        if assist_skip_app_command:
            assist_app_name = None
            assist_command = query_words[0].replace("_", " ")
        else:
            assist_app_name = query_words[0].lower()
            assist_command = query_words[1].replace("_", " ")
        # list commands
        found = False
        for num, command in enumerate(guild_commands):
            if (command["app_name"].lower().replace(" ", "_") == assist_app_name or assist_skip_app_command) and guild_commands_permitted[num]:
                command_name = command["name"].lower()
                score = fuzzy_match_score(assist_command, command_name)
                if score < worst_score and assist_command:
                    continue
                if assist_skip_app_command:
                    name = f"{command_name.replace(" ", "_")} ({command["app_name"]})"
                    value = f"{command["app_name"].lower().replace(" ", "_")} {command_name.replace(" ", "_")}"
                else:
                    name = command_name.replace(" ", "_")
                    value = command_name.replace(" ", "_")
                if command.get("description"):
                    name += f" - {command["description"]}"
                heapq.heappush(results, (name, value, score))
                if len(results) > limit:
                    heapq.heappop(results)
                    worst_score = results[0][2]
                found = True
        if not found:    # skip my commands if found in guild commands
            for command in my_commands:
                if (command["app_name"].lower().replace(" ", "_") == assist_app_name or assist_skip_app_command) and ((not dm) or command.get("dm")):
                    command_name = command["name"].lower()
                    score = fuzzy_match_score(assist_command, command_name)
                    if score < worst_score and assist_command:
                        continue
                    if assist_skip_app_command:
                        name = f"{command_name.replace(" ", "_")} ({command["app_name"]})"
                        value = f"{command["app_name"].lower().replace(" ", "_")} {command_name.replace(" ", "_")}"
                    else:
                        name = command_name.replace(" ", "_")
                        value = command_name.replace(" ", "_")
                    if command.get("description"):
                        name += f" - {command["description"]}"
                    heapq.heappush(results, (name, value, score))
                    if len(results) > limit:
                        heapq.heappop(results)
                        worst_score = results[0][2]

    elif depth == 3:   # group/subcommand/option
        results.append(("EXECUTE", None, 10000))
        assist_app_name = query_words[0].lower()
        assist_command = query_words[1].lower()
        assist_subcommand = query_words[2].replace("_", " ")
        # find command
        for num, command in enumerate(guild_commands):
            if command["app_name"].lower().replace(" ", "_") == assist_app_name and guild_commands_permitted[num] and assist_command == command["name"].lower().replace(" ", "_"):
                break
        else:
            for command in my_commands:
                if command["app_name"].lower().replace(" ", "_") == assist_app_name and assist_command == command["name"].lower().replace(" ", "_") and ((not dm) or command.get("dm")):
                    break
            else:
                command = None
        if command:
            # list groups/subcommands/options
            for subcommand in command.get("options", []):
                subcommand_name = subcommand["name"].lower()
                score = fuzzy_match_score(assist_subcommand, subcommand_name)
                if score < worst_score and assist_subcommand:
                    continue
                if subcommand["type"] == 1:
                    name = f"{subcommand_name.replace(" ", "_")} - subcommand"
                    value = subcommand_name.replace(" ", "_")
                elif subcommand["type"] == 2:
                    name = f"{subcommand_name.replace(" ", "_")} - group"
                    value = subcommand_name.replace(" ", "_")
                else:
                    name = f"{subcommand_name.replace(" ", "_")} - option: {COMMAND_OPT_TYPE[int(subcommand["type"])-1]}"
                    value = f"--{subcommand_name.replace(" ", "_")}="
                if subcommand.get("required"):
                    name += " (required)"
                if subcommand.get("description"):
                    name += f" - {subcommand["description"]}"
                heapq.heappush(results, (name, value, score))
                if len(results) > limit:
                    heapq.heappop(results)
                    worst_score = results[0][2]
            # list option choices
            else:
                match = re.search(match_command_arguments, query_words[2].lower())
                if match:
                    for option in command.get("options", []):
                        if option["name"].lower() == match.group(1):
                            break
                    else:
                        option = None
                    if option and "choices" in option:
                        value = match.group(2).replace("_", " ") if match.group(2) else ""
                        for choice in option["choices"]:
                            score = fuzzy_match_score(value, choice["name"])
                            if score < worst_score and value:
                                continue
                            heapq.heappush(results, (choice["name"], choice["value"], score))
                            if len(results) > limit:
                                heapq.heappop(results)
                                worst_score = results[0][2]
                    elif option and option.get("autocomplete"):
                        autocomplete = True

    elif depth == 4:   # groups subcommand and options
        results.append(("EXECUTE", None, 10000))
        assist_app_name = query_words[0].lower()
        assist_command = query_words[1].lower()
        assist_subcommand = query_words[2].lower()
        assist_group_subcommand = query_words[3].replace("_", " ")
        options_only = False
        # find command
        for num, command in enumerate(guild_commands):
            if command["app_name"].lower().replace(" ", "_") == assist_app_name and guild_commands_permitted[num] and assist_command == command["name"].lower().replace(" ", "_"):
                break
        else:
            for command in my_commands:
                if command["app_name"].lower().replace(" ", "_") == assist_app_name and assist_command == command["name"].lower().replace(" ", "_") and ((not dm) or command.get("dm")):
                    break
            else:
                command = None
        if command:
            # find subcommand
            for subcommand in command.get("options", []):
                if subcommand["name"].lower().replace(" ", "_") == assist_subcommand:
                    break
            else:
                if re.search(match_command_arguments, assist_subcommand):
                    subcommand = command   # when adding multiple options
                    options_only = True
                else:
                    subcommand = None
            if subcommand:
                # list group_subcommands/options
                for group_subcommand in subcommand.get("options", []):
                    group_subcommand_name = group_subcommand["name"].lower()
                    score = fuzzy_match_score(assist_group_subcommand, group_subcommand_name)
                    if score < worst_score and assist_group_subcommand:
                        continue
                    if options_only and group_subcommand["type"] in (1, 2):
                        continue   # skip non-options
                    if group_subcommand["type"] == 1:
                        name = f"{group_subcommand_name.replace(" ", "_")} - subcommand"
                        value = group_subcommand_name.replace(" ", "_")
                    else:
                        name = f"{group_subcommand_name.replace(" ", "_")} - option: {COMMAND_OPT_TYPE[int(group_subcommand["type"])-1]}"
                        value = f"--{group_subcommand_name.replace(" ", "_")}="
                    if group_subcommand.get("required"):
                        name += " (required)"
                    if group_subcommand.get("description"):
                        name += f" - {group_subcommand["description"]}"
                    heapq.heappush(results, (name, value, score))
                    if len(results) > limit:
                        heapq.heappop(results)
                        worst_score = results[0][2]
                # list option choices
                else:
                    match = re.search(match_command_arguments, query_words[3].lower())
                    if match:
                        for option in subcommand.get("options", []):
                            if option["name"].lower() == match.group(1):
                                break
                        else:
                            option = None
                        if option and "choices" in option:
                            value = match.group(2).replace("_", " ") if match.group(2) else ""
                            for choice in option["choices"]:
                                score = fuzzy_match_score(value, choice["name"])
                                if score < worst_score and value:
                                    continue
                                heapq.heappush(results, (choice["name"], choice["value"], score))
                                if len(results) > limit:
                                    heapq.heappop(results)
                                    worst_score = results[0][2]
                        elif option and option.get("autocomplete"):
                            autocomplete = True

    elif depth >= 5:   # options
        results.append(("EXECUTE", None, 10000))
        assist_app_name = query_words[0].lower()
        assist_command = query_words[1].lower()
        assist_subcommand = query_words[2].lower()
        assist_group_subcommand = query_words[3].lower()
        assist_option = query_words[4].replace("_", " ")
        options_only = False
        # find command
        for num, command in enumerate(guild_commands):
            if command["app_name"].lower().replace(" ", "_") == assist_app_name and guild_commands_permitted[num] and assist_command == command["name"].lower().replace(" ", "_"):
                break
        else:
            for command in my_commands:
                if command["app_name"].lower().replace(" ", "_") == assist_app_name and assist_command == command["name"].lower().replace(" ", "_") and ((not dm) or command.get("dm")):
                    break
            else:
                command = None
        if command:
            # find subcommand
            for subcommand in command.get("options", []):
                if subcommand["name"].lower().replace(" ", "_") == assist_subcommand:
                    break
            else:
                if re.search(match_command_arguments, assist_subcommand):
                    subcommand = command   # when adding multiple options
                    options_only = True
                else:
                    subcommand = None
            if subcommand:
                # find group subcommand
                for group_subcommand in subcommand.get("options", []):
                    if group_subcommand["name"].lower().replace(" ", "_") == assist_group_subcommand:
                        break
                else:
                    if re.search(match_command_arguments, assist_group_subcommand):
                        group_subcommand = subcommand   # when adding multiple options
                        options_only = True
                    else:
                        group_subcommand = None
                if group_subcommand:
                    # list options
                    for option in group_subcommand.get("options", []):
                        option_name = option["name"].lower()
                        score = fuzzy_match_score(assist_option, option_name)
                        if score < worst_score and assist_option:
                            continue
                        if options_only and option["type"] in (1, 2):
                            continue   # skip non-options
                        name = f"{option_name.replace(" ", "_")} - option: {COMMAND_OPT_TYPE[int(option["type"])-1]}"
                        value = f"--{option_name.replace(" ", "_")}="
                        if option.get("required"):
                            name += " (required)"
                        if option.get("description"):
                            name += f" - {option["description"]}"
                        heapq.heappush(results, (name, value, score))
                        if len(results) > limit:
                            heapq.heappop(results)
                            worst_score = results[0][2]
                    # list option choices
                    else:
                        match = re.search(match_command_arguments, query_words[4].lower())
                        if match:
                            for option in group_subcommand.get("options", []):
                                if option["name"].lower() == match.group(1):
                                    break
                            else:
                                option = None
                            if option and "choices" in option:
                                value = match.group(2).replace("_", " ") if match.group(2) else ""
                                for choice in option["choices"]:
                                    score = fuzzy_match_score(value, choice["name"])
                                    if score < worst_score and value:
                                        continue
                                    heapq.heappush(results, (choice["name"], choice["value"], score))
                                    if len(results) > limit:
                                        heapq.heappop(results)
                                        worst_score = results[0][2]
                            elif option and option.get("autocomplete"):
                                autocomplete = True

    return sorted(results, key=lambda x: x[2], reverse=True), autocomplete
