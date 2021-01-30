from aiohttp import ClientSession
from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime

from ..utils.utils import load_commands_from_json
from ..utils.paginator import Paginator

cmd = load_commands_from_json("fortniteapicom")


class FortniteAPIcom(Cog):
    def __init__(self, bot):
        self.bot = bot


    @command(name=cmd["news"]["name"], aliases=cmd["news"]["aliases"], 
            brief=cmd["news"]["brief"],
            description=cmd["news"]["description"],
            usage=cmd["news"]["usage"],
            help=cmd["news"]["help"],
            hidden=cmd["news"]["hidden"], enabled=True)
    async def show_fortnite_news_command(self, ctx, mode: str = "br", language: str = "ru"):
        mode = mode.lower()
        placeholder = "https://cdn.discordapp.com/attachments/774698479981297664/774700936958312468/placeholder.png"

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


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fortniteapicom")


def setup(bot):
    bot.add_cog(FortniteAPIcom(bot))
