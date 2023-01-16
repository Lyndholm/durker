import ast
from datetime import datetime

from discord.ext import tasks
from discord.ext.commands import Cog

from ..utils.constants import (KAPITALIST_ROLE_ID,
                               MAGNAT_ROLE_ID, MECENAT_ROLE_ID)
from ..utils.utils import edit_user_reputation


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


async def setup(bot):
    await bot.add_cog(PurchasesHandler(bot))
