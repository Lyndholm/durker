import ast
import json
import os
from asyncio import TimeoutError
from datetime import datetime
from typing import Optional

from discord import Color, Embed
from discord.ext import tasks
from discord.ext.commands import Cog, command, dm_only, guild_only, is_owner
from discord.ext.menus import ListPageSource, MenuPages

from ..db import db
from ..utils.checks import is_any_channel, is_channel
from ..utils.constants import (CONSOLE_CHANNEL, KAPITALIST_ROLE_ID,
                               MAGNAT_ROLE_ID, MECENAT_ROLE_ID,
                               SAC_SCREENSHOTS_CHANNEL, STATS_CHANNEL)
from ..utils.decorators import listen_for_guilds
from ..utils.paginator import Paginator
from ..utils.utils import edit_user_reputation, load_commands_from_json

cmd = load_commands_from_json('purchases_handler')


class VbucksPurchasesMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=5)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)
        embed = Embed(title='🛍️ Список покупок',color=Color.blue(), timestamp=datetime.utcnow())
        embed.set_footer(text=f'{offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}')
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/640675233342291969.png')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = '⠀' + ('\n'.join(f'\n> **{entry[0]}** \n> **Цена:** {entry[1]} В-баксов\n> **Дата:** {entry[2][:-3]}'
                for idx, entry in enumerate(entries)))

        fields.append(('Список внутриигровых покупок за В-баксы.', table))

        return await self.write_page(menu, offset, fields)

class RealMoneyPurchasesMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=5)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)
        embed = Embed(title='💸 Список покупок',color=Color.green(), timestamp=datetime.utcnow())
        embed.set_footer(text=f'{offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}')
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/718071523524739074.gif')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = '⠀' + ('\n'.join(f'\n> **{entry[0]}** \n> **Цена:** {entry[1]} руб.\n> **Дата:** {entry[2][:-3]}'
                for idx, entry in enumerate(entries)))

        fields.append(('Список покупок, совершённых за реальные деньги.', table))

        return await self.write_page(menu, offset, fields)


class PurchasesHandler(Cog, name='Покупки и не только'):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    async def init_vars(self):
        self.mod_cog = self.bot.get_cog('Модерация')
        self.mecenat = self.bot.guild.get_role(MECENAT_ROLE_ID)
        self.kapitalist = self.bot.guild.get_role(KAPITALIST_ROLE_ID)
        self.magnat = self.bot.guild.get_role(MAGNAT_ROLE_ID)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.mod_cog = self.bot.get_cog('Модерация')
            self.mecenat = self.bot.guild.get_role(MECENAT_ROLE_ID)
            self.kapitalist = self.bot.guild.get_role(KAPITALIST_ROLE_ID)
            self.magnat = self.bot.guild.get_role(MAGNAT_ROLE_ID)
            self.bot.cogs_ready.ready_up("purchases_handler")

    @tasks.loop(hours=24.0)
    async def check_mecenat_role(self):
        for member in self.bot.guild.members:
            if self.mod_cog.is_member_muted(member) or member.pending:
                continue

            try:
                data = await self.bot.db.fetchone(
                    ['purchases'], 'users_stats', 'user_id', member.id)
                purchases = ast.literal_eval(data[0])['vbucks_purchases']
            except TypeError:
                continue

            if purchases:
                lpd = purchases[-1]['date']
                if self.mecenat in member.roles and self.kapitalist not in member.roles:
                    if (datetime.now() - datetime.strptime(lpd, '%d.%m.%Y %H:%M:%S')).days > 90:
                        await member.remove_roles(self.mecenat, reason='С момента последней покупки прошло более 3 месяцев')

    @check_mecenat_role.before_loop
    async def before_check_mecenat_role(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1.5)
    async def check_support_role_task(self):
        for member in self.bot.guild.members:
            await self.check_support_roles(member)

    @check_support_role_task.before_loop
    async def before_check_supporter_role(self):
        await self.bot.wait_until_ready()

    async def check_support_roles(self, member):
        if self.mod_cog.is_member_muted(member) or member.pending:
            return

        data = await self.bot.db.fetchone(
            ['purchases'], 'users_stats', 'user_id', member.id)
        purchases = ast.literal_eval(data[0])['vbucks_purchases']
        vbucks_count = sum(purchases[i]['price'] for i in range(len(purchases)))

        if self.mecenat not in member.roles and vbucks_count > 0:
            lpd = purchases[-1]['date']
            if (datetime.now() - datetime.strptime(lpd, '%d.%m.%Y %H:%M:%S')).days < 90:
                await member.add_roles(self.mecenat)
                await edit_user_reputation(self.bot.pg_pool, member.id, '+', 100)
        if self.kapitalist not in member.roles and vbucks_count >= 10_000:
            await member.add_roles(self.kapitalist)
            await edit_user_reputation(self.bot.pg_pool, member.id, '+', 1000)
        if self.magnat not in member.roles and vbucks_count >= 25_000:
            await member.add_roles(self.magnat)
            await edit_user_reputation(self.bot.pg_pool, member.id, '+', 2500)

    @command(name=cmd["addvbucks"]["name"], aliases=cmd["addvbucks"]["aliases"],
            brief=cmd["addvbucks"]["brief"],
            description=cmd["addvbucks"]["description"],
            usage=cmd["addvbucks"]["usage"],
            help=cmd["addvbucks"]["help"],
            hidden=cmd["addvbucks"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def addvbucks_command(self, ctx, user_id: int, amount: int, *, item: Optional[str] = 'Не указано'):
        member = self.bot.guild.get_member(user_id)
        purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', user_id)[0]
        transaction = {
            'id': len(purchases['vbucks_purchases'])+1,
            'item': item,
            'price': amount,
            'date': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        purchases['vbucks_purchases'].append(transaction)
        db.execute("UPDATE users_stats SET purchases = %s WHERE user_id = %s",
                   json.dumps(purchases, ensure_ascii=False), user_id)
        db.commit()
        await self.check_support_roles(member)
        await ctx.reply(embed=Embed(
            title='В-баксы добавлены',
            color=member.color,
            timestamp=datetime.utcnow(),
            description= 'Количество потраченных с тегом В-баксов пользователя '
                        f'**{member.display_name}** ({member.mention}) было увеличено на **{amount}**.'
        ))


    @command(name=cmd["addrubles"]["name"], aliases=cmd["addrubles"]["aliases"],
            brief=cmd["addrubles"]["brief"],
            description=cmd["addrubles"]["description"],
            usage=cmd["addrubles"]["usage"],
            help=cmd["addrubles"]["help"],
            hidden=cmd["addrubles"]["hidden"], enabled=False)
    @dm_only()
    @is_owner()
    async def addrubles_command(self, ctx, user_id: int, amount: int, *, item: Optional[str] = 'Не указано'):
        member = self.bot.guild.get_member(user_id)
        purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', user_id)[0]
        transaction = {
            'id': len(purchases['realMoney_purchases'])+1,
            'item': item,
            'price': amount,
            'date': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        purchases['realMoney_purchases'].append(transaction)
        db.execute("UPDATE users_stats SET purchases = %s WHERE user_id = %s",
                   json.dumps(purchases, ensure_ascii=False), user_id)
        db.commit()
        await ctx.reply(embed=Embed(
            title='Рубли добавлены',
            color=member.color,
            timestamp=datetime.utcnow(),
            description= f'Количество рублей пользователя **{member.display_name}**'
                        f'({member.mention}) было увеличено на **{amount}**.'
        ))


    @command(name=cmd["resetpurchases"]["name"], aliases=cmd["resetpurchases"]["aliases"],
            brief=cmd["resetpurchases"]["brief"],
            description=cmd["resetpurchases"]["description"],
            usage=cmd["resetpurchases"]["usage"],
            help=cmd["resetpurchases"]["help"],
            hidden=cmd["resetpurchases"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def reset_user_purchases_command(self, ctx, user_id: int, *, reason: Optional[str] = 'Не указана'):
        data = db.fetchone(['purchases'], 'users_stats', 'user_id', user_id)[0]
        data['reason'] = reason
        time_now = datetime.now().strftime("%d.%m.%Y %H.%M.%S")
        with open(f"./data/purchases_backup/{user_id} [{time_now}].json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)

        purchases = {"vbucks_purchases":[],"realMoney_purchases":[]}
        db.execute("UPDATE users_stats SET purchases = %s WHERE user_id = %s",
                   json.dumps(purchases, ensure_ascii=False), user_id)
        db.commit()
        await ctx.message.add_reaction('✅')


async def setup(bot):
    await bot.add_cog(PurchasesHandler(bot))
