from datetime import datetime
from itertools import cycle

from discord import Activity, ActivityType
from discord.ext import tasks
from discord.ext.commands import Cog
from discord.utils import get

from ..utils.constants import (CAPTAIN_ROLE_ID, OLD_ROLE_ID, VETERAN_ROLE_ID,
                               WORKER_ROLE_ID)
from ..utils.utils import edit_user_reputation

ACTIVITIES = cycle([
    '+help | durker.fun',
    '+help | docs.durker.fun',
    '+help | fortnitefun.ru',
    '+help | youtube.com/c/fnfun',
    '+help | vk.com/fnfun',
    ])

class BackgroundTasks(Cog, name='Фоновые процессы'):
    def __init__(self, bot):
        self.bot = bot
        self.change_bot_activity.start()
        self.check_activity_role.start()
        self.update_user_nickname.start()
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    async def init_vars(self):
        self.mod_cog = self.bot.get_cog('Модерация')

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.mod_cog = self.bot.get_cog('Модерация')
            self.bot.cogs_ready.ready_up("background_tasks")


    @tasks.loop(minutes=3.0)
    async def change_bot_activity(self):
        await self.bot.change_presence(activity=Activity(type=ActivityType.listening, name=next(ACTIVITIES)))

    @change_bot_activity.before_loop
    async def before_change_bot_activity(self):
        await self.bot.wait_until_ready()


    @tasks.loop(minutes=10.0)
    async def check_activity_role(self):
        worker = get(self.bot.guild.roles, id=WORKER_ROLE_ID)
        old = get(self.bot.guild.roles, id=OLD_ROLE_ID)
        captain = get(self.bot.guild.roles, id=CAPTAIN_ROLE_ID)
        veteran = get(self.bot.guild.roles, id=VETERAN_ROLE_ID)

        for member in self.bot.guild.members:
            if self.mod_cog.is_member_muted(member) or member.pending:
                continue

            try:
                joined_at = await self.bot.pg_pool.fetchval(
                    'SELECT joined_at FROM users_info WHERE user_id = $1', member.id)
                messages_count = await self.bot.pg_pool.fetchval(
                    'SELECT messages_count FROM users_stats WHERE user_id = $1', member.id)
                time_delta = (datetime.utcnow() - joined_at).days
            except TypeError:
                continue

            if worker not in member.roles and messages_count >= 750 and time_delta >= 7:
                await member.add_roles(worker)
                await edit_user_reputation(self.bot.pg_pool, member.id, '+', 250)

            if old not in member.roles and messages_count >= 3_500 and time_delta >= 31:
                await member.add_roles(old)
                await edit_user_reputation(self.bot.pg_pool, member.id, '+', 750)

            if captain not in member.roles and messages_count >= 10_000 and time_delta >= 91:
                await member.add_roles(captain)
                await edit_user_reputation(self.bot.pg_pool, member.id, '+', 1_500)

            if veteran not in member.roles and messages_count >= 25_000 and time_delta >= 181:
                await member.add_roles(veteran)
                await edit_user_reputation(self.bot.pg_pool, member.id, '+', 3_000)

    @check_activity_role.before_loop
    async def before_check_activity_role(self):
        await self.bot.wait_until_ready()


    @tasks.loop(hours=3.5)
    async def update_user_nickname(self):
        for member in self.bot.guild.members:
            if member.pending:
                continue

            try:
                nickname = await self.bot.pg_pool.fetchval(
                    'SELECT nickname FROM users_info WHERE user_id = $1', member.id)
            except TypeError:
                continue

            if nickname != member.display_name:
                await self.bot.pg_pool.execute(
                    'UPDATE users_info SET nickname = $1 WHERE user_id = $2',
                    member.display_name, member.id
                )

    @update_user_nickname.before_loop
    async def before_update_user_nickname(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(BackgroundTasks(bot))
