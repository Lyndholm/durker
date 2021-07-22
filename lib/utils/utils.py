import fnmatch
import inspect
import json
import os
from datetime import datetime
from pathlib import Path

import aiofiles
import discord
from discord.ext import commands
from discord.ext.buttons import Paginator

from ..db import db


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


def load_commands_from_json(cog_name: str = None) -> dict:
    """Returns a dictionary containing all commands of the specified cog"""

    f = open('./data/commands.json', 'r', encoding='utf8')
    commands = json.load(f)

    if cog_name is not None:
        return commands[cog_name]
    else:
        return commands


async def insert_new_user_in_db(member: discord.Member) -> None:
    """Adds user data to the database"""

    tables = ["casino", "durka_stats", "leveling", "users_stats"]
    for table in tables:
        db.insert(f"{table}", {"user_id": member.id})

    db.insert("users_info", {"user_id": member.id,
                             "nickname": member.display_name,
                             "joined_at": member.joined_at,
                             "mention": member.mention})
    await try_to_restore_stats(member)


def delete_user_from_db(user_id: int):
    """Deletes user data from the database"""

    tables = [
        'casino', 'durka_stats', 'fn_profiles', 'leveling',
        'users_stats', 'users_info', 'stats_customization'
    ]

    for table in tables:
        db.execute(f"DELETE FROM {table} WHERE user_id = {user_id}")
        db.commit()


async def dump_user_data_in_json(member: discord.Member) -> None:
    """Dump part of the user's data to a json file"""

    data = {}
    cursor = db.get_cursor()

    cursor.execute("SELECT * FROM casino where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["casino"] = {"cash": rec[1], "e-cash": rec[2], "credits": rec[3]}

    cursor.execute(
        "SELECT * FROM durka_stats where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["durka_stats"] = {"available_durka_calls": rec[1],
                           "received_durka_calls": rec[2], "sent_durka_calls": rec[3]}

    cursor.execute("SELECT * FROM leveling where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["leveling"] = {"level": rec[1], "xp": rec[2], "xp_total": rec[3]}

    cursor.execute("SELECT * FROM users_info where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["users_info"] = {"joined_at": str(rec[3]), "brief_biography": rec[4]}

    cursor.execute(
        "SELECT * FROM users_stats where user_id = %s", (member.id,))
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
        "warns_story": rec[10],
        "roles": [role.name for role in member.roles]
    }

    cursor.execute(
        "SELECT * FROM stats_customization where user_id = %s", (member.id,))
    rec = cursor.fetchone()
    data["stats_customization"] = {
        "rank_background_color": rec[1],
        "rank_background_image": rec[2],
        "rank_bar_color": rec[3],
        "rank_level_int_color": rec[4]
    }

    timestamp = int(datetime.now().timestamp())

    async with aiofiles.open(f'./data/users_backup/{member.id}_{timestamp}.json', 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))


async def try_to_restore_stats(member: discord.Member) -> None:
    backups = fnmatch.filter(os.listdir(
        './data/users_backup/'), f'{member.id}_*.json')
    if not backups:
        return

    file = sorted(backups)[-1]
    async with aiofiles.open(f'./data/users_backup/{file}', 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())

    if (rep_rank := data['users_stats']['rep_rank']) < 0:
        db.execute("UPDATE users_stats SET rep_rank = %s WHERE user_id = %s",
                   rep_rank, member.id)

    if (lost_rep := data['users_stats']['lost_reputation']) > 0:
        db.execute("UPDATE users_stats SET lost_reputation = %s WHERE user_id = %s",
                   lost_rep, member.id)

    if (profanity_triggers := data['users_stats']['profanity_triggers']) > 0:
        db.execute("UPDATE users_stats SET profanity_triggers = %s WHERE user_id = %s",
                   profanity_triggers, member.id)

    if (mutes_story := data['users_stats']['mutes_story']):
        db.execute("UPDATE users_stats SET mutes_story = %s WHERE user_id = %s",
                   json.dumps(mutes_story, ensure_ascii=False), member.id)

    if (warns_story := data['users_stats']['warns_story']):
        db.execute("UPDATE users_stats SET warns_story = %s WHERE user_id = %s",
                   json.dumps(warns_story, ensure_ascii=False), member.id)

    if (customization := data['stats_customization']):
        db.execute("UPDATE stats_customization SET rank_background_color = %s, "
                   "rank_background_image = %s, rank_bar_color = %s, rank_level_int_color = %s "
                   "WHERE user_id = %s", customization['rank_background_color'],
                   customization['rank_background_image'], customization['rank_bar_color'],
                   customization['rank_level_int_color'], member.id)

    db.commit()


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
        db.execute("UPDATE users_stats SET rep_rank = rep_rank + %s WHERE user_id = %s",
                   value, user_id)
    elif action == '-':
        db.execute("UPDATE users_stats SET rep_rank = rep_rank - %s WHERE user_id = %s",
                   value, user_id)
        db.execute("UPDATE users_stats SET lost_reputation = lost_reputation + %s WHERE user_id = %s",
                   value, user_id)
    elif action == '=':
        db.execute("UPDATE users_stats SET rep_rank = %s WHERE user_id = %s",
                   value, user_id)
    db.commit()


def edit_user_messages_count(user_id: int = None, action: str = None, value: int = None):
    if action == '+':
        db.execute("UPDATE users_stats SET messages_count = messages_count + %s WHERE user_id = %s",
                   value, user_id)
    elif action == '-':
        db.execute("UPDATE users_stats SET messages_count = messages_count - %s WHERE user_id = %s",
                   value, user_id)
    elif action == '=':
        db.execute("UPDATE users_stats SET messages_count = %s WHERE user_id = %s",
                   value, user_id)
    db.commit()


def cooldown_timer_str(retry_after: float) -> str:
    """Return a string with cooldown timer"""
    seconds = round(retry_after, 2)
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    hours_plural = russian_plural(int(hours), ['час', 'часа', 'часов'])
    minutes_plural = russian_plural(
        int(minutes), ['минуту', 'минуты', 'минут'])
    seconds_plural = russian_plural(
        int(seconds+1), ['секунду', 'секунды', 'секунд'])
    time_str = ''
    if hours:
        time_str += f"**{hours} {hours_plural}** "
    if minutes:
        time_str += f"**{minutes} {minutes_plural}** "
    time_str += f"**{seconds+1} {seconds_plural}**."

    return time_str


def joined_date(member: discord.Member) -> datetime:
    """
    Return a datetime object that specifies the date and time that the member joined the guild.
    The data is taken from the database, not from Discord API.
    """
    try:
        joined_at = db.fetchone(
            ['joined_at'], 'users_info', 'user_id', member.id)[0]
        return joined_at
    except TypeError:
        return member.joined_at


async def get_command_required_level(cmd: commands.Command) -> int:
    """
    Return the level that is required to run the command.
    """
    path = Path(inspect.getfile(cmd.cog.__class__)).stem
    async with aiofiles.open('./data/commands.json', mode='r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    level = data[path][cmd.name]['required_level']
    return level


async def get_command_text_channels(cmd: commands.Command) -> str:
    """
    Return a string with channels where command can be invoked.
    """
    path = Path(inspect.getfile(cmd.cog.__class__)).stem
    async with aiofiles.open('./data/commands.json', mode='r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    help = data[path][cmd.name]['help'].split('\n')
    txt = str(*[i for i in help if 'Работает ' in i])
    return txt


async def check_member_privacy(ctx: commands.Context, member: discord.Member) -> bool:
    """Check the member's privacy settings"""
    privacy_flag = db.fetchone(
        ['is_profile_public'], 'users_info', 'user_id', member.id)[0]
    if privacy_flag is False:
        embed = discord.Embed(
            title='❗ Внимание!', color=discord.Color.red(), timestamp=datetime.utcnow(),
            description=f'Статистика участника **{member.display_name}** ({member.mention}) скрыта. '
                        'Просматривать её может только владелец.')
        embed.set_footer(text=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.reply(embed=embed, mention_author=False)
        return False
    else:
        return True
