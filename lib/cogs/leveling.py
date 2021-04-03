from datetime import datetime, timedelta
from math import floor
from random import randint

from discord import Embed, Message, TextChannel
from discord.ext.commands import Cog, command, guild_only

from ..db import db
from ..utils.decorators import listen_for_guilds
from ..utils.utils import (edit_user_reputation,
                           find_n_term_of_arithmetic_progression,
                           load_commands_from_json)

cmd = load_commands_from_json("leveling")


class Leveling(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profanity_whitelisted_users = (
            384728793895665675, #tvoya_pechal
            342783617983840257, #lexenus
            375722626636578816, #lyndholm
        )
        self.channels_with_xp_counting = (
            546404724216430602, #админы-текст
            686499834949140506, #гвардия-общение
            698568751968419850, #спонсорское-общение
            721480135043448954, #общение (главный чат)
            546408250158088192, #поддержка,
            644523860326219776, #медиа,
            # 793153650083627018, #баги
            # 640475254128640003, #творческий-режим
            # 546700132390010882, #ваши-вопросы
            # 639925210849476608, #заявки-на-рассмотрение
            # 811901577396092930, #жалобы
            708601604353556491, #консоль на dev сервере
            777979537795055636, #testing на dev сервере
        )

    async def can_message_be_counted(self, message: Message) -> bool:
        message_content = message.clean_content.replace("*", "")
        ctx = await self.bot.get_context(message)

        if not message.author.bot and isinstance(message.channel, TextChannel):
            if self.bot.profanity.contains_profanity(message_content):
                if message.author.id not in self.profanity_whitelisted_users:
                    return False
            if not ctx.command:
                if message.channel.id in self.channels_with_xp_counting:
                    if len(message.clean_content) > 2:
                        if message.clean_content[0] != "<" and message.clean_content[-1] != ">":
                            return True
                    elif message.attachments:
                        return True
                    else:
                        return False

    async def process_xp(self, message: Message):
        level, xp, xp_total, xp_lock = db.fetchone(['level', 'xp', 'xp_total', 'xp_lock'], 'leveling', 'user_id', message.author.id)

        if datetime.now() > xp_lock:
            await self.add_xp(message, xp, xp_total, level)

    async def add_xp(self, message: Message, xp: int, xp_total: int, level: int):
        xp_to_add = randint(5, 15)
        xp_end = floor(5 * (level ^ 2) + 50 * level + 100)

        db.execute("UPDATE leveling SET xp = xp + %s, xp_total = xp_total + %s WHERE user_id = %s", xp_to_add, xp_to_add, message.author.id)
        db.commit()

        if xp_end < xp + xp_to_add:
            await self.increase_user_level(message, xp, xp_total, xp_to_add, xp_end, level)

        db.execute("UPDATE leveling SET xp_lock = %s WHERE user_id = %s", datetime.now() + timedelta(seconds=60), message.author.id)
        db.commit()

    async def increase_user_level(self,  message: Message, xp: int, xp_total: int, xp_to_add: int, xp_end: int, level: int):
        db.execute(
            "UPDATE leveling SET level = %s, xp = %s, xp_total = xp_total - %s WHERE user_id = %s",
            level+1, 0, (xp + xp_to_add) - xp_end, message.author.id
        )
        db.commit()

        rep_reward = find_n_term_of_arithmetic_progression(10, 10, level+1)
        edit_user_reputation(message.author.id, '+', rep_reward)

        embed = Embed(
            title='🎉 GG 🎉',
            color=message.author.color,
            description=f'Участник {message.author.mention} достиг нового уровня: **{level + 1}** 🥳'
                        f'\nРепутация пользователя увеличена на **{rep_reward}** очков.'
        )
        await message.channel.send(embed=embed, delete_after=15)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("leveling")

    @Cog.listener()
    @listen_for_guilds()
    async def on_message(self, message):
        if await self.can_message_be_counted(message):
            await self.process_xp(message)

    @command(name=cmd["rank"]["name"], aliases=cmd["rank"]["aliases"],
            brief=cmd["rank"]["brief"],
            description=cmd["rank"]["description"],
            usage=cmd["rank"]["usage"],
            help=cmd["rank"]["help"],
            hidden=cmd["rank"]["hidden"], enabled=True)
    @guild_only()
    async def rank_command(self, ctx):
        xp, xp_total, level = db.fetchone(['xp', 'xp_total', 'level'], 'leveling', 'user_id', ctx.author.id)
        xp_end = floor(5 * (level ^ 2) + 50 * level + 100)
        boxes = int((xp/(200*((1/2) * (level+1)))) * 20)

        cursor = db.get_cursor()
        cursor.execute("SELECT user_id FROM leveling ORDER BY xp_total DESC")
        data = cursor.fetchall()

        embed = Embed(title=f'Статистика уровней {ctx.author.display_name}', color=ctx.author.color)
        embed.set_thumbnail(url=ctx.author.avatar_url)
        fields = [
            ('Уровень', level, True),
            ('XP', xp, True),
            ('Всего XP', xp_total, True),
            ('До нового уровня осталось', f'{xp_end - xp} XP', True),
            ('Позиция в рейтинге', [i for sub in data for i in sub].index(ctx.author.id)+1, True),
            ('Прогресс уровня', f'{round(xp/xp_end*100)}%', True),
            ('Прогресс бар', boxes * '🟦' + (20-boxes) * '⬜', False)
        ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Leveling(bot))
