import json
import re
import time
from asyncio import sleep
from datetime import datetime, timedelta
from math import floor
from random import choice, randint
from typing import Optional

from discord import Color, Embed, Invite, Member, Message, PartialInviteGuild
from discord.errors import NotFound
from discord.ext import tasks
from discord.ext.commands import (BadArgument, Cog, Converter, Greedy,
                                  bot_has_permissions, check_any, command,
                                  guild_only, has_any_role, has_permissions)
from discord.utils import find
from jishaku.functools import executor_function
from loguru import logger

from ..db import db
from ..utils.constants import (AUDIT_LOG_CHANNEL, CHASOVIE_CHANNEL,
                               CHASOVOY_ROLE_ID, MODERATION_PUBLIC_CHANNEL,
                               MUTE_ROLE_ID, READ_ROLE_ID)
from ..utils.decorators import listen_for_guilds
from ..utils.utils import (edit_user_reputation, load_commands_from_json,
                           russian_plural)

cmd = load_commands_from_json("moderation")


class BannedUser(Converter):
    async def convert(self, ctx, arg):
        ban_list = await ctx.guild.bans()
        try:
            member_id = int(arg, base=10)
            entity = find(lambda u: u.user.id == member_id, ban_list)
        except ValueError:
            entity = find(lambda u: str(u.user) == arg, ban_list)
        if entity is None:
            raise BadArgument
        return entity


class Moderation(Cog, name='Модерация'):
    def __init__(self, bot):
        self.bot = bot
        self.reading_members = {}
        self.URL_REGEX = r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})'
        self.DISCORD_INVITE_REGEX = r'discord(?:\.com|app\.com|\.gg)[\/invite\/]?(?:[a-zA-Z0-9\-]{2,32})'
        self.EMOJI_REGEX = r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>'
        self.UNICODE_EMOJI_REGEX = r'[\U00010000-\U0010ffff]'
        self.ban_members_with_negative_reputaion.start()
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    @logger.catch
    async def init_vars(self):
        self.moderation_channel = self.bot.get_channel(MODERATION_PUBLIC_CHANNEL)
        self.audit_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
        self.chasovie_channel = self.bot.get_channel(CHASOVIE_CHANNEL)
        self.mute_role = self.bot.guild.get_role(MUTE_ROLE_ID)
        self.read_role = self.bot.guild.get_role(READ_ROLE_ID)
        self.helper_role = self.bot.guild.get_role(CHASOVOY_ROLE_ID)

    def is_member_muted(self, member: Member) -> bool:
        if self.mute_role in member.roles or self.read_role in member.roles:
            return True
        else:
            return False

    @logger.catch
    async def kick_members(self, message, targets, reason):
        for target in targets:
            if message.guild.me.top_role.position < target.top_role.position:
                embed = Embed(
                    title='Неудачная попытка кикнуть участника',
                    description=f"Пользователь {message.author.mention} пытался выгнать {target.mention}\nПричина кика: {reason}",
                    color=Color.red()
                )
                await self.audit_channel.send(embed=embed)
                continue

            await target.kick(reason=reason)

            embed = Embed(
                title="Участник выгнан с сервера",
                color=Color.dark_red(),
                timestamp=datetime.utcnow()
            )

            fields = [
                ("Пользователь", f"{target.display_name} ({target.mention})", False),
                ("Администратор", message.author.mention, False),
                ("Причина", reason.capitalize(), False)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await self.moderation_channel.send(embed=embed)

    @command(name=cmd["kick"]["name"], aliases=cmd["kick"]["aliases"],
            brief=cmd["kick"]["brief"],
            description=cmd["kick"]["description"],
            usage=cmd["kick"]["usage"],
            help=cmd["kick"]["help"],
            hidden=cmd["kick"]["hidden"], enabled=True)
    @bot_has_permissions(kick_members=True)
    @has_permissions(kick_members=True)
    @guild_only()
    @logger.catch
    async def kick_members_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо выгнать с сервера.", delete_after=10)
        else:
            await self.kick_members(ctx.message, targets, reason)


    @logger.catch
    async def ban_members(self, message, targets, delete_days, reason):
        for target in targets:
            if message.guild.me.top_role.position < target.top_role.position:
                embed = Embed(
                    title='Неудачная попытка забанить участника',
                    description=f"Пользователь {message.author.mention} пытался забанить {target.mention}\nПричина бана: {reason}",
                    color=Color.red()
                )
                await self.audit_channel.send(embed=embed)
                continue

            await target.ban(delete_message_days=delete_days, reason=reason)

            embed = Embed(
                title="Участник забанен",
                color=Color.dark_red(),
                timestamp=datetime.utcnow()
            )

            fields = [
                ("Пользователь", f"{target.display_name} ({target.mention})", False),
                ("Администратор", message.author.mention, False),
                ("Причина", reason.capitalize(), False)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await self.moderation_channel.send(embed=embed)

    @command(name=cmd["ban"]["name"], aliases=cmd["ban"]["aliases"],
            brief=cmd["ban"]["brief"],
            description=cmd["ban"]["description"],
            usage=cmd["ban"]["usage"],
            help=cmd["ban"]["help"],
            hidden=cmd["ban"]["hidden"], enabled=True)
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    @guild_only()
    @logger.catch
    async def ban_members_command(self, ctx, targets: Greedy[Member],
                                        delete_days: Optional[int] = 1, *,
                                        reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо забанить.", delete_after=10)
        else:
            await self.ban_members(ctx.message, targets, delete_days, reason)

    @logger.catch
    async def unban_members(self, message, targets, reason):
        for target in targets:
            await message.guild.unban(target, reason=reason)

            embed = Embed(
                title="Пользователь разбанен",
                color=Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_thumbnail(url=target.avatar_url)

            fields = [
                ("Пользователь", f"{target.name} ({target.mention})", False),
                ("Администратор", message.author.mention, False),
                ("Причина", reason.capitalize(), False)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await self.moderation_channel.send(embed=embed)

    @command(name=cmd["unban"]["name"], aliases=cmd["unban"]["aliases"],
            brief=cmd["unban"]["brief"],
            description=cmd["unban"]["description"],
            usage=cmd["unban"]["usage"],
            help=cmd["unban"]["help"],
            hidden=cmd["unban"]["hidden"], enabled=True)
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    @guild_only()
    @logger.catch
    async def unban_members_command(self, ctx, targets: Greedy[BannedUser], *,
                                    reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо разбанить.", delete_after=10)
        else:
            await self.unban_members(ctx.message, targets, reason)


    @logger.catch
    async def mute_members(self, message, targets, time, reason, mute_type):
        def _notification_embed(target: Member, description: str, time_field: tuple) -> Embed:
            embed = Embed(
                title="Участник получил мут",
                description=description,
                color=Color.blue(),
                timestamp=datetime.utcnow()
            )

            fields = [
                ("Причина", reason.capitalize(), True),
                time_field,
                ("Администратор", message.author.mention, True)
            ]

            if mute_type == "mute":
                fields.insert(0, ("Пользователь", f"{target.display_name} ({target.mention})", False))
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            return embed

        def _extend_mute_story(message: Message, target: Member, time: int, reason: str):
            rec = db.fetchone(["mutes_story"], "users_stats", "user_id", target.id)[0]
            rec['user_mute_story'].append(
                {
                    "id": len(rec['user_mute_story']) + 1,
                    "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "mute_time": time,
                    "reason": reason,
                    "moderator": f"{message.author.name} | {message.author.id}"
                }
            )
            db.execute("UPDATE users_stats SET mutes_story = %s WHERE user_id = %s",
                        json.dumps(rec, ensure_ascii=False), target.id)
            db.commit()

        unmutes = []

        for target in targets:
            if self.mute_role not in target.roles:
                if message.guild.me.top_role.position < target.top_role.position or target.id == message.author.id:
                    continue

                role_ids = ",".join([str(r.id) for r in target.roles])
                managed_roles = [r for r in target.roles if r.managed]
                await target.edit(roles=[self.mute_role] + managed_roles)

                if mute_type == "ugol":
                    end_time = datetime.now() + timedelta(minutes=30)
                    embed = _notification_embed(
                        target,
                        f"**Нарушитель `{target.display_name}` ({target.mention}) теперь в углу.**",
                        ("Срок мута", "30 минут", True)
                    )
                    _extend_mute_story(message, target, 1800, reason)
                    await edit_user_reputation(self.bot.pg_pool, target.id, '-', 100)
                    await self.moderation_channel.send(embed=embed)

                elif mute_type == "isolator":
                    end_time = datetime.now() + timedelta(hours=3)
                    embed = _notification_embed(
                        target,
                        f"**Шизоид <:durka:684794973358522426> `{target.display_name}` ({target.mention}) <:durka:684794973358522426> в изоляторе. Кукуха чата в безопасности.**",
                        ("Срок мута", "3 часа", True)
                    )
                    _extend_mute_story(message, target, 10800, reason)
                    await edit_user_reputation(self.bot.pg_pool, target.id, '-', 250)
                    await self.moderation_channel.send(embed=embed)

                elif mute_type == "dungeon":
                    end_time = datetime.now() + timedelta(hours=12)
                    embed = _notification_embed(
                        target,
                        f"**Slave `{target.display_name}` ({target.mention}) отправлен в ♂️ Dungeon ♂️**",
                        ("Срок мута", "12 часов", True)
                    )
                    _extend_mute_story(message, target, 43200, reason)
                    await edit_user_reputation(self.bot.pg_pool, target.id, '-', 500)
                    await self.moderation_channel.send(embed=embed)

                elif mute_type == "gulag":
                    end_time = datetime.now() + timedelta(hours=24)
                    embed = _notification_embed(
                        target,
                        f"**Нарушитель `{target.display_name}` ({target.mention}) отправлен в ГУЛАГ.**",
                        ("Срок мута", "24 часа", True)
                    )
                    _extend_mute_story(message, target, 86400, reason)
                    await edit_user_reputation(self.bot.pg_pool, target.id, '-', 1000)
                    await self.moderation_channel.send(embed=embed)

                else:
                    end_time = datetime.now() + timedelta(hours=float(time)) if time and time.isdigit() else None
                    embed = _notification_embed(target, None,
                            ("Срок мута", f"{time} {russian_plural(int(time),['час','часа','часов'])}" if time and time.isdigit() else "Бессрочно", True)
                    )
                    _extend_mute_story(message, target, int(time) * 3600 if time and time.isdigit() else 0, reason)
                    await edit_user_reputation(self.bot.pg_pool, target.id, '-', floor(5 * (int(time) ^ 2) + 50 * int(time) + 100) if time and time.isdigit() else 0)
                    await self.moderation_channel.send(embed=embed)

                db.insert("mutes", {"user_id": target.id,
                       "role_ids": role_ids,
                       "mute_end_time": end_time})

                if time:
                    unmutes.append(target)

            else:
                embed = Embed(
                    title="Внимание!",
                    color=Color.red(),
                    description=f"Участник `{target.display_name}` ({target.mention}) уже замьючен!"
                )
                await message.channel.send(embed=embed, delete_after=10)
                return

        return unmutes

    @logger.catch
    async def unmute_members(self, ctx, targets, reason: Optional[str] = "Не указана"):
        for target in targets:
            if self.mute_role in target.roles:
                role_ids = db.fetchone(["role_ids"], "mutes", "user_id", target.id)[0]
                roles = [ctx.guild.get_role(int(id_)) for id_ in role_ids.split(",") if len (id_)]

                db.execute("DELETE FROM mutes WHERE user_id = %s", target.id)
                db.commit()

                try:
                    await target.edit(roles=roles)
                except NotFound:
                    continue

                embed = Embed(
                    title="Участник размьючен",
                    color=Color.green(),
                    timestamp=datetime.utcnow()
                )

                fields = [("Пользователь", f"{target.display_name} ({target.mention})", False),
                          ("Причина", reason.capitalize(), False)]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.moderation_channel.send(embed=embed)


    @command(name=cmd["mute"]["name"], aliases=cmd["mute"]["aliases"],
            brief=cmd["mute"]["brief"],
            description=cmd["mute"]["description"],
            usage=cmd["mute"]["usage"],
            help=cmd["mute"]["help"],
            hidden=cmd["mute"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def mute_members_command(self, ctx, targets: Greedy[Member], hours: Optional[str],
                                   *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо замутить.", delete_after=10)
            return

        unmutes = await self.mute_members(ctx.message, targets, hours, reason, "mute")
        if len(unmutes):
            if hours.isdigit():
                await sleep(int(hours)*3600)
                await self.unmute_members(ctx, targets, "Время мута истекло.")


    @command(name=cmd["ugol"]["name"], aliases=cmd["ugol"]["aliases"],
            brief=cmd["ugol"]["brief"],
            description=cmd["ugol"]["description"],
            usage=cmd["ugol"]["usage"],
            help=cmd["ugol"]["help"],
            hidden=cmd["ugol"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def ugol_mute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в угол.", delete_after=10)
            return

        unmutes = await self.mute_members(ctx.message, targets, 0.5, reason, "ugol")
        if len(unmutes):
            await sleep(1800)
            await self.unmute_members(ctx, targets, "Время пребывания в углу истекло.")


    @command(name=cmd["isolator"]["name"], aliases=cmd["isolator"]["aliases"],
        brief=cmd["isolator"]["brief"],
        description=cmd["isolator"]["description"],
        usage=cmd["isolator"]["usage"],
        help=cmd["isolator"]["help"],
        hidden=cmd["isolator"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def isolator_mute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в изолятор.", delete_after=10)
            return

        unmutes = await self.mute_members(ctx.message, targets, 3, reason, "isolator")
        if len(unmutes):
            await sleep(10800)
            await self.unmute_members(ctx, targets, "Время пребывания в изоляторе истекло.")


    @command(name=cmd["dungeon"]["name"], aliases=cmd["dungeon"]["aliases"],
        brief=cmd["dungeon"]["brief"],
        description=cmd["dungeon"]["description"],
        usage=cmd["dungeon"]["usage"],
        help=cmd["dungeon"]["help"],
        hidden=cmd["dungeon"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def dungeon_mute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в ♂️ Dungeon ♂️", delete_after=10)
            return

        unmutes = await self.mute_members(ctx.message, targets, 12, reason, "dungeon")
        if len(unmutes):
            await sleep(43200)
            await self.unmute_members(ctx, targets, "Время пребывания в ♂️ Dungeon ♂️ истекло.")


    @command(name=cmd["gulag"]["name"], aliases=cmd["gulag"]["aliases"],
        brief=cmd["gulag"]["brief"],
        description=cmd["gulag"]["description"],
        usage=cmd["gulag"]["usage"],
        help=cmd["gulag"]["help"],
        hidden=cmd["gulag"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def gulag_mute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в ГУЛАГ.", delete_after=10)
            return

        unmutes = await self.mute_members(ctx.message, targets, 24, reason, "gulag")
        if len(unmutes):
            await sleep(86400)
            await self.unmute_members(ctx, targets, "Время пребывания в ГУЛАГе истекло.")


    @logger.catch
    async def warn_member(self, message, target, warns, reason):
        @executor_function
        def _warn_sleep(sleep_time: int):
            time.sleep(sleep_time)

        def _warn_notification(target: Member, warns: list, time_field: tuple) -> Embed:
            embed = Embed(
                title="Участник получил warn",
                description=f"**Пользователь `{target.display_name}` ({target.mention}) получил warn и был отправлен в мут.**",
                color=Color.red(),
                timestamp=datetime.utcnow()
            )

            fields = [
                ("Причина", reason.capitalize(), True),
                time_field,
                ("Общее количество предупреждений", len(warns), True),
                ("Администратор", message.author.mention, True)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            return embed


        if self.mute_role not in target.roles:
            if message.guild.me.top_role.position < target.top_role.position or target.id == message.author.id:
                return

            if len(warns) == 1:
                await edit_user_reputation(self.bot.pg_pool, target.id, '-', 1000)

            if len(warns) == 2:
                await edit_user_reputation(self.bot.pg_pool, target.id, '-', 2500)

            if len(warns) == 3:
                await edit_user_reputation(self.bot.pg_pool, target.id, '-', 5000)

                if target.id not in self.bot.banlist:
                    self.bot.banlist.append(target.id)
                    db.insert('blacklist', {'user_id':target.id,'reason':'Получил 3 варна'})

            if len(warns) > 3:
                await self.ban_members(message, [target], 1, "Максимум варнов | " + reason)
                return

            params = self._warn_mute_params(len(warns))
            role_ids = ",".join([str(r.id) for r in target.roles])
            managed_roles = [r for r in target.roles if r.managed]
            await target.edit(roles=[self.mute_role] + managed_roles)

            end_time = datetime.now() + timedelta(seconds=params[0])
            embed = _warn_notification(target, warns, ("Срок мута", params[1], True))
            await self.moderation_channel.send(embed=embed)

            db.insert("mutes", {"user_id": target.id,
                "role_ids": role_ids,
                "mute_end_time": end_time})

            await _warn_sleep(sleep_time=params[0])
            ctx = await self.bot.get_context(message)
            await self.unmute_members(ctx, [target], "Срок мута за варн истёк.")
        else:
            embed = Embed(
                title="Внимание!",
                color=Color.red(),
                description=f"Участник `{target.display_name}` ({target.mention}) уже замьючен!"
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

    def _warn_mute_params(self, warns_len: int) -> tuple:
        if warns_len == 1:
            return (21600, "6 часов")
        elif warns_len == 2:
            return (43200, "12 часов")
        elif warns_len == 3:
            return (86400, "24 часа")
        elif warns_len > 3:
            return (0, "ban")

    @command(name=cmd["warn"]["name"], aliases=cmd["warn"]["aliases"],
        brief=cmd["warn"]["brief"],
        description=cmd["warn"]["description"],
        usage=cmd["warn"]["usage"],
        help=cmd["warn"]["help"],
        hidden=cmd["warn"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def warn_mute_command(self, ctx, target: Optional[Member], *, reason: Optional[str] = "Не указана"):
        await ctx.message.delete()

        if not target:
            await ctx.send(f"{ctx.author.mention}, укажите пользователя, которому необходимо выдать варн.", delete_after=10)
            return

        if self.mute_role not in target.roles:
            rec = db.fetchone(["warns_story"], "users_stats", "user_id", target.id)[0]
            rec['user_warn_story'].append(
                {
                    "id": len(rec['user_warn_story']) + 1,
                    "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "mute_time": self._warn_mute_params(len(rec['user_warn_story'])+1)[0],
                    "reason": reason,
                    "moderator": f"{ctx.author.name} | {ctx.author.id}"
                }
            )
            db.execute("UPDATE users_stats SET warns_story = %s WHERE user_id = %s",
                        json.dumps(rec, ensure_ascii=False), target.id)
            db.commit()
            await self.warn_member(ctx.message, target, rec['user_warn_story'], reason)
        else:
            embed = Embed(
                title="Внимание!",
                color=Color.red(),
                description=f"Участник `{target.display_name}` ({target.mention}) уже замьючен!"
            )
            await ctx.send(embed=embed, delete_after=10)


    @command(name=cmd["unmute"]["name"], aliases=cmd["unmute"]["aliases"],
            brief=cmd["unmute"]["brief"],
            description=cmd["unmute"]["description"],
            usage=cmd["unmute"]["usage"],
            help=cmd["unmute"]["help"],
            hidden=cmd["unmute"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def unmute_members_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Мут снят вручную администратором."):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо размутить.", delete_after=10)
            return

        await self.unmute_members(ctx, targets, reason)


    @logger.catch
    async def readrole_members(self, ctx, targets):
      for target in targets:
        if self.read_role not in target.roles:
            if ctx.message.guild.me.top_role.position < target.top_role.position or target.id == ctx.message.author.id:
                continue

            self.reading_members[target.id] = target.roles
            await target.edit(roles=[self.read_role] + [r for r in target.roles if r.managed])

            embed = Embed(
                title="Правила нужно знать!",
                color=Color.orange(),
                timestamp=datetime.utcnow(),
                description=f'**Пользователь `{target.display_name}` ({target.mention}) отправлен изучать правила сервера и описание ролей.**'
            )

            fields = [('Администратор', ctx.author.mention, True),
                      ('Срок', '5 минут', True)]
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            await edit_user_reputation(self.bot.pg_pool, target.id, '-', 100)
            await self.moderation_channel.send(embed=embed)

    @command(name=cmd["readrole"]["name"], aliases=cmd["readrole"]["aliases"],
            brief=cmd["readrole"]["brief"],
            description=cmd["readrole"]["description"],
            usage=cmd["readrole"]["usage"],
            help=cmd["readrole"]["help"],
            hidden=cmd["readrole"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def readrole_command(self, ctx, targets: Greedy[Member]):
        await ctx.message.delete()
        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить читать правила.", delete_after=10)
            return

        await self.readrole_members(ctx, targets)
        await sleep(300)
        await self.remove_readrole_members(ctx, targets)


    @logger.catch
    async def remove_readrole_members(self, ctx, targets):
      for target in targets:
        if self.read_role in target.roles:
            roles = self.reading_members.get(target.id, ctx.guild.default_role)
            try:
                await target.edit(roles=roles)
            except NotFound:
                continue
            del self.reading_members[target.id]

            embed = Embed(
                title="Изучение правил завершено.",
                color=Color.green(),
                timestamp=datetime.utcnow(),
                description=f'**Пользователь `{target.display_name}` ({target.mention}) завершил изучение правил и описания ролей сервера.**'
            )
            await self.moderation_channel.send(embed=embed)

    @command(name=cmd["removereadrole"]["name"], aliases=cmd["removereadrole"]["aliases"],
            brief=cmd["removereadrole"]["brief"],
            description=cmd["removereadrole"]["description"],
            usage=cmd["removereadrole"]["usage"],
            help=cmd["removereadrole"]["help"],
            hidden=cmd["removereadrole"]["hidden"], enabled=True)
    @bot_has_permissions(manage_roles=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def remove_readrole_command(self, ctx, targets: Greedy[Member]):
        await ctx.message.delete()
        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которым необходимо завершить изучение правил.", delete_after=10)
            return

        await self.remove_readrole_members(ctx, targets)


    @command(name=cmd["purge"]["name"], aliases=cmd["purge"]["aliases"],
            brief=cmd["purge"]["brief"],
            description=cmd["purge"]["description"],
            usage=cmd["purge"]["usage"],
            help=cmd["purge"]["help"],
            hidden=cmd["purge"]["hidden"], enabled=True)
    @bot_has_permissions(manage_messages=True)
    @has_permissions(administrator=True)
    @guild_only()
    @logger.catch
    async def clear_messages_command(self, ctx, targets: Greedy[Member], limit: Optional[int] = 1):
        def _check(message):
            return not len(targets) or message.author in targets

        def decrease_message_counter(users: dict):
            for key, value in users.items():
                rec = db.fetchone(["messages_count"], "users_stats", "user_id", key)[0]
                db.execute("UPDATE users_stats SET messages_count = %s WHERE user_id = %s",
                            rec - value, key)
                db.commit()

        users = {}

        if not targets:
            async for message in ctx.channel.history(limit=limit):
                if message.author not in users:
                    users[message.author.id] = 0

            async for message in ctx.channel.history(limit=limit):
                users[message.author.id] += 1

            deleted = await ctx.channel.purge(limit=limit+1)
            if ctx.channel.id in self.bot.channels_with_message_counting:
                decrease_message_counter(users)

            embed = Embed(
                title='purge command invoked',
                color=Color.random(),
                description=f'Удалено сообщений: {len(deleted)}\n' \
                            f'Удаление выполнено пользователем: {ctx.author.mention}\n' \
                            f'Канал: {ctx.channel.mention}')
            await self.bot.logs_channel.send(embed=embed)

        else:
            deleted = await ctx.channel.purge(limit=limit+1, check=_check)
            msg_author_ids = [message.author.id for message in deleted]
            for entry in msg_author_ids:
                users[entry] = msg_author_ids.count(entry)

            if ctx.channel.id in self.bot.channels_with_message_counting:
                decrease_message_counter(users)

            embed = Embed(
                title='purge (with targets) command invoked',
                color=Color.random(),
                description=f'Удалено сообщений: {len(deleted)}\n' \
                            f'Удаление выполнено пользователем: {ctx.author.mention}\n' \
                            f'Канал: {ctx.channel.mention}')
            await self.bot.logs_channel.send(embed=embed)


    async def hat_replies(self, ctx, target, lost_rep):
        replies = (
            f'{target.mention} получил по шапке.',
            f'{target.mention}, для мута рановато, но по шапке ты получил.',
            f'{target.mention}, дружище, как с шапкой дела обстоят?',
            f'{target.mention}, шапка в порядке?',
            f'{target.mention}, проверь шапку.',
            f'{target.mention}, так и до мута недалеко.',
            f'{target.mention}, пока ты только по шапке получил, но скоро и мут заработаешь.',
        )
        reply = choice(replies) + f"\nТвоя репутация была уменьшена на **{lost_rep}** {russian_plural(lost_rep, ['единицу','единицы','единиц'])}."
        await ctx.send(reply)

    @command(name=cmd["hat"]["name"], aliases=cmd["hat"]["aliases"],
            brief=cmd["hat"]["brief"],
            description=cmd["hat"]["description"],
            usage=cmd["hat"]["usage"],
            help=cmd["hat"]["help"],
            hidden=cmd["hat"]["hidden"], enabled=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def hat_command(self, ctx, targets: Greedy[Member]):
        if not targets:
            return

        for target in targets:
            lost_rep = randint(50, 150)
            await edit_user_reputation(self.bot.pg_pool, target.id, '-', lost_rep)
            await self.hat_replies(ctx, target, lost_rep)


    def find_discord_invites(self, message: Message) -> bool:
        regex = re.compile(self.DISCORD_INVITE_REGEX)
        invites = regex.findall(message.clean_content)

        return True if invites else False

    @Cog.listener('on_message')
    @listen_for_guilds()
    async def moderation_on_message_event(self, message):
        ### Find discord invites in message content
        if self.find_discord_invites(message):
            regex = re.compile(self.DISCORD_INVITE_REGEX)
            try:
                guild_invite = await self.bot.fetch_invite(url=regex.search(message.clean_content).group(0))
            except NotFound:
                return

            if message.author.guild_permissions.administrator or self.helper_role in message.author.roles:
                pass
            else:
                if isinstance(guild_invite, Invite):
                    if guild_invite.guild.id != self.bot.guild.id:
                        await message.delete()
                        return await message.author.ban(reason="Автомодерация: Ссылки и приглашения")

                elif isinstance(guild_invite, PartialInviteGuild):
                    if guild_invite.id != self.bot.guild.id:
                        await message.delete()
                        return await message.author.ban(reason="Автомодерация: Ссылки и приглашения")

        ### Emoji anti-spam
        if message.content and not message.author.bot:
            emoji = re.findall(self.EMOJI_REGEX, message.content)
            unicode_emoji = re.findall(self.UNICODE_EMOJI_REGEX, message.content)
            if (len(emoji) + len(unicode_emoji)) > 7:
                if message.author.guild_permissions.administrator or self.helper_role in message.author.roles:
                    pass
                else:
                    await message.delete()
                    await message.channel.send(f'{message.author.mention}, побереги свои эмоции!', delete_after=15)

    ### Anti-Scam logic
    def scam_notifier(self, message: Message) -> Embed:
        embed = Embed(
            title='❗ Подозрительное сообщение.',
            color=Color.red(),
            timestamp=datetime.utcnow(),
            description=f"Обнаружена фишинговая ссылка, сообщение удалено автоматически."
        ).set_thumbnail(url=message.author.avatar_url)
        fields = [
                ('Автор сообщения', message.author, True),
                ('ID автора', message.author.id, True),
                ('Канал', message.channel.mention, True),
                ('Сообщение', message.clean_content, False)
        ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        return embed

    async def delete_scam_message(self, message: Message) -> None:
        await message.delete()
        await message.author.add_roles(self.mute_role)
        embed = self.scam_notifier(message)
        await self.chasovie_channel.send(embed=embed)

    @Cog.listener('on_message')
    @listen_for_guilds()
    async def anti_scam_on_message_event(self, message):
        if message.author.guild_permissions.administrator or self.helper_role in message.author.roles:
            return

        if not (re.compile(self.URL_REGEX).search(message.clean_content)):
            return

        if 'steamcommunity.com' not in message.clean_content:
            if 'partner=' and 'token=' in message.clean_content:
                await self.delete_scam_message(message)
                return

        if 'discord.com' and 'steamcommunity.com' not in message.clean_content:
            words = ('gift', 'nitro', 'steam')
            if any(word in message.clean_content for word in words):
                await self.delete_scam_message(message)
                return

    ### Tasks
    @tasks.loop(hours=6)
    async def ban_members_with_negative_reputaion(self):
        msg = await self.bot.guild.get_channel(604621910386671616).fetch_message(861627953736843294)
        for member in self.bot.guild.members:
            try:
                rep = await self.bot.pg_pool.fetchval(
                    'SELECT rep_rank FROM users_stats WHERE user_id = $1', member.id)
                if rep <= -1000:
                    await self.ban_members(msg, [member], 0, 'Критический уровень репутации (<= -1000).')
            except:
                continue

    @ban_members_with_negative_reputaion.before_loop
    async def before_ban_negative_members(self):
        await self.bot.wait_until_ready()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.moderation_channel = self.bot.get_channel(MODERATION_PUBLIC_CHANNEL)
            self.audit_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
            self.chasovie_channel = self.bot.get_channel(CHASOVIE_CHANNEL)
            self.mute_role = self.bot.guild.get_role(MUTE_ROLE_ID)
            self.read_role = self.bot.guild.get_role(READ_ROLE_ID)
            self.helper_role = self.bot.guild.get_role(CHASOVOY_ROLE_ID)
            self.bot.cogs_ready.ready_up("moderation")


def setup(bot):
    bot.add_cog(Moderation(bot))
