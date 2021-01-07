from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.commands import is_owner, guild_only
from random import randint

from ..utils import checks

class Fun(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(name="test", aliases=["testalias"], 
            brief="Краткое описание команды для help message.",
            description="Подробное описание при запросе help для этой команды.",
            usage="Пример использования команды с приведением аргументов.",
            help="The long help text for the command.",
            enabled=True, hidden=False)
    @guild_only()
    @is_owner()
    async def test_command(self, ctx):
        await ctx.send('A simple command that works only for bot owner!')


    @command(name="dice", aliases=["roll"])
    @guild_only()
    @is_owner()
    async def dice_command(self, ctx, dice_string: str):
        dice, value = (int(term) for term in dice_string.split("d"))
        rolls = [randint(1, value) for i in range(dice)]

        await ctx.send(" + ".join([str(r) for r in rolls]) + f" = {sum(rolls)}")


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fun")


def setup(bot):
    bot.add_cog(Fun(bot))
