from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.commands import is_owner, dm_only


from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("owner")


class Owner(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name=cmd["loadcog"]["name"], aliases=cmd["loadcog"]["aliases"], 
            brief=cmd["loadcog"]["brief"],
            description=cmd["loadcog"]["description"],
            usage=cmd["loadcog"]["usage"],
            help=cmd["loadcog"]["help"],
            hidden=cmd["loadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def load_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=':thumbsup: Успешно!', description=f'Cog **`{cog}`** успешно загружен и активирован!', color = Color.green())
            await ctx.send(embed=embed)


    @command(name=cmd["unloadcog"]["name"], aliases=cmd["unloadcog"]["aliases"], 
            brief=cmd["unloadcog"]["brief"],
            description=cmd["unloadcog"]["description"],
            usage=cmd["unloadcog"]["usage"],
            help=cmd["unloadcog"]["help"],
            hidden=cmd["unloadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def unload_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=':thumbsup: Успешно!', description=f'Cog **`{cog}`** успешно деактивирован и выгружен!', color = Color.green())
            await ctx.send(embed=embed)


    @command(name=cmd["reloadcog"]["name"], aliases=cmd["reloadcog"]["aliases"], 
            brief=cmd["reloadcog"]["brief"],
            description=cmd["reloadcog"]["description"],
            usage=cmd["reloadcog"]["usage"],
            help=cmd["reloadcog"]["help"],
            hidden=cmd["reloadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def reload_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=':thumbsup: Успешно!', description=f'Cog **`{cog}`** успешно перезагружен!', color = Color.green())
            await ctx.send(embed=embed)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("owner")


def setup(bot):
    bot.add_cog(Owner(bot))