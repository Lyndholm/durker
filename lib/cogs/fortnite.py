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
from loguru import logger

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
    @logger.catch
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

    @command(name=cmd["searchparams"]["name"], aliases=cmd["searchparams"]["aliases"],
            brief=cmd["searchparams"]["brief"],
            description=cmd["searchparams"]["description"],
            usage=cmd["searchparams"]["usage"],
            help=cmd["searchparams"]["help"],
            hidden=cmd["searchparams"]["hidden"], enabled=True)
    @required_level(cmd["searchparams"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def cosmetics_search_params_command(self, ctx):
        params_embeds = []
        params_images = (
            'https://cdn.discordapp.com/attachments/774698479981297664/861552271589376071/cosmetics_search_params_1.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/861552297565224970/cosmetics_search_params_2.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/861552316011905044/cosmetics_search_params_3.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/861552338070405130/cosmetics_search_params_4.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/861552361251536896/cosmetics_search_params_5.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/861552398308999168/cosmetics_search_params_6.png'
        )

        for image in params_images:
            params_embeds.append(Embed(title="Параметры поиска косметических предметов Fortnite", color=Color.orange()).set_image(url=image))

        message = await ctx.reply(embed=params_embeds[0], mention_author=False)
        page = Paginator(self.bot, message, only=ctx.author, embeds=params_embeds)
        await page.start()


    @command(name=cmd["news"]["name"], aliases=cmd["news"]["aliases"],
            brief=cmd["news"]["brief"],
            description=cmd["news"]["description"],
            usage=cmd["news"]["usage"],
            help=cmd["news"]["help"],
            hidden=cmd["news"]["hidden"], enabled=True)
    @required_level(cmd["news"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["news"]["cooldown_rate"], cmd["news"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_fortnite_news_command(self, ctx, mode: str = "br", language: str = "ru"):
        mode = mode.lower()

        if mode not in ["br", "stw", "creative"]:
            embed = Embed(title='❗ Внимание!', description ="Укажите режим корректно: `br`, `stw`, `creative`.", color= Color.red())
            await ctx.message.reply(embed=embed, mention_author=False)
            return

        async with ClientSession() as session:
            async with session.get(f"https://fortnite-api.com/v2/news/{mode}", params={"language": language}) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()
                gif = data.get("data", {}).get("image", PLACEHOLDER)
                embed=Embed(color=Color.random(), timestamp=datetime.utcnow())
                embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
                if mode == "br":
                    embed.title = "Новости Королевской Битвы"
                    embed.set_image(url=gif)
                elif mode == "creative":
                    embed.title = "Новости Творческого режима"
                    embed.set_image(url=gif)
                elif mode == "stw":
                    embeds = []
                    for i in range(len(data["data"]["messages"])):
                        content = data["data"]["messages"][i]
                        embed = Embed(
                            title=content["title"] + " | " + content["adspace"],
                            description=content["body"],
                            color=Color.random())
                        embed.set_image(url=content["image"])
                        embeds.append(embed)

                    message = await ctx.reply(embed=embeds[0], mention_author=False)
                    page = Paginator(self.bot, message, only=ctx.author, embeds=embeds)
                    return await page.start()

                await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["creatorcode"]["name"], aliases=cmd["creatorcode"]["aliases"],
            brief=cmd["creatorcode"]["brief"],
            description=cmd["creatorcode"]["description"],
            usage=cmd["creatorcode"]["usage"],
            help=cmd["creatorcode"]["help"],
            hidden=cmd["creatorcode"]["hidden"], enabled=True)
    @is_owner()
    @logger.catch
    async def show_creator_code_data_command(self, ctx, code: Optional[str]):
        if code is None:
            return await ctx.reply('Укажите код автора.', mention_author=False)

        async with ClientSession() as session:
            async with session.get(f"https://fortnite-api.com/v2/creatorcode/search/all", params={"name": code}) as r:
                if r.status == 404:
                    embed = Embed(title='❗ Внимание!', description ="Указанный тег автора не найден.", color= Color.gold())
                    await ctx.message.reply(embed=embed, mention_author=False)
                elif r.status == 200:
                    data = await r.json()
                    data = data["data"]
                    code_embeds = []

                    for i in range(0,len(data)):
                        embed = Embed(
                            title=f'Код автора: {data[i]["code"]}',
                            color=Color.green() if data[i]["status"] == 'ACTIVE' else Color.red(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(
                            name="Account",
                            value=f'Name: {data[i]["account"]["name"]}\nID: {data[i]["account"]["id"]}',
                            inline=False
                        )
                        embed.add_field(
                            name="Status",
                            value=data[i]["status"],
                            inline=True
                        )
                        code_embeds.append(embed)

                    message = await ctx.reply(embed=code_embeds[0], mention_author=False)
                    page = Paginator(self.bot, message, only=ctx.author, embeds=code_embeds)
                    await page.start()

                else:
                    await ctx.reply(f"```json\n{r.text}```", mention_author=False)


    @command(name=cmd["shop"]["name"], aliases=cmd["shop"]["aliases"],
            brief=cmd["shop"]["brief"],
            description=cmd["shop"]["description"],
            usage=cmd["shop"]["usage"],
            help=cmd["shop"]["help"],
            hidden=cmd["shop"]["hidden"], enabled=True)
    @required_level(cmd["shop"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def show_battle_royale_shop_command(self, ctx):
        # I'm kinda lazy, so i hardcoded path to shop image which is generated by another script
        try:
            embed = Embed(
                title="Магазин Королевской Битвы",
                color=0x0050BE,
                timestamp=datetime.utcnow(),
                description=f"⌛ Дата: {datetime.now().strftime('%d.%m.%Y')}"
            )
            shop_img = File("/home/lyndholm/cataba/itemshop.png", filename="itemshop.png")
            embed.set_image(url="attachment://itemshop.png")
            try:
                await ctx.reply(embed=embed, file=shop_img, mention_author=False)
            except HTTPException:
                shop_img = File("/home/lyndholm/cataba/itemshop.jpg", filename="itemshop.jpg")
                embed.set_image(url="attachment://itemshop.jpg")
                await ctx.reply(embed=embed, file=shop_img, mention_author=False)
        except FileNotFoundError:
            shop_img = File("athena/itemshop.jpg", filename="itemshop.jpg")
            embed.set_image(url="attachment://itemshop.jpg")
            await ctx.reply(embed=embed, file=shop_img, mention_author=False)


    ### Fortniteapi.io
    @command(name=cmd["map"]["name"], aliases=cmd["map"]["aliases"],
            brief=cmd["map"]["brief"],
            description=cmd["map"]["description"],
            usage=cmd["map"]["usage"],
            help=cmd["map"]["help"],
            hidden=cmd["map"]["hidden"], enabled=True)
    @required_level(cmd["map"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def show_fortnite_map_command(self, ctx, poi:str="None", language="ru"):
        embed = Embed(title="Карта Королевской Битвы",color=Color.orange(), timestamp=datetime.utcnow())
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        if poi.lower() == "poi":
            embed.set_image(url=f"https://media.fortniteapi.io/images/map.png?showPOI=true&lang={language}")
        else:
            embed.set_image(url="https://media.fortniteapi.io/images/map.png")

        await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["fnach"]["name"], aliases=cmd["fnach"]["aliases"],
            brief=cmd["fnach"]["brief"],
            description=cmd["fnach"]["description"],
            usage=cmd["fnach"]["usage"],
            help=cmd["fnach"]["help"],
            hidden=cmd["fnach"]["hidden"], enabled=True)
    @required_level(cmd["fnach"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["fnach"]["cooldown_rate"], cmd["fnach"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_fortnite_achievements_command(self, ctx, language: str ="ru"):
        achievement_embeds = []
        divided = []

        async with ClientSession(headers=self.fnapiio_headers) as session:
            async with session.get("https://fortniteapi.io/v1/achievements", params={"lang":language}) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()

                for i in range(0, len(data["achievements"]), 10):
                    for j in range(i, i+10):
                        try:
                            embed=Embed(
                            title=data["achievements"][j]['name'],
                            description=data["achievements"][j]['description'],
                            color=Color.purple()
                            )
                            embed.set_thumbnail(url=data["achievements"][j]['image'])
                            divided.append(embed)

                        except IndexError:
                            pass

                    achievement_embeds.append([*divided])
                    divided.clear()

        message = await ctx.reply(embed=achievement_embeds[0][0], mention_author=False)
        page = Paginator(self.bot, message, only=ctx.author, use_more=True, embeds=achievement_embeds)
        await page.start()


    @command(name=cmd["fish"]["name"], aliases=cmd["fish"]["aliases"],
            brief=cmd["fish"]["brief"],
            description=cmd["fish"]["description"],
            usage=cmd["fish"]["usage"],
            help=cmd["fish"]["help"],
            hidden=cmd["fish"]["hidden"], enabled=True)
    @required_level(cmd["fish"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def show_fortnite_fish_list_command(self, ctx, number: int = 0):
        async with aiofiles.open('./data/json/fish_s19.json', mode='r', encoding='utf-8') as f:
            data = json.loads(await f.read())

        if number == 0:
            fish_embeds = []
            for count, entry in enumerate(data["fish"]):
                embed = Embed(
                    title=f"{choice(['🐟','🐠','🐡'])} {entry['name']} | {str(count+1)}",
                    color=Color.blue(),
                    description=entry['description'],
                )
                embed.set_thumbnail(url=entry['image'])

                fields = [
                    ("Подробности", entry["details"], True),
                    ("Требуется проф. удочка", "Да" if entry["needsProFishingRod"] else "Нет", True),
                    ("Редкость", entry["rarity"], True),
                    ("Минимальный размер", entry["sizeMin"], True),
                    ("Максимальный размер", entry["sizeMax"], True),
                    ("Максимум в слоте", entry["maxStackSize"], True)
                ]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                fish_embeds.append(embed)

            message = await ctx.reply(embed=fish_embeds[0], mention_author=False)
            page = Paginator(self.bot, message, only=ctx.author, embeds=fish_embeds)
            await page.start()
            return

        else:
            if number > len(data['fish']) or number < 0:
                embed = Embed(
                    title=f'Некорректный номер рыбки! Введите номер от 1 до {len(data["fish"])}.',
                    color= Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)
                return

            number-=1
            embed = Embed(
                    title=f"{choice(['🐟','🐠','🐡'])} {data['fish'][number]['name']} | {str(number+1)}",
                    color=Color.blue(),
                    description=data['fish'][number]['description']
                )
            embed.set_thumbnail(url=data['fish'][number]['image'])

            fields = [
                    ("Подробности", data['fish'][number]["details"], True),
                    ("Требуется проф. удочка", "Да" if data['fish'][number]["needsProFishingRod"] else "Нет", True),
                    ("Редкость", data['fish'][number]["rarity"], True),
                    ("Минимальный размер", data['fish'][number]["sizeMin"], True),
                    ("Максимальный размер", data['fish'][number]["sizeMax"], True),
                    ("Максимум в слоте", data['fish'][number]["maxStackSize"], True)
                ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["challenges"]["name"], aliases=cmd["challenges"]["aliases"],
            brief=cmd["challenges"]["brief"],
            description=cmd["challenges"]["description"],
            usage=cmd["challenges"]["usage"],
            help=cmd["challenges"]["help"],
            hidden=cmd["challenges"]["hidden"], enabled=True)
    @required_level(cmd["challenges"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["challenges"]["cooldown_rate"], cmd["challenges"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_fortnite_rare_challenges_command(self, ctx, language: str = "ru"):
        QUEST_ID = "Quest_S19_Milestone"
        quest_embeds = []
        xp_total = 0
        async with ClientSession(headers=self.fnapiio_headers) as session:
            async with session.get("https://fortniteapi.io/v1/challenges", params={"season":"current", "lang":language}) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()

        for item in data['other']:
            if QUEST_ID in item['challenges'][0]['quest_id']:
                embed = Embed(
                    title=f"📘 {item['challenges'][0]['title']}",
                    color=Color.random()
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/808066523671167006/battle_pass_quests_logo.png")

                for count, challenge in enumerate(item['challenges']):
                    embed.add_field(
                        name=f"Этап {count+1}",
                        value=f"{challenge['progress_total']} | Награда: {challenge['xp']} XP",
                        inline=False)
                    xp_total+=challenge['xp']
                embed.add_field(
                        name=f"Всего опыта за задание",
                        value=f"{xp_total} XP",
                        inline=False)
                xp_total = 0
                quest_embeds.append(embed)

        message = await ctx.reply(embed=quest_embeds[0], mention_author=False)
        page = Paginator(self.bot, message, only=ctx.author, embeds=quest_embeds)
        await page.start()


    @command(name=cmd["npc"]["name"], aliases=cmd["npc"]["aliases"],
            brief=cmd["npc"]["brief"],
            description=cmd["npc"]["description"],
            usage=cmd["npc"]["usage"],
            help=cmd["npc"]["help"],
            hidden=cmd["npc"]["hidden"], enabled=True)
    @required_level(cmd["npc"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def show_fortnite_characters_command(self, ctx, number: int = 0):
        async with aiofiles.open('./data/json/characters_s19.json', mode='r', encoding='utf-8') as f:
            data = json.loads(await f.read())

        if number == 0:
            npc_embeds = []
            embed = Embed(
                title="Все персонажи и боссы в 1 сезоне 3 главы",
                color=Color.random(),
                description=(
                    "Каждый сезон мы страдаем от сбора персонажей и, видимо, все никак не настрадаемся. "
                    "И в книге коллекций 1 сезона 3 главы, на самом старте, 20 персонажей. "
                    "Все они мирные ребята, за исключением багнутого Основателя. Он вроде мирный, но пока "
                    "его не сагришь, он не засчитается в книгу коллекций. Также есть персонажи, спавн которых "
                    "очень редок, но о них непосредственно во время перечисления."
                )
            )
            embed.set_image(url="https://fortnitefun.ru/wp-content/uploads/2021/12/%D0%92%D1%81%D0%B5-%D0%BF%D0%B5%D1%80%D1%81%D0%BE%D0%BD%D0%B0%D0%B6%D0%B8-%D0%B8-%D0%B1%D0%BE%D1%81%D1%81%D1%8B-%D0%B2-1-%D1%81%D0%B5%D0%B7%D0%BE%D0%BD%D0%B5-3-%D0%B3%D0%BB%D0%B0%D0%B2%D1%8B.jpg")
            npc_embeds.append(embed)

            for count, entry in enumerate(data):
                embed = Embed(
                    title=f"{choice(['🔵','🟦','🔷'])} {entry['name']} | {str(count+1)}",
                    color=Color.blue(),
                    description=entry['description']['index'] + entry['description']['secondary'],
                )
                embed.set_thumbnail(url=entry['images']['icon'])
                embed.set_image(url=entry['map'])

                npc_embeds.append(embed)

            message = await ctx.reply(embed=npc_embeds[0], mention_author=False)
            page = Paginator(self.bot, message, only=ctx.author, embeds=npc_embeds)
            await page.start()
            return

        else:
            if number > len(data) or number < 0:
                embed = Embed(
                    title=f'Некорректный номер NPC! Введите номер от 1 до {len(data)}.',
                    color= Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)
                return

            number-=1
            embed = Embed(
                    title=f"{choice(['🔵','🟦','🔷'])} {data[number]['name']} | {str(number+1)}",
                    color=Color.blue(),
                    description=data[number]['description']['index'] + data[number]['description']['secondary']
                )
            embed.set_thumbnail(url=data[number]['images']['icon'])
            embed.set_image(url=data[number]['map'])

            await ctx.reply(embed=embed, mention_author=False)


    ### Benbot
    @command(name=cmd["benbotstatus"]["name"], aliases=cmd["benbotstatus"]["aliases"],
            brief=cmd["benbotstatus"]["brief"],
            description=cmd["benbotstatus"]["description"],
            usage=cmd["benbotstatus"]["usage"],
            help=cmd["benbotstatus"]["help"],
            hidden=cmd["benbotstatus"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def fetch_benbot_status_command(self, ctx):
        async with ClientSession() as session:
            async with session.get('https://benbot.app/api/v1/status') as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()
                await ctx.reply(
                    embed=Embed(title="BenBot Status", color=Color.random())
                    .add_field(
                        name="Version",
                        value=f"`{data.get('currentFortniteVersion', 'Unknown')}`",
                        inline=False,
                    )
                    .add_field(
                        name="CDN Version",
                        value=f"`{data.get('currentCdnVersion', 'Unknown')}`",
                        inline=False,
                    )
                    .add_field(
                        name="Pak Count",
                        value=f"`{len(data.get('mountedPaks', []))}/{data.get('totalPakCount', 'Unknown')}`",
                        inline=False,
                    ),
                    mention_author=False
                )


    @command(name=cmd["aes"]["name"], aliases=cmd["aes"]["aliases"],
            brief=cmd["aes"]["brief"],
            description=cmd["aes"]["description"],
            usage=cmd["aes"]["usage"],
            help=cmd["aes"]["help"],
            hidden=cmd["aes"]["hidden"], enabled=True)
    @is_channel(CONSOLE_CHANNEL)
    @required_level(cmd["aes"]["required_level"])
    @guild_only()
    @cooldown(cmd["aes"]["cooldown_rate"], cmd["aes"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def fetch_fortnite_aes_command(self, ctx, version: Optional[str]):
        async with ClientSession() as session:
            async with session.get('https://benbot.app/api/v1/aes', params={"version":version} if version else None) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                data = await r.json()
                aes_embeds = []
                embed = Embed(title=data.get("version", "Unknown Version"), color=Color.teal()
                            ).add_field(name="**Main Key**", value=data.get("mainKey", "Unknown"))
                aes_embeds.append(embed)

                for pak in data.get("dynamicKeys", {}):
                    embed = Embed(title=pak.split("/")[-1], description=data.get("dynamicKeys", {}).get(pak, "Unknown"),
                                color=Color.teal())
                    aes_embeds.append(embed)

                message = await ctx.reply(embed=aes_embeds[0], mention_author=False)
                page = Paginator(self.bot, message, only=ctx.author, embeds=aes_embeds)
                await page.start()


    @command(name=cmd["cosmeticinfo"]["name"], aliases=cmd["cosmeticinfo"]["aliases"],
            brief=cmd["cosmeticinfo"]["brief"],
            description=cmd["cosmeticinfo"]["description"],
            usage=cmd["cosmeticinfo"]["usage"],
            help=cmd["cosmeticinfo"]["help"],
            hidden=cmd["cosmeticinfo"]["hidden"], enabled=True)
    @required_level(cmd["cosmeticinfo"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def show_fn_cosmetic_info_command(self, ctx, id: str):
        async with ClientSession() as session:
            async with session.get(f"https://benbot.app/api/v1/cosmetics/br/{id}", params={"lang":"ru"}) as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                cosmetic = await r.json()
                embed = Embed(
                    title=cosmetic.get("name", id),
                    description=f"{cosmetic.get('description', '')}\n{cosmetic.get('setText', 'Not part of any set.')}",
                    color=Color.random()
                ).add_field(name="Редкость", value=cosmetic.get("rarity", "Unknown"), inline=True)
                if type(cosmetic.get("series", "")) == dict:
                    embed.add_field(
                        name="Набор", value=cosmetic["series"].get("name", "None"), inline=True
                    )
                else:
                    embed.add_field(name="Series", value="None", inline=True)
                embed.add_field(
                    name="Backend Type",
                    value=cosmetic.get("backendType", "Unknown"),
                    inline=True,
                ).add_field(
                    name="Gameplay Tags",
                    value="```" + "\n".join(cosmetic.get("gameplayTags", "None")) + "```",
                    inline=False,
                ).add_field(
                    name="Path", value="`" + cosmetic.get("path", "Unknown") + "`", inline=False
                )
                if type(cosmetic.get("icons", "")) == dict:
                    if cosmetic["icons"].get("icon", None) is not None:
                        embed.set_thumbnail(url=cosmetic["icons"]["icon"])
                    if cosmetic["icons"].get("featured", None) is not None:
                        embed.set_image(url=cosmetic["icons"]["featured"])
                await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["extractasset"]["name"], aliases=cmd["extractasset"]["aliases"],
            brief=cmd["extractasset"]["brief"],
            description=cmd["extractasset"]["description"],
            usage=cmd["extractasset"]["usage"],
            help=cmd["extractasset"]["help"],
            hidden=cmd["extractasset"]["hidden"], enabled=True)
    @is_owner()
    @logger.catch
    async def extract_fn_asset_command(self, ctx, path: str, *, args: str = None):
        if args is not None:
            parser = Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument('-lang', nargs='+')
            parser.add_argument('-rawIcon', nargs='+')
            parser.add_argument('-noFeatured', nargs='+')
            parser.add_argument('-noVariants', nargs='+')
            parser.add_argument('-priceDaily', nargs='+')
            parser.add_argument('-priceFeatured', nargs='+')

            try:
                args = parser.parse_args(shlex.split(args))
            except Exception as e:
                await ctx.reply(str(e), mention_author=False)

            parameter = ""

            if args.lang:
                parameter += f"&lang={args.lang[0].lower()}"
            else:
                parameter += "&lang=ru"

            if args.rawIcon:
                parameter += f"&rawIcon={args.rawIcon[0].lower()}"

            if args.noFeatured:
                parameter += f"&noFeatured={args.noFeatured[0].lower()}"

            if args.noVariants:
                parameter += f"&noVariants={args.noVariants[0].lower()}"

            if args.priceDaily:
                parameter += f"&priceDaily={args.priceDaily[0].lower()}"

            if args.priceFeatured:
                parameter += f"&priceFeatured={args.priceFeatured[0].lower()}"

        else:
            parameter = "&lang=ru"

        async with ClientSession() as session:
            async with session.get(f"https://benbot.app/api/v1/exportAsset?path={path}{parameter}") as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return

                elif r.headers.get("Content-Type", None) == "audio/ogg":
                    await ctx.reply(
                        file=File(
                            fp=BytesIO(await r.read()),
                            filename=r.headers.get("filename", "audio.ogg")
                        ),
                        mention_author=False
                    )
                elif r.headers.get("Content-Type", None) == "image/png":
                    await ctx.reply(
                        file=File(
                            fp=BytesIO(await r.read()),
                            filename=r.headers.get("filename", "image.png"),
                        ),
                        mention_author=False
                    )
                elif r.headers.get("Content-Type", None) == "application/json":
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                else:
                    await ctx.reply(
                        f"```Unknown Content-Type: {r.headers.get('Content-Type', 'Unknown')}```",
                        mention_author=False
                    )


    @command(name=cmd["shopsections"]["name"], aliases=cmd["shopsections"]["aliases"],
            brief=cmd["shopsections"]["brief"],
            description=cmd["shopsections"]["description"],
            usage=cmd["shopsections"]["usage"],
            help=cmd["shopsections"]["help"],
            hidden=cmd["shopsections"]["hidden"], enabled=True)
    @required_level(cmd["shopsections"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["shopsections"]["cooldown_rate"], cmd["shopsections"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def display_fortnite_section_store_command(self, ctx, lang: str = 'ru'):
        async with ClientSession() as session:
            async with session.get(f'https://fn-api.com/api/shop/sections?lang={lang}') as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )
                    return
                data = await r.json()

        time = ""
        j = data['data']['timestamp'].split("T")
        i = j[0].split("-")
        time += f"{i[2]}.{i[1]}.{i[0]} {j[1][:-1]}"

        embed = Embed(
            title="Разделы магазина предметов",
            color=Color.gold(),
            timestamp=datetime.utcnow(),
            description=f'Актуально до: {time} UTC.\n\n'
        )

        var = ""
        for section in data['data']['sections']:
            name = section["name"] if section["name"] else section["id"]
            var += f'— **{name}**'
            if section['quantity'] > 1:
                var += f' (x{section["quantity"]})\n'
            else:
                var += '\n'

        embed.description += var
        await ctx.reply(embed=embed, mention_author=False)


    ### Fortnite dev servers
    @command(name=cmd["fndev"]["name"], aliases=cmd["fndev"]["aliases"],
            brief=cmd["fndev"]["brief"],
            description=cmd["fndev"]["description"],
            usage=cmd["fndev"]["usage"],
            help=cmd["fndev"]["help"],
            hidden=cmd["fndev"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def fortnite_dev_servers_state_command(self, ctx, server: str = 'None'):
        servers_embeds = []
        if server.lower() == "stage":
            async with ClientSession() as session:
                async with session.get("https://fortnite-public-service-stage.ol.epicgames.com/fortnite/api/version") as r:
                    if r.status != 200:
                        await ctx.reply(
                            f"""```json\n{await r.text()}```""",
                            mention_author=False
                        )
                        return

                    data = await r.json()

                    embed = Embed(
                        title="FortniteStageMain",
                        color=Color.orange(),
                        timestamp=ctx.message.created_at,
                        )

                    embed.add_field(name="Module", value=data["moduleName"], inline=True)
                    embed.add_field(name="Branch", value=data["branch"], inline=True)
                    embed.add_field(name="Version", value=data["version"], inline=True)
                    embed.add_field(name="Build", value=data["build"], inline=True)
                    embed.add_field(name="Build-Date", value=data["buildDate"], inline=True)
                    embed.add_field(name="Changelog #", value=data["cln"], inline=True)

                    await ctx.reply(embed=embed, mention_author=False)
                    return
        else:
            async with aiofiles.open('./data/json/fn_dev_servers.json', 'r', encoding='utf-8') as f:
                data = json.loads(await f.read())
                servers = data['servers']

            wait_embed = Embed(
                title="Fornite Dev Servers",
                color=Color.magenta(),
                description="⏳ Сбор данных. Пожалуйста, подождите."
            )
            wait_msg = await ctx.reply(embed=wait_embed, mention_author=False)

            async with ctx.typing():
                for url in servers:
                    try:
                        async with ClientSession() as session:
                            server_url = "https://" + url + "/fortnite/api/version"
                            async with session.get(server_url) as r:
                                if r.status != 200:
                                    continue

                                data = await r.json()

                                embed = Embed(
                                    title="Fortnite Dev Server",
                                    color=Color.orange(),
                                    timestamp=ctx.message.created_at,
                                    description=f"**Server:** `{url}`"
                                    )

                                embed.add_field(name="Module", value=data["moduleName"], inline=True)
                                embed.add_field(name="Branch", value=data["branch"], inline=True)
                                embed.add_field(name="Version", value=data["version"], inline=True)
                                embed.add_field(name="Build", value=data["build"], inline=True)
                                embed.add_field(name="Build-Date", value=data["buildDate"], inline=True)
                                embed.add_field(name="Changelog #", value=data["cln"], inline=True)

                                servers_embeds.append(embed)

                    except:
                        continue

            await wait_msg.delete()
            msg = await ctx.reply(embed=servers_embeds[0], mention_author=False)
            page = Paginator(self.bot, msg, only=ctx.author, embeds=servers_embeds)
            await page.start()


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
    @logger.catch
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


def setup(bot):
    bot.add_cog(Fortnite(bot))
