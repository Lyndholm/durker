from discord import Embed, MessageType
from discord.ext.commands import Cog

from ..utils.constants import HIDEOUT_MODMAIL_CHANNEL
from ..utils.decorators import listen_for_dms


class ModMail(Cog, name='ModMail'):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    async def init_vars(self):
        self.modmail_channel = self.bot.get_channel(HIDEOUT_MODMAIL_CHANNEL)

    @Cog.listener()
    @listen_for_dms()
    async def on_message(self, message):
        if message.author.id in self.bot.banlist:
            return

        if message.type != MessageType.default:
            return

        ctx = await self.bot.get_context(message)
        if not message.author.bot and not ctx.command:
            member = self.bot.guild.get_member(message.author.id)
            embed = Embed(
                title="ModMail",
                color=member.color,
                timestamp=message.created_at,
                description=message.content
            ).set_thumbnail(url=member.avatar_url
            ).set_author(name=member, icon_url=member.avatar_url)

            fields = [("Message ID:", message.id, True),
                    ("DM Channel ID:", message.channel.id, True),
                    ("User ID:", member.id, True)]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            if message.attachments:
                embed.add_field(
                    name="Attachments:",
                    value="\n".join([attachment.url for attachment in message.attachments]),
                    inline=False
                )
            await self.modmail_channel.send(embed=embed)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.modmail_channel = self.bot.get_channel(HIDEOUT_MODMAIL_CHANNEL)
           self.bot.cogs_ready.ready_up("modmail")

async def setup(bot):
    await bot.add_cog(ModMail(bot))
