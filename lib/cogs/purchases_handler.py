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
from loguru import logger

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
        self.check_mecenat_role.start()
        self.check_support_role_task.start()
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    @logger.catch
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
    @logger.catch
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
    @logger.catch
    async def check_support_role_task(self):
        for member in self.bot.guild.members:
            await self.check_support_roles(member)

    @check_support_role_task.before_loop
    async def before_check_supporter_role(self):
        await self.bot.wait_until_ready()

    @logger.catch
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
    @logger.catch
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
    @logger.catch
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
    @logger.catch
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


    @command(name=cmd["purchases"]["name"], aliases=cmd["purchases"]["aliases"],
            brief=cmd["purchases"]["brief"],
            description=cmd["purchases"]["description"],
            usage=cmd["purchases"]["usage"],
            help=cmd["purchases"]["help"],
            hidden=cmd["purchases"]["hidden"], enabled=True)
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @logger.catch
    async def fetch_purchases_command(self, ctx):
        data = db.fetchone(
            ['purchases'], 'users_stats', 'user_id', ctx.author.id)
        purchases = data[0]['vbucks_purchases']

        if not purchases:
            await ctx.reply(
                '📝 Ваш список покупок пуст.\n'
                '🕐 Если вы недавно прислали скриншот покупки, подождите '
                'некоторое время, пока статистика обновится.\n'
                '✅ Ознакомиться с требованиями к скриншотам и c правилами засчитывания '
                f'покупок можно по команде `{ctx.prefix or self.bot.PREFIX[0]}faq`.'
                '\n\n**P.S.** После обновления бота от 1 июля 2021 г. статистика покупок '
                'была сброшена у всех пользователей. Ознакомиться с причинами вайпа можно '
                f'по команде `{ctx.prefix or self.bot.PREFIX[0]}wipe`.')
            return

        vbucks_count = sum(purchases[i]['price'] for i in range(len(purchases)))

        embed = Embed(
            title='💰 Покупки',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description='**Для просмотра списка покупок нажмите на реакцию под сообщением.**'
        ).add_field(name="<:Vbucks:640675233342291969> Потрачено В-баксов с тегом FNFUN:",
                    value=vbucks_count,
                    inline=False
        ).add_field(name="🙂 Количество покупок с тегом FNFUN:",
					value=len(purchases),
                    inline=False
        ).add_field(name="📅 Дата последней покупки с тегом FNFUN:",
					value=purchases[-1]['date'][:-3],
                    inline=False
        )

        if self.kapitalist not in ctx.author.roles:
            if vbucks_count < 10_000:
                embed.add_field(
                    name=f"🤑 До роли `{self.kapitalist.name}` осталось: ",
                    value=f"{int(10_000 - vbucks_count)} В-баксов",
                    inline=False)
        if self.kapitalist in ctx.author.roles and self.magnat not in ctx.author.roles:
            if vbucks_count < 25_000:
                embed.add_field(
                    name=f"🤑 До роли `{self.magnat.name}` осталось: ",
                    value=f"{int(25_000 - vbucks_count)} В-баксов",
                    inline=False)

        message = await ctx.reply(embed=embed, mention_author=False)
        await message.add_reaction('✅')

        try:
            confirmation = await self.bot.wait_for(
                'reaction_add', timeout=120.0,
                check=lambda confirmation, user: user == ctx.author
                and confirmation.message.channel == ctx.channel
                and str(confirmation.emoji) == '✅')
        except TimeoutError:
            await message.clear_reactions()
            return

        if confirmation:
            data = [tuple(list(item.values())[1:]) for item in purchases]
            menu = MenuPages(source=VbucksPurchasesMenu(ctx, data), clear_reactions_after=True)
            await message.delete()
            await menu.start(ctx)


    @command(name=cmd["faq"]["name"], aliases=cmd["faq"]["aliases"],
            brief=cmd["faq"]["brief"],
            description=cmd["faq"]["description"],
            usage=cmd["faq"]["usage"],
            help=cmd["faq"]["help"],
            hidden=cmd["faq"]["hidden"], enabled=True)
    @is_any_channel([STATS_CHANNEL, CONSOLE_CHANNEL])
    @guild_only()
    @logger.catch
    async def faq_command(self, ctx):
        embeds = []
        embeds.append(Embed(
            title='🛍️ О покупках и правилах их засчитывания',
            color=0x408FE1,
            timestamp=datetime.utcnow(),
            description= \
            '⠀\n'
            '> **Сделал покупку с вашим тегом. Куда прислать фото?**\n\n'
            '> **Прислал скриншот/видео с покупкой, но моя статистика не изменилась. Почему?**\n\n'
            '> **Почему моя статистика покупок была сброшена?**\n\n'
            '> **Каковы правила засчитывания покупок?**\n\n'
            '**Ответы на эти (и не только) вопросы можно получить в этом меню.**'
        ).set_image(url='https://cdn.discordapp.com/attachments/774698479981297664/835805462716743690/unknown.png'))

        embeds.append(Embed(
            title='🤔 Куда присылать фото покупок с тегом?',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description= \
            '🪙 Совершили в магазине предметов покупку с нашим тегом автора? '
            'Присылайте скриншот/видео в <#546408250158088192> '
            '(новичкам недоступен просмотр истории канала, '
            ' но это не помеха для отправки скринов). '
            f'За поддержку и присланное фото вам достанется роль <@&{MECENAT_ROLE_ID}>\n'
            'Потратив с тегом **10 000** и **25 000** В-баксов, вы получите роли '
            f'<@&{KAPITALIST_ROLE_ID}> и <@&{MAGNAT_ROLE_ID}> соответственно.\n\n'
            '💸 К сожалению, стартер паки и прочие платные наборы, в которых есть В-баксы, '
            'не считаются за поддержку автора. Таковы правила Epic Games. Однако это '
            'не мешает вам прислать скрин такой покупки в <#546408250158088192>, но '
            'в этом случае роль за поддержку вы не получите. Подобная покупка будет '
            'засчитана отдельно, она не отразится на счётчике потраченных с '
            'тегом В-баксов.'
        ))

        embeds.append(Embed(
            title='😕 Почему моя статистика покупок не обновилась?',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description= \
            'Есть две основные причины, по которым покупка может быть не засчитана.\n\n'
            '**1.** *Покупка или скриншот с ней не соответствует требованиям.*\n'
            'Узнать правила засчитывания покупок можно на одной из следующих страниц.\n\n'
            '**2.** *Человеческий фактор.*\n'
            'Пожалуйста, учитывайте, что все скриншоты проверяются и засчитываются '
            '**вручную**. Время засчитывания может составлять от пары минут до '
            'нескольких дней. Это зависит от нагруженности модератора.\nВ '
            'случае необходимости вас могут попросить подтвердить покупку, '
            'предоставить дополнительные скриншоты/видео.'
        ))

        embeds.append(Embed(
            title='😥 Почему моя статистика покупок была сброшена?',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description= \
            'Главное, что стоит знать — просто так вашу статистику покупок '
            'никто сбрасывать не будет. Для этого должна быть веская причина. '
            'И такой причиной может быть лишь одно — обман со скринами поддержки.\n'
            'Если администрация сервера '
            'заподозрит вас в воровстве чужих скриншотов, ваша статистика будет '
            'сброшена на время расследования. Если подозреваемый сможет доказать, '
            'что не воровал скрины и не выдавал их за свои, его статистика '
            'вернётся в прежнее состояние. В противном случае за обман и '
            'воровство предусмотрен бан на сервере.\n\n'
            '**P.S.** После обновления бота от 1 июля 2021 г. '
            'статистика покупок была сброшена у всех пользователей. '
            'Это произошло по двум причинам:\n\n'
            '**1.** Изменение структуры базы данных бота.\n'
            '**2.** Появление новых правил засчитывания покупок.\n\n'
        ))

        embeds.append(Embed(
            title='📜 Каковы правила засчитывания покупок?',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description= \
            '**Для засчитывания внутриигровых покупок установлены слудующие правила:**\n\n'
            '> **1.** На фото отчётливо виден тег автора **FNFUN**.\n\n'
            '> **2.** Виден сам факт покупки предмета.\n\n'
            '> **3.** Если вы отправили подарок, на фото должна быть соответствующая надпись.\n\n'
            '> **4.** Есть надпись и кнопка для отмены покупки. Это подтверждение '
            'того, что предмет куплен только что и именно с нашим тегом.\n> *Правило не является '
            'обязательным и не распространяется на подарки, стартер паки и прочие наборы, '
            'которые возврату не подлежат.*\n\n'
            '> **5.** Покупку Боевого пропуска можно продемонстрировать, прислав 2 скриншота, '
            'на одном из которых виден факт покупки, а на втором - тег автора в магазине '
            'предметов. Вы также можете отправить видео с покупкой БП ('
            'загрузите видео на YouTube и пришлите ссылку на ролик, если не '
            'можете загрузить видео через Discord).\n\n'
            'Администрация вправе делать исключения по своему усмотрению '
            'и засчитывать (или не засчитывать) покупки наперекор правилам.'
        ).set_image(url='https://cdn.discordapp.com/attachments/774698479981297664/835853888041123840/why.png'))

        embeds.append(Embed(
            title='📝 Краткий список действий при покупке',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description= \
            '> **1.** Проверьте тег **FNFUN** в игровом магазине.\n\n'
            '> **2.** Купите нужный предмет.\n\n'
            '> **3.** Нажмите кнопку «Принять» для всех предметов.\n\n'
            '> **4.** Сделайте скриншот и отправьте его в <#546408250158088192>'
        ).set_image(url='https://cdn.discordapp.com/attachments/774698479981297664/835805462716743690/unknown.png'))

        message = await ctx.reply(embed=embeds[0], mention_author=False)
        page = Paginator(self.bot, message, only=ctx.author, embeds=embeds)
        await page.start()


    @Cog.listener()
    @listen_for_guilds()
    async def on_message(self, message):
        if message.channel.id == SAC_SCREENSHOTS_CHANNEL and not message.author.bot:
            if message.attachments:
                if not os.path.exists(f'./data/purchases_photos/{message.author.id}'):
                    os.makedirs(f'./data/purchases_photos/{message.author.id}')

                time_now = datetime.now().strftime('%d.%m.%Y %H.%M.%S')
                for attachment in message.attachments:
                    await attachment.save(
                        f'./data/purchases_photos/{message.author.id}/'
                        f'{time_now} — {str(message.id)} — {attachment.filename}'
                    )

def setup(bot):
    bot.add_cog(PurchasesHandler(bot))
