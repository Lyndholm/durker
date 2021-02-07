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
    async def show_fortnite_achievements_command(self, ctx, language="ru"):
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


def setup(bot):
    bot.add_cog(FortniteAPIio(bot))
