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
        self.anime_images = []
        self.parse_anime_images.start()
        self.check_anime_suggestions.start()

    @tasks.loop(hours=3.0)
    @logger.catch
    async def parse_anime_images(self):
        async with ClientSession() as session:
            async with session.get("https://raw.githubusercontent.com/OlekLolKek/Escape-from-Anime/main/anime.json") as r:
                if r.status == 200:
                    data = await r.read()
                    data = json.loads(data)
                    self.anime_images = data['anime']
                else:
                    async with aiofiles.open(f'data/json/anime_images.json', mode='r', encoding='utf-8') as f:
                        data = json.loads(await f.read())
                        self.anime_images = data['anime']

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
                await self.bot.get_user(i).send(
                    'Новые картинки на добавление в команду `anipic`.',
                    file=File(path, filename=f'anisuggestions_{time}.json')
                )
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps({'images':[]}, indent=2, sort_keys=True, ensure_ascii=False))

    @check_anime_suggestions.before_loop
    async def before_check_anime_suggestions(self):
        await self.bot.wait_until_ready()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("nekos")

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
    async def random_anime_picture_command(self, ctx):
        embed = Embed(color=Color.random(), timestamp=ctx.message.created_at)
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        embed.set_image(url=choice(self.anime_images))
        await ctx.send(embed=embed)

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
