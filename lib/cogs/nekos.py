import json
from random import choice

import aiofiles
from discord import Color, Embed
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

        bot.loop.create_task(self.parse_anime_images())

    @logger.catch
    async def parse_anime_images(self):
        async with aiofiles.open(f'data/json/anime_images.json', mode='r', encoding='utf-8') as f:
            data = json.loads(await f.read())
            self.anime_images = data['anime']

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

def setup(bot):
    bot.add_cog(Nekos(bot))
