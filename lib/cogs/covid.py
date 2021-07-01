from datetime import datetime

from aiohttp import ClientSession
from discord import Color, Embed
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from loguru import logger

from lib.utils.checks import is_channel

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("covid")

class Covid(Cog, name='COVID-19'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("covid")

    @command(name=cmd["covid"]["name"], aliases=cmd["covid"]["aliases"],
            brief=cmd["covid"]["brief"],
            description=cmd["covid"]["description"],
            usage=cmd["covid"]["usage"],
            help=cmd["covid"]["help"],
            hidden=cmd["covid"]["hidden"], enabled=True)
    @required_level(cmd["covid"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["covid"]["cooldown_rate"], cmd["covid"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def covid_stats_command(self, ctx, country: str = None):
        if not country:
            embed = Embed(
                title='❗ Внимание!',
                description =f"Пожалуйста, введите название страны на английском языке.",
                color=Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        async with ClientSession() as session:
            async with session.get("https://corona.lmao.ninja/v2/countries") as r:
                    if r.status == 200:
                        data = await r.json()
                    else:
                        embed = Embed(
                            title='❗ Внимание!',
                            description =f"Что-то пошло не так. API вернуло: {r.status}",
                            color=Color.red()
                        )
                        await ctx.reply(embed=embed, mention_author=False)
                        return

        for item in data:
            if item["country"].lower() == country.lower():
                date = datetime.fromtimestamp(item["updated"]/1000).strftime("%d.%m.%Y %H:%M:%S")
                embed = Embed(
                    title=f'Статистика Коронавируса | {country.upper()}',
                    description=f"Дата обновления статистики: **{date}**",
                    color = Color.red()
                )

                embed.add_field(name=f'Заболеваний:', value=f'{item["cases"]:,}')

                embed.add_field(name=f'Заболеваний за сутки:', value=f'+{item["todayCases"]:,}')

                embed.add_field(name=f'Активные зараженные:', value=f'{item["active"]:,}')

                embed.add_field(name=f'Выздоровело:', value=f'{item["recovered"]:,}')

                embed.add_field(name=f'Выздоровело за сутки:', value=f'+{item["todayRecovered"]:,}')

                embed.add_field(name=f'В тяжелом состоянии:', value=f'{item["critical"]:,}')

                embed.add_field(name=f'Погибло:', value=f'{item["deaths"]:,}')

                embed.add_field(name=f'Погибло за сутки:', value=f'{item["todayDeaths"]:,}')

                embed.add_field(name=f'Проведено тестов:', value=f'{item["tests"]:,}')

                embed.set_thumbnail(url=item["countryInfo"]['flag'])

                await ctx.reply(embed=embed, mention_author=False)
                break
        else:
            embed = Embed(
                title='❗ Внимание!',
                description=f'**{country.capitalize()}** нет в списке стран. ' \
                            'Учитывайте, что названия стран необходимо писать на '
                            'английском языке.',
                color=Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)


def setup(bot):
    bot.add_cog(Covid(bot))
