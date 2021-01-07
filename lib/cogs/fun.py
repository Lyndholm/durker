from discord import Embed, Color, Member
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.commands import is_owner, guild_only
from discord.ext.commands.errors import CheckFailure
from discord.errors import HTTPException

from random import randint, choice
from aiohttp import ClientSession
from asyncio import sleep

from ..utils import checks

class Fun(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hug_gifs = ["https://media4.giphy.com/media/PHZ7v9tfQu0o0/giphy.gif", 
                        "https://i.pinimg.com/originals/f2/80/5f/f2805f274471676c96aff2bc9fbedd70.gif",
                        "https://media.tenor.com/images/b6d0903e0d54e05bb993f2eb78b39778/tenor.gif",
                        "https://thumbs.gfycat.com/AlienatedFearfulJanenschia-small.gif",
                        "https://i.imgur.com/r9aU2xv.gif",
                        "https://25.media.tumblr.com/2a3ec53a742008eb61979af6b7148e8d/tumblr_mt1cllxlBr1s2tbc6o1_500.gif",
                        "https://media.tenor.com/images/ca88f916b116711c60bb23b8eb608694/tenor.gif"]


    @command(name="hug", aliases=["обнять","обнимашки"], 
            brief="Обнимите кого-нибудь!",
            description="Покажите всем свою любовь и обнимите кого-нибудь!",
            usage="<member>",
            help="The long help text for the command.",
            enabled=True, hidden=False)
    async def hug_command(self, ctx, *, member: Member):
        await ctx.message.delete()
        async with ClientSession() as session:
            async with session.get('https://some-random-api.ml/animu/hug') as r:
                if r.status == 200:
                    data = await r.json()
                    hug_gif_url = data["link"]
                else:
                    hug_gif_url = choice(self.hug_gifs)

        embed = Embed(title = f'**Обнимашки!**',description = f'{ctx.author.mention} обнял(-а) {member.mention} :heart::sparkles:', color=ctx.author.color)
        embed.set_image(url=hug_gif_url)
        await ctx.send(embed=embed, delete_after=180)


    @command(name="coin", aliases=['монетка', 'орел_решка','о_р','орёл_решка'],
            brief="Сыграйте в орёл-решка.",
            description='Бот подбрасывает монетку.',
            help="Пригодится при непростом выборе.",
            enabled=True, hidden=False)
    @checks.required_level(5)
    @checks.is_any_channel([777979537795055636, 796439346344493107, 708601604353556491])
    @guild_only()
    async def drop_coin_command(self, ctx):
        robot_choice = choice(["орёл", "решка"])
                                   
        embed = Embed(title=":coin: Орёл или решка", description = "Подбрасываем монетку....", color=Color.red())
        message = await ctx.send(embed=embed)

        await sleep(3)

        embed_new = embed = Embed(title=":coin: Орел или решка", description = f"Выпало: {'**Орёл**' if robot_choice == 'орёл' else '**Решка**'}", color=Color.green(), timestamp=ctx.message.created_at)
        embed_new.set_footer(text=f'{ctx.author.name}', icon_url=ctx.author.avatar_url)
        await message.edit(embed=embed_new)

    @drop_coin_command.error
    async def drop_coin_command_error(self, ctx, exc):
        await ctx.message.delete()
        if isinstance(exc, CheckFailure):
            embed = Embed(title=':exclamation: Ошибка!', description =f"{ctx.author.mention}\nКоманда `{ctx.command}` может быть использована только в канале <#708601604353556491>"
            "\nТакже у вас должен быть 5-й и выше уровень.", color = Color.red())
            await ctx.send(embed=embed, delete_after = 30)


    @command(name="dice", aliases=["roll"])
    @guild_only()
    @is_owner()
    async def dice_command(self, ctx, dice_string: str):
        dice, value = (int(term) for term in dice_string.split("d"))
        rolls = [randint(1, value) for i in range(dice)]

        await ctx.send(" + ".join([str(r) for r in rolls]) + f" = {sum(rolls)}")

    @dice_command.error
    async def dice_command_error(self, ctx, exc):
        if isinstance(exc.original, HTTPException):
            await ctx.send("Длина получившейся комбинации превышает лимит символов (2000). Пожалуйста, используйте числа меньше.", delete_after = 15)
        elif isinstance(exc.original, ValueError):
            await ctx.send("Пожалуйста, введите корректную комбинацию.", delete_after = 15)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fun")


def setup(bot):
    bot.add_cog(Fun(bot))
