from discord.ext.commands import Cog
from discord.ext.commands import command


class Nekos(Cog):
    def __init__(self, bot):
        self.bot = bot


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("nekos")


def setup(bot):
    bot.add_cog(Nekos(bot))
