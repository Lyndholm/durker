from discord import Member, Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command, guild_only
from datetime import datetime, timedelta
from asyncio.exceptions import TimeoutError

from ..db import db
from ..utils.utils import load_commands_from_json


cmd = load_commands_from_json("user_stats")


class UserStats(Cog):
    def __init__(self, bot):
        self.bot = bot


    @command(name=cmd["profile"]["name"], aliases=cmd["profile"]["aliases"], 
        brief=cmd["profile"]["brief"],
        description=cmd["profile"]["description"],
        usage=cmd["profile"]["usage"],
        help=cmd["profile"]["help"],
        hidden=cmd["profile"]["hidden"], enabled=True)
    @guild_only()
    async def fetch_member_profile_command(self, ctx, member: Member = None):
        if member:
            is_member_profile_public = db.fetchone(["is_profile_public"], "users_info", "user_id", member.id)
            if is_member_profile_public[0] is False:
                embed = Embed(title=":exclamation: Внимание!", color=Color.red(), timestamp=datetime.utcnow(),
                            description=f"Профиль участника **{member.display_name}** ({member.mention}) скрыт. Просматривать его может только хозяин.")
                embed.set_footer(text=f"Запрос от: {ctx.author}")
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

        total_mute_time = sum(moderation_stats[0]['user_mute_story'][i]['mute_time'] for i in range(len(moderation_stats[0]['user_mute_story'])))

        vbucks_count = sum(purchases[0]['vbucks_purchases'][i]['price'] for i in range(len(purchases[0]['vbucks_purchases'])))

        realMoney = sum(purchases[0]['realMoney_purchases'][i]['price_in_rubles'] for i in range(len(purchases[0]['realMoney_purchases'])))

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
                                                                                            "Сделать это можно по команде `_setbio <ваша биография>`",
                            inline=False)

        embed.add_field(name=':calendar: Аккаунт создан:', value=target.created_at.strftime("%d.%m.%Y %H:%M"),
                        inline=True)

        embed.add_field(name=':calendar_spiral: Дата захода на сервер:',
                        value=target.joined_at.strftime("%d.%m.%Y %H:%M"), inline=True)

        embed.add_field(name=':calendar_spiral: Количество дней на сервере:',
                        value=(datetime.now() - target.joined_at).days, inline=True)

        embed.add_field(name=f":grinning: Роли ({len(target.roles) - 1})",
                        value=" ".join([role.mention for role in target.roles[1:]]), inline=True)

        embed.add_field(name=":sunglasses: Наивысшая роль:", value=target.top_role.mention, inline=True)

        embed.add_field(name=":military_medal: Количество достижений:", value=len(user_stats[0]["user_achievements_list"]), inline=True)

        embed.add_field(name=":envelope: Количество сообщений:", value=user_stats[1], inline=True)

        embed.add_field(name=":green_circle: Уровень:", value=leveling[0], inline=True)

        embed.add_field(name=":green_circle: XP:", value=leveling[1], inline=True)

        embed.add_field(name=":face_with_monocle: Репутация:", value=user_stats[2], inline=True)

        embed.add_field(name=":thumbsdown: Потеряно репутации:", value=user_stats[4], inline=True)

        embed.add_field(name="<:durka:745936793148588083>  Получено путёвок в дурку:", value=durka_stats[0],
                        inline=True)

        embed.add_field(name=":face_with_symbols_over_mouth: Количество триггеров мат-фильтра:", value=len(moderation_stats[2]["user_profanity_story"]),
                        inline=True)

        embed.add_field(name=":moneybag:  Потрачено в-баксов с тегом FNFUN:",
                        value=vbucks_count, inline=True)

        if len(purchases[0]['vbucks_purchases']) > 0:

            embed.add_field(name=":slight_smile: Количество покупок с тегом FNFUN:",
                            value=len(purchases[0]['vbucks_purchases']), inline=True)

            embed.add_field(name=":date: Дата последней покупки с тегом FNFUN:",
                            value=purchases[0]['vbucks_purchases'][-1]['date'].strftime("%d.%m.%Y %H:%M"))

        if len(purchases[0]['realMoney_purchases']) > 0:
            embed.add_field(name=":money_with_wings: Поддержка автора в рублях:",
                            value=realMoney, inline=True)

        if kapitalist not in target.roles:
            embed.add_field(name=f":moneybag: До роли `{kapitalist.name}` осталось: ",
                            value=f"{int(10000 - vbucks_count)} в-баксов", inline=True)

        if magnat not in target.roles and kapitalist in target.roles:
            embed.add_field(name=f":moneybag: До роли `{magnat.name}` осталось: ",
                            value=f"{int(25000 - vbucks_count)} в-баксов", inline=True)

        embed.add_field(name=":speaker: Время, проведенное в голосовых каналах:",
                        value=timedelta(seconds=user_stats[4]), inline=True)

        embed.add_field(name=":coin: FUN-коинов:", value=casino[0] + casino[1], inline=True)

        embed.add_field(name=":warning: Количество предупреждений:", value=len(moderation_stats[1]["user_warn_story"]), inline=True)

        embed.add_field(name=":speak_no_evil: Количество мутов:", value=len(moderation_stats[0]["user_mute_story"]), inline=True)

        embed.add_field(name=":timer: Время, проведенное в муте:", value=timedelta(seconds=total_mute_time),
                        inline=True)

        embed.add_field(name=":zap: Бустер сервера:", value='Да' if bool(target.premium_since) else 'Нет',
                        inline=True)

        if member:
            embed.set_footer(text=f"Запрос от: {ctx.author}")
        else:
            embed.set_footer(text="Карточка сформирована " + datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

        await ctx.send(embed=embed)

    
    @command(name=cmd["setbio"]["name"], aliases=cmd["setbio"]["aliases"], 
        brief=cmd["setbio"]["brief"],
        description=cmd["setbio"]["description"],
        usage=cmd["setbio"]["usage"],
        help=cmd["setbio"]["help"],
        hidden=cmd["setbio"]["hidden"], enabled=True)
    @guild_only()
    async def setbio_command(self, ctx, *, bio: str = None):
        if bio is None:
            db_bio = db.fetchone(["brief_biography"], "users_info", "user_id", ctx.author.id)[0]

            if db_bio is not None:
                    r_list = ['🟩', '🟥']
                    embed = Embed(title=':exclamation: Внимание!', color = Color.red(), timestamp = datetime.utcnow(),
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
                embed = Embed(title=':exclamation: Внимание!', color = Color.red(),
                            description = f"{ctx.author.mention}, пожалуйста, напишите Вашу биографию. Учитывайте, что максимальная длина текста — **255** символов.")
                await ctx.send(embed=embed)

        elif len(bio.strip()) > 255:
            embed = Embed(title=':exclamation: Внимание!', color = Color.red(),
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


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("user_stats")


def setup(bot):
    bot.add_cog(UserStats(bot))
