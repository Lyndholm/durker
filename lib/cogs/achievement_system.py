from datetime import datetime
from random import choice
from typing import Optional

from discord import Color, Embed
from discord.ext.commands import Cog, command, guild_only
from discord.ext.menus import ListPageSource, MenuPages
from loguru import logger

from ..db import db
from ..utils.lazy_paginator import paginate
from ..utils.utils import load_commands_from_json

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

        embed = Embed(color=self.ctx.author.color).set_thumbnail(url=(self.thumbnails))
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
        table = ('\n'.join(f'\n> **{entry[2]}**\n> **Описание:** {entry[3]}'
                for idx, entry in enumerate(entries)))

        if self.overview_type == 'global':
            fields.append(('Достижения:', table))
        elif self.overview_type == 'user':
            fields.append(('Открытые достижения:', table))

        return await self.write_page(menu, offset, fields)


class AchievementSystem(Cog, name='Система достижений'):
    def __init__(self, bot):
        self.bot = bot

    def chuncks(self, l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def can_view_hidden_achievement(self, ctx, internal_id: str):
        if ctx.author.id == self.bot.owner_ids[0]:
            return True

        rec = db.fetchone(['achievements_list'], 'users_stats', 'user_id', ctx.author.id)
        data = rec[0]['user_achievements_list']
        user_achievements = [key for dic in data for key in dic.keys()]
        return internal_id in user_achievements

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
            embed.set_footer(text=f'Достижение №{idx} из {len(achievements)}')

        return achievements

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
        if ctx.author.id == self.bot.owner_ids[0]:
            fields.extend([
                ('id', data[0], True),
                ('internal_id', data[1], True),
                ('hidden', data[8], True),
            ])
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        return [embed]


    @command(name=cmd["achieve"]["name"], aliases=cmd["achieve"]["aliases"],
            brief=cmd["achieve"]["brief"],
            description=cmd["achieve"]["description"],
            usage=cmd["achieve"]["usage"],
            help=cmd["achieve"]["help"],
            hidden=cmd["achieve"]["hidden"], enabled=True)
    @guild_only()
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
        f'`{ctx.prefix}achievements`\nСписок достижений пополняется. ' \
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
    @guild_only()
    @logger.catch
    async def achievements_list_command(self, ctx):
        data = db.records('SELECT * FROM achievements')
        if ctx.author.id != self.bot.owner_ids[0]:
            data = [i for i in data if i[8] is False]

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
        except TimeoutError:
            await message.clear_reactions()
            return
        await message.delete()
        method = "detailed" if str(method.emoji) == '1️⃣' else "briefly"

        if method == 'detailed':
            embed = self.advanced_achievements_memu(ctx, data)
            await paginate(ctx, embed)
        else:
            menu = MenuPages(
                source=AchievementMenu(ctx, data, 'global'),
                clear_reactions_after=True,
                timeout=120.0)
            await menu.start(ctx)


    @command(name=cmd["getinfo"]["name"], aliases=cmd["getinfo"]["aliases"],
            brief=cmd["getinfo"]["brief"],
            description=cmd["getinfo"]["description"],
            usage=cmd["getinfo"]["usage"],
            help=cmd["getinfo"]["help"],
            hidden=cmd["getinfo"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def get_achievement_command(self, ctx, *, achievement: Optional[str]):
        if achievement:
            internal_id = db.field(
                "SELECT internal_id FROM achievements WHERE "
                "to_tsvector(name) @@ to_tsquery(''%s'')",
                achievement)

            if internal_id is not None:
                data = db.records(
                   'SELECT * FROM achievements WHERE internal_id '
                   'LIKE %s', internal_id
                )[0]
                if data[8] is False:
                    await paginate(ctx, self.achievement_helper(ctx, data))
                else:
                    if self.can_view_hidden_achievement(ctx, internal_id):
                        await paginate(ctx, self.achievement_helper(ctx, data))
                    else:
                        await ctx.reply('🕵️ Достижение скрыто.', mention_author=False)
            else:

                await ctx.reply('4️⃣0️⃣4️⃣ Достижение не найдено.', mention_author=False)
        else:
            await ctx.reply('📒 Укажите название достижения.', mention_author=False)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("achievement_system")


def setup(bot):
    bot.add_cog(AchievementSystem(bot))
