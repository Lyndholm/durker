from discord.ext import commands
from ..utils import constants


def is_me():
    def predicate(ctx):
        return ctx.message.author.id == constants.OWNER_ID
    return commands.check(predicate)