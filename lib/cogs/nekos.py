from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command

from aiohttp import ClientSession
from random import choice

import json


from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("nekos")


class Nekos(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.anime_categories = ("waifu", "neko", "megumin")
        self.anime_weeb_services = ("senko", "neko", "kanna")
        self.waifu_images = ("https://cdn.discordapp.com/attachments/774698479981297664/797231152477765682/unity_girl.png",
                            "https://cdn.discordapp.com/attachments/774698479981297664/797231173847220264/c_animegirl.png")

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
    async def random_anime_picture_command(self, ctx):  
        async with ClientSession() as session:
            async with session.get(f'https://waifu.pics/api/sfw/{choice(self.anime_categories)}') as r:
                    if r.status == 200:
                        data = await r.json()
                        img = data["url"]
                    else:
                        img = choice(self.waifu_images)

        embed = Embed(color=Color.random(), timestamp=ctx.message.created_at)
        embed.set_image(url=img)
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Nekos(bot))
