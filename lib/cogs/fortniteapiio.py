import json
import aiofiles
from os import getenv
from aiohttp import ClientSession
from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime
from random import randint, choice

from ..utils.utils import load_commands_from_json
from ..utils.paginator import Paginator

cmd = load_commands_from_json("fortniteapiio")


class FortniteAPIio(Cog, name='Fortnite API 3'):
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
    async def show_fortnite_fish_list_command(self, ctx, number: int = 0):
        async with aiofiles.open('./data/json/fish_s16.json', mode='r', encoding='utf-8') as f:
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

            await ctx.send(embed=embed)


    @command(name=cmd["challenges"]["name"], aliases=cmd["challenges"]["aliases"],
            brief=cmd["challenges"]["brief"],
            description=cmd["challenges"]["description"],
            usage=cmd["challenges"]["usage"],
            help=cmd["challenges"]["help"],
            hidden=cmd["challenges"]["hidden"], enabled=True)
    async def show_fortnite_rare_challenges_command(self, ctx, language: str = "ru"):
        QUEST_ID = "Quest_S16_Milestone"
        quest_embeds = []
        xp_total = 0
        async with ClientSession(headers=self.headers) as session:
            async with session.get("https://fortniteapi.io/v1/challenges", params={"season":"current", "lang":language}) as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
                    return

                data = await r.json()

        for item in data['other']:
            if QUEST_ID in item['challenges'][0]['quest_id']:
                embed = Embed(
                    title=f"📘 {item['challenges'][0]['title']}",
                    color=Color.random()
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/808066523671167006/battle_pass_quests_logo.png")

                if randint(0, 100) == 1:
                    embed.set_image(url="https://cdn.discordapp.com/attachments/708601604353556491/808062904325767248/i.png")
                    embed.description = "**Опа, пасхал04ка**"

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

        message = await ctx.send(embed=quest_embeds[0])
        page = Paginator(self.bot, message, only=ctx.author, embeds=quest_embeds)
        await page.start()


    @command(name=cmd["npc"]["name"], aliases=cmd["npc"]["aliases"],
            brief=cmd["npc"]["brief"],
            description=cmd["npc"]["description"],
            usage=cmd["npc"]["usage"],
            help=cmd["npc"]["help"],
            hidden=cmd["npc"]["hidden"], enabled=True)
    async def show_fortnite_characters_command(self, ctx, number: int = 0):
        async with aiofiles.open('./data/json/characters_s16.json', mode='r', encoding='utf-8') as f:
            data = json.loads(await f.read())

        if number == 0:
            npc_embeds = []
            embed = Embed(
                title="Все персонажи и боссы в 16 сезоне фортнайт",
                color=Color.random(),
                description="Персонажей на карте 16 сезона фортнайт суммарно 46. Это аж на 6 больше, чем в начале прошлого сезона!\n"
                            "Среди них присутствует 4 босса (к ним стражи охраняющие свои башни не относятся). После смерти боссы становятся персонажами, которые также предлагают что-то к покупке.\n"
                            "Сразу отметим, что некоторых персонажей очень сложно найти. Они либо через раз спавнятся, либо вообще появляются только в командной потасовке, или наоборот, в обыкновенных режимах. Поэтому, если какого-то персонажа вы найти не можете, смените режим, возможно, это вам поможет."
            )
            embed.set_image(url="https://fortnitefun.ru/wp-content/uploads/2021/03/%D0%B2%D1%81%D0%B5-%D0%BF%D0%B5%D1%80%D1%81%D0%BE%D0%BD%D0%B0%D0%B6%D0%B8.jpg")
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

            message = await ctx.send(embed=npc_embeds[0])
            page = Paginator(self.bot, message, only=ctx.author, embeds=npc_embeds)
            await page.start()
            return

        else:
            if number > len(data) or number < 0:
                embed = Embed(title='Некорректный номер NPC!', color= Color.red())
                await ctx.message.reply(embed=embed)
                return

            number-=1
            embed = Embed(
                    title=f"{choice(['🔵','🟦','🔷'])} {data[number]['name']} | {str(number+1)}",
                    color=Color.blue(),
                    description=data[number]['description']['index'] + data[number]['description']['secondary']
                )
            embed.set_thumbnail(url=data[number]['images']['icon'])
            embed.set_image(url=data[number]['map'])

            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(FortniteAPIio(bot))
