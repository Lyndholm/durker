import json
import discord

from ..db import db
from datetime import datetime
from discord.ext.buttons import Paginator


class Pag(Paginator):
    async def teardown(self):
        try:
            await self.page.clear_reactions()
        except discord.HTTPException:
            pass


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
    """Adds user data to the database"""

    tables = ["casino", "durka_stats", "leveling", "users_stats"]
    for table in tables:
        db.insert(f"{table}", {"user_id": member.id})

    db.insert("users_info", {"user_id": member.id, 
                            "nickname": member.display_name,
                            "mention": member.mention})


def delete_user_from_db(user_id: int):
    """Deletes user data from the database"""

    tables = ["casino", "durka_stats", "fn_profiles", "leveling", "users_stats", "users_info"]

    for table in tables:
        db.execute(f"DELETE FROM {table} WHERE user_id = {user_id}")
        db.commit()


def dump_user_data_in_json(member: discord.Member):
    """Dump part of the user's data to a json file"""

    data = {}
    cursor = db.get_cursor()

    cursor.execute("SELECT * FROM casino where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["casino"] = {"cash":rec[1],"e-cash":rec[2],"credits":rec[3]}

    cursor.execute("SELECT * FROM durka_stats where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["durka_stats"] = {"available_durka_uses":rec[1],"received_durka_calls":rec[2],"sent_durka_calls":rec[3]}

    cursor.execute("SELECT * FROM leveling where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["leveling"] = {"level":rec[1],"xp":rec[2],"total_xp":rec[3]}

    cursor.execute("SELECT * FROM users_info where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["users_info"] = {"joined_at":str(member.joined_at),"brief_biography":rec[4]}

    cursor.execute("SELECT * FROM users_stats where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["users_stats"] = {
        "achievements_list": rec[1],
        "messages_count": rec[2],
        "rep_rank": rec[4],
        "lost_reputation": rec[5],
        "profanity_triggers": rec[6],
        "invoice_time": rec[7],
        "purchases": rec[8],
        "mutes_story": rec[9],
        "warns_story": rec[10]
    }

    time_now = datetime.now().strftime("%d.%m.%Y %H.%M.%S")

    with open(f"./data/users_backup/{member.id} [{time_now}].json", "w") as f:
        json.dump(data, f, indent=4, sort_keys=True, ensure_ascii=False)


def clean_code(content: str) -> str:
    """Clear code the ``` chars from"""
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content


def find_n_term_of_arithmetic_progression(a1: int, d: int, n: int) -> int:
    return (a1 + (n-1)*d)


def edit_user_reputation(user_id: int = None, action: str = None, value: int = None):
    if action == '+':
        db.execute(f"UPDATE users_stats SET rep_rank = rep_rank + {value} WHERE user_id = {user_id}")
    elif action == '-':
        db.execute(f"UPDATE users_stats SET rep_rank = rep_rank - {value} WHERE user_id = {user_id}")
        db.execute(f"UPDATE users_stats SET lost_reputation = lost_reputation + {value} WHERE user_id = {user_id}")
    elif action == '=':
        db.execute(f"UPDATE users_stats SET rep_rank = {value} WHERE user_id = {user_id}")
    db.commit()
