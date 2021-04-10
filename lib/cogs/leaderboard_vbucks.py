from operator import itemgetter

from discord import Embed
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import ListPageSource, MenuPages
from loguru import logger

from ..db import db
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json('leaderboard_vbucks')


class VbucksLeaderboardMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title='🏆 Список лидеров', color=0x55acee)
        embed.set_thumbnail(url=self.ctx.author.avatar_url)
        embed.set_footer(text=f'Позиции {offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}.')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ('\n'.join(f'🔵 **{idx+offset}.** {self.ctx.guild.get_member(entry[0]).display_name} | В-баксов: **{entry[1]}**'
                for idx, entry in enumerate(entries)))

        fields.append(("Рейтинг по количеству потраченных с тегом в-баксов:", table))

        return await self.write_page(menu, offset, fields)


class VbucksLeaderboard(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(name=cmd["vbucksboard"]["name"], aliases=cmd["vbucksboard"]["aliases"],
            brief=cmd["vbucksboard"]["brief"],
            description=cmd["vbucksboard"]["description"],
            usage=cmd["vbucksboard"]["usage"],
            help=cmd["vbucksboard"]["help"],
            hidden=cmd["vbucksboard"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def vbucks_leaderboard_command(self, ctx):
        data = db.records("SELECT user_id, purchases FROM users_stats")
        records = [
            (user_id, sum(purchases['vbucks_purchases'][i]['price']
            for i in range(len(purchases['vbucks_purchases']))))
            for user_id, purchases in data
        ]
        records = sorted(records, key=itemgetter(1), reverse=True)
        menu = MenuPages(source=VbucksLeaderboardMenu(ctx, records), clear_reactions_after=True)
        await menu.start(ctx)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("leaderboard_vbucks")


def setup(bot):
    bot.add_cog(VbucksLeaderboard(bot))
