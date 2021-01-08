from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command

from aiohttp import ClientSession
from random import choice, randint

import json


class Nekos(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.anime_categories = ("waifu", "neko", "megumin")
        self.anime_weeb_services = ("senko", "neko", "kanna")
        self.waifu_images = ("https://cdn.discordapp.com/attachments/774698479981297664/797231152477765682/unity_girl.png",
                            "https://cdn.discordapp.com/attachments/774698479981297664/797231173847220264/c_animegirl.png")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("nekos")

    @command(name="anipic", aliases=['аниме', 'anime'],
        brief="Отображает случайную аниме картинку.",
        description='Бот присылает случайную картинку c аниме-тян.',
        help="Все картинки SFW (safe for work) и не содержат эротический контент. По крайней мере, так написано в документации используемого API. "
            "Если вы обнаружили, что картинка таковой не является, сообщите, пожалуйста, об этом администрации сервера.",
        enabled=True, hidden=False)
    async def random_anime_picture_command(self, ctx):  
        chance = randint(0,100)
        if 40 < chance < 100:
            async with ClientSession() as session:
                async with session.get(f'https://waifu.pics/api/sfw/{choice(self.anime_categories)}') as r:
                        if r.status == 200:
                            data = await r.json()
                            img = data["url"]

        elif 3 < chance < 39:
            img = f'https://{choice(self.anime_weeb_services)}.weeb.services/'

        else:
            img = choice(self.waifu_images)

        embed = Embed(title = f'Anime picture',color=Color.random(), timestamp=ctx.message.created_at)
        embed.set_image(url=img)
        embed.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Nekos(bot))
