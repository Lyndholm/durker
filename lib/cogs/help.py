from discord import Embed, Color
from discord.utils import get
from discord.ext.menus import MenuPages, ListPageSource
from discord.ext.commands import Cog
from discord.ext.commands import command

from typing import Optional

from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("help")


def syntax(command):
    cmd_and_aliases = "|".join([str(command), *command.aliases])
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")
    
    params = " ".join(params)
    return f"```{cmd_and_aliases} {params}```"


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=3)

    async def write_page(self, menu, fields = []):
        offset = (menu.current_page*self.per_page+1)
        len_data = len(self.entries)

        embed = Embed(title="Dungeon Durker Help", description="Help меню.", color=self.ctx.author.color)
        embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,} команд.")
        if self.ctx.guild:
            embed.set_thumbnail(url=self.ctx.guild.icon_url)

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page (self, menu, entries):
        fields = []

        for entry in entries:
            fields.append((entry.brief or "Описание отсутсвует.", syntax(entry)))

        return await self.write_page(menu, fields)


class Help(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")
    
    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("help")

    async def cmd_help(self, ctx, command):
        embed = Embed(title=f"Команда: {str(command)}", description=command.help, color=ctx.author.color)
        embed.add_field(name="Синтаксис:", value=syntax(command))
        await ctx.send(embed=embed)

    @command(name=cmd["help"]["name"], aliases=cmd["help"]["aliases"], 
            brief=cmd["help"]["brief"],
            description=cmd["help"]["description"],
            usage=cmd["help"]["usage"],
            help=cmd["help"]["help"],
            hidden=cmd["help"]["hidden"], enabled=True)
    async def help_command(self, ctx, cmd: Optional[str]):
        if cmd is None:
            commands_list = []
            
            for command in self.bot.commands:
                if not command.hidden:
                    commands_list.append(command)

            menu = MenuPages(source=HelpMenu(ctx, commands_list),
                             clear_reactions_after=True,
                             delete_message_after=False,
                             timeout=60.0)

            await menu.start(ctx)

        else:
            command = get(self.bot.commands, name=cmd)
            if command and not command.hidden:
                await self.cmd_help(ctx, command)
            elif command and command.hidden and ctx.author.id == 375722626636578816:
                await self.cmd_help(ctx, command)
            else:
                embed = Embed(title=':exclamation: Ошибка!', description =f"Указанная команда не существует, либо она скрыта или отключена.", color = Color.red())
                await ctx.send(embed=embed, delete_after = 30)


def setup(bot):
    bot.add_cog(Help(bot))
