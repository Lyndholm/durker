from os import getenv
from aiohttp import ClientSession
from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime

from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("fortniteapiio")


class FortniteAPIio(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_token = getenv('FORTNITEAPIIO_TOKEN')

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fortniteapiio")

    @command(name=cmd["map"]["name"], aliases=cmd["map"]["aliases"], 
            brief=cmd["map"]["brief"],
            description=cmd["map"]["description"],
            usage=cmd["map"]["usage"],
            help=cmd["map"]["help"],
            hidden=cmd["map"]["hidden"], enabled=True)
    async def show_fortnite_map_command(self, ctx, poi:str="None", language="ru"):
        embed = Embed(title="Карта Королевской Битвы",color=Color.orange(), timestamp=datetime.utcnow())
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        if poi.lower() == "poi":
            embed.set_image(url=f"https://media.fortniteapi.io/images/map.png?showPOI=true&lang={language}")
        else:
            embed.set_image(url="https://media.fortniteapi.io/images/map.png")

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(FortniteAPIio(bot))
