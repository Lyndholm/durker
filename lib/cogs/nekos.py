import asyncio
import json
from datetime import datetime
from random import choice
from typing import Optional

import aiofiles
from aiohttp import ClientSession
from discord import Color, Embed, File
from discord.ext import tasks
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("nekos")


class Nekos(Cog, name='Аниме'):
    def __init__(self, bot):
        self.bot = bot
        self.anime_images = {}
        self.ANIME_ENDPOINT = 'https://raw.githubusercontent.com/OlekLolKek/Escape-from-Anime/main/'
        self.parse_anime_images.start()
        self.check_anime_suggestions.start()

    @tasks.loop(hours=3.0)
    @logger.catch
    async def parse_anime_images(self):
        categories = (
            'NewAnimaru', 'NewGifs', 'NewMaid', 'NewMilitary', 'NewMonster',
            'NewMusic', 'NewPixel', 'NewRegular', 'NewSchool', 'NewWitch',
        )
        async with ClientSession() as session:
            for category in categories:
                async with session.get(f'{self.ANIME_ENDPOINT}{category}.json') as r:
                    if r.status == 200:
                        data = json.loads(await r.read())
                        self.anime_images[category] = data['anime']

    @parse_anime_images.before_loop
    async def before_parse_anime_images(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30.0)
    @logger.catch
    async def check_anime_suggestions(self):
        path = './data/json/anisuggestions.json'
        time = int(datetime.now().timestamp())
        async with aiofiles.open(path, 'r', encoding='utf-8') as f:
            data = json.loads(await f.read())

        if len(data['images']) == 0:
            return

        if (19 < datetime.now().hour < 21) or len(data['images']) >= 30:
            for i in [375722626636578816, 195637386221191170]:
                try:
                    await self.bot.get_user(i).send(
                        'Новые картинки на добавление в команду `anipic`.',
                        file=File(path, filename=f'anisuggestions_{time}.json'))
                except:
                    continue
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps({'images': []}, indent=2, sort_keys=True, ensure_ascii=False))

    @check_anime_suggestions.before_loop
    async def before_check_anime_suggestions(self):
        await self.bot.wait_until_ready()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("nekos")

    def parse_anipic_category(self, category: str) -> str:
        if category in ('animal', 'animaru'):
            return 'NewAnimaru'
        elif category in ('gifs', 'gif', 'гиф', 'гифка'):
            return 'NewGifs'
        elif category in ('maid', 'служанка'):
            return 'NewMaid'
        elif category in ('military'):
            return 'NewMilitary'
        elif category in ('monster'):
            return 'NewMonster'
        elif category in ('music'):
            return 'NewMusic'
        elif category in ('pixel'):
            return 'NewPixel'
        elif category in ('school'):
            return 'NewSchool'
        elif category in ('witch'):
            return 'NewWitch'
        else:
            return 'NewRegular'

    @command(name=cmd["anipic"]["name"], aliases=cmd["anipic"]["aliases"],
             brief=cmd["anipic"]["brief"],
             description=cmd["anipic"]["description"],
             usage=cmd["anipic"]["usage"],
             help=cmd["anipic"]["help"],
             hidden=cmd["anipic"]["hidden"], enabled=True)
    @required_level(cmd["anipic"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["anipic"]["cooldown_rate"], cmd["anipic"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def random_anime_picture_command(self, ctx,
                                           repeat: Optional[int] = 1,
                                           category: Optional[str] = 'NewRegular'):
        if abs(repeat) > 10:
            repeat = 10
        category = self.parse_anipic_category(category.lower())

        for _ in range(abs(repeat)):
            embed = Embed(color=Color.random(),
                          timestamp=ctx.message.created_at)
            embed.set_footer(text=ctx.author.name,
                             icon_url=ctx.author.avatar_url)
            embed.set_image(url=choice(self.anime_images[category]))
            await ctx.send(embed=embed)
            await asyncio.sleep(1)

    @command(name=cmd["anisuggest"]["name"], aliases=cmd["anisuggest"]["aliases"],
             brief=cmd["anisuggest"]["brief"],
             description=cmd["anisuggest"]["description"],
             usage=cmd["anisuggest"]["usage"],
             help=cmd["anisuggest"]["help"],
             hidden=cmd["anisuggest"]["hidden"], enabled=True)
    @required_level(cmd["anisuggest"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def suggest_anime_picture_command(self, ctx, *images: Optional[str]):
        if not images and not ctx.message.attachments:
            await ctx.reply('Прикрепите к сообщению изображения, либо укажите ссылку на них.')
            return

        images = list(images)
        images.extend([image.proxy_url for image in ctx.message.attachments])

        async with aiofiles.open('./data/json/anisuggestions.json', 'r', encoding='utf-8') as f:
            data = json.loads(await f.read())
            data['images'].extend(images)

        async with aiofiles.open('./data/json/anisuggestions.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))

        await ctx.message.add_reaction('✅')

        if len(data['images']) >= 30:
            await self.check_anime_suggestions()


def setup(bot):
    bot.add_cog(Nekos(bot))
