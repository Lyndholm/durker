import shlex
from argparse import ArgumentParser
from asyncio.exceptions import TimeoutError
from aiohttp import ClientSession
from discord import Embed, Color, File, HTTPException
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime

from ..utils.constants import PLACEHOLDER
from ..utils.utils import load_commands_from_json
from ..utils.paginator import Paginator

cmd = load_commands_from_json("fortniteapicom")


class Arguments(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class FortniteAPIcom(Cog):
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
    async def search_fortnite_cosmetic_command(self, ctx, *, args: str = None):
        if args is not None:
            parser = Arguments(add_help=False, allow_abbrev=False)
            parser.add_argument('-name', nargs='+')
            parser.add_argument('-lang', nargs='+')
            parser.add_argument('-rarity', nargs='+')
            parser.add_argument('-unseenFor', nargs='+')
            parser.add_argument('-id', nargs='+')

            try:
                args = parser.parse_args(shlex.split(args))
            except Exception as e:
                await ctx.send(str(e))
                return

            parameter = "?"

            if args.name:
                name = ""
                for i in args.name:
                    if i != args.name[len(args.name) - 1]:
                        name += f"{i}+"
                    else:
                        name += f"{i}"
                parameter += f"&name={name}"

            if args.lang:
                parameter += f"&language={args.lang[0].lower()}"
            else:
                parameter += "&language=ru"

            if args.rarity:
                parameter += f"&rarity={args.rarity[0].lower()}"

            if args.unseenFor:
                parameter += f"&unseenFor={args.unseenFor[0].lower()}"

            if args.id:
                parameter += f"&id={args.id[0].lower()}"

            async with ClientSession() as session:
                async with session.get(
                        url=f"https://fortnite-api.com/v2/cosmetics/br/search{parameter}&matchMethod=contains") as r:
                    data = await r.json()

                    if r.status == 404:
                        embed = Embed(
                            title='Предмет не найден.', 
                            description=f"```txt\n" + data["error"] + "```", 
                            color=Color.red(),
                            timestamp=datetime.utcnow())
                        return await ctx.send(embed=embed)

                    elif r.status == 200:
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
                            embed.add_field(name="Первое появление:", value=i["introduction"]["text"], inline=False)
                        except:
                            pass
                        try:
                            hist = "```\n"
                            for i2 in i["shopHistory"]:
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
                        except Exception as ex:
                            #print(ex)
                            pass

                        if variants is True:
                            embed.set_footer(text="Нажмите на реакцию, чтобы увидеть дополнительные стили.")

                        msg = await ctx.send(embed=embed)
                        if variants is True:
                            await msg.add_reaction("✅")
                            try:
                                p = await self.bot.wait_for("raw_reaction_add", timeout=120,
                                                            check=lambda p: p.user_id == ctx.author.id and str(
                                                                p.emoji) == "✅" and p.channel_id == ctx.channel.id)
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
                            await page.start()

                        return
                    else:
                        embed = Embed(
                            title=':exclamation: Ошибка!', 
                            description=str(data["status"]) + "\n```txt\n" + data["error"] + "```", 
                            color=Color.red(),
                            timestamp=datetime.utcnow())
                        await ctx.send(embed=embed)
                        return
        else:
            await ctx.send(
                "Пожалуйста, введите аргументы корректно.\n\n```+searchcosmetic -name Renegade Raider -lang ru -rarity "
                "epic -unseenFor 120```")


    @command(name=cmd["news"]["name"], aliases=cmd["news"]["aliases"], 
            brief=cmd["news"]["brief"],
            description=cmd["news"]["description"],
            usage=cmd["news"]["usage"],
            help=cmd["news"]["help"],
            hidden=cmd["news"]["hidden"], enabled=True)
    async def show_fortnite_news_command(self, ctx, mode: str = "br", language: str = "ru"):
        mode = mode.lower()
        placeholder = PLACEHOLDER

        if mode not in ["br", "stw", "creative"]:
            embed = Embed(title=':exclamation: Внимание!', description ="Укажите режим корректно: `br`, `stw`, `creative`.", color= Color.red())
            await ctx.message.reply(embed=embed, mention_author=False)
            return

        async with ClientSession() as session:
            async with session.get(f"https://fortnite-api.com/v2/news/{mode}", params={"language": language}) as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
                    return

                data = await r.json()
                gif = data.get("data", {}).get("image", placeholder)
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

                    message = await ctx.send(embed=embeds[0])
                    page = Paginator(self.bot, message, only=ctx.author, embeds=embeds)
                    await page.start()
                    return

                await ctx.send(embed=embed)            


    @command(name=cmd["creatorcode"]["name"], aliases=cmd["creatorcode"]["aliases"], 
            brief=cmd["creatorcode"]["brief"],
            description=cmd["creatorcode"]["description"],
            usage=cmd["creatorcode"]["usage"],
            help=cmd["creatorcode"]["help"],
            hidden=cmd["creatorcode"]["hidden"], enabled=True)
    async def show_creator_code_data_command(self, ctx, code: str = "fnfun"):
        async with ClientSession() as session:
            async with session.get(f"https://fortnite-api.com/v2/creatorcode/search/all", params={"name": code}) as r:
                if r.status == 404:
                    embed = Embed(title=':exclamation: Внимание!', description ="Указанный тег автора не найден.", color= Color.red())
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

                    message = await ctx.send(embed=code_embeds[0])
                    page = Paginator(self.bot, message, only=ctx.author, embeds=code_embeds)
                    await page.start()

                else:
                    await ctx.send(f"```json\n{r.text}```")


    @command(name=cmd["shop"]["name"], aliases=cmd["shop"]["aliases"], 
            brief=cmd["shop"]["brief"],
            description=cmd["shop"]["description"],
            usage=cmd["shop"]["usage"],
            help=cmd["shop"]["help"],
            hidden=cmd["shop"]["hidden"], enabled=True)
    async def show_battle_royale_shop_command(self, ctx):
        shop_img = File("athena/itemshop.jpg", filename="itemshop.jpg")

        embed = Embed(
            title="Магазин Королевской Битвы",
            color=Color.magenta(),
            timestamp=datetime.utcnow(),
            description=f":hourglass: Дата: {datetime.now().strftime('%d.%m.%Y')}\n:game_die: Тег автора: FNFUN"
        )
        embed.set_image(url="attachment://itemshop.jpg")
        try:
            await ctx.send(embed=embed, file=shop_img)         
        except HTTPException:
            embed = Embed(title=':exclamation: HTTPException', 
            description =f"Если вы видите это сообщение, значит, вес изображения с магазином превышает 8 Мб, вследствие чего его невозможно отправить.\n"
                        "Пожалуйста, сообщите об этом <@375722626636578816>",
            color= Color.red())
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(FortniteAPIcom(bot))
