import json
import os
from datetime import datetime

import aiofiles
from aiohttp import ClientSession
from discord.ext import tasks
from discord.ext.commands import Cog
from jishaku.functools import executor_function

ITEM_SHOP_ENDPOINT = "https://fortnite-api.com/v2/shop/br/combined"


class BackgroundTasks(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_shop_hash.start()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("background_tasks")

    @executor_function
    def create_item_shop_image(self, data: dict):
        if data['len'] <= 59:
            os.system("python ./athena/athena.py")
        else:
            os.system("python ./athena/athena_monotonic.py")

    @tasks.loop(minutes=1.0)
    async def update_shop_hash(self):
        """Makes a request to the api and checks if the hash has been updated"""
        async with ClientSession() as session:
            async with session.get(url=ITEM_SHOP_ENDPOINT) as r:
                if r.status != 200:
                    return

                data = await r.json()
                new_hash = data['data']['hash']
                new_len = len(data['data']['featured']['entries']) + len(data['data']['daily']['entries'])
                async with aiofiles.open('athena/cache.json', mode='r', encoding='utf-8') as f:
                    cached_data = json.loads(await f.read())
                    cached_hash = cached_data['hash']
                    cached_len = cached_data['len']

        if new_hash != cached_hash or new_len != cached_len:
            date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            cache = {"hash": new_hash, "date":date, "len": new_len}

            async with aiofiles.open('athena/cache.json', 'w', encoding='utf-8') as f:
                await f.write(json.dumps(cache, indent=2, sort_keys=True, ensure_ascii=False))

            await self.create_item_shop_image(data=cache)
            await self.bot.get_user(self.bot.owner_ids[0]).send(
                f"Shop updated & rendered for `{date}` | `{cache['hash']}` | `{cache['len']}`"
            )

    @update_shop_hash.before_loop
    async def before_update_shop_hash(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(BackgroundTasks(bot))
