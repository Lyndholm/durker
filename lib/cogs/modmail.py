from datetime import datetime

from discord import Color, DMChannel, Embed
from discord.ext.commands import Cog, command


class ModMail(Cog, name='ModMail'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        if isinstance(message.channel, DMChannel) and not message.author.bot and not ctx.command:
            member = self.bot.guild.get_member(message.author.id)
            embed = Embed(
                title="ModMail",
                color=member.color,
                timestamp=datetime.utcnow(),
                description=message.clean_content[:2040]
            )
            embed.set_thumbnail(url=member.avatar_url)

            fields = [("User:", member.mention, True),
                        ("User ID:", member.id, True),
                        ("DM Channel ID:", message.channel.id, True)
                    ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            if message.attachments:
                embed.add_field(
                    name="Attachments:",
                    value="\n".join([attachment.url for attachment in message.attachments]),
                    inline=False
                )
            await self.bot.get_user(self.bot.owner_ids[0]).send(embed=embed)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("modmail")

def setup(bot):
    bot.add_cog(ModMail(bot))
