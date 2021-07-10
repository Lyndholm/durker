import json
import os
from datetime import datetime
from itertools import cycle

import aiofiles
from aiohttp import ClientSession
from discord import Activity, ActivityType
from discord.ext import tasks
from discord.ext.commands import Cog
from discord.utils import get
from jishaku.functools import executor_function
from loguru import logger

from ..db import db
from ..utils.constants import (CAPTAIN_ROLE_ID, KAPITALIST_ROLE_ID,
                               MAGNAT_ROLE_ID, MECENAT_ROLE_ID, OLD_ROLE_ID,
                               VETERAN_ROLE_ID, WORKER_ROLE_ID)
from ..utils.utils import edit_user_reputation, joined_date

ITEM_SHOP_ENDPOINT = "https://fortnite-api.com/v2/shop/br/combined"
ACTIVITIES = cycle([
    '+help | durker.fun',
    '+help | docs.durker.fun',
    '+help | fortnitefun.ru',
    '+help | youtube.com/c/fnfun',
    '+help | vk.com/fnfun',
    '+help | USE CODE FNFUN'])

class BackgroundTasks(Cog, name='Фоновые процессы'):
    def __init__(self, bot):
        self.bot = bot
        self.change_bot_activity.start()
        self.check_activity_role.start()
        self.check_mecenat_role.start()
        self.check_supporter_role.start()
        self.update_user_nickname.start()
        self.update_fortnite_shop_hash.start()
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    @logger.catch
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
    @logger.catch
    async def check_activity_role(self):
        worker = get(self.bot.guild.roles, id=WORKER_ROLE_ID)
        old = get(self.bot.guild.roles, id=OLD_ROLE_ID)
        captain = get(self.bot.guild.roles, id=CAPTAIN_ROLE_ID)
        veteran = get(self.bot.guild.roles, id=VETERAN_ROLE_ID)

        for member in self.bot.guild.members:
            if self.mod_cog.is_member_muted(member) or member.pending:
                continue

            try:
                joined_at = joined_date(member)
                messages_count, rep_rank = db.fetchone(['messages_count', 'rep_rank'], 'users_stats', 'user_id', member.id)
                time_delta = (datetime.utcnow() - joined_at).days
            except TypeError:
                continue

            if worker not in member.roles and messages_count >= 750 and time_delta >= 7:
                await member.add_roles(worker)
                edit_user_reputation(member.id, '+', 250)

            if old not in member.roles and messages_count >= 3500 and time_delta >= 31:
                await member.add_roles(old)
                edit_user_reputation(member.id, '+', 750)

            if captain not in member.roles and messages_count >= 10000 and time_delta >= 91:
                await member.add_roles(captain)
                edit_user_reputation(member.id, '+', 1500)

            if veteran not in member.roles and messages_count >= 25000 and time_delta >= 181:
                await member.add_roles(veteran)
                edit_user_reputation(member.id, '+', 3000)

    @check_activity_role.before_loop
    async def before_check_activity_role(self):
        await self.bot.wait_until_ready()


    @tasks.loop(hours=24.0)
    @logger.catch
    async def check_mecenat_role(self):
        mecenat = get(self.bot.guild.roles, id=MECENAT_ROLE_ID)
        kapitalist = get(self.bot.guild.roles, id=KAPITALIST_ROLE_ID)

        for member in self.bot.guild.members:
            if self.mod_cog.is_member_muted(member) or member.pending:
                continue

            try:
                purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', member.id)[0]['vbucks_purchases']
            except TypeError:
                continue

            if purchases:
                lpd = purchases[-1]['date']
                if mecenat in member.roles and kapitalist not in member.roles:
                    if (datetime.now() - datetime.strptime(lpd, '%d.%m.%Y %H:%M:%S')).days > 90:
                        await member.remove_roles(mecenat, reason='С момента последней покупки прошло более 3 месяцев')

    @check_mecenat_role.before_loop
    async def before_check_mecenat_role(self):
        await self.bot.wait_until_ready()


    @tasks.loop(hours=1.0)
    @logger.catch
    async def check_supporter_role(self):
        kapitalist = get(self.bot.guild.roles, id=KAPITALIST_ROLE_ID)
        magnat = get(self.bot.guild.roles, id=MAGNAT_ROLE_ID)

        for member in self.bot.guild.members:
            if self.mod_cog.is_member_muted(member) or member.pending:
                continue

            try:
                purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', member.id)[0]
                vbucks_count = sum(purchases['vbucks_purchases'][i]['price'] for i in range(len(purchases['vbucks_purchases'])))
            except TypeError:
                continue

            if vbucks_count >= 10000 and kapitalist not in member.roles:
                await member.add_roles(kapitalist)
                edit_user_reputation(member.id, '+', 1000)
            if vbucks_count >= 25000 and magnat not in member.roles:
                await member.add_roles(magnat)
                edit_user_reputation(member.id, '+', 2500)

    @check_supporter_role.before_loop
    async def before_check_supporter_role(self):
        await self.bot.wait_until_ready()


    @tasks.loop(hours=3.5)
    @logger.catch
    async def update_user_nickname(self):
        for member in self.bot.guild.members:
            if member.pending:
                continue

            try:
                nickname = db.fetchone(['nickname'], 'users_info', 'user_id', member.id)[0]
            except TypeError:
                continue

            if nickname != member.display_name:
                db.execute('UPDATE users_info SET nickname = %s WHERE user_id = %s', member.display_name, member.id)
                db.commit()

    @update_user_nickname.before_loop
    async def before_update_user_nickname(self):
        await self.bot.wait_until_ready()


    @executor_function
    def create_item_shop_image(self, data: dict):
        if data['len'] <= 59:
            os.system("python ./athena/athena.py")
        else:
            os.system("python ./athena/athena_monotonic.py")

    @tasks.loop(minutes=1.0)
    @logger.catch
    async def update_fortnite_shop_hash(self):
        """Makes a request to the api and checks if the hash has been updated"""
        async with ClientSession() as session:
            async with session.get(url=ITEM_SHOP_ENDPOINT) as r:
                if r.status != 200:
                    return

                data = await r.json()
                new_hash = data['data']['hash']
                new_len = len(data['data']['featured']['entries']) + len(data['data']['daily']['entries'])
                async with aiofiles.open('athena/athena_cache.json', mode='r', encoding='utf-8') as f:
                    cached_data = json.loads(await f.read())
                    cached_hash = cached_data['hash']
                    cached_len = cached_data['len']

        if new_hash != cached_hash or new_len != cached_len:
            date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            cache = {"hash": new_hash, "date":date, "len": new_len}

            async with aiofiles.open('athena/athena_cache.json', 'w', encoding='utf-8') as f:
                await f.write(json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False))

            await self.create_item_shop_image(data=cache)
            date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            await self.bot.get_user(self.bot.owner_ids[0]).send(
                f"Shop updated & rendered for `{date}` | `{cache['hash']}` | `{cache['len']}`"
            )

    @update_fortnite_shop_hash.before_loop
    async def before_update_shop_hash(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(BackgroundTasks(bot))
