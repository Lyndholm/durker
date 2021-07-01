from discord.ext import commands


class InsufficientLevel(commands.CommandError):
    pass

class NotInAllowedTextChannel(commands.CommandError):
    pass

class InForbiddenTextChannel(commands.CommandError):
    pass
