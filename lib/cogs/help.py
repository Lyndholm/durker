import json
from random import choice
from typing import Optional

import aiofiles
from discord import Color, Embed
from discord.ext.commands import Cog, Command, check_any, command, dm_only
from discord.utils import get
from loguru import logger
from transliterate import translit

from ..utils.checks import is_any_channel
from ..utils.constants import CONSOLE_CHANNEL, PLACEHOLDER, STATS_CHANNEL, CHASOVOY_ROLE_ID
from ..utils.lazy_paginator import paginate
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("help")


class Help(Cog, name='Help меню'):
    def __init__(self, bot):
        self.bot = bot
        self.help_gifs = []
        self.bot.remove_command("help")

        bot.loop.create_task(self.parse_help_gifs_from_json())

    async def parse_help_gifs_from_json(self):
        async with aiofiles.open('./data/json/help_gifs.json', mode='r', encoding='utf-8') as f:
            self.help_gifs = json.loads(await f.read())

    def thumbnail(self, cog_name) -> str:
        cog = self.bot.get_cog(cog_name)
        name = cog.__class__.__name__
        url = choice(self.help_gifs.get(name, [PLACEHOLDER]))
        return url

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("help")

    @command(name=cmd["help"]["name"], aliases=cmd["help"]["aliases"],
            brief=cmd["help"]["brief"],
            description=cmd["help"]["description"],
            usage=cmd["help"]["usage"],
            help=cmd["help"]["help"],
            hidden=cmd["help"]["hidden"], enabled=True)
    @check_any(dm_only(), is_any_channel([CONSOLE_CHANNEL, STATS_CHANNEL]))
    @logger.catch
    async def help_command(self, ctx, *, cmd: Optional[str]):
        if cmd is None:
            embed = self.help_memu(ctx)
            await paginate(ctx, embed)
        else:
            thing = ctx.bot.get_cog(cmd) or ctx.bot.get_command(cmd)
            if isinstance(thing, Command):
                if not thing.hidden:
                    await paginate(ctx, self.command_helper(ctx, thing))
                elif thing.hidden and ctx.author.id == 375722626636578816:
                    await paginate(ctx, self.command_helper(ctx, thing))
                else:
                    embed = Embed(
                        title='❗ Ошибка!',
                        description =f"Указанная команда не существует, либо она скрыта или отключена.",
                        color = Color.red()
                    )
                    await ctx.reply(embed=embed, delete_after=15)

            elif isinstance(thing, Cog):
                await paginate(ctx, self.cog_helper(ctx, thing))
            else:
                await ctx.reply(
                    'Ничего не найдено. Проверьте правильность написания команды/раздела.'
                    'Учитывайте, что названия разделов чувствительны к регистру.',
                    delete_after=15
                )

    def chuncks(self, l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    @logger.catch
    def help_memu(self, ctx):
        hidden_cogs = ['модерация']
        commands = []
        sorted_cogs = sorted(ctx.bot.cogs, key=lambda x: translit(x, 'ru'))
        cogs = sorted_cogs.copy()
        if ctx.guild:
            chasovoy = get(ctx.guild.roles, id=CHASOVOY_ROLE_ID)
            for cog in sorted_cogs:
                if cog.lower() in hidden_cogs:
                    if ctx.author.top_role.position < chasovoy.position:
                        cogs.remove(cog)
        else:
            for cog in sorted_cogs:
                if cog.lower() in hidden_cogs:
                    cogs.remove(cog)


        for cog in cogs:
            if ctx.author.id == 375722626636578816:
                cmds = [i for i in ctx.bot.get_cog(cog).get_commands()]
            else:
                cmds = [i for i in ctx.bot.get_cog(cog).get_commands() if not i.hidden and i.enabled]

            for cmds_chunks in list(self.chuncks(list(cmds), 5)):
                embed = Embed(
                    title=f'Раздел: {cog} | Команд: {len(cmds)}',
                    color=ctx.author.color
                ).set_thumbnail(url=self.thumbnail(cog))
                for cmd in cmds_chunks:
                    embed.add_field(
                        name=f'{cmd.brief}',
                        value=f'```{ctx.prefix}{cmd.signature}```',
                        inline=False
                    )
                commands.append(embed)

            for idx, embed in enumerate(commands, 1):
                embed.set_footer(
                    text=f'Страница {idx} из {len(commands)} | {ctx.prefix}help <command> для подробностей о команде'
                )
        return commands

    @logger.catch
    def cog_helper(self, ctx, cog):
        name = cog.qualified_name or cog.__class__.__name__
        commands = []
        if ctx.author.id == 375722626636578816:
            cmds = [i for i in cog.get_commands()]
        else:
            cmds = [i for i in cog.get_commands() if not i.hidden and i.enabled]

        if not cmds:
            no_entry_embed = Embed(
                title='⛔ В доступе отказано.',
                color=Color.red(),
                description=f'Команды раздела `{name}` скрыты.'
            )
            return no_entry_embed

        for cmds_chunks in list(self.chuncks(list(cmds), 5)):
            embed = Embed(
                title=f'Раздел: {name} | Команд: {len(cmds)}',
                color=ctx.author.color
            ).set_thumbnail(url=self.thumbnail(name))
            for cmd in cmds_chunks:
                embed.add_field(
                    name=f'{cmd.brief}',
                    value=f'```{ctx.prefix}{cmd.signature}```',
                    inline=False
                )
            commands.append(embed)

        for idx, embed in enumerate(commands, 1):
            embed.set_footer(
                text=f'Страница {idx} из {len(commands)} | {ctx.prefix}help <command> для подробностей о команде'
            )
        return commands

    @logger.catch
    def command_helper(self, ctx, cmd):
        try:
            commands = []
            command = [i for i in cmd.commands if not i.hidden and i.enabled]

            for cmd_chunks in list(self.chuncks(list(command), 5)):
                aliases = '|'.join([*cmd.aliases])
                embed = Embed(
                    title=f'{ctx.prefix}{cmd.signature}',
                    color=ctx.author.color,
                    description=f'{cmd.help}\n**Алиасы:**\n```{aliases}```'
                )
                for c in cmd_chunks:
                    embed.add_field(
                        name=f'{c.brief}',
                        value=f'```{ctx.prefix}{c.signature}```',
                        inline=False
                    )
                commands.append(embed)

            for idx, embed in enumerate(commands, 1):
                embed.set_footer(
                    text=f'Страница {idx} из {len(commands)} | {ctx.prefix}help <command> для подробностей о команде'
                )
            return commands
        except AttributeError:
            aliases = '|'.join([*cmd.aliases])
            embed = Embed(
                title=f'{ctx.prefix}{cmd.signature}',
                color=ctx.author.color,
                description=f'{cmd.help}\n**Алиасы:**\n```{aliases}```'
            )
            return [embed]


def setup(bot):
    bot.add_cog(Help(bot))
