import shlex
from argparse import ArgumentParser
from asyncio.exceptions import TimeoutError
from datetime import datetime

from aiohttp import ClientSession
from discord import Color, Embed, File, HTTPException
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL, PLACEHOLDER
from ..utils.paginator import Paginator
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("fortniteapicom")


class Arguments(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class FortniteAPIcom(Cog, name='Fortnite API 2'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fortniteapicom")

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
            embed = Embed(color=Color.random())
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

            try:
                embed.add_field(name="ID:", value=i["id"] + " (**" + str(len(i["id"])) + "**)",
                                inline=False)
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
                for i2 in i["shopHistory"][::-1]:
                    i2 = i2.split("T")
                    i2 = i2[0].split("-")
                    hist += f"{i2[2]}.{i2[1]}.{i2[0]}\n"
                hist += "```"
                embed.add_field(name="Появления в магазине:", value=hist[:1024], inline=False)
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

            msg = await ctx.reply(embed=embed, mention_author=False)
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
            'https://cdn.discordapp.com/attachments/774698479981297664/817861711813148752/cosmetics_search_params_1.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/817861722312146984/cosmetics_search_params_2.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/817861887441109012/cosmetics_search_params_3.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/817861907868287026/cosmetics_search_params_4.png',
            'https://cdn.discordapp.com/attachments/774698479981297664/817861931984879627/cosmetics_search_params_5.png'
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
    @required_level(cmd["creatorcode"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["creatorcode"]["cooldown_rate"], cmd["creatorcode"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_creator_code_data_command(self, ctx, code: str = "fnfun"):
        async with ClientSession() as session:
            async with session.get(f"https://fortnite-api.com/v2/creatorcode/search/all", params={"name": code}) as r:
                if r.status == 404:
                    embed = Embed(title='❗ Внимание!', description ="Указанный тег автора не найден.", color= Color.red())
                    await ctx.message.reply(embed=embed, mention_author=False)
                elif r.status == 200:
                    data = await r.json()
                    data = data["data"]
                    code_embeds = []

                    for i in range(0,len(data)):
                        embed = Embed(
                            title=f'Код автора: {data[i]["code"]}',
                            color=Color.random(),
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
                        embed.add_field(
                            name="Verified",
                            value=data[i]["verified"],
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
        shop_img = File("athena/itemshop.png", filename="itemshop.png")

        embed = Embed(
            title="Магазин Королевской Битвы",
            color=Color.magenta(),
            timestamp=datetime.utcnow(),
            description=f"⌛ Дата: {datetime.now().strftime('%d.%m.%Y')}\n🎲 Тег автора: FNFUN"
        )
        embed.set_image(url="attachment://itemshop.png")
        try:
            await ctx.reply(embed=embed, file=shop_img, mention_author=False)
        except HTTPException:
            try:
                shop_img = File("athena/itemshop.jpg", filename="itemshop.jpg")
                embed.set_image(url="attachment://itemshop.jpg")
                await ctx.reply(embed=embed, file=shop_img, mention_author=False)
            except:
                embed = Embed(title='❗ HTTPException',
                description=f"Если вы видите это сообщение, значит, вес изображения с магазином превышает 8 Мб, "
                            "вследствие чего картинку невозможно отправить.\n"
                            "Пожалуйста, сообщите об этом <@375722626636578816>",
                color=Color.red())
                await ctx.reply(embed=embed, mention_author=False)


def setup(bot):
    bot.add_cog(FortniteAPIcom(bot))
