import ast
import asyncio
import json
from datetime import datetime
from operator import itemgetter
from random import choice
from typing import Optional

from discord import Color, Embed, Forbidden, Member
from discord.ext.commands import (Cog, check_any, command, dm_only, guild_only,
                                  has_permissions, is_owner)
from discord.ext.menus import ListPageSource, MenuPages
from loguru import logger

from ..utils.checks import is_channel, required_level
from ..utils.constants import STATS_CHANNEL
from ..utils.lazy_paginator import paginate
from ..utils.utils import edit_user_reputation, load_commands_from_json

cmd = load_commands_from_json('achievement_system')


class AchievementMenu(ListPageSource):
    def __init__(self, ctx, data, overview_type):
        self.ctx = ctx
        self.overview_type = overview_type
        self.thumbnails = (
            'https://school25.edu.yar.ru/dlya_stranits/trophy_icon_by_papillonstudio_d9dtwte_w394_h394.png',
            'https://icon-library.com/images/achievements-icon/achievements-icon-8.jpg',
            'https://cdn.iconscout.com/icon/free/png-512/achievement-1589036-1347675.png',
            'https://cdn4.iconfinder.com/data/icons/gamification-1/256/--02-512.png',
            'https://img.icons8.com/cotton/2x/sport-badge.png'
            )

        super().__init__(data, per_page=5)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(color=self.ctx.author.color).set_thumbnail(url=choice(self.thumbnails))
        embed.set_footer(text=f'{offset} — {min(len_data, offset+self.per_page-1)} из {len_data} достижений'
                              f' | {self.ctx.prefix}getinfo <achievement> для подробностей о достижении')
        if self.overview_type == 'global':
            embed.title = '🎖️ Список достижений'
        elif self.overview_type == 'user':
            embed.title = f'🎖️ Достижения {self.ctx.author.display_name}'

        for name, value, in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1
        fields = []

        if self.overview_type == 'global':
            table = ('\n'.join(f'\n> **{entry[2]}**\n> {entry[3]}'
                    for idx, entry in enumerate(entries)))
            fields.append(('Достижения, которые можно получить:', table))
        elif self.overview_type == 'user':
            table = ('\n'.join(f'\n> **{entry[2]}**\n> **Дата получения:** {entry[-1][:-3]} МСК'
                    for idx, entry in enumerate(entries)))
            fields.append(('Открытые достижения:', table))

        return await self.write_page(menu, offset, fields)


class AchievementSystem(Cog, name='Система достижений'):
    def __init__(self, bot):
        self.bot = bot
        self.achievements_banlist = []

    def chuncks(self, l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    async def can_view_hidden_achievement(self, user_id: int, achievement: str) -> bool:
        if user_id == self.bot.owner.id:
            return True
        return (await self.user_have_achievement(user_id, achievement))

    async def user_have_achievement(self, user_id: int, achievement: str) -> bool:
        data = await self.bot.pg_pool.fetchval(
            'SELECT achievements_list FROM users_stats WHERE user_id = $1',
            user_id)
        data = ast.literal_eval(data)
        data = data['user_achievements_list']
        user_achievements = [key for dic in data for key in dic.keys()]
        return achievement in user_achievements

    async def edit_rep_for_achievement(self, target_id: int, achievement: str, action: str):
        rep_boost = await self.bot.pg_pool.fetchval(
                   'SELECT rep_boost FROM achievements WHERE internal_id '
                   'LIKE $1', achievement)
        await edit_user_reputation(self.bot.pg_pool, target_id, action, rep_boost)

    @logger.catch
    async def give_achievement(self, admin_id: int, target_id: int, achievement: str):
        if not (await self.user_have_achievement(target_id, achievement)):
            rec = await self.bot.pg_pool.fetchval(
                "SELECT id FROM achievements WHERE "
                "to_tsvector(internal_id) @@ to_tsquery($1)",
                achievement)
            if rec is None:
                return
            data = await self.bot.pg_pool.fetchval(
                'SELECT achievements_list FROM users_stats WHERE user_id = $1',
                target_id)
            data = ast.literal_eval(data)
            transaction = {
                achievement: {
                    'id': len(data['user_achievements_list'])+1,
                    'achieved_at': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'given_by': admin_id
                    }
                }
            data['user_achievements_list'].append(transaction)
            await self.bot.pg_pool.execute(
                'UPDATE users_stats SET achievements_list = $1 WHERE user_id = $2',
                json.dumps(data, ensure_ascii=False), target_id)
            await self.edit_rep_for_achievement(target_id, achievement, '+')

    @logger.catch
    async def take_achievement_away(self, target_id: int, achievement: str):
        if (await self.user_have_achievement(target_id, achievement)):
            data = await self.bot.pg_pool.fetchval(
                'SELECT achievements_list FROM users_stats WHERE user_id = $1',
                target_id)
            data = ast.literal_eval(data)
            temp = data['user_achievements_list']
            new_list = [a for a in temp if achievement not in list(a.keys())]
            data['user_achievements_list'] = new_list
            await self.bot.pg_pool.execute(
                'UPDATE users_stats SET achievements_list = $1 WHERE user_id = $2',
                json.dumps(data, ensure_ascii=False), target_id)
            await self.edit_rep_for_achievement(target_id, achievement, '-')

    @logger.catch
    def advanced_achievements_memu(self, ctx, data):
        achievements = []

        for ach_chunks in list(self.chuncks(data, 1)):
            ach_chunks = ach_chunks[0]
            embed = Embed(
                title=f'🎖️ Достижение: {ach_chunks[2]}',
                color=ctx.author.color,
                description=ach_chunks[3]
            ).set_thumbnail(url=ach_chunks[4])
            fields = [
                ('Буст репутации', ach_chunks[6], True),
                ('Выдаётся автоматически', 'Да' if ach_chunks[7] else 'Нет', True),
                ('Первое появление', ach_chunks[5], True)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
            achievements.append(embed)

        for idx, embed in enumerate(achievements, 1):
            embed.set_footer(text=f'Достижение {idx} из {len(achievements)}')

        return achievements

    @logger.catch
    def advanced_user_achievements_memu(self, ctx, data):
        achievements = []

        for ach_chunks in list(self.chuncks(data, 1)):
            ach_chunks = ach_chunks[0]
            embed = Embed(
                title=f'🏅 {ach_chunks[2]}',
                color=ctx.author.color,
                description=ach_chunks[3]
            ).set_thumbnail(url=ach_chunks[4]
            ).set_author(name=f'Достижения {ctx.author.display_name}', icon_url=ctx.author.avatar_url)
            fields = [
                ('Дата получения:', ach_chunks[-1][:-3] + ' МСК', True)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
            achievements.append(embed)

        for idx, embed in enumerate(achievements, 1):
            embed.set_footer(text=f'Достижение {idx} из {len(achievements)}')

        return achievements

    @logger.catch
    def achievement_helper(self, ctx, data):
        embed = Embed(
           title=f'🎖️ Достижение: {data[2]}',
           color=ctx.author.color,
           description=data[3]
        ).set_thumbnail(url=data[4])
        fields = [
                ('Буст репутации', data[6], True),
                ('Выдаётся автоматически', "Да" if data[7] else "Нет", True),
                ('Первое появление', data[5], True)
            ]
        if ctx.author.id == self.bot.owner.id:
            fields.extend([
                ('id', data[0], True),
                ('internal_id', data[1], True),
                ('hidden', data[8], True),
            ])
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        return [embed]

    @logger.catch
    async def display_method(self, ctx) -> str:
        reactions = ['1️⃣', '2️⃣']
        embed = Embed(
            title='💠 Выбор метода отображения',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description='**Пожалуйста, выберите метод отображения списка достижений:\n\n'
                        '1️⃣ — подробное описание каждого достижения. 1 страница = 1 достижение.\n'
                        '2️⃣ — краткая сводка по каждому достижению. 1 страница = 5 достижений.**'
        )
        message = await ctx.reply(embed=embed, mention_author=False)
        for r in reactions:
            await message.add_reaction(r)
        try:
            method, user = await self.bot.wait_for(
                'reaction_add', timeout=120.0,
                check=lambda method, user: user == ctx.author
                and method.message.channel == ctx.channel
                and method.emoji in reactions)
        except asyncio.TimeoutError:
            await message.clear_reactions()
            return
        await message.delete()

        if str(method.emoji) == '1️⃣':
            method = 'detailed'
        elif str(method.emoji) == '2️⃣':
            method = 'briefly'
        else:
            method = None
        return method

    @logger.catch
    async def achievement_award_notification(self, achievement: str, target: Member):
        data = await self.bot.pg_pool.fetchrow(
            'SELECT * FROM achievements WHERE '
            'to_tsvector(internal_id) @@ to_tsquery($1)',
            achievement)
        embed = Embed(
            title='Открыто новое достижение!',
            color=Color.random(),
            timestamp=datetime.utcnow(),
            description=f'Поздравляем! Вы заработали достижение **{data[2]}** '
                        f'на сервере **{target.guild}**\n\nПосмотреть список '
                        f'своих достижений можно по команде `{self.bot.PREFIX[0]}inventory`.'
        ).set_thumbnail(url=data[4])
        try:
            await target.send(embed=embed)
        except Forbidden:
            pass

    @command(name=cmd["achieve"]["name"], aliases=cmd["achieve"]["aliases"],
            brief=cmd["achieve"]["brief"],
            description=cmd["achieve"]["description"],
            usage=cmd["achieve"]["usage"],
            help=cmd["achieve"]["help"],
            hidden=cmd["achieve"]["hidden"], enabled=True)
    @check_any(dm_only(), is_channel(STATS_CHANNEL))
    @required_level(cmd["achieve"]["required_level"])
    @logger.catch
    async def how_achievement_sys_works_command(self, ctx):
        embed = Embed(
            title='🏆 Достижения: что это, для чего нужны, как зарабатывать.',
            color=ctx.author.color,
            timestamp=datetime.utcnow()
        ).set_thumbnail(url='https://i.pinimg.com/originals/88/40/b8/8840b8d2c07bf805cdab22c0e4b54f59.gif')
        embed.set_footer(text=ctx.author, icon_url=ctx.author.avatar_url)
        embed.description = \
        'На сервере работает система достижений.\nДостижения ' \
        '— один из основных способов заработка репутации. У каждой ачивки ' \
        'есть определённые условия получения и бонусные очки репутации, ' \
        'которые даются за открытие этой самой ачивки. Б**о**льшая часть ' \
        'достижений выдаётся автоматически, но некоторые ачивки могут выдать ' \
        'только администраторы севрера. Со списком всех достижений можно ' \
        'ознакомиться в канале <#604621910386671616> по команде ' \
        f'`{ctx.prefix or self.bot.PREFIX[0]}achievements`\nСписок достижений пополняется. ' \
        'Если у вас есть предложения по добавлению новой ачивки, напишите об ' \
        'этом в канале <#639925210849476608>\nВ случае возникновения ' \
        'каких-либо вопросов вы можете обратиться к <@375722626636578816>'
        await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["achievements"]["name"], aliases=cmd["achievements"]["aliases"],
            brief=cmd["achievements"]["brief"],
            description=cmd["achievements"]["description"],
            usage=cmd["achievements"]["usage"],
            help=cmd["achievements"]["help"],
            hidden=cmd["achievements"]["hidden"], enabled=True)
    @check_any(dm_only(), is_channel(STATS_CHANNEL))
    @required_level(cmd["achievements"]["required_level"])
    @logger.catch
    async def achievements_list_command(self, ctx):
        data = await self.bot.pg_pool.fetch(
            'SELECT * FROM achievements ORDER BY id')
        if ctx.author.id != self.bot.owner.id:
            data = [i for i in data if i[8] is False]
        if not data:
            await ctx.reply(
                '😳 Этого не должно было произойти, но база данных достижений пуста.'
                f'\nПожалуйста, сообщите об этом **{self.bot.owner}**',
                mention_author=False
            )
            return

        method = await self.display_method(ctx)
        if method == 'detailed':
            embed = self.advanced_achievements_memu(ctx, data)
            await paginate(ctx, embed)
        elif method == 'briefly':
            menu = MenuPages(
                source=AchievementMenu(ctx, data, 'global'),
                clear_reactions_after=True,
                timeout=120.0)
            await menu.start(ctx)
        else:
            return


    @command(name=cmd["getinfo"]["name"], aliases=cmd["getinfo"]["aliases"],
            brief=cmd["getinfo"]["brief"],
            description=cmd["getinfo"]["description"],
            usage=cmd["getinfo"]["usage"],
            help=cmd["getinfo"]["help"],
            hidden=cmd["getinfo"]["hidden"], enabled=True)
    @check_any(dm_only(), is_channel(STATS_CHANNEL))
    @required_level(cmd["getinfo"]["required_level"])
    @logger.catch
    async def get_achievement_command(self, ctx, *, achievement: Optional[str]):
        if achievement:
            internal_id = await self.bot.pg_pool.fetchval(
                'SELECT internal_id FROM achievements WHERE '
                'to_tsvector(name) @@ plainto_tsquery($1)',
                achievement)

            if internal_id is not None:
                data = await self.bot.pg_pool.fetchrow(
                   'SELECT * FROM achievements WHERE internal_id '
                   'LIKE $1', internal_id)
                if data[8] is False:
                    await paginate(ctx, self.achievement_helper(ctx, data))
                else:
                    if (await self.can_view_hidden_achievement(ctx.author.id, internal_id)):
                        await paginate(ctx, self.achievement_helper(ctx, data))
                    else:
                        await ctx.reply('🕵️ Достижение скрыто.', mention_author=False)
            else:
                await ctx.reply('4️⃣0️⃣4️⃣ Достижение не найдено.', mention_author=False)
        else:
            await ctx.reply('📒 Укажите название достижения.', mention_author=False)


    @command(name=cmd["inventory"]["name"], aliases=cmd["inventory"]["aliases"],
            brief=cmd["inventory"]["brief"],
            description=cmd["inventory"]["description"],
            usage=cmd["inventory"]["usage"],
            help=cmd["inventory"]["help"],
            hidden=cmd["inventory"]["hidden"], enabled=True)
    @check_any(dm_only(), is_channel(STATS_CHANNEL))
    @required_level(cmd["inventory"]["required_level"])
    @logger.catch
    async def inventory_command(self, ctx):
        rec = await self.bot.pg_pool.fetchval(
            'SELECT achievements_list FROM users_stats WHERE user_id = $1',
            ctx.author.id)
        rec = ast.literal_eval(rec)
        user_data = rec['user_achievements_list']
        if user_data:
            user_achievements = tuple(
                [key for dic in user_data for key in dic.keys()]
            )
            achievements_data = await self.bot.pg_pool.fetch(
                'SELECT * FROM achievements WHERE internal_id = any($1::text[]) ORDER BY id',
                user_achievements)
            achievements_data = [list(l) for l in achievements_data]

            for dic in user_data:
                achievement_id = list(dic.keys())[0]
                for entry in achievements_data:
                    if achievement_id in entry:
                        entry.append(dic[achievement_id]['achieved_at'])
            data = sorted(achievements_data, key=itemgetter(-1), reverse=True)

            method = await self.display_method(ctx)
            if method == 'detailed':
                embed = self.advanced_user_achievements_memu(ctx, data)
                await paginate(ctx, embed)
            elif method == 'briefly':
                menu = MenuPages(
                    source=AchievementMenu(ctx, data, 'user'),
                    clear_reactions_after=True,
                    timeout=120.0)
                await menu.start(ctx)
            else:
                return
        else:
            await ctx.reply(
                'У вас нет ни одного достижения. Со списком всех достижений можно '
                'ознакомиться в канале <#604621910386671616> по команде '
                f'`{ctx.prefix or self.bot.PREFIX[0]}achievements`',
                mention_author=False
            )


    @command(name=cmd["addachievement"]["name"], aliases=cmd["addachievement"]["aliases"],
            brief=cmd["addachievement"]["brief"],
            description=cmd["addachievement"]["description"],
            usage=cmd["addachievement"]["usage"],
            help=cmd["addachievement"]["help"],
            hidden=cmd["addachievement"]["hidden"], enabled=True)
    @has_permissions(administrator=True)
    @guild_only()
    @logger.catch
    async def add_achievement_to_user_command(self, ctx, member: Optional[Member], *, achievement: Optional[str]):
        if member is None:
            await ctx.reply(
                '📝 Укажите пользователя, которому необходимо выдать достижение.',
                mention_author=False
            )
            return
        if achievement:
            data = await self.bot.pg_pool.fetchrow(
                'SELECT name, internal_id FROM achievements WHERE '
                'to_tsvector(internal_id) @@ to_tsquery($1)',
                achievement)
            if data is not None:
                if not (await self.user_have_achievement(member.id, achievement)):
                    await self.give_achievement(ctx.author.id, member.id, achievement)
                    await self.achievement_award_notification(achievement, member)
                    await ctx.reply(
                        f'✅ Достижение **{data[0]}** успешно выдано пользователю **{member.display_name}**.',
                        mention_author=False
                    )
                else:
                    await ctx.reply(
                        '⛔ У пользователя уже есть указанное достижение. Повторная выдача невозможна.',
                        mention_author=False
                    )
            else:
                await ctx.reply(
                    '4️⃣0️⃣4️⃣ Указанное достижение не найдено, выдача невозможна.',
                    mention_author=False
                )
        else:
            await ctx.reply(
                '📒 Укажите название достижения.', mention_author=False
            )


    @command(name=cmd["removeachievement"]["name"], aliases=cmd["removeachievement"]["aliases"],
            brief=cmd["removeachievement"]["brief"],
            description=cmd["removeachievement"]["description"],
            usage=cmd["removeachievement"]["usage"],
            help=cmd["removeachievement"]["help"],
            hidden=cmd["removeachievement"]["hidden"], enabled=True)
    @has_permissions(administrator=True)
    @guild_only()
    @logger.catch
    async def remove_achievement_from_user_command(self, ctx, member: Optional[Member], *, achievement: Optional[str]):
        if member is None:
            await ctx.reply(
                '📝 Укажите пользователя, у которого необходимо забрать достижение.',
                mention_author=False
            )
            return
        if achievement:
            data = await self.bot.pg_pool.fetchrow(
                'SELECT name, internal_id FROM achievements WHERE '
                'to_tsvector(internal_id) @@ to_tsquery($1)',
                achievement
            )
            if data is not None:
                if (await self.user_have_achievement(member.id, achievement)):
                    await self.take_achievement_away(member.id, achievement)
                    await ctx.reply(
                        f'✅ Достижение **{data[0]}** успешно отобрано у пользователя **{member.display_name}**.',
                        mention_author=False
                    )
                else:
                    await ctx.reply(
                        '⛔ У пользователя нет указанного достижения, забрать его невозможно.',
                        mention_author=False
                    )
            else:
                await ctx.reply(
                    '4️⃣0️⃣4️⃣ Указанное достижение не найдено, забрать его невозможно.',
                    mention_author=False
                )
        else:
            await ctx.reply(
                '📒 Укажите название достижения.', mention_author=False
            )


    @command(name=cmd["resetachievements"]["name"], aliases=cmd["resetachievements"]["aliases"],
            brief=cmd["resetachievements"]["brief"],
            description=cmd["resetachievements"]["description"],
            usage=cmd["resetachievements"]["usage"],
            help=cmd["resetachievements"]["help"],
            hidden=cmd["resetachievements"]["hidden"], enabled=True)
    @is_owner()
    @dm_only()
    @logger.catch
    async def reset_achievements_command(self, ctx, user_id: Optional[int]):
        if user_id is None:
            return await ctx.message.add_reaction('🟥')

        data = {'user_achievements_list': []}
        await self.bot.pg_pool.execute(
            'UPDATE users_stats SET achievements_list = $1 WHERE user_id = $2',
            json.dumps(data, ensure_ascii=False), user_id)
        self.achievements_banlist.append(user_id)
        embed = Embed(
                title='✅ Успешно!',
                color=Color.green(),
                timestamp=datetime.utcnow(),
                description=f'Достижения пользователя <@{user_id}> сброшены.'
            )
        await ctx.reply(embed=embed, mention_author=False)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("achievement_system")


def setup(bot):
    bot.add_cog(AchievementSystem(bot))
