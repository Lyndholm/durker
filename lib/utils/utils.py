import fnmatch
import inspect
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import aiofiles
import asyncpg
import discord
from discord.ext import commands

from ..db import async_db, db


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


async def insert_new_user_in_db(db: async_db.DatabaseWrapper, pool: asyncpg.Pool, member: discord.Member) -> None:
    """Adds user data to the database"""

    tables = [
        'casino', 'durka_stats', 'leveling', 'users_stats',
        'stats_customization'
    ]
    for table in tables:
        await db.insert(f"{table}", {"user_id": member.id})

    await db.insert("users_info",
                    {"user_id": member.id,
                     "nickname": member.display_name,
                     "joined_at": member.joined_at,
                     "mention": member.mention})
    await try_to_restore_stats(pool, member)


async def delete_user_from_db(pool: asyncpg.Pool, user_id: int):
    """Deletes user data from the database"""

    tables = (
        'casino', 'durka_stats', 'fn_profiles', 'leveling',
        'users_stats', 'users_info', 'stats_customization'
    )

    for table in tables:
        await pool.execute(f"DELETE FROM {table} WHERE user_id = {user_id}")


def type_converter(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()


async def dump_user_data_in_json(pool: asyncpg.Pool, member: discord.Member) -> None:
    """Dump the user's data to a json file"""

    data = {}
    tables = (
        'casino', 'durka_stats', 'leveling', 'users_info',
        'users_stats', 'stats_customization'
    )
    for table in tables:
        rec = await pool.fetchrow(f'SELECT * FROM {table} WHERE user_id = $1', member.id)
        temp = {}
        for key, value in rec.items():
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except:
                    pass
            temp[key] = value
        data[table] = temp

    data['users_stats']['roles'] = [role.name for role in member.roles]

    timestamp = int(datetime.now().timestamp())

    async with aiofiles.open(f'./data/users_backup/{member.id}_{timestamp}.json', 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=type_converter))


async def try_to_restore_stats(pool: asyncpg.Pool, member: discord.Member) -> None:
    backups = fnmatch.filter(os.listdir(
        './data/users_backup/'), f'{member.id}_*.json')
    if not backups:
        return

    file = sorted(backups)[-1]
    async with aiofiles.open(f'./data/users_backup/{file}', 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())

    if (rep_rank := data['users_stats']['rep_rank']) < 0:
        await pool.execute("UPDATE users_stats SET rep_rank = $1 WHERE user_id = $2",
                           rep_rank, member.id)

    if (lost_rep := data['users_stats']['lost_reputation']) > 0:
        await pool.execute("UPDATE users_stats SET lost_reputation = $1 WHERE user_id = $2",
                           lost_rep, member.id)

    if (profanity_triggers := data['users_stats']['profanity_triggers']) > 0:
        await pool.execute("UPDATE users_stats SET profanity_triggers = $1 WHERE user_id = $2",
                           profanity_triggers, member.id)

    if (mutes_story := data['users_stats']['mutes_story']):
        await pool.execute("UPDATE users_stats SET mutes_story = $1 WHERE user_id = $2",
                           json.dumps(mutes_story, ensure_ascii=False), member.id)

    if (warns_story := data['users_stats']['warns_story']):
        await pool.execute("UPDATE users_stats SET warns_story = $1 WHERE user_id = $2",
                           json.dumps(warns_story, ensure_ascii=False), member.id)


def clean_code(content: str) -> str:
    """Clear code the ``` chars from"""
    if content.startswith("```") and content.endswith("```"):
        return "\n".join(content.split("\n")[1:])[:-3]
    else:
        return content


def find_n_term_of_arithmetic_progression(a1: int, d: int, n: int) -> int:
    return (a1 + (n-1)*d)


async def edit_user_reputation(pool: asyncpg.Pool, user_id: int = None, action: str = None, value: int = None):
    if action == '+':
        await pool.execute("UPDATE users_stats SET rep_rank = rep_rank + $1 WHERE user_id = $2",
                           value, user_id)
    elif action == '-':
        await pool.execute("UPDATE users_stats SET rep_rank = rep_rank - $1 WHERE user_id = $2",
                           value, user_id)
        await pool.execute("UPDATE users_stats SET lost_reputation = lost_reputation + $1 WHERE user_id = $2",
                           value, user_id)
    elif action == '=':
        await pool.execute("UPDATE users_stats SET rep_rank = $1 WHERE user_id = $2",
                           value, user_id)


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


async def joined_date(pool: asyncpg.Pool, member: discord.Member) -> datetime:
    """
    Return a datetime object that specifies the date and time that the member joined the guild.
    The data is taken from the database, not from Discord API.
    """
    try:
        joined_at = await pool.fetchval(
            'SELECT joined_at FROM users_info WHERE user_id = $1', member.id)
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


async def check_member_privacy(pool: asyncpg.Pool, ctx: commands.Context, member: discord.Member) -> bool:
    """Check the member's privacy settings"""
    privacy_flag = await pool.fetchval('SELECT is_profile_public FROM users_info WHERE user_id = $1', member.id)
    if privacy_flag is False:
        return False
    else:
        return True


async def get_context_target(pool: asyncpg.Pool,
                             ctx: commands.Context,
                             target: Optional[discord.Member]
                            ) -> Union[discord.Member, bool]:
    if target and target != ctx.author:
        if (await check_member_privacy(pool, ctx, target)) is False:
            embed = discord.Embed(
                title='❗ Внимание!', color=discord.Color.red(), timestamp=datetime.utcnow(),
                description=f'Статистика участника **{target.display_name}** ({target.mention}) скрыта. '
                             'Просматривать её может только владелец.')
            embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed, mention_author=False)
            return False
        else:
            return target
    else:
        return ctx.author
