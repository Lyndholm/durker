import json
import shlex
from argparse import ArgumentParser
from asyncio.exceptions import TimeoutError
from datetime import datetime
from io import BytesIO
from os import getenv
from random import choice
from typing import Optional

import aiofiles
from aiohttp import ClientSession
from discord import Color, Embed, File, HTTPException
from discord.ext.commands import (BucketType, Cog, command, cooldown, dm_only,
                                  guild_only, is_owner)

from ..utils.cataba_icon import BaseIcon
from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL, PLACEHOLDER, STATS_CHANNEL
from ..utils.paginator import Paginator
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("fortnite")


class Arguments(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class Fortnite(Cog, name='Fortnite'):
    def __init__(self, bot):
        self.bot = bot
        self.trn_headers = {"TRN-Api-Key": getenv("TRN_API_KEY")}
        self.fnapicom_headers = {"x-api-key", getenv("FORTNITEAPICOM_TOKEN")}
        self.fnapiio_headers = {"Authorization": getenv("FORTNITEAPIIO_TOKEN")}

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fortnite")

    def item_rarity_to_color(self, rarity: str) -> hex:
        colors = {
            "common": 0x959595,
            "uncommon": 0x4da328,
            "rare": 0x1f75c5,
            "epic": 0xa44dc7,
            "legendary": 0xffa540,
            "dark": 0x8b018f,
            "dc": 0x3262ae,
            "exotic": 0x45d5b3,
            "frozen": 0xa0c0e6,
            "gaminglegends": 0x500e56,
            "icon": 0x45eced,
            "lava": 0x9c352d,
            "marvel": 0xde2b27,
            "mythic": 0xeac244,
            "shadow": 0x5f5db2,
            "slurp": 0x5cd8ff,
            "starwars": 0x1d1c1d,
            "transcendent": 0xc44563
        }
        return colors.get(rarity, Color.random())

    ### Fortnite-api.com
    @command(name=cmd["searchcosmetic"]["name"], aliases=cmd["searchcosmetic"]["aliases"],
            brief=cmd["searchcosmetic"]["brief"],
            description=cmd["searchcosmetic"]["description"],
            usage=cmd["searchcosmetic"]["usage"],
            help=cmd["searchcosmetic"]["help"],
            hidden=cmd["searchcosmetic"]["hidden"], enabled=True)
    @required_level(cmd["searchcosmetic"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    async def search_fortnite_cosmetic_command(self, ctx, *, args: str = None):
        if args is not None:
            parser = Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument('-lang', nargs='+')
            parser.add_argument('-searchLang', nargs='+')
            parser.add_argument('-matchMethod', nargs='+')
            parser.add_argument('-id', nargs='+')
            parser.add_argument('-name', nargs='+')
            parser.add_argument('-description', nargs='+')
            parser.add_argument('-type', nargs='+')
            parser.add_argument('-displayType', nargs='+')
            parser.add_argument('-backendType', nargs='+')
            parser.add_argument('-rarity', nargs='+')
            parser.add_argument('-displayRarity', nargs='+')
            parser.add_argument('-backendRarity', nargs='+')
            parser.add_argument('-hasSeries', nargs='+')
            parser.add_argument('-series', nargs='+')
            parser.add_argument('-backendSeries', nargs='+')
            parser.add_argument('-hasSet', nargs='+')
            parser.add_argument('-set', nargs='+')
            parser.add_argument('-setText', nargs='+')
            parser.add_argument('-backendSet', nargs='+')
            parser.add_argument('-hasIntroduction', nargs='+')
            parser.add_argument('-backendIntroduction', nargs='+')
            parser.add_argument('-introductionChapter', nargs='+')
            parser.add_argument('-introductionSeason', nargs='+')
            parser.add_argument('-hasFeaturedImage', nargs='+')
            parser.add_argument('-hasVariants', nargs='+')
            parser.add_argument('-hasGameplayTags', nargs='+')
            parser.add_argument('-gameplayTag', nargs='+')
            parser.add_argument('-hasMetaTags', nargs='+')
            parser.add_argument('-metaTag', nargs='+')
            parser.add_argument('-hasDynamicPakId', nargs='+')
            parser.add_argument('-dynamicPakId', nargs='+')
            parser.add_argument('-added', nargs='+')
            parser.add_argument('-addedSince', nargs='+')
            parser.add_argument('-unseenFor', nargs='+')
            parser.add_argument('-lastAppearance', nargs='+')

            try:
                args = parser.parse_args(shlex.split(args))
            except Exception as e:
                await ctx.reply(str(e), mention_author=False)
                return

            parameter = "?"

            if args.lang:
                parameter += f"&language={args.lang[0].lower()}"
            else:
                parameter += "&language=ru"

            if args.searchLang:
                parameter += f"&searchLanguage={args.searchLang[0].lower()}"
            else:
                parameter += "&searchLanguage=ru"

            if args.matchMethod:
                parameter += f"&matchMethod={args.matchMethod[0].lower()}"
            else:
                parameter += "&matchMethod=contains"

            if args.id:
                parameter += f"&id={args.id[0].lower()}"

            if args.name:
                name = ""
                for i in args.name:
                    if i != args.name[len(args.name) - 1]:
                        name += f"{i}+"
                    else:
                        name += f"{i}"
                parameter += f"&name={name}"

            if args.description:
                description = ""
                for i in args.description:
                    if i != args.description[len(args.description) - 1]:
                        description += f"{i}+"
                    else:
                        description += f"{i}"
                parameter += f"&description={description}"

            if args.type:
                parameter += f"&type={args.type[0].lower()}"

            if args.displayType:
                parameter += f"&displayType={args.displayType[0].lower()}"

            if args.backendType:
                parameter += f"&backendType={args.backendType[0].lower()}"

            if args.rarity:
                parameter += f"&rarity={args.rarity[0].lower()}"

            if args.displayRarity:
                parameter += f"&displayRarity={args.displayRarity[0].lower()}"

            if args.backendRarity:
                parameter += f"&backendRarity={args.backendRarity[0].lower()}"

            if args.hasSeries:
                parameter += f"&hasSeries={args.hasSeries[0].lower()}"

            if args.series:
                series = ""
                for i in args.series:
                    if i != args.series[len(args.series) - 1]:
                        series += f"{i}+"
                    else:
                        series += f"{i}"
                parameter += f"&series={series}"

            if args.backendSeries:
                parameter += f"&backendSeries={args.backendSeries[0].lower()}"

            if args.hasSet:
                parameter += f"&hasSet={args.hasSet[0].lower()}"

            if args.set:
                item_set = ""
                for i in args.set:
                    if i != args.set[len(args.set) - 1]:
                        item_set += f"{i}+"
                    else:
                        item_set += f"{i}"
                parameter += f"&set={item_set}"

            if args.setText:
                setText = ""
                for i in args.setText:
                    if i != args.setText[len(args.setText) - 1]:
                        setText += f"{i}+"
                    else:
                        setText += f"{i}"
                parameter += f"&setText={setText}"

            if args.backendSet:
                parameter += f"&backendSet={args.backendSet[0].lower()}"

            if args.hasIntroduction:
                parameter += f"&hasIntroduction={args.hasIntroduction[0].lower()}"

            if args.backendIntroduction:
                parameter += f"&backendIntroduction={args.backendIntroduction[0].lower()}"

            if args.introductionChapter:
                parameter += f"&introductionChapter={args.introductionChapter[0].lower()}"

            if args.introductionSeason:
                parameter += f"&introductionSeason={args.introductionSeason[0].lower()}"

            if args.hasFeaturedImage:
                parameter += f"&hasFeaturedImage={args.hasFeaturedImage[0].lower()}"

            if args.hasVariants:
                parameter += f"&hasVariants={args.hasVariants[0].lower()}"

            if args.hasGameplayTags:
                parameter += f"&hasGameplayTags={args.hasGameplayTags[0].lower()}"

            if args.gameplayTag:
                parameter += f"&gameplayTag={args.gameplayTag[0].lower()}"

            if args.hasMetaTags:
                parameter += f"&hasMetaTags={args.hasMetaTags[0].lower()}"

            if args.metaTag:
                parameter += f"&metaTag={args.metaTag[0].lower()}"

            if args.hasDynamicPakId:
                parameter += f"&hasDynamicPakId={args.hasDynamicPakId[0].lower()}"

            if args.dynamicPakId:
                parameter += f"&dynamicPakId={args.dynamicPakId[0].lower()}"

            if args.added:
                parameter += f"&added={args.added[0].lower()}"

            if args.addedSince:
                parameter += f"&addedSince={args.addedSince[0].lower()}"

            if args.unseenFor:
                parameter += f"&unseenFor={args.unseenFor[0].lower()}"

            if args.lastAppearance:
                parameter += f"&lastAppearance={args.lastAppearance[0].lower()}"

            async with ClientSession() as session:
                async with session.get(url=f"https://fortnite-api.com/v2/cosmetics/br/search{parameter}") as r:
                    response_data = await r.json()
                    if r.status == 404:
                        embed = Embed(
                            title='Предмет не найден.',
                            description=f"```txt\n" + response_data["error"] + "```",
                            color=Color.red(),
                            timestamp=datetime.utcnow())
                        return await ctx.reply(embed=embed, mention_author=False)

                    elif r.status == 200:
                        data = response_data

                    else:
                        embed = Embed(
                            title='❗ Ошибка!',
                            description=str(response_data["status"]) + "\n```txt\n" + response_data["error"] + "```",
                            color=Color.red(),
                            timestamp=datetime.utcnow())
                        return await ctx.reply(embed=embed, mention_author=False)

            i = data["data"]
            embed = Embed(color=self.item_rarity_to_color(i['rarity']['value']))
            embed.set_author(name=i["name"])

            if i["images"]["icon"]:
                embed.set_thumbnail(url=i["images"]["icon"])
            elif i["images"]["smallIcon"]:
                embed.set_thumbnail(url=i["images"]["smallIcon"])
            elif i["images"]["featured"]:
                embed.set_thumbnail(url=i["images"]["featured"])
            elif i["images"]["other"]:
                embed.set_thumbnail(url=i["images"]["other"])
            else:
                embed.set_thumbnail(url=PLACEHOLDER)

            byte_io = BytesIO()
            cataba_image = await BaseIcon().generate_icon(i)
            cataba_image.save(byte_io, format='PNG')
            f = File(BytesIO(byte_io.getvalue()), filename=f"{i['id']}.png")
            embed.set_image(url=f"attachment://{i['id']}.png")

            try:
                embed.add_field(name="ID:", value=i["id"], inline=False)
            except:
                pass
            try:
                embed.add_field(name="Описание:", value=i["description"], inline=False)
            except:
                pass
            try:
                embed.add_field(name="Редкость:", value=i["rarity"]["displayValue"], inline=False)
            except:
                pass
            try:
                embed.add_field(name="Дополнительная информация:", value=i["introduction"]["text"], inline=False)
            except:
                pass
            try:
                hist = "```\n"
                for i2 in i["shopHistory"][::-1][:10]:
                    i2 = i2.split("T")
                    i2 = i2[0].split("-")
                    hist += f"{i2[2]}.{i2[1]}.{i2[0]}\n"
                hist += "```"
                embed.add_field(name="Появления в магазине (последние 10):", value=hist, inline=False)
            except:
                pass
            variants = False
            try:
                if i["variants"]:
                    variants = True
            except Exception:
                pass

            if variants is True:
                embed.set_footer(text="Нажмите на реакцию, чтобы увидеть дополнительные стили.")

            msg = await ctx.reply(embed=embed, file=f, mention_author=False)
            if variants is True:
                await msg.add_reaction("✅")
                try:
                    p = await self.bot.wait_for(
                        "raw_reaction_add", timeout=60, check=lambda p:
                        p.user_id == ctx.author.id
                        and str(p.emoji) == "✅"
                        and p.channel_id == ctx.channel.id
                        and p.message_id == msg.id
                    )

                except TimeoutError:
                    await msg.clear_reactions()
                    return

                if i["variants"]:
                    variants_embeds = []
                    for i2 in i["variants"]:
                        for i3 in i2["options"]:
                            embed = Embed(
                                title=i2["channel"] + " | " + i2["type"].title(),
                                color=Color.green(),
                                timestamp=datetime.utcnow()
                            )
                            embed.add_field(name=i3["name"], value=i3.get("unlockRequirements", "Стиль открыт по умолчанию."), inline=False)
                            embed.set_image(url=i3.get("image", PLACEHOLDER))
                            variants_embeds.append(embed)

                variants_msg = await msg.reply(embed=variants_embeds[0], mention_author=False)
                page = Paginator(self.bot, variants_msg, only=ctx.author, embeds=variants_embeds)
                return await page.start()

        else:
            await ctx.reply(
                "Пожалуйста, введите аргументы корректно.\n\n```+searchcosmetic -name Рейдер-Изгой -rarity epic```",
                mention_author=False
            )


    ### FortniteTracker.com
    @command(name=cmd["fnstats"]["name"], aliases=cmd["fnstats"]["aliases"],
            brief=cmd["fnstats"]["brief"],
            description=cmd["fnstats"]["description"],
            usage=cmd["fnstats"]["usage"],
            help=cmd["fnstats"]["help"],
            hidden=cmd["fnstats"]["hidden"], enabled=True)
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @cooldown(cmd["fnstats"]["cooldown_rate"], cmd["fnstats"]["cooldown_per_second"], BucketType.guild)
    async def fortnite_stats_command(self, ctx, *, profile:str=None):
        if profile is None:
            embed = Embed(
                title='❗ Внимание!',
                description=f"{ctx.author.mention}\nПожалуйста, укажите никнейм запрашиваемого аккаунта.",
                color=Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)
            ctx.command.reset_cooldown(ctx)
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
                        "\n\n**P.S.** Данные берутся из разных источников, поэтому статистика "
                        "может меняться в зависимости от выбранного вами метода. "
                        "Как правило, при отображении через Embed статистика точнее и актуальнее."
        )
        main_message = await ctx.reply(embed=embed, mention_author=False)

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
            await main_message.edit(embed=Embed(title="Операция прервана пользователем."))
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
            async with ClientSession(headers=self.fnapicom_headers) as session:
                async with session.get('https://fortnite-api.com/v2/stats/br/v2', params=params) as r:
                    if r.status != 200:
                        await main_message.delete()
                        await ctx.reply(
                            f"""```json\n{await r.text()}```""",
                            mention_author=False
                        )
                        return

                    data = await r.json()

                stats_embed= Embed(
                    title="Статистика игрового профиля Fortnite",
                    color=Color.blurple()
                )
                stats_embed.set_image(url=data["data"]["image"])
                await main_message.edit(embed=stats_embed)


        elif prefered_api == "fortnitetracker":
            if str(platform_react.emoji) == '⌨️':
                mode = 'kbm'
            elif str(platform_react.emoji) == '🎮':
                mode = 'gamepad'
            elif str(platform_react.emoji) == '📱':
                mode = 'touch'
            elif str(platform_react.emoji) == '💡':
                mode = 'all'

            async with ClientSession(headers=self.trn_headers) as session:
                async with session.get(f'https://api.fortnitetracker.com/v1/profile/{mode}/{profile}') as r:
                    if r.status != 200:
                        await main_message.delete()
                        await ctx.reply(
                            f"""```ini\n{r.status}```""",
                            mention_author=False
                        )
                        return

                    data = await r.json()

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


async def setup(bot):
    await bot.add_cog(Fortnite(bot))
