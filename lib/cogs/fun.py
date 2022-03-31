import json
from asyncio import sleep
from random import choice, randint
from typing import Optional

import aiofiles
from aiohttp import ClientSession
from discord import Color, Embed, Member, File
from discord.ext.commands import (BucketType, Cog, Greedy, command, cooldown,
                                  guild_only, max_concurrency)
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import CONSOLE_CHANNEL
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("fun")


class Fun(Cog, name='Развлечения'):
    def __init__(self, bot):
        self.bot = bot
        self.hug_gifs = ["https://media4.giphy.com/media/PHZ7v9tfQu0o0/giphy.gif",
                        "https://i.pinimg.com/originals/f2/80/5f/f2805f274471676c96aff2bc9fbedd70.gif",
                        "https://media.tenor.com/images/b6d0903e0d54e05bb993f2eb78b39778/tenor.gif",
                        "https://thumbs.gfycat.com/AlienatedFearfulJanenschia-small.gif",
                        "https://i.imgur.com/r9aU2xv.gif",
                        "https://25.media.tumblr.com/2a3ec53a742008eb61979af6b7148e8d/tumblr_mt1cllxlBr1s2tbc6o1_500.gif",
                        "https://media.tenor.com/images/ca88f916b116711c60bb23b8eb608694/tenor.gif"]

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("fun")

    @command(name=cmd["hug"]["name"], aliases=cmd["hug"]["aliases"],
            brief=cmd["hug"]["brief"],
            description=cmd["hug"]["description"],
            usage=cmd["hug"]["usage"],
            help=cmd["hug"]["help"],
            hidden=cmd["hug"]["hidden"], enabled=True)
    @required_level(cmd["hug"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["hug"]["cooldown_rate"], cmd["hug"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def hug_command(self, ctx, targets: Greedy[Member]):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


    @command(name=cmd["coin"]["name"], aliases=cmd["coin"]["aliases"],
            brief=cmd["coin"]["brief"],
            description=cmd["coin"]["description"],
            usage=cmd["coin"]["usage"],
            help=cmd["coin"]["help"],
            hidden=cmd["coin"]["hidden"], enabled=True)
    @required_level(cmd["coin"]["required_level"])
    @logger.catch
    async def drop_coin_command(self, ctx):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


    @command(name=cmd["saper"]["name"], aliases=cmd["saper"]["aliases"],
            brief=cmd["saper"]["brief"],
            description=cmd["saper"]["description"],
            usage=cmd["saper"]["usage"],
            help=cmd["saper"]["help"],
            hidden=cmd["saper"]["hidden"], enabled=True)
    @required_level(cmd["saper"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["saper"]["cooldown_rate"], cmd["saper"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def saper_command(self, ctx):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


    @command(name=cmd["flags"]["name"], aliases=cmd["flags"]["aliases"],
            brief=cmd["flags"]["brief"],
            description=cmd["flags"]["description"],
            usage=cmd["flags"]["usage"],
            help=cmd["flags"]["help"],
            hidden=cmd["flags"]["hidden"], enabled=True)
    @max_concurrency(number=1, per=BucketType.guild, wait=False)
    @required_level(cmd["flags"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["flags"]["cooldown_rate"], cmd["flags"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def guess_flags_command(self, ctx):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


    @command(name=cmd["knb"]["name"], aliases=cmd["knb"]["aliases"],
            brief=cmd["knb"]["brief"],
            description=cmd["knb"]["description"],
            usage=cmd["knb"]["usage"],
            help=cmd["knb"]["help"],
            hidden=cmd["knb"]["hidden"], enabled=True)
    @required_level(cmd["knb"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def stone_scissors_paper_command(self, ctx, item: str):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


    @command(name=cmd["8ball"]["name"], aliases=cmd["8ball"]["aliases"],
            brief=cmd["8ball"]["brief"],
            description=cmd["8ball"]["description"],
            usage=cmd["8ball"]["usage"],
            help=cmd["8ball"]["help"],
            hidden=cmd["8ball"]["hidden"], enabled=True)
    @required_level(cmd["8ball"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def magic_ball_command(self, ctx, *, question: str):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


    @command(name=cmd["randint"]["name"], aliases=cmd["randint"]["aliases"],
            brief=cmd["randint"]["brief"],
            description=cmd["randint"]["description"],
            usage=cmd["randint"]["usage"],
            help=cmd["randint"]["help"],
            hidden=cmd["randint"]["hidden"], enabled=True)
    @logger.catch
    async def randint_command(self, ctx, a: int, b: int):
        await ctx.reply('Bruh', file=File('./data/images/bruh.jpg'))


def setup(bot):
    bot.add_cog(Fun(bot))
