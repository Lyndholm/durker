from asyncio.exceptions import TimeoutError
from datetime import datetime, timedelta

from discord import Color, Embed, Member
from discord.ext.commands import Cog, command, guild_only
from discord.utils import get
from loguru import logger

from ..db import db
from ..utils.utils import load_commands_from_json, russian_plural

cmd = load_commands_from_json("user_stats")


class UserStats(Cog, name='Статистика'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("user_stats")

    @command(name=cmd["profile"]["name"], aliases=cmd["profile"]["aliases"],
        brief=cmd["profile"]["brief"],
        description=cmd["profile"]["description"],
        usage=cmd["profile"]["usage"],
        help=cmd["profile"]["help"],
        hidden=cmd["profile"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def fetch_member_profile_command(self, ctx, member: Member = None):
        if member and member != ctx.author:
            is_member_profile_public = db.fetchone(["is_profile_public"], "users_info", "user_id", member.id)
            if is_member_profile_public[0] is False:
                embed = Embed(title="❗ Внимание!", color=Color.red(), timestamp=datetime.utcnow(),
                            description=f"Профиль участника **{member.display_name}** ({member.mention}) скрыт. Просматривать его может только владелец.")
                embed.set_footer(text=ctx.author, icon_url=ctx.author.avatar_url)
                await ctx.send(embed=embed)
                return
            else:
                target = member
        else:
            target = ctx.author


        casino = db.fetchone(["cash", "e_cash"], "casino", 'user_id', target.id)

        durka_stats = db.fetchone(["received_durka_calls"], "durka_stats", 'user_id', target.id)

        leveling = db.fetchone(["level", "xp"], "leveling", 'user_id', target.id)

        biography = db.fetchone(["brief_biography"], "users_info", 'user_id', target.id)

        purchases = db.fetchone(["purchases"], "users_stats", 'user_id', target.id)

        user_stats = db.fetchone(["achievements_list", "messages_count", "rep_rank", "invoice_time", "lost_reputation"],
                                "users_stats", 'user_id', target.id)

        moderation_stats = db.fetchone(["mutes_story", "warns_story", "profanity_triggers"],
                                    "users_stats", 'user_id', target.id)

        total_mute_time = sum(moderation_stats[0]['user_mute_story'][i]['mute_time'] for i in range(len(moderation_stats[0]['user_mute_story']))) + \
            sum(moderation_stats[1]['user_warn_story'][i]['mute_time'] for i in range(len(moderation_stats[1]['user_warn_story'])))

        vbucks_count = sum(purchases[0]['vbucks_purchases'][i]['price'] for i in range(len(purchases[0]['vbucks_purchases'])))

        realMoney = sum(purchases[0]['realMoney_purchases'][i]['price'] for i in range(len(purchases[0]['realMoney_purchases'])))

        kapitalist = ctx.guild.get_role(730017005029294121)

        magnat = ctx.guild.get_role(774686818356428841)

        embed = Embed(color=target.color)

        embed.set_author(name=f"{target.display_name}", icon_url=target.avatar_url)

        embed.set_thumbnail(url=target.avatar_url)

        if member:
            embed.add_field(name=':pencil: О пользователе:', value=biography[0] if biography[0] else "Пользователь не указал свою биографию.",
                            inline=False)
        else:
            embed.add_field(name=':pencil: О себе:', value=biography[0] if biography[0] else "Вы ничего не написали о себе. "
                                                                                            "Сделать это можно по команде "
                                                                                            f"`{ctx.prefix or self.bot.PREFIX}"
                                                                                            "setbio <ваша биография>`",
                            inline=False)

        embed.add_field(name=':calendar: Аккаунт создан:', value=target.created_at.strftime("%d.%m.%Y %H:%M"),
                        inline=True)

        embed.add_field(name=':calendar_spiral: Дата захода на сервер:',
                        value=target.joined_at.strftime("%d.%m.%Y %H:%M"), inline=True)

        embed.add_field(name=':calendar_spiral: Количество дней на сервере:',
                        value=(datetime.now() - target.joined_at).days, inline=True)
        if len(target.roles) > 1:
            embed.add_field(name=f":grinning: Роли ({len(target.roles) - 1})",
                        value=" ".join([role.mention for role in target.roles[1:]]), inline=True)
        else:
            embed.add_field(name=f":grinning: Роли ({len(target.roles)})",
                                    value=" ".join([role.mention for role in target.roles]), inline=True)

        embed.add_field(name=":sunglasses: Наивысшая роль:", value=target.top_role.mention, inline=True)

        embed.add_field(name=":military_medal: Количество достижений:", value=len(user_stats[0]["user_achievements_list"]), inline=True)

        embed.add_field(name=":envelope: Количество сообщений:", value=user_stats[1], inline=True)

        embed.add_field(name=":green_circle: Уровень:", value=leveling[0], inline=True)

        embed.add_field(name=":green_circle: XP:", value=leveling[1], inline=True)

        embed.add_field(name=":face_with_monocle: Репутация:", value=user_stats[2], inline=True)

        embed.add_field(name=":thumbsdown: Потеряно репутации:", value=user_stats[4], inline=True)

        embed.add_field(name="<:durka:745936793148588083>  Получено путёвок в дурку:", value=durka_stats[0],
                        inline=True)

        embed.add_field(name=":face_with_symbols_over_mouth: Количество триггеров мат-фильтра:", value=moderation_stats[2],
                        inline=True)

        embed.add_field(name=":moneybag:  Потрачено В-Баксов с тегом FNFUN:",
                        value=vbucks_count, inline=True)

        if len(purchases[0]['vbucks_purchases']) > 0:

            embed.add_field(name=":slight_smile: Количество покупок с тегом FNFUN:",
                            value=len(purchases[0]['vbucks_purchases']), inline=True)

            embed.add_field(name=":date: Дата последней покупки с тегом FNFUN:",
                            value=purchases[0]['vbucks_purchases'][-1]['date'][:-3])

        if kapitalist not in target.roles:
            embed.add_field(name=f":moneybag: До роли `{kapitalist.name}` осталось: ",
                            value=f"{int(10000 - vbucks_count)} В-Баксов", inline=True)

        if magnat not in target.roles and kapitalist in target.roles:
            embed.add_field(name=f":moneybag: До роли `{magnat.name}` осталось: ",
                            value=f"{int(25000 - vbucks_count)} В-Баксов", inline=True)

        if len(purchases[0]['realMoney_purchases']) > 0:
            embed.add_field(name=":money_with_wings: Поддержка автора в рублях:",
                            value=realMoney, inline=True)

        embed.add_field(name=":speaker: Время, проведенное в голосовых каналах:",
                        value=timedelta(seconds=user_stats[3]), inline=True)

        embed.add_field(name=":coin: FUN-коинов:", value=casino[0] + casino[1], inline=True)

        embed.add_field(name=":warning: Количество предупреждений:", value=len(moderation_stats[1]["user_warn_story"]), inline=True)

        embed.add_field(name=":speak_no_evil: Количество мутов:", value=(len(moderation_stats[0]["user_mute_story"]) + len(moderation_stats[1]["user_warn_story"])), inline=True)

        embed.add_field(name=":timer: Время, проведенное в муте:", value=timedelta(seconds=total_mute_time),
                        inline=True)

        embed.add_field(name=":zap: Бустер сервера:", value='Да' if bool(target.premium_since) else 'Нет',
                        inline=True)

        if member:
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text=f"Запрос от: {ctx.author}", icon_url=ctx.author.avatar_url)
        else:
            embed.set_footer(text='Данные актуальны на ' + datetime.now().strftime("%d.%m.%Y %H:%M:%S") + ' МСК')

        await ctx.reply(
            'После обновления бота от 1 июля 2021 г. статистика '
            'покупок (по В-Баксам) была сброшена у всех пользователей. '
            'Ознакомится с причиной вайпа и новыми правилами засчитывания '
            f'покупок можно по команде `{ctx.prefix or self.bot.PREFIX}faq`.', embed=embed)


    @command(name=cmd["setbio"]["name"], aliases=cmd["setbio"]["aliases"],
        brief=cmd["setbio"]["brief"],
        description=cmd["setbio"]["description"],
        usage=cmd["setbio"]["usage"],
        help=cmd["setbio"]["help"],
        hidden=cmd["setbio"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def setbio_command(self, ctx, *, bio: str = None):
        if bio is None:
            db_bio = db.fetchone(["brief_biography"], "users_info", "user_id", ctx.author.id)[0]

            if db_bio is not None:
                    r_list = ['🟩', '🟥']
                    embed = Embed(title='❗ Внимание!', color = Color.red(), timestamp = datetime.utcnow(),
                            description = f"{ctx.author.mention}, ваша биография уже написана. Вы желаете её сбросить?\n\n"
                            "🟩 — нет.\n\n🟥 — да, сбросить мою биографию.")
                    msg = await ctx.send(embed=embed)

                    for r in r_list:
                        await msg.add_reaction(r)
                    try:
                        react, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=lambda react,
                                    user: user == ctx.author and react.message.channel == ctx.channel
                                    and react.emoji in r_list)

                    except TimeoutError:
                        await msg.clear_reactions()
                        embed = Embed(title="Время вышло", color=Color.magenta(), timestamp=datetime.utcnow(),
                                    description=f"{ctx.author.mention}, время на выбор вышло, дейсвтие оменено.")
                        await msg.reply(embed=embed)
                        return


                    else:
                        if str(react.emoji) == r_list[0]:
                            embed = Embed(title=':white_check_mark: Действие отменено', color = Color.green(), timestamp = datetime.utcnow(),
                                        description = f"Сброс биографии отменён.\n"
                                        "Если вы хотите изменить биографию, введите команду ещё раз, указав необходимый текст.\n"
                                        "**Пример:** +setbio Это моя новая биография!")
                            await ctx.send(embed=embed)
                            return

                        if str(react.emoji) == r_list[1]:
                            db.execute("UPDATE users_info SET brief_biography = %s WHERE user_id = %s",
                            None, ctx.author.id)
                            db.commit()

                            embed = Embed(title=':white_check_mark: Выполнено!', color = Color.green(), timestamp = datetime.utcnow(),
                                        description = f"Биография пользователя **{ctx.author.display_name}** сброшена.")
                            await ctx.send(embed=embed)
                            return
            else:
                embed = Embed(title='❗ Внимание!', color = Color.red(),
                            description = f"{ctx.author.mention}, пожалуйста, напишите Вашу биографию. Учитывайте, что максимальная длина текста — **255** символов.")
                await ctx.send(embed=embed)

        elif len(bio.strip()) > 255:
            embed = Embed(title='❗ Внимание!', color = Color.red(),
                        description = f"{ctx.author.mention}, пожалуйста, уменьшите длину Вашей биографии. Вы превысили допустимый объём на {len(bio) - 255} символ(-а).")
            await ctx.send(embed=embed)

        else:
            bio = bio.replace('`', '`­')
            try:
                db.execute("UPDATE users_info SET brief_biography = %s WHERE user_id = %s",
                            bio.strip(), ctx.author.id)
                db.commit()

                embed = Embed(title=':white_check_mark: Выполнено!', color = Color.green(), timestamp = datetime.utcnow(),
                            description = f"Поздравляем, **{ctx.author.display_name}**! Ваша биография обновлена:\n```{bio}```")
                await ctx.send(embed=embed)

            except Exception as e:
                raise e


    @command(name=cmd["setprivacy"]["name"], aliases=cmd["setprivacy"]["aliases"],
        brief=cmd["setprivacy"]["brief"],
        description=cmd["setprivacy"]["description"],
        usage=cmd["setprivacy"]["usage"],
        help=cmd["setprivacy"]["help"],
        hidden=cmd["setprivacy"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def set_user_profile_privacy_command(self, ctx):
        r_list = ['🟩', '🟥', '❌']
        embed = Embed(
            color = Color.magenta(),
            description = f"Пожалуйста, выберите тип вашего профиля:\n\n"
                "🟩 — Открытый, просматривать его могут все пользователи в любое время.\n🟥 — Закрытый, просматровать профиль можете только вы."
                "\n\n❌ — выход."
            )
        msg = await ctx.send(embed=embed)

        for r in r_list:
            await msg.add_reaction(r)
        try:
            react, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=lambda react,
                        user: user == ctx.author and react.message.channel == ctx.channel
                        and react.emoji in r_list)

        except TimeoutError:
            await msg.clear_reactions()
            embed = Embed(title="Время вышло", color=Color.magenta(), timestamp=datetime.utcnow(),
                        description=f"{ctx.author.mention}, время на выбор вышло, дейсвтие оменено.")
            await msg.reply(embed=embed)
            return


        if str(react.emoji) == r_list[2]:
            await msg.delete()
            embed = Embed(
                title='❌ Действие отменено',
                сolor = Color.dark_red(),
                timestamp = datetime.utcnow()
            )
            await ctx.message.reply(embed=embed)
            return

        if str(react.emoji) == r_list[0]:
            await msg.clear_reactions()

            db.execute("UPDATE users_info SET is_profile_public = %s WHERE user_id = %s",
                    True, ctx.author.id)
            db.commit()

            embed = Embed(
                title=':white_check_mark: Выполнено!',
                color = Color.green(),
                timestamp = datetime.utcnow(),
                description = f"**{ctx.author.display_name}**, ваши настройки приватности обновлены.\nТип вашего профиля: **Открытый**"
            )
            await msg.edit(embed=embed)
            return

        elif str(react.emoji) == r_list[1]:
            await msg.clear_reactions()

            db.execute("UPDATE users_info SET is_profile_public = %s WHERE user_id = %s",
                    False, ctx.author.id)
            db.commit()

            embed = Embed(
                title=':white_check_mark: Выполнено!',
                color = Color.red(),
                timestamp = datetime.utcnow(),
                description = f"**{ctx.author.display_name}**, ваши настройки приватности обновлены.\nТип вашего профиля: **Закрытый**"
            )
            await msg.edit(embed=embed)


    @command(name=cmd["amount"]["name"], aliases=cmd["amount"]["aliases"],
        brief=cmd["amount"]["brief"],
        description=cmd["amount"]["description"],
        usage=cmd["amount"]["usage"],
        help=cmd["amount"]["help"],
        hidden=cmd["amount"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def amount_command(self, ctx):
        activity_role_1 = get(ctx.guild.roles, name='Работяга')
        activity_role_2 = get(ctx.guild.roles, name='Олд')
        activity_role_3 = get(ctx.guild.roles, name='Капитан')
        activity_role_4 = get(ctx.guild.roles, name='Ветеран')
        msg_counter = db.fetchone(["messages_count"], "users_stats", 'user_id', ctx.author.id)[0]
        desc = f"{ctx.author.mention}, ваше количество сообщений: **{msg_counter}**"

        embed = Embed(color=ctx.author.color)
        embed.set_author(name="Количество сообщений", icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/814988530219614249/message.png")

        if activity_role_1 not in ctx.author.roles:
            desc += f"\n\nДо роли {activity_role_1.mention} осталось **{750-msg_counter}** {russian_plural(750-msg_counter,['сообщение','сообщения','сообщений'])}"
            if old := (datetime.now() - ctx.author.joined_at).days <= 7:
                desc += f" и **{old+1}** {russian_plural(old+1,['день','дня','дней'])} пребывания на сервере."
        elif activity_role_2 not in ctx.author.roles:
            desc += f"\n\nДо роли {activity_role_2.mention} осталось **{3500-msg_counter}** {russian_plural(3500-msg_counter,['сообщение','сообщения','сообщений'])}"
            if old := (datetime.now() - ctx.author.joined_at).days <= 30:
                desc += f" и **{old+1}** {russian_plural(old+1,['день','дня','дней'])} пребывания на сервере."
        elif activity_role_3 not in ctx.author.roles:
            desc += f"\n\nДо роли {activity_role_3.mention} осталось **{10000-msg_counter}** {russian_plural(10000-msg_counter,['сообщение','сообщения','сообщений'])}"
            if old := (datetime.now() - ctx.author.joined_at).days <= 90:
                desc += f" и **{old+1}** {russian_plural(old+1,['день','дня','дней'])} пребывания на сервере."
        elif activity_role_4 not in ctx.author.roles:
            desc += f"\n\nДо роли {activity_role_4.mention} осталось **{25000-msg_counter}** {russian_plural(25000-msg_counter,['сообщение','сообщения','сообщений'])}"
            if old := (datetime.now() - ctx.author.joined_at).days <= 180:
                desc += f" и **{old+1}** {russian_plural(old+1,['день','дня','дней'])} пребывания на сервере."

        embed.description = desc
        await ctx.send(embed=embed)


    @command(name=cmd["myrep"]["name"], aliases=cmd["myrep"]["aliases"],
        brief=cmd["myrep"]["brief"],
        description=cmd["myrep"]["description"],
        usage=cmd["myrep"]["usage"],
        help=cmd["myrep"]["help"],
        hidden=cmd["myrep"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def myrep_command(self, ctx):
        rep_rank = db.fetchone(["rep_rank"], "users_stats", 'user_id', ctx.author.id)[0]
        desc = f"{ctx.author.mention}, количество ваших очков репутации: **{rep_rank}**"

        embed = Embed(color=ctx.author.color)
        embed.set_author(name="Очки репутации", icon_url=ctx.author.avatar_url)
        if rep_rank <= 0:
            desc += f"\n\nВаш ранг: **Отсутствует**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298656462700634/no_rank.png")
        elif 1 <= rep_rank <= 1499:
            desc += f"\n\nВаш ранг: **Бронза**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298685498949662/rank_bronze.png")
        elif 1500 <= rep_rank <= 2999:
            desc += f"\n\nВаш ранг: **Серебро**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298847705792522/rank_silver.png")
        elif 3000 <= rep_rank <= 4499:
            desc += f"\n\nВаш ранг: **Золото**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298881285652550/rank_gold.png")
        elif 4500 <= rep_rank <= 6999:
            desc += f"\n\nВаш ранг: **Платина**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298909161259028/rank_platinum.png")
        elif 7000 <= rep_rank <= 9999:
            desc += f"\n\nВаш ранг: **Алмаз**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298936734220349/rank_diamond.png")
        elif 10000 <= rep_rank <= 14999:
            desc += f"\n\nВаш ранг: **Мастер**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298973065543680/rank_master.png")
        elif 15000 <= rep_rank <= 19999:
            desc += f"\n\nВаш ранг: **Элита**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298996959445042/rank_grandmaster.png")
        elif rep_rank > 20000:
            desc += f"\n\nВаш ранг: **Совершенство**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815299017948004402/rank_perfection.png")

        embed.description = desc
        await ctx.send(embed=embed)


    @command(name=cmd["rep"]["name"], aliases=cmd["rep"]["aliases"],
        brief=cmd["rep"]["brief"],
        description=cmd["rep"]["description"],
        usage=cmd["rep"]["usage"],
        help=cmd["rep"]["help"],
        hidden=cmd["rep"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def how_rep_sys_works_command(self, ctx):
        embed = Embed(
            title="Репутация: что это, для чего нужна, как зарабатывать.",
            color=ctx.author.color,
            description="На сервере работает система репутации.\n"
            "У каждого участника есть свой уровень репутации. "
            "Репутация отображает активность пользователя; его манеру общения и то, как он соблюдает правила."
            "\n\nРепутацию можно заработать разными способами, наиболее распространённые:"
            "\n— Активное общение в чате\n— Получение ролей\n— Открытие достижений | `+achievements`\n— Повышение уровня | `+rank`"
            "\n\nРепутацию можно и потерять. Использование нецензурной лексики, муты, предупреждения от администраторов уменьшают уровень репутации."
            "\n\nВ зависимости от количества репутации меняется ранг участника."
            " Существуют 8 рангов репутации:"
            "\n— **Бронза** (1 - 1499)"
            "\n— **Серебро** (1500 - 2999)"
            "\n— **Золото** (3000 - 4499)"
            "\n— **Платина** (4500 - 6999)"
            "\n— **Алмаз** (7000 - 9999)"
            "\n— **Мастер** (10000 - 14999)"
            "\n— **Элита** (15000 - 19999)"
            "\n— **Совершенство** (20000 и больше)"
            f"\n\nУзнать свой уровень репутации можно по команде `{ctx.prefix or self.bot.PREFIX}myrep`"
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815282991668133888/reputation.png")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(UserStats(bot))
