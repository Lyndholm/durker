import ast
from asyncio.exceptions import TimeoutError
from datetime import datetime, timedelta
from typing import Optional
from random import randint
from discord import Color, Embed, Member
from discord.ext.commands import BucketType, Cog, command, cooldown, guild_only
from discord.utils import get
from loguru import logger

from ..db import db
from ..utils.checks import is_channel
from ..utils.constants import STATS_CHANNEL
from ..utils.utils import (get_context_target, joined_date,
                           load_commands_from_json, russian_plural)

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
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @logger.catch
    async def fetch_member_profile_command(self, ctx, *, member: Optional[Member]):
        target = await get_context_target(self.bot.pg_pool, ctx, member)
        if not target:
            return

        biography = await self.bot.pg_pool.fetchval(
            'SELECT brief_biography FROM users_info WHERE user_id = $1', target.id)

        user_stats = await self.bot.db.fetchone(
            ['achievements_list', 'invoice_time'],
            'users_stats', 'user_id',
            target.id)

        durka_stats = await self.bot.db.fetchone(
            ['received_durka_calls'],
            'durka_stats', 'user_id',
            target.id)

        moderation_stats = await self.bot.db.fetchone(
            ['mutes_story', 'warns_story', 'profanity_triggers'],
            'users_stats', 'user_id',
            target.id)

        mutes = ast.literal_eval(moderation_stats[0])
        mutes = mutes['user_mute_story']
        mute_time = sum(
            mutes[i]['mute_time']
            for i in range(len(mutes))
        )
        warns = ast.literal_eval(moderation_stats[1])
        warns = warns['user_warn_story']
        warn_time = sum(
            warns[i]['mute_time']
            for i in range(len(warns))
        )
        total_mute_time = mute_time + warn_time
        joined = await joined_date(self.bot.pg_pool, target)
        embed = Embed(color=target.color)
        embed.set_author(name=target.display_name, icon_url=target.avatar_url)
        embed.set_thumbnail(url=target.avatar_url)

        if member:
            if biography:
                value = biography
            else:
                value = 'Пользователь не указал свою биографию.'
            embed.add_field(name='📝 О пользователе:',
                            value=value, inline=False)
        else:
            if biography:
                value = biography
            else:
                value = f'No biography moment'
            embed.add_field(name='📝 О себе:', value=value, inline=False)

        embed.add_field(name='📆 Аккаунт создан:',
                        value='Vchera (eto tochno)',
                        inline=True)

        embed.add_field(name='📆 Дата захода на сервер:',
                        value='Zavtra (toje tochno)',
                        inline=True)

        embed.add_field(name='📆 Количество дней на сервере:',
                        value=randint(-9999999, -1),
                        inline=True)

        if len(target.roles) > 1:
            embed.add_field(name=f'😀 Роли ({randint(1, 9999999)})',
                            value=ctx.guild.default_role.mention,
                            inline=False)
        else:
            embed.add_field(name=f'😀 Роли ({randint(1, 9999999)})',
                            value=ctx.guild.default_role.mention,
                            inline=False)

        embed.add_field(name='😎 Наивысшая роль:',
                        value='BAN ROLE',
                        inline=True)

        embed.add_field(name='🎖️ Количество достижений:',
                        value=randint(1, 9999999),
                        inline=True)

        embed.add_field(name="⚡ Бустер сервера:",
                        value='May bit',
                        inline=True)

        embed.add_field(name="<:durka:684794973358522426>  Получено путёвок в дурку:",
                        value=randint(1, 9999999),
                        inline=True)

        embed.add_field(name="🤬 Количество триггеров мат-фильтра:",
                        value=randint(100, 9999999),
                        inline=True)

        embed.add_field(name="🔈 Время, проведённое в голосовых каналах:",
                        value='pchel, no voice time for u',
                        inline=True)

        embed.add_field(name="⚠️ Количество предупреждений:",
                        value='3 (skoro ban (no eto ne tochno))',
                        inline=True)

        embed.add_field(name="🙊 Количество мутов:",
                        value=randint(1, 99999),
                        inline=True)

        embed.add_field(name="⏲️ Время, проведённое в муте:",
                        value='∞',
                        inline=True)

        if member:
            embed.timestamp = datetime.utcnow()
            embed.set_footer(
                text=f"Запрос от: {ctx.author}", icon_url=ctx.author.avatar_url)
        else:
            embed.set_footer(text='Данные актуальны на Zavtra')

        await ctx.reply(embed=embed, mention_author=False)

    @command(name=cmd["setbio"]["name"], aliases=cmd["setbio"]["aliases"],
        brief=cmd["setbio"]["brief"],
        description=cmd["setbio"]["description"],
        usage=cmd["setbio"]["usage"],
        help=cmd["setbio"]["help"],
        hidden=cmd["setbio"]["hidden"], enabled=True)
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @cooldown(cmd["setbio"]["cooldown_rate"], cmd["setbio"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def setbio_command(self, ctx, *, bio: str = None):
        if bio is None:
            db_bio = db.fetchone(["brief_biography"], "users_info", "user_id", ctx.author.id)[0]

            if db_bio is not None:
                    r_list = ['🟩', '🟥']
                    embed = Embed(title='❗ Внимание!', color = Color.red(), timestamp = datetime.utcnow(),
                            description = f"{ctx.author.mention}, ваша биография уже написана. Вы желаете её сбросить?\n\n"
                            "🟩 — нет.\n\n🟥 — да, сбросить мою биографию.")
                    msg = await ctx.reply(embed=embed, mention_author=False)

                    for r in r_list:
                        await msg.add_reaction(r)
                    try:
                        react, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=lambda react,
                                    user: user == ctx.author and react.message.channel == ctx.channel
                                    and react.emoji in r_list)

                    except TimeoutError:
                        await msg.clear_reactions()
                        embed = Embed(title="Время вышло", color=Color.magenta(), timestamp=datetime.utcnow(),
                                    description=f"{ctx.author.mention}, время на выбор вышло, действие отменено.")
                        await msg.reply(embed=embed)
                        return


                    else:
                        if str(react.emoji) == r_list[0]:
                            embed = Embed(title=':white_check_mark: Действие отменено', color = Color.green(), timestamp = datetime.utcnow(),
                                        description = f"Сброс биографии отменён.\n"
                                        "Если вы хотите изменить биографию, введите команду ещё раз, указав необходимый текст.\n"
                                        "**Пример:** +setbio Это моя новая биография!")
                            await ctx.reply(embed=embed, mention_author=False)
                            ctx.command.reset_cooldown(ctx)
                            return

                        if str(react.emoji) == r_list[1]:
                            db.execute("UPDATE users_info SET brief_biography = %s WHERE user_id = %s",
                            None, ctx.author.id)
                            db.commit()

                            embed = Embed(title=':white_check_mark: Выполнено!', color = Color.green(), timestamp = datetime.utcnow(),
                                        description = f"Биография пользователя **{ctx.author.display_name}** сброшена.")
                            await ctx.reply(embed=embed, mention_author=False)
                            ctx.command.reset_cooldown(ctx)
                            return
            else:
                embed = Embed(title='❗ Внимание!', color = Color.red(),
                            description = f"{ctx.author.mention}, пожалуйста, напишите Вашу биографию. Учитывайте, что максимальная длина текста — **255** символов.")
                await ctx.reply(embed=embed, mention_author=False)
                ctx.command.reset_cooldown(ctx)

        elif len(bio.strip()) > 255:
            embed = Embed(title='❗ Внимание!', color = Color.red(),
                        description = f"{ctx.author.mention}, пожалуйста, уменьшите длину Вашей биографии. Вы превысили допустимый объём на {len(bio) - 255} символ(-а).")
            await ctx.reply(embed=embed, mention_author=False)

        else:
            bio = bio.replace('`', '`­')
            try:
                db.execute("UPDATE users_info SET brief_biography = %s WHERE user_id = %s",
                            bio.strip(), ctx.author.id)
                db.commit()

                embed = Embed(title=':white_check_mark: Выполнено!', color = Color.green(), timestamp = datetime.utcnow(),
                            description = f"Поздравляем, **{ctx.author.display_name}**! Ваша биография обновлена:\n```{bio}```")
                await ctx.reply(embed=embed, mention_author=False)

            except Exception as e:
                raise e


    @command(name=cmd["setprivacy"]["name"], aliases=cmd["setprivacy"]["aliases"],
        brief=cmd["setprivacy"]["brief"],
        description=cmd["setprivacy"]["description"],
        usage=cmd["setprivacy"]["usage"],
        help=cmd["setprivacy"]["help"],
        hidden=cmd["setprivacy"]["hidden"], enabled=True)
    @is_channel(STATS_CHANNEL)
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
        msg = await ctx.reply(embed=embed, mention_author=False)

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
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @logger.catch
    async def amount_command(self, ctx, *, member: Optional[Member]):
        target = await get_context_target(self.bot.pg_pool, ctx, member)
        if not target:
            return

        activity_role_1 = get(ctx.guild.roles, name='Работяга')
        activity_role_2 = get(ctx.guild.roles, name='Олд')
        activity_role_3 = get(ctx.guild.roles, name='Капитан')
        activity_role_4 = get(ctx.guild.roles, name='Ветеран')
        joined = await joined_date(self.bot.pg_pool, target)
        msg_counter = randint(0, 999999999)
        rnd = randint(1, 500)

        desc = f'Количество сообщений: **{msg_counter}**'

        embed = Embed(color=target.color)
        embed.set_author(name=target.display_name, icon_url=target.avatar_url)
        embed.set_thumbnail(url="https://antislang.ru/wp-content/uploads/bruh-4.jpg")

        if activity_role_1 not in target.roles:
            desc += f"\n\nДо роли {activity_role_1.mention} нужно сделать **{750-rnd}** {russian_plural(750-rnd,['компиляцию','компиляции','компиляций'])} PYTHON BRUH EDITION 2.28"

        elif activity_role_2 not in target.roles:
            desc += f"\n\nДо роли {activity_role_2.mention} нужно сделать **{3_500-rnd}** {russian_plural(3_500-rnd,['интерпретацию','интерпретации','интерпретаций'])} c hashtag"

        elif activity_role_3 not in target.roles:
            desc += f"\n\nДо роли {activity_role_3.mention} нужно сделать **{10_000-rnd}** {russian_plural(10_000-rnd,['сборку','сборки','сборок'])} Docker контейнеров"

        elif activity_role_4 not in target.roles:
            desc += f"\n\nДо роли {activity_role_4.mention} нужно сделать **{25_000-rnd}** {russian_plural(25_000-rnd,['деплой','деплоя','деплоев'])} в Kubernetes"

        embed.description = desc
        await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["rep"]["name"], aliases=cmd["rep"]["aliases"],
        brief=cmd["rep"]["brief"],
        description=cmd["rep"]["description"],
        usage=cmd["rep"]["usage"],
        help=cmd["rep"]["help"],
        hidden=cmd["rep"]["hidden"], enabled=True)
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @logger.catch
    async def reputation_command(self, ctx, *, member: Optional[Member]):
        target = await get_context_target(self.bot.pg_pool, ctx, member)
        if not target:
            return

        rep_rank, lost_rep = randint(1, 9999999), randint(1, 9999999)
        desc = f'Количество очков репутации: **{rep_rank}**\n' \
               f'Потеряно очков репутации: **{lost_rep}**'

        embed = Embed(color=target.color)
        embed.set_author(name=target.display_name, icon_url=target.avatar_url)
        if rep_rank <= 0:
            desc += f"\n\nРанг: **Отсутствует**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298656462700634/no_rank.png")
        elif 1 <= rep_rank <= 1_499:
            desc += f"\n\nРанг: **Бронза**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298685498949662/rank_bronze.png")
        elif 1_500 <= rep_rank <= 2_999:
            desc += f"\n\nРанг: **Серебро**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298847705792522/rank_silver.png")
        elif 3_000 <= rep_rank <= 4_499:
            desc += f"\n\nРанг: **Золото**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298881285652550/rank_gold.png")
        elif 4_500 <= rep_rank <= 6_999:
            desc += f"\n\nРанг: **Платина**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298909161259028/rank_platinum.png")
        elif 7_000 <= rep_rank <= 9_999:
            desc += f"\n\nРанг: **Алмаз**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298936734220349/rank_diamond.png")
        elif 10_000 <= rep_rank <= 14_999:
            desc += f"\n\nРанг: **Мастер**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298973065543680/rank_master.png")
        elif 15_000 <= rep_rank <= 19_999:
            desc += f"\n\nРанг: **Элита**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815298996959445042/rank_grandmaster.png")
        elif rep_rank > 20_000:
            desc += f"\n\nРанг: **Совершенство**"
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815299017948004402/rank_perfection.png")

        embed.description = desc
        await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["repinfo"]["name"], aliases=cmd["repinfo"]["aliases"],
        brief=cmd["repinfo"]["brief"],
        description=cmd["repinfo"]["description"],
        usage=cmd["repinfo"]["usage"],
        help=cmd["repinfo"]["help"],
        hidden=cmd["repinfo"]["hidden"], enabled=True)
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
            f"\n\nУзнать свой уровень репутации можно по команде `{ctx.prefix or self.bot.PREFIX[0]}rep`"
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/774698479981297664/815282991668133888/reputation.png")
        await ctx.reply(embed=embed, mention_author=False)


def setup(bot):
    bot.add_cog(UserStats(bot))
