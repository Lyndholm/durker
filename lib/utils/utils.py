import json
import discord

from ..db import db


def russian_plural(value: int, quantitative: list) -> str:

    """Returns a string with a declined noun"""
    if value % 100 in (11, 12, 13, 14):
        return quantitative[2]
    if value % 10 == 1:
        return quantitative[0]
    if value % 10 in (2, 3, 4):
        return quantitative[1]
    return quantitative[2]


def load_commands_from_json(cog_name:str = None) -> dict:
    """Returns a dictionary containing all commands of the specified cog"""

    f = open('./data/commands.json', 'r', encoding = 'utf8')
    commands = json.load(f)

    if cog_name is not None:
        return commands[cog_name]
    else:
        return commands


def insert_new_user_in_db(member: discord.Member):
    db.insert("casino", {"user_id": member.id})
    db.insert("durka_stats", {"user_id": member.id})
    db.insert("leveling", {"user_id": member.id})
    db.insert("users_stats", {"user_id": member.id})
    db.insert("users_info", {"user_id": member.id, 
                            "nickname": member.display_name,
                            "mention": member.mention})
