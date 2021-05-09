import json
from asyncio import TimeoutError
from datetime import datetime
from typing import Optional

from discord import Color, Embed
from discord.ext.commands import Cog, command, dm_only, guild_only, is_owner
from discord.ext.menus import ListPageSource, MenuPages
from discord.utils import get
from loguru import logger

from ..db import db
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
        table = '⠀' + ('\n'.join(f'\n> **{entry[0]}** \n> **Цена:** {entry[1]}\n> **Дата:** {entry[2][:-3]}'
                for idx, entry in enumerate(entries)))

        fields.append(('Список внутриигровых покупок за В-Баксы.', table))

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
        table = '⠀' + ('\n'.join(f'\n> **{entry[0]}** \n> **Цена:** {entry[1]}\n> **Дата:** {entry[2][:-3]}'
                for idx, entry in enumerate(entries)))

        fields.append(('Список покупок, совершённых за реальные деньги.', table))

        return await self.write_page(menu, offset, fields)


class PurchasesHandler(Cog, name='Покупки и не только'):
    def __init__(self, bot):
        self.bot = bot

    async def check_support_roles(self, member):
        purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', member.id)[0]
        vbucks_count = sum(purchases['vbucks_purchases'][i]['price'] for i in range(len(purchases['vbucks_purchases'])))

        mecenat = get(self.bot.guild.roles, id=731241570967486505)
        kapitalist = get(self.bot.guild.roles, id=730017005029294121)
        magnat = get(self.bot.guild.roles, id=774686818356428841)

        if mecenat not in member.roles:
            await member.add_roles(mecenat)
            edit_user_reputation(member.id, '+', 100)
        if kapitalist not in member.roles and vbucks_count >= 10000:
            await member.add_roles(kapitalist)
            edit_user_reputation(member.id, '+', 1000)
        if magnat not in member.roles and vbucks_count >= 25000:
            await member.add_roles(magnat)
            edit_user_reputation(member.id, '+', 2500)

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
                   json.dumps(purchases), user_id)
        db.commit()
        await self.check_support_roles(member)
        await ctx.reply(embed=Embed(
            title='В-Баксы добавлены',
            color=member.color,
            timestamp=datetime.utcnow(),
            description= 'Количество потраченных с тегом В-Баксов пользователя '
                        f'**{member.display_name}** ({member.mention}) было увеличено на **{amount}**.'
        ))


    @command(name=cmd["addrubles"]["name"], aliases=cmd["addrubles"]["aliases"],
            brief=cmd["addrubles"]["brief"],
            description=cmd["addrubles"]["description"],
            usage=cmd["addrubles"]["usage"],
            help=cmd["addrubles"]["help"],
            hidden=cmd["addrubles"]["hidden"], enabled=True)
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
                   json.dumps(purchases), user_id)
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
    async def reset_user_purchases_command(self, ctx, user_id: int, reason: Optional[str] = 'Не указана'):
        data = db.fetchone(['purchases'], 'users_stats', 'user_id', user_id)[0]
        data['reason'] = reason
        time_now = datetime.now().strftime("%d.%m.%Y %H.%M.%S")
        with open(f"./data/purchases_backup/{user_id} [{time_now}].json", "w") as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)

        purchases = {"vbucks_purchases":[],"realMoney_purchases":[]}
        db.execute("UPDATE users_stats SET purchases = %s WHERE user_id = %s",
                   json.dumps(purchases), user_id)
        db.commit()
        await ctx.message.add_reaction('✅')


    @command(name=cmd["purchases"]["name"], aliases=cmd["purchases"]["aliases"],
            brief=cmd["purchases"]["brief"],
            description=cmd["purchases"]["description"],
            usage=cmd["purchases"]["usage"],
            help=cmd["purchases"]["help"],
            hidden=cmd["purchases"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def fetch_purchases_command(self, ctx):
        reactions = ['1️⃣', '2️⃣']
        embed = Embed(
            title='💱 Выбор валюты',
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
            description='**Пожалуйста, выберите, покупки в какой валюте вы желаете просмотреть:\n\n'
                        '1️⃣ — покупки за В-Баксы.\n2️⃣ — покупки за реальные деньги (рубли).**'
        )
        message = await ctx.send(embed=embed)
        for r in reactions:
            await message.add_reaction(r)
        try:
            currency, user = await self.bot.wait_for(
                'reaction_add', timeout=120.0,
                check=lambda currency, user: user == ctx.author
                and currency.message.channel == ctx.channel
                and currency.emoji in reactions)
        except TimeoutError:
            await message.clear_reactions()
            return

        currency = "vbucks" if str(currency.emoji) == '1️⃣' else "rubles"

        if currency == "vbucks":
            purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', ctx.author.id)[0]['vbucks_purchases']
            data = [tuple(list(item.values())[1:]) for item in purchases]
            menu = MenuPages(source=VbucksPurchasesMenu(ctx, data), clear_reactions_after=True)
        else:
            purchases = db.fetchone(['purchases'], 'users_stats', 'user_id', ctx.author.id)[0]['realMoney_purchases']
            data = [tuple(list(item.values())[1:]) for item in purchases]
            menu = MenuPages(source=RealMoneyPurchasesMenu(ctx, data), clear_reactions_after=True)

        if purchases:
            await message.delete()
            await menu.start(ctx)
        else:
            await message.clear_reactions()
            await message.edit(content=f'{ctx.author.mention}, у вас нет покупок, которые соответствуют требованиям. '
                f'Ознакомиться с правилами засчитывания покупок можно по команде `{ctx.prefix or self.bot.PREFIX}faq`', embed=None)


    @command(name=cmd["faq"]["name"], aliases=cmd["faq"]["aliases"],
            brief=cmd["faq"]["brief"],
            description=cmd["faq"]["description"],
            usage=cmd["faq"]["usage"],
            help=cmd["faq"]["help"],
            hidden=cmd["faq"]["hidden"], enabled=True)
    @guild_only()
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
            'За поддержку и присланное фото вам достанется роль <@&731241570967486505>\n'
            'Потратив с тегом **10 000** и **25 000** В-Баксов, вы получите роль '
            '<@&730017005029294121> и <@&774686818356428841> соответственно.\n\n'
            '💸 К сожалению, стартер паки и прочие платные наборы, в которых есть В-Баксы, '
            'не считаются за поддержку автора. Таковы правила Epic Games. Однако это '
            'не мешает вам прислать скрин такой покупки в <#546408250158088192>, но '
            'в этом случае роль за поддержку вы не получите. Подобная покупка будет '
            'засчитана отдельно, она не отразится на счётчике потраченных с '
            'тегом В-Баксов.'
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
            '**Внимание!** После обновления бота от 1 июля 2021 г. '
            'статистика покупок **всех** пользователей была сброшена. '
            'Это произошло по двум причинам:\n\n**1.** *Изменение структуры '
            'хранения данных.*\nВ обновлении v3.0.0 база данных бота '
            'претерпела серьезные изменения, которые не позволили '
            'сохранить всю статистику пользователей. Некоторые показатели '
            'пришлось сбросить. Счётчик потраченных В-Баксов один из них.\n\n'
            '**2.** *Появление новых правил засчитывания покупок.*\n'
            'В последнее время участились случаи кражи чужих скриншотов '
            ' поддержки. Недобросовестные пользователи воруют фото покупок '
            'у участников сервера и выдают их за свои. В связи с этим было '
            'решено ужесточить политику засчитывания покупок путём введения '
            'новых правил. Ознакомиться с ними можно на следующей странице.'
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
            'того, что предмет куплен только что и именно с нашим тегом. | *Правило '
            'не распространяется на подарки, стартер паки и прочие наборы, '
            'которые возврату не подлежат.*\n\n'
            '> **5.** Покупку Боевого пропуска можно продемонстрировать, прислав 2 скриншота, '
            'на одном из которых виден факт покупки, а на втором - тег автора в магазине '
            'предметов. Вы также можете отправить видео с покупкой БП ('
            'загрузите видео на YouTube и пришлите ссылку на ролик, если не '
            'можете загрузить видео через Discord).\n\n'
            'Администрация вправе делать исключения по своему усмотрению '
            'и засчитывать покупки наперекор правилам.'
        ).set_image(url='https://cdn.discordapp.com/attachments/774698479981297664/835853888041123840/why.png'))

        message = await ctx.send(embed=embeds[0])
        page = Paginator(self.bot, message, only=ctx.author, embeds=embeds)
        await page.start()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("purchases_handler")


def setup(bot):
    bot.add_cog(PurchasesHandler(bot))
