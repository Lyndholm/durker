from asyncio import sleep
from random import randint

from apscheduler.triggers.cron import CronTrigger
from discord import Member
from discord.ext.commands import (Cog, CommandError, CommandOnCooldown, Greedy,
                                  NoPrivateMessage, check, command, cooldown,
                                  guild_only)
from discord.ext.commands.cooldowns import BucketType
from discord.utils import get
from loguru import logger

from ..db import db
from ..utils.constants import CHASOVOY_ROLE_ID
from ..utils.utils import cooldown_timer_str, load_commands_from_json

cmd = load_commands_from_json("durka")


class NoAvaliableDurkaCalls(CommandError):
    pass

class NotEnoughPermsForCalling(CommandError):
    pass

def have_available_durka_calls() -> bool:
    def predicate(ctx):
        chasovoy = get(ctx.guild.roles, id=CHASOVOY_ROLE_ID)
        if ctx.author.top_role.position >= chasovoy.position:
            return True

        rec = db.fetchone(["available_durka_calls"], "durka_stats", "user_id", ctx.author.id)[0]
        if rec > 0:
            if not ctx.command.is_on_cooldown(ctx):
                db.execute(f"UPDATE durka_stats SET available_durka_calls = available_durka_calls - 1 WHERE user_id = {ctx.author.id}")
                db.commit()
            return True
        else:
            raise NoAvaliableDurkaCalls

    return check(predicate)

def have_enough_perms_for_calling() -> bool:
    def predicate(ctx):
        allowed_roles = (
            686499129895157761, #гвардия
            546417656018763793, #олд
            546417889884897293, #капитан
            765942949476302849, #ветеран
            643879247433433108, #часовой
            682157177959481363, #добряк
            546418128490332161, #джон уик
            546403143643037696, #cactus' role
            546409562631045170, #создатель
            790664227706241068, #dev role (dev server)
        )
        if set([int(r.id) for r in ctx.author.roles]).intersection(allowed_roles):
            return True
        else:
            raise NotEnoughPermsForCalling

    return check(predicate)


class Durka(Cog, name='Родина-Дурка'):
    def __init__(self, bot):
        self.bot = bot
        self.durka_emoji = "<:durka:684794973358522426>"
        self.shizoid_emoji = "<:shizoid:717756757958459443>"
        self.one_target_emoji = f"{self.durka_emoji}{self.durka_emoji}{self.shizoid_emoji}{self.durka_emoji}{self.durka_emoji}"
        self.multiple_targets_emoji = f"{self.durka_emoji}{self.shizoid_emoji}{self.shizoid_emoji}{self.shizoid_emoji}{self.durka_emoji}"
        self.schedule_durka_calls_update(self.bot.scheduler)
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    @logger.catch
    async def init_vars(self):
        self.chasovoy = self.bot.guild.get_role(CHASOVOY_ROLE_ID)

    def update_available_durka_calls(self):
        for member in self.bot.guild:
            db.execute("UPDATE durka_stats SET available_durka_calls = 3 WHERE user_id = %s", member.id)
            db.commit()

    def schedule_durka_calls_update(self, sched):
        sched.add_job(self.update_available_durka_calls, CronTrigger(hour=3))

    async def durka_replies(self, ctx, targets):
        if len(targets) == 1:
            answer = randint(1,6)
            if answer == 1:
                content = f"Замечен шизоид {self.shizoid_emoji*3}\nДурка в пути. Пожалуйста, ожидайте."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nДурка прибыла. Пациент {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} теперь у нас.\n{self.one_target_emoji}\nСпасибо, {ctx.author.mention}, что пользуетесь нашими услугами!"
                await message.edit(content=content)

            elif answer == 2:
                content = f"Здравствуйте, {ctx.author.mention}! Спасибо, что позвонили в нашу психиатрическую больницу №47. " \
                          f"Шизоид {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} будет помещён в комнату с мягкими стенами."
                message = await ctx.send(content)
                await sleep(5)
                content += f'\n\nСанитары прибыли. Пациент {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} успешно упакован и отправлен в больничку на дурко-мобиле.\n{self.one_target_emoji}'
                await message.edit(content=content)

            elif answer == 3:
                content = f"{ctx.author.mention} объявил охоту санитаров на шизоида {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji}."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nШизоид {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} не смог избежать поимки санитарами.\n{self.one_target_emoji}\nПациент отправлен в дурку."
                await message.edit(content=content)

            elif answer == 4:
                content = f"Здравствуйте, {ctx.author.mention}! Благодарим за обращение в OOO «Durka United»! Шизоид {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} в кратчайшие сроки будет доставлен в ближайшее отделение дурки."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nШизоид {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} успешно доставлен в дурку.\n{self.one_target_emoji}\nБлагодарим за использование услуг нашей компании. Счёт для оплаты будет выслан по голубиной почте."
                await message.edit(content=content)

            elif answer == 5:
                content = f"Здравствуйте, {ctx.author.mention}! Спасибо за звонок в нашу психиатрическую больницу. Из-за серьезных бед с башкой у {targets[0].mention} мы вынуждены забрать его в дурку, дабы уберечь здоровых людей."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nСанитары успешно доставили {targets[0].mention} в дурку.\n{self.one_target_emoji}\nТеперь никто не сможет пострадать от больного."
                await message.edit(content=content)

            elif answer == 6:
                content = f"{targets[0].mention} — неееет ты не можешь забрать меня в дурку просто командой для бота\n{ctx.guild.me.mention} — хаха дуркомобиль делает врррррррр"
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nДуркомобиль успешно привёз {targets[0].mention} в дурку.\n{self.one_target_emoji}\nшизоид делает ахщвщхщ."
                await message.edit(content=content)
        else:
            answer = randint(1,6)
            if answer == 1:
                content = f"Шизоиды на горизонте.\nДурка в пути. {ctx.author.mention}, пожалуйста, ожидайте."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nДурка прибыла. Пациенты {' '.join([member.mention for member in targets])} теперь у нас.\n{self.multiple_targets_emoji}" \
                           f"\n{self.multiple_targets_emoji}\nСпасибо, {ctx.author.mention}, что пользуетесь нашими услугами!"
                await message.edit(content=content)

            elif answer == 2:
                content = f"Здравствуйте, {ctx.author.mention}! Спасибо, что позвонили в нашу психиатрическую больницу №47. " \
                          f"Шизоиды {self.shizoid_emoji}{targets[0].mention}{self.shizoid_emoji} будут помещены в комнату с мягкими стенами."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nСанитары прибыли. Пациенты {' '.join([member.mention for member in targets])} успешно упакованы и отправлены в больничку на дурко-мобиле.\n{self.multiple_targets_emoji}"
                await message.edit(content=content)

            elif answer == 3:
                content = f"{ctx.author.mention} объявил охоту санитаров на шизоидов {self.shizoid_emoji*len(targets)}."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nШизоиды {' '.join([member.mention for member in targets])} не смогли избежать поимки санитарами.\n{self.multiple_targets_emoji}\nПациенты отправлены в дурку."
                await message.edit(content=content)

            elif answer == 4:
                content = f"Здравствуйте, {ctx.author.mention}! Благодарим за обращение в OOO «Durka United»! Шизоиды {self.shizoid_emoji*len(targets)} в кратчайшие сроки будут доставлены в ближайшее отделение дурки."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nШизоиды {' '.join([member.mention for member in targets])} успешно доставлены в дурку.\n{self.multiple_targets_emoji}\nБлагодарим за использование услуг нашей компании. Счёт для оплаты будет выслан по голубиной почте."
                await message.edit(content=content)

            elif answer == 5:
                content = f"Здравствуйте, {ctx.author.mention}! Спасибо за звонок в нашу психиатрическую больницу. Из-за серьезных бед с башкой у {' '.join([member.mention for member in targets])} мы вынуждены забрать их в дурку, дабы уберечь здоровых людей."
                message = await ctx.send(content)
                await sleep(5)
                content += f"\n\nСанитары успешно доставили {' '.join([member.mention for member in targets])} в дурку.\n{self.multiple_targets_emoji}\nТеперь никто не сможет пострадать от больных."
                await message.edit(content=content)

    @command(name=cmd["durka"]["name"], aliases=cmd["durka"]["aliases"],
            brief=cmd["durka"]["brief"],
            description=cmd["durka"]["description"],
            usage=cmd["durka"]["usage"],
            help=cmd["durka"]["help"],
            hidden=cmd["durka"]["hidden"], enabled=True)
    @have_available_durka_calls()
    @have_enough_perms_for_calling()
    @guild_only()
    @cooldown(cmd["durka"]["cooldown_rate"], cmd["durka"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def durka_command(self, ctx, targets: Greedy[Member]):
        durka_ban_list = (ctx.guild.me, ctx.guild.get_member(375722626636578816))

        if not targets:
            await ctx.send(f"Здравствуйте, **{ctx.author.display_name}**! Благодарим за звонок в психиатрическую больницу.\n"
                "Судя по всему, в чате творится дурка. К счастью, наш оператор готов принять заказ на шизоидов. "
                "Пожалуйста, укажите пользователей, которых необходимо забрать на лечение: `+дурка @users`\n"
                "Учтите, места в дурко-мобиле ограничены, санитары не могут перевозить более 5 пациентов за раз. "
                "Также за сутки вы можете вызвать дурку не более 3-х раз.", delete_after=60)
            ctx.command.reset_cooldown(ctx)
            if ctx.author.top_role.position < self.chasovoy.position:
                db.execute("UPDATE durka_stats SET available_durka_calls = available_durka_calls + 1 WHERE user_id = %s", ctx.author.id)
                db.commit()
            return

        if len(targets) > 5:
            await ctx.send("Места в дурко-мобиле ограничены. Санитары не могут перевозить более 5 пациентов за раз.")
            return

        targets = [t for t in targets if t not in durka_ban_list]

        if not targets:
            await ctx.send(f"Шизоид {self.durka_emoji}{ctx.message.author.mention}{self.durka_emoji}, ты кому дурку вызываешь? Вернись в палату.\nЯ уже вызвал тебе санитаров, они в пути.")
            return

        for target in targets:
            db.execute("UPDATE durka_stats SET received_durka_calls = received_durka_calls + 1 WHERE user_id = %s", target.id)
            db.commit()
            if ctx.author.top_role.position >= self.chasovoy.position:
                ctx.command.reset_cooldown(ctx)
                db.execute("UPDATE users_stats SET rep_rank = rep_rank - 50 WHERE user_id = %s", target.id)
                db.commit()

        if 50 <= randint(1, 100) <= 55:
            if ctx.author != ctx.guild.get_member(375722626636578816):
                await ctx.channel.send(f'Шизоид {self.durka_emoji}{ctx.message.author.mention}{self.durka_emoji}, ты как из палаты выбрался?. Вернись обратно немедленно.\nСанитары уже в пути.')
            else:
                await self.durka_replies(ctx, targets)
        else:
            await self.durka_replies(ctx, targets)

    @durka_command.error
    async def durka_command_error(self, ctx, exc):
        if isinstance(exc, NotEnoughPermsForCalling):
            await ctx.message.delete(delay=30)
            await ctx.reply(
                f'Дружище {ctx.author.mention}, ты пока не можешь вызывать дурку. '
                'Тебе необходимо получить роль **Олд**, как минимум.',
                mention_author=False, delete_after=30
            )
        elif isinstance(exc, NoAvaliableDurkaCalls):
            await ctx.message.delete(delay=30)
            await ctx.reply(
                f'{ctx.author.mention}, вы исчерпали суточный лимит использования дурки. '
                'В день вы можете вызвать саниторов не более **трёх** раз. Количество '
                'вызовов сбрасывается ежедневно в **03:00 МСК**.',
                mention_author=False, delete_after=30
            )
        elif isinstance(exc, CommandOnCooldown):
            await ctx.message.delete(delay=30)
            await ctx.reply(
                f'Не так быстро! Дурка может принять заказ от одного пользователя раз в '
                '**60 минут**. Новый вызов можно будет сделать через '
                f'{cooldown_timer_str(exc.retry_after)}',
                mention_author=False, delete_after=30
            )
        elif isinstance(exc, NoPrivateMessage):
            await ctx.reply('Дурка не работает в личных сообщениях.', mention_author=False)
        else:
            raise exc


    @command(name=cmd["durkachat"]["name"], aliases=cmd["durkachat"]["aliases"],
            brief=cmd["durkachat"]["brief"],
            description=cmd["durkachat"]["description"],
            usage=cmd["durkachat"]["usage"],
            help=cmd["durkachat"]["help"],
            hidden=cmd["durkachat"]["hidden"], enabled=True)
    @have_available_durka_calls()
    @have_enough_perms_for_calling()
    @guild_only()
    @cooldown(cmd["durkachat"]["cooldown_rate"], cmd["durkachat"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def durka_chat_command(self, ctx):
        content = f"Внимание! Наши специалисты заметили чрезвычайно высокое содержание бреда в чате.\nСанитары уже выдвинулись для разрешения проблемы " \
                  f"{self.durka_emoji}{self.shizoid_emoji}{self.durka_emoji}{self.shizoid_emoji}{self.durka_emoji}"
        message = await ctx.send(content)
        await sleep(5)
        content += f"\n\nУгроза шизы ликвидирована, санитары возвращаются в офис. Просим в дальнейшем избегать превышения нормы дурки в чате.\nСпасибо, {ctx.author.mention}, что пользуетесь нашими услугами!"
        await message.edit(content=content)

    @durka_chat_command.error
    async def durka_chat_command_error(self, ctx, exc):
        if isinstance(exc, NotEnoughPermsForCalling):
            await ctx.message.delete(delay=30)
            await ctx.reply(
                f'Дружище {ctx.author.mention}, ты пока не можешь вызывать дурку. '
                'Тебе необходимо получить роль **Олд**, как минимум.',
                mention_author=False, delete_after=30
            )
        elif isinstance(exc, NoAvaliableDurkaCalls):
            await ctx.message.delete(delay=30)
            await ctx.reply(
                f'{ctx.author.mention}, вы исчерпали суточный лимит использования дурки. '
                'В день вы можете вызвать саниторов не более **трёх** раз. Количество '
                'вызовов сбрасывается ежедневно в **03:00 МСК**.',
                mention_author=False, delete_after=30
            )
        elif isinstance(exc, CommandOnCooldown):
            await ctx.message.delete(delay=30)
            await ctx.reply(
                f'Не так быстро! Дурку чату можно вызвать один раз в **15 минут**. '
                'Новый вызов можно будет сделать через '
                f'{cooldown_timer_str(exc.retry_after)}',
                delete_after=30, mention_author=False
            )
        elif isinstance(exc, NoPrivateMessage):
            await ctx.reply("Дурка не работает в личных сообщениях.", mention_author=False)
        else:
            raise exc


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.chasovoy = self.bot.guild.get_role(CHASOVOY_ROLE_ID)
            self.bot.cogs_ready.ready_up("durka")


def setup(bot):
    bot.add_cog(Durka(bot))
