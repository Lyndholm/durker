from discord import Embed
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import ListPageSource, MenuPages
from loguru import logger

from ..db import db
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json('leaderboard_messages')


class MessagesLeaderboardMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title='🏆 Список лидеров', color=0xfdcb58)
        embed.set_thumbnail(url=self.ctx.author.avatar_url)
        embed.set_footer(text=f'Позиции {offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}.')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ('\n'.join(f'🟡 **{idx+offset}.** {self.ctx.guild.get_member(entry[0]).display_name} | Сообщений: **{entry[1]}**'
                for idx, entry in enumerate(entries)))

        fields.append(("Рейтинг по количеству сообщений:", table))

        return await self.write_page(menu, offset, fields)


class MessagesLeaderboard(Cog, name='Список лидеров — сообщения'):
    def __init__(self, bot):
        self.bot = bot

    @command(name=cmd["messageboard"]["name"], aliases=cmd["messageboard"]["aliases"],
            brief=cmd["messageboard"]["brief"],
            description=cmd["messageboard"]["description"],
            usage=cmd["messageboard"]["usage"],
            help=cmd["messageboard"]["help"],
            hidden=cmd["messageboard"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def messages_leaderboard_command(self, ctx):
        records = db.records("SELECT user_id, messages_count FROM users_stats ORDER BY messages_count DESC")
        menu = MenuPages(source=MessagesLeaderboardMenu(ctx, records), clear_reactions_after=True)
        await menu.start(ctx)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("leaderboard_messages")


def setup(bot):
    bot.add_cog(MessagesLeaderboard(bot))
