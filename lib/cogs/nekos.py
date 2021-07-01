from io import BytesIO
from random import choice, randint

from aiohttp import ClientSession
from discord import Color, Embed, File
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("nekos")


class Nekos(Cog, name='Аниме'):
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
    @required_level(cmd["anipic"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["anipic"]["cooldown_rate"], cmd["anipic"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def random_anime_picture_command(self, ctx):
        embed = Embed(color=Color.random(), timestamp=ctx.message.created_at)
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)

        async with ClientSession() as session:
            chance = randint(1, 100)
            if 50 < chance < 100:
                async with session.get(f'https://waifu.pics/api/sfw/{choice(self.anime_categories)}') as r:
                        if r.status == 200:
                            data = await r.json()
                            embed.set_image(url=data["url"])
                        else:
                            embed.set_image(url=choice(self.waifu_images))
                        await ctx.send(embed=embed)

            elif 0 < chance < 50:
                async with session.get(f'https://{choice(self.anime_weeb_services)}.weeb.services/') as r:
                        if r.status == 200:
                            f = File(BytesIO(await r.read()), filename="weeb.png")
                            embed.set_image(url="attachment://weeb.png")
                            await ctx.send(embed=embed, file=f)


def setup(bot):
    bot.add_cog(Nekos(bot))
