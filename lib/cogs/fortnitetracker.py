from asyncio.exceptions import TimeoutError
from os import getenv

import requests
from aiohttp import ClientSession
from discord import Color, Embed, File
from discord.ext.commands import Cog, command
from loguru import logger

from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("fortnitetracker")


class FortniteTracker(Cog, name='Fortnite Stats'):
    def __init__(self, bot):
        self.bot = bot
        self.headers = {"TRN-Api-Key": getenv("TRN_API_KEY")}

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fortnitetracker")

    @command(name=cmd["fnstats"]["name"], aliases=cmd["fnstats"]["aliases"],
            brief=cmd["fnstats"]["brief"],
            description=cmd["fnstats"]["description"],
            usage=cmd["fnstats"]["usage"],
            help=cmd["fnstats"]["help"],
            hidden=cmd["fnstats"]["hidden"], enabled=True)
    @logger.catch
    async def fortnite_stats_command(self, ctx, *, profile:str=None):
        if profile is None:
            embed = Embed(title='❗ Внимание!', description =f"{ctx.author.mention}\nПожалуйста, укажите никнейм запрашиваемого аккаунта.", color= Color.red())
            await ctx.send(embed=embed)
            return

        plarform_reactions = ['💡', '⌨️', '🎮', '📱']
        prefered_api = None
        mode = 'all'

        embed = Embed(
            title="Статистика игрового профиля Fortnite",
            color=Color.gold(),
            description="Пожалуйста, выберите удобный вам способ показа статистики:\n\n"
                        "1️⃣ — отображение статистики через картинку.\n"
                        "2️⃣ — отображение в Embed.\n"
                        "\n❌ — выход."
                        "\n\n**P.S.** Данные берутся из разных источников, поэтому статистика может меняться в зависимости от выбранного вами метода."
                        " Как правило, при отображении через Embed статистика точнее и актуальнее.\n\n"
        )
        main_message = await ctx.send(embed=embed)

        for reaction in ['1️⃣', '2️⃣', '❌']:
            await main_message.add_reaction(reaction)

        try:
            api_react, user = await self.bot.wait_for(
                'reaction_add', timeout=120.0, check=lambda api_react,
                user: user == ctx.author and api_react.message.channel == ctx.channel and api_react.emoji in ['1️⃣', '2️⃣', '❌']
            )
        except TimeoutError:
            await main_message.clear_reactions()
            return

        if str(api_react.emoji) == '1️⃣':
            prefered_api = "fnapi"

        elif str(api_react.emoji) == '2️⃣':
            prefered_api = "fortnitetracker"

        elif str(api_react.emoji) == '❌':
            await main_message.clear_reactions()
            await main_message.edit(embed=Embed(title="Операция прервана пользоватем"))
            return

        await main_message.clear_reactions()

        select_platform_embed = Embed(
                title="Выбор платформы",
                color=Color.dark_teal(),
                description="Пожалуйста, выберите платформу, на которой вы играете.\n\n"
                            f"{plarform_reactions[0]} — Общая статистика по всем платформам.\n"
                            f"{plarform_reactions[1]} — ПК\n{plarform_reactions[2]} — Консоль\n{plarform_reactions[3]} — Мобильное устройство"
            )

        await main_message.edit(embed=select_platform_embed)

        for reaction in plarform_reactions:
            await main_message.add_reaction(reaction)

        try:
            platform_react, user = await self.bot.wait_for(
                'reaction_add', timeout=120.0, check=lambda platform_react,
                user: user == ctx.author and platform_react.message.channel == ctx.channel and platform_react.emoji in plarform_reactions
            )

        except TimeoutError:
            await main_message.clear_reactions()
            return

        await main_message.clear_reactions()

        if prefered_api == "fnapi":
            if str(platform_react.emoji) == '⌨️':
                mode = "keyboardMouse"
            elif str(platform_react.emoji) == '🎮':
                mode = 'gamepad'
            elif str(platform_react.emoji) == '📱':
                mode = 'touch'
            elif str(platform_react.emoji) == '💡':
                mode = 'all'

            params = {"name": profile, "image": mode}
            async with ClientSession() as session:
                async with session.get('https://fortnite-api.com/v1/stats/br/v2', params=params) as r:
                    if r.status != 200:
                        await main_message.delete()
                        await ctx.message.reply(f"""```json\n{await r.text()}```""")
                        return

                    data = await r.json()

                    stats_embed= Embed(
                        title="Статистика игрового профиля Fortnite",
                        color=Color.blurple(),
                        description="**Внимание!**\nДанный метод нестабилен. Он может отображать некорректную информацию или вовсе ничего не показывать."
                        )
                    stats_embed.set_image(url=data["data"]["image"])
                    await main_message.edit(embed=stats_embed)


        elif prefered_api == "fortnitetracker":
            if str(platform_react.emoji) == '⌨️':
                mode = "kbm"
            elif str(platform_react.emoji) == '🎮':
                mode = 'gamepad'
            elif str(platform_react.emoji) == '📱':
                mode = 'touch'
            elif str(platform_react.emoji) == '💡':
                mode = 'all'

            r = requests.get(
                f"https://api.fortnitetracker.com/v1/profile/{mode}/{profile}",
                headers=self.headers,
            )

            if r.status_code != 200:
                await main_message.delete()
                await ctx.message.reply(f"""```json\n{await r.text()}```""")
                return

            data = r.json()
            embed = Embed(
                title=f"{data.get('epicUserHandle', profile)} ({data.get('platformNameLong', mode)})",
                color=Color.random()
            )
            stats = data.get("lifeTimeStats", {})
            for s in stats:
                embed.add_field(
                    name=s.get("key", "Unknown"), value=s.get("value", "Unknown")
                )
            await main_message.edit(embed=embed)


def setup(bot):
    bot.add_cog(FortniteTracker(bot))
