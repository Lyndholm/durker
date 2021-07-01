from typing import List

from discord.ext import commands

from ..db import db
from . import exceptions

radio_whitelisted_users = [
    384728793895665675, #tvoya_pechal
    342783617983840257, #lexenus
    479499525921308703, #cactus
    375722626636578816, #lyndholm
    195637386221191170, #nednar
]


def is_channel(channel: int):
    """
    A check() that checks if the command is invoked in allowed channel.
    """
    def predicate(ctx):
        if ctx.message.channel.id == channel:
            return True
        else:
            raise exceptions.NotInAllowedTextChannel
    return commands.check(predicate)


def is_any_channel(channels: List[int]):
    """
    Similar to is_channel(), but checks if the command is invoked in any allowed channel.
    """
    def predicate(ctx):
        if any([ctx.message.channel.id == cid for cid in channels]):
            return True
        else:
            raise exceptions.NotInAllowedTextChannel
    return commands.check(predicate)


def forbidden_channel(channel: int):
    """
    A check() that checks if the command is invoked in forbidden channel. It can not be used wuth is_channel() or is_any_channel() methods.
    """
    def predicate(ctx):
        if ctx.message.channel.id != channel:
            return True
        else:
            raise exceptions.InForbiddenTextChannel
    return commands.check(predicate)


def forbidden_channels(channels: List[int]):
    """
    Similar to forbidden_channel(), but checks if the command is invoked in any forbidden channel.
    """
    def predicate(ctx):
        if all([ctx.message.channel.id != cid for cid in channels]):
            return True
        else:
            raise exceptions.InForbiddenTextChannel
    return commands.check(predicate)


def required_level(level:int):
    """
    A check() that checks if member has minimal required level to run a command.
    """
    def predicate(ctx):
        rec = db.fetchone(["level"], "leveling", 'user_id', ctx.author.id)
        if int(rec[0]) >= level:
            return True
        else:
            raise exceptions.InsufficientLevel

    return commands.check(predicate)


def can_manage_radio():
    """
    A check() that checks if member can manage radio (use radio commands).
    """
    def predicate(ctx):
        return ctx.author.id in radio_whitelisted_users

    return commands.check(predicate)


def can_manage_radio_suggestions():
    """
    A check() that checks if member can manage radio suggestions.
    """
    def predicate(ctx):
        return ctx.author.id in [375722626636578816, 195637386221191170]

    return commands.check(predicate)
