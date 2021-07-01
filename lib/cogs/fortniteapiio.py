import json
from datetime import datetime
from os import getenv
from random import choice, randint

import aiofiles
from aiohttp import ClientSession
from discord import Color, Embed
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.paginator import Paginator
from ..utils.utils import load_commands_from_json

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

        async with ClientSession(headers=self.headers) as session:
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
        async with aiofiles.open('./data/json/fish_s17.json', mode='r', encoding='utf-8') as f:
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
        QUEST_ID = "Quest_S17_Milestone"
        quest_embeds = []
        xp_total = 0
        async with ClientSession(headers=self.headers) as session:
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
        async with aiofiles.open('./data/json/characters_s17.json', mode='r', encoding='utf-8') as f:
            data = json.loads(await f.read())

        if number == 0:
            npc_embeds = []
            embed = Embed(
                title="Все персонажи и боссы в 17 сезоне фортнайт",
                color=Color.random(),
                description=\
                    "17 сезон фортнайт оказался весьма хилым на разнообразие персонажей, а потому мы имеем только 17 NPC. "
                    "Да, тут явно сыграл символизм — 17 сезон, значит и персонажей 17.\n\n"
                    "Сейчас вы видите карту всех персонажей фортнайт. Как обычно, есть отличившиеся, которые спавнятся не в одном месте. "
                    "Красным кругляшом отмечены персонажи — боссы, так что подходите к ним аккуратнее, а то съедят."
            )
            embed.set_image(url="https://fortnitefun.ru/wp-content/uploads/2021/06/%D0%92%D0%A1%D0%95.jpg")
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


def setup(bot):
    bot.add_cog(FortniteAPIio(bot))
