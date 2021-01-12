from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.commands import is_owner, dm_only


from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("owner")


class Owner(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.modified_commands = {}
    
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


    @command(name=cmd["disablecmd"]["name"], aliases=cmd["disablecmd"]["aliases"], 
            brief=cmd["disablecmd"]["brief"],
            description=cmd["disablecmd"]["description"],
            usage=cmd["disablecmd"]["usage"],
            help=cmd["disablecmd"]["help"],
            hidden=cmd["disablecmd"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def disable_cmd_command(self, ctx, *, cmd: str):
        try:
            command = self.bot.get_command(name=cmd)
            if command.enabled:
                cmd_data = {
                    "command": cmd,
                    "cog": command.cog.qualified_name
                }
                self.modified_commands[cmd] = cmd_data
                command.update(enabled=False, hidden=True)
                embed = Embed(title=':thumbsup: Успешно!', description=f'Команда **`{cmd}`** отключена!', color = Color.green())
                await ctx.send(embed=embed)
            else:
                embed = Embed(title=':exclamation: Ошибка!', description=f'Команда `{cmd}` уже отключена.', color = Color.red())
                await ctx.send(embed=embed)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)


    @command(name=cmd["enablecmd"]["name"], aliases=cmd["enablecmd"]["aliases"], 
            brief=cmd["enablecmd"]["brief"],
            description=cmd["enablecmd"]["description"],
            usage=cmd["enablecmd"]["usage"],
            help=cmd["enablecmd"]["help"],
            hidden=cmd["enablecmd"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def enable_cmd_command(self, ctx, *, cmd: str):
        try:
            command = self.bot.get_command(name=cmd)
            if not command.enabled:
                command_cog = self.bot.get_cog(self.modified_commands[cmd]["cog"])
                command.update(enabled=True, hidden=False)
                command.cog = command_cog
                del self.modified_commands[cmd]
                embed = Embed(title=':thumbsup: Успешно!', description=f'Команда **`{cmd}`** включена!', color = Color.green())
                await ctx.send(embed=embed)
            else:
                embed = Embed(title=':exclamation: Ошибка!', description=f'Команда `{cmd}` сейчас активна. Повторное включение невозможно', color = Color.red())
                await ctx.send(embed=embed)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
    

    @command(name=cmd["disabledcmds"]["name"], aliases=cmd["disabledcmds"]["aliases"], 
            brief=cmd["disabledcmds"]["brief"],
            description=cmd["disabledcmds"]["description"],
            usage=cmd["disabledcmds"]["usage"],
            help=cmd["disabledcmds"]["help"],
            hidden=cmd["disabledcmds"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def show_disabled_cmds_command(self, ctx):
        disabled_cmds = []
        for command in self.bot.commands:
            if not command.enabled:
                disabled_cmds.append(str(command))
        embed = Embed(title=':arrow_down: Отключённые команды.', description="\n".join(disabled_cmds) if disabled_cmds else "Все команды работают в штатном режиме.", color = Color.red())
        await ctx.send(embed=embed)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("owner")


def setup(bot):
    bot.add_cog(Owner(bot))