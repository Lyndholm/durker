import json
import aiofiles
from os import getenv
from aiohttp import ClientSession
from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime

from ..utils.utils import load_commands_from_json
from ..utils.paginator import Paginator

cmd = load_commands_from_json("fortniteapiio")


class FortniteAPIio(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.headers = {"Authorization": getenv("FORTNITEAPIIO_TOKEN")}

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fortniteapiio")

    @command(name=cmd["map"]["name"], aliases=cmd["map"]["aliases"], 
            brief=cmd["map"]["brief"],
            description=cmd["map"]["description"],
            usage=cmd["map"]["usage"],
            help=cmd["map"]["help"],
            hidden=cmd["map"]["hidden"], enabled=True)
    async def show_fortnite_map_command(self, ctx, poi:str="None", language="ru"):
        embed = Embed(title="Карта Королевской Битвы",color=Color.orange(), timestamp=datetime.utcnow())
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        if poi.lower() == "poi":
            embed.set_image(url=f"https://media.fortniteapi.io/images/map.png?showPOI=true&lang={language}")
        else:
            embed.set_image(url="https://media.fortniteapi.io/images/map.png")

        await ctx.send(embed=embed)


    @command(name=cmd["fnach"]["name"], aliases=cmd["fnach"]["aliases"], 
            brief=cmd["fnach"]["brief"],
            description=cmd["fnach"]["description"],
            usage=cmd["fnach"]["usage"],
            help=cmd["fnach"]["help"],
            hidden=cmd["fnach"]["hidden"], enabled=True)
    async def show_fortnite_achievements_command(self, ctx, language: str ="ru"):
        achievement_embeds = []
        divided = []

        async with ClientSession(headers=self.headers) as session:
            async with session.get("https://fortniteapi.io/v1/achievements", params={"lang":language}) as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
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

        message = await ctx.send(embed=achievement_embeds[0][0])
        page = Paginator(self.bot, message, only=ctx.author, use_more=True, embeds=achievement_embeds)
        await page.start()


    @command(name=cmd["fish"]["name"], aliases=cmd["fish"]["aliases"], 
            brief=cmd["fish"]["brief"],
            description=cmd["fish"]["description"],
            usage=cmd["fish"]["usage"],
            help=cmd["fish"]["help"],
            hidden=cmd["fish"]["hidden"], enabled=True)
    async def show_fortnite_fish_list_command(self, ctx, number: int = 0, language: str ="ru"):
        async with aiofiles.open('./data/fish.json', mode='r', encoding='utf-8') as f:
            data = json.loads(await f.read())

        if number == 0:
            fish_embeds = []
            for count, entry in enumerate(data["fish"]):
                embed = Embed(
                    title=entry['name'] + f" | {str(count+1)}",
                    color=Color.blue(),
                    description=entry['description'],
                )
                embed.set_thumbnail(url=entry['image'])

                fields = [
                    ("Редкость", entry["rarity"], True),
                    ("Подробности", entry["details"], True),
                    ("Требуется проф. удочка", "Да" if entry["needsProFishingRod"] else "Нет", True),
                    ("Минимальный размер", entry["sizeMin"], True),
                    ("Максимальный размер", entry["sizeMax"], True),
                    ("Максимум в слоте", entry["maxStackSize"], True)
                ]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                fish_embeds.append(embed)

            message = await ctx.send(embed=fish_embeds[0])
            page = Paginator(self.bot, message, only=ctx.author, embeds=fish_embeds)
            await page.start()
            return

        else:
            if number > len(data['fish']) or number < 0:
                embed = Embed(title='Некорректный номер рыбки!', color= Color.red())
                await ctx.message.reply(embed=embed)
                return
            number-=1
            embed = Embed(
                    title=data['fish'][number]['name'] + f" | {str(number+1)}",
                    color=Color.blue(),
                    description=data['fish'][number]['description']
                )
            embed.set_thumbnail(url=data['fish'][number]['image'])

            fields = [
                    ("Редкость", data['fish'][number]["rarity"], True),
                    ("Подробности", data['fish'][number]["details"], True),
                    ("Требуется проф. удочка", "Да" if data['fish'][number]["needsProFishingRod"] else "Нет", True),
                    ("Минимальный размер", data['fish'][number]["sizeMin"], True),
                    ("Максимальный размер", data['fish'][number]["sizeMax"], True),
                    ("Максимум в слоте", data['fish'][number]["maxStackSize"], True)
                ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await ctx.send(embed=embed)
                

def setup(bot):
    bot.add_cog(FortniteAPIio(bot))
