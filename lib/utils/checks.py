from discord.ext import commands

from typing import List

from ..utils import constants
from ..db import db


def is_channel(channel: int):
    """
    A check() that checks if the command is invoked in allowed channel.
    """
    def predicate(ctx):
        return ctx.message.channel.id == channel
    return commands.check(predicate)


def is_any_channel(channels: List[int]):
    """
    Similar to is_channel(), butchecks if the command is invoked in any allowed channel.
    """
    def predicate(ctx):
        return any([ctx.message.channel.id == cid for cid in channels])
    return commands.check(predicate)


def required_level(level:int):
    """
    A check() that checks if member has minimal required level to run a command.
    """
    def predicate(ctx):
        rec = db.fetchone(["level"], "leveling", 'user_id', ctx.author.id)
        return True if int(rec[0]) >= level else False

    return commands.check(predicate)