from discord import Embed
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import ListPageSource, MenuPages
from loguru import logger

from ..db import db
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json('leaderboard_leveling')


class LevelsLeaderboardMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title='🏆 Список лидеров', color=0xf4900c)
        embed.set_thumbnail(url=self.ctx.author.avatar_url)
        embed.set_footer(text=f'Позиции {offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}.')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ('\n'.join(f'🟠 **{idx+offset}.** {self.ctx.guild.get_member(entry[0]).display_name} | Уровень: **{entry[1]}** | XP: **{entry[2]}**'
                for idx, entry in enumerate(entries)))

        fields.append(('Рейтинг по уровню на сервере:', table))

        return await self.write_page(menu, offset, fields)


class LevelingLeaderboard(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(name=cmd["levelboard"]["name"], aliases=cmd["levelboard"]["aliases"],
            brief=cmd["levelboard"]["brief"],
            description=cmd["levelboard"]["description"],
            usage=cmd["levelboard"]["usage"],
            help=cmd["levelboard"]["help"],
            hidden=cmd["levelboard"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def leveling_leaderboard_command(self, ctx):
        records = db.records("SELECT user_id, level, xp FROM leveling ORDER BY xp_total DESC")
        menu = MenuPages(source=LevelsLeaderboardMenu(ctx, records), clear_reactions_after=True)
        await menu.start(ctx)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("leaderboard_leveling")


def setup(bot):
    bot.add_cog(LevelingLeaderboard(bot))
