import time
from aiohttp import ClientSession
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
                self.modified_commands[cmd] = command.cog.qualified_name
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
                command_cog = self.bot.get_cog(self.modified_commands[cmd])
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


    @command(name=cmd["fnping"]["name"], aliases=cmd["fnping"]["aliases"], 
            brief=cmd["fnping"]["brief"],
            description=cmd["fnping"]["description"],
            usage=cmd["fnping"]["usage"],
            help=cmd["fnping"]["help"],
            hidden=cmd["fnping"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def ping_fortnite_apis_command(self, ctx):
        """Get the response time for APIs."""
        message = await ctx.send("Response time for APIs:")
        async with ClientSession() as session:
            now = time.monotonic()
            async with session.get('https://benbotfn.tk/api/v1/status') as r:
                benbot_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://fortnite-api.com') as r:
                fnapicom_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://fortniteapi.io') as r:
                fnapiio_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://fortnitetracker.com') as r:
                fntracker_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://api.nitestats.com') as r:
                ninestats_ping = time.monotonic() - now if r.status == 200 else 0

        await message.edit(
            embed=Embed(color=Color.random())
            .add_field(name="Discord", value=f"{round(self.bot.latency * 1000)} ms.")
            .add_field(
                name="BenBot",
                value=f"{round(benbot_ping * 1000)} ms.",
            )
            .add_field(
                name="FortniteAPI.com",
                value=f"{round(fnapicom_ping * 1000)} ms.",
            )
            .add_field(
                name="FortniteAPI.io",
                value=f"{round(fnapiio_ping * 1000)} ms.",
            )
            .add_field(
                name="FortniteTracker",
                value=f"{round(fntracker_ping * 1000)} ms.",
            )
            .add_field(
                name="NiteStats",
                value=f"{round(ninestats_ping * 1000)} ms.",
            ),
        )
        inline = True


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("owner")


def setup(bot):
    bot.add_cog(Owner(bot))