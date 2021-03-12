import io
import discord
import textwrap
import contextlib

from discord.ext import commands
from discord.ext.commands import Cog
from discord.ext.commands import command, is_owner
from traceback import format_exception

from ..utils.utils import Pag, clean_code, load_commands_from_json

cmd = load_commands_from_json("eval")


class Eval(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("eval")

    @command(name=cmd["eval"]["name"], aliases=cmd["eval"]["aliases"],
            brief=cmd["eval"]["brief"],
            description=cmd["eval"]["description"],
            usage=cmd["eval"]["usage"],
            help=cmd["eval"]["help"],
            hidden=cmd["eval"]["hidden"], enabled=True)
    @is_owner()
    async def eval_command(self, ctx, *, code: str):
        code = clean_code(code)

        local_variables = {
            "discord": discord,
            "commands": commands,
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message
        }

        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                exec(
                    f"async def func():\n{textwrap.indent(code, '    ')}", local_variables,
                )

                obj = await local_variables["func"]()
                result = f"{stdout.getvalue()}\n-- {obj}\n"
        except Exception as e:
            result = "".join(format_exception(e, e, e.__traceback__))

        pager = Pag(
            timeout=100,
            entries=[result[i: i + 2000] for i in range(0, len(result), 2000)],
            length=1,
            prefix="```py\n",
            suffix="```"
        )

        await pager.start(ctx)


def setup(bot):
    bot.add_cog(Eval(bot))
