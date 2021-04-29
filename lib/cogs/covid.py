from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime

from aiohttp import ClientSession

from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("covid")

class Covid(Cog, name='COVID'):
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
    async def covid_stats_command(self, ctx, country: str = None):
        if not country:
            embed = Embed(title=':exclamation: Внимание!', description =f"Пожалуйста, введите название страны на английском языке.", color = Color.red())
            await ctx.send(embed=embed)
        else:
            async with ClientSession() as session:
                async with session.get("https://corona.lmao.ninja/v2/countries") as r:
                        if r.status == 200:
                            data = await r.json()
                            for item in data:
                                if item["country"].lower() == country.lower():
                                    date = datetime.fromtimestamp(item["updated"]/1000).strftime("%d.%m.%Y %H:%M:%S")
                                    embed = Embed(
                                        title=f'Статистика Коронавируса | {country.upper()}',
                                        description=f"Дата обновления статистики: **{date}**",
                                        color = Color.red())

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

                                    await ctx.send(embed=embed)

                        else:
                            embed = Embed(title=':exclamation: Внимание!', description =f"Что-то пошло не так. API вернуло: {r.status}", color = Color.red())
                            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Covid(bot))
