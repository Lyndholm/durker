from io import BytesIO

from aiohttp import ClientSession
from discord import Color, Embed, File
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from loguru import logger

from ..utils.checks import is_channel
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("peelyde")


class PeelyDE(Cog, name='Fortnite API 4'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("peelyde")


    @command(name=cmd["upcoming"]["name"], aliases=cmd["upcoming"]["aliases"],
            brief=cmd["upcoming"]["brief"],
            description=cmd["upcoming"]["description"],
            usage=cmd["upcoming"]["usage"],
            help=cmd["upcoming"]["help"],
            hidden=cmd["upcoming"]["hidden"], enabled=True)
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["upcoming"]["cooldown_rate"], cmd["upcoming"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_fortnite_upcoming_items_command(self, ctx, mode:str="current", language:str="ru"):
        embed = Embed(
            title="Fortnite upcoming items",
            color=Color.random(),
            timestamp=ctx.message.created_at
            )
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)

        async with ClientSession() as session:
            if mode.lower() == "full":
                async with ctx.typing():
                    async with session.get(f'https://api.peely.de/cdn/current/leaks?lang={language}') as r:
                        if r.status != 200:
                            await ctx.reply(
                                f"""```ini\nHTTP: {r.status}```""",
                                mention_author=False
                            )
                            return

                        f = File(BytesIO(await r.read()), filename="fn_upcoming_full.png")
                        embed.set_image(url="attachment://fn_upcoming_full.png")
                await ctx.reply(embed=embed, file=f, mention_author=False)
            else:
                async with ctx.typing():
                    async with session.get(f'https://api.peely.de/cdn/current/leaks.png') as r:
                        if r.status != 200:
                            await ctx.reply(
                                f"""```ini\nHTTP: {r.status}```""",
                                mention_author=False
                            )
                            return

                        f = File(BytesIO(await r.read()), filename="fn_upcoming_current.png")
                        embed.set_image(url="attachment://fn_upcoming_current.png")
                await ctx.reply(embed=embed, file=f, mention_author=False)


    @command(name=cmd["fnseason"]["name"], aliases=cmd["fnseason"]["aliases"],
            brief=cmd["fnseason"]["brief"],
            description=cmd["fnseason"]["description"],
            usage=cmd["fnseason"]["usage"],
            help=cmd["fnseason"]["help"],
            hidden=cmd["fnseason"]["hidden"], enabled=True)
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["fnseason"]["cooldown_rate"], cmd["fnseason"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_battle_royal_season_data_command(self, ctx):
        embed = Embed(
            title="Королевская битва",
            color=Color.random(),
            timestamp=ctx.message.created_at
            )
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)

        async with ClientSession() as session:
            async with session.get("https://api.peely.de/v1/br/progress/data") as r:
                if r.status != 200:
                    await ctx.reply(
                            f"""```ini\nHTTP: {r.status}```""",
                            mention_author=False
                    )
                    return

                data = await r.json()
                embed.description = f'Продолжительность текущего сезона в днях: **{data["data"]["SeasonLength"]}**\n\n' \
                                    f'Прошло дней с начала сезона: **{abs(data["data"]["DaysGone"])}**\n\n' \
                                    f'Осталось до конца сезона: **{data["data"]["DaysLeft"]}**'

            async with session.get("https://api.peely.de/v1/br/progress") as r:
                f = File(BytesIO(await r.read()), filename="br_progress.png")
                embed.set_image(url="attachment://br_progress.png")

            await ctx.reply(embed=embed, file=f, mention_author=False)


def setup(bot):
    bot.add_cog(PeelyDE(bot))
