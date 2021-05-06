from operator import itemgetter

from discord import Embed
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import ListPageSource, MenuPages
from loguru import logger

from ..db import db
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json('leaderboards')


class AchievementsLeaderboardMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title='🏆 Список лидеров', color=0xe6e7e8)
        embed.set_thumbnail(url=self.ctx.author.avatar_url)
        embed.set_footer(text=f'Позиции {offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}.')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ('\n'.join(f'⚪ **{idx+offset}.** {self.ctx.guild.get_member(entry[0]).display_name} | Достижений: **{entry[1]}**'
                for idx, entry in enumerate(entries)))

        fields.append(("Рейтинг по количеству достижений:", table))

        return await self.write_page(menu, offset, fields)


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


class ReputationLeaderboardMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=10)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title='🏆 Список лидеров', color=0x78b159)
        embed.set_thumbnail(url=self.ctx.author.avatar_url)
        embed.set_footer(text=f'Позиции {offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}.')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ('\n'.join(f'🟢 **{idx+offset}.** {self.ctx.guild.get_member(entry[0]).display_name} | Очков репутации: **{entry[1]}**'
                for idx, entry in enumerate(entries)))

        fields.append(("Рейтинг по количеству репутации:", table))

        return await self.write_page(menu, offset, fields)


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
        table = ('\n'.join(f'🔵 **{idx+offset}.** {self.ctx.guild.get_member(entry[0]).display_name} | В-Баксов: **{entry[1]}**'
                for idx, entry in enumerate(entries)))

        fields.append(("Рейтинг по количеству потраченных с тегом В-Баксов:", table))

        return await self.write_page(menu, offset, fields)


class Leaderboards(Cog, name='Списки лидеров'):
    def __init__(self, bot):
        self.bot = bot

    @command(name=cmd["achievementboard"]["name"], aliases=cmd["achievementboard"]["aliases"],
            brief=cmd["achievementboard"]["brief"],
            description=cmd["achievementboard"]["description"],
            usage=cmd["achievementboard"]["usage"],
            help=cmd["achievementboard"]["help"],
            hidden=cmd["achievementboard"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def achievements_leaderboard_command(self, ctx):
        data = db.records("SELECT user_id, achievements_list FROM users_stats ORDER BY json_array_length(achievements_list->'user_achievements_list')")
        records = [(user_id, len(achievements['user_achievements_list'])) for user_id, achievements in data]
        records = sorted(records, key=itemgetter(1), reverse=True)
        menu = MenuPages(source=AchievementsLeaderboardMenu(ctx, records), clear_reactions_after=True)
        await menu.start(ctx)


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


    @command(name=cmd["reputationboard"]["name"], aliases=cmd["reputationboard"]["aliases"],
            brief=cmd["reputationboard"]["brief"],
            description=cmd["reputationboard"]["description"],
            usage=cmd["reputationboard"]["usage"],
            help=cmd["reputationboard"]["help"],
            hidden=cmd["reputationboard"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def reputation_leaderboard_command(self, ctx):
        records = db.records("SELECT user_id, rep_rank FROM users_stats ORDER BY rep_rank DESC")
        menu = MenuPages(source=ReputationLeaderboardMenu(ctx, records), clear_reactions_after=True)
        await menu.start(ctx)


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
           self.bot.cogs_ready.ready_up("leaderboards")


def setup(bot):
    bot.add_cog(Leaderboards(bot))
