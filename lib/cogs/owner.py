from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.commands import is_owner, dm_only


class Owner(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name="loadcog", aliases=["cogload"], 
            brief="Загружает указанный cog в бота.",
            description="Загружает, инициализирует и запускает cog.",
            usage="cogs.{cog_name}",
            help="Большой текст для help команды.",
            enabled=True, hidden=True)
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


    @command(name="unloadcog", aliases=["cogunload"], 
        brief="Выгружает из бота указанный cog.",
        description="Деактивирует и выгружает cog.",
        usage="cogs.{cog_name}",
        help="Большой текст для help команды.",
        enabled=True, hidden=True)
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


    @command(name="reloadcog", aliases=["cogreload"], 
    brief="Перезагружает указанный cog.",
    description="Деактивирует, выгружает, загружает и активирует cog.",
    usage="cogs.{cog_name}",
    help="Большой текст для help команды.",
    enabled=True, hidden=True)
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