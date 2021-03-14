from random import sample, shuffle
from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command, guild_only, is_owner
from datetime import datetime, timedelta

from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("contests")


class Contests(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways = []

    @command(name=cmd["giveaway"]["name"], aliases=cmd["giveaway"]["aliases"],
            brief=cmd["giveaway"]["brief"],
            description=cmd["giveaway"]["description"],
            usage=cmd["giveaway"]["usage"],
            help=cmd["giveaway"]["help"],
            hidden=cmd["giveaway"]["hidden"], enabled=True)
    @guild_only()
    @is_owner()
    async def create_giveaway(self, ctx, mins: int = None, winners: int = 1, *, description: str = "Розыгрыш."):
        await ctx.message.delete()
        if winners <= 0:
            return

        embed = Embed(
            title="🎁 Розыгрыш",
            description=description + "\n\n**Нажмите на реакцию ✅ под сообщением, чтобы принять участие!**",
            color=ctx.author.color,
            timestamp=datetime.utcnow()
        ).add_field(
            name=f"Дата начала",
            value=f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')} МСК"
        ).add_field(
            name="Дата окончания",
            value=f"{(datetime.now() + timedelta(minutes=mins)).strftime('%d.%m.%Y %H:%M:%S')} МСК"
        ).add_field(
            name="Куратор",
            value=ctx.author.mention
        )

        message = await ctx.send(embed=embed)

        self.giveaways.append((message.channel.id, message.id))
        self.bot.scheduler.add_job(self.complete_giveaway, "date", run_date=datetime.now()+timedelta(minutes=mins),
                                args=[message.channel.id, message.id, embed, winners])
        await message.add_reaction('✅')

    async def complete_giveaway(self, channel_id, message_id, embed, winners_count):
        message = await self.bot.get_channel(channel_id).fetch_message(message_id)

        if len(entrants := [user for user in await message.reactions[0].users().flatten() if not user.bot]) >= winners_count:
            shuffle(entrants)
            winners = sample(entrants, winners_count)
            if winners_count <= 1:
                await message.reply(f'🎁 Розыгрыш завершён.\n🎉 **Победитель:** {" ".join([w.mention for w in winners])}')
            else:
                reply_string = ''
                for c, w in enumerate(winners):
                    reply_string += f'\n**{c+1}.** {w.mention}'
                await message.reply(f'🎁 Розыгрыш завершён.\n🎉 Победители:{reply_string}')
            self.giveaways.remove((message.channel.id, message.id))
        else:
            await message.reply('Недостаточно участников для подведения итогов. Розыгрыш завершён.')
            self.giveaways.remove((message.channel.id, message.id))

        await message.edit(embed=embed.set_footer(text="Розыгрыш завершён."))

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("contests")


def setup(bot):
    bot.add_cog(Contests(bot))
