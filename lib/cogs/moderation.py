import enum
import json
import re
from asyncio import sleep
from datetime import datetime, timedelta
from os import getenv
from random import choice, randint
from typing import Optional

import aiohttp
from discord import Color, Embed, Invite, Member, Message, PartialInviteGuild
from discord.errors import NotFound
from discord.ext import tasks
from discord.ext.commands import (BadArgument, Cog, Converter, Greedy,
                                  bot_has_permissions, check_any, command,
                                  guild_only, has_any_role, has_permissions)
from discord.utils import find
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


class MuteTypes(enum.Enum):
    timeout   = 0
    ugol      = 1
    isolator  = 2
    dungeon   = 3
    gulag     = 4


class Moderation(Cog, name='Модерация'):
    def __init__(self, bot):
        self.bot = bot
        self.reading_members = {}
        self.URL_REGEX = r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})'
        self.DISCORD_INVITE_REGEX = r'discord(?:\.com|app\.com|\.gg)[\/invite\/]?(?:[a-zA-Z0-9\-]{2,32})'
        self.EMOJI_REGEX = r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>'
        self.UNICODE_EMOJI_REGEX = r'[\U00010000-\U0010ffff]'
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
                ("Причина", reason, False)
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
    async def kick_members_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = 'Не указана'):
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
                ("Причина", reason, False)
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
                                        reason: Optional[str] = 'Не указана'):
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
                ("Причина", reason, False)
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
                                    reason: Optional[str] = 'Не указана'):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо разбанить.", delete_after=10)
        else:
            await self.unban_members(ctx.message, targets, reason)


    async def put_in_timeout(
        self,
        ctx,
        member: Member = None,
        seconds: Optional[int] = 0
    ) -> None:
        if not member:
            await ctx.reply('Укажите пользователя.', delete_after=15)
            return

        if seconds > 2_592_000:
            await ctx.reply('Время не может превышать 30 дней.', delete_after=15)
            return

        url = f"https://discord.com/api/v9/guilds/{ctx.guild.id}/members/{member.id}"
        headers = {
            "User-Agent": "Durker",
            "Authorization": f"Bot {getenv('DISCORD_BOT_TOKEN')}",
            "Content-Type": "application/json",
        }
        data = {
            "communication_disabled_until": (datetime.utcnow() + timedelta(seconds=seconds)).isoformat() if seconds else None
        }

        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=data) as r:
                if not 200 <= r.status <= 299:
                    await ctx.send('Что-то пошло не так, действие отменено.', delete_after=60)


    @logger.catch
    async def mute_members(
        self,
        ctx,
        targets: Greedy[Member],
        seconds: Optional[int] = 60,
        reason: Optional[str] = 'Не указана',
        mute_type: MuteTypes = MuteTypes.timeout
    ):
        def _notification_embed(target: Member, description: str, time_field: tuple) -> Embed:
            embed = Embed(
                title="Участник получил мут",
                color=Color.blue(),
                timestamp=datetime.utcnow()
            )
            if description: embed.description = description

            fields = [
                ("Причина", reason, True),
                time_field,
                ("Администратор", ctx.author.mention, True)
            ]

            if mute_type is MuteTypes.timeout:
                fields.insert(0, ("Пользователь", f"{target.display_name} ({target.mention})", False))
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            return embed

        def _extend_mute_story(message: Message, target: Member, seconds: int, reason: str):
            rec = db.fetchone(["mutes_story"], "users_stats", "user_id", target.id)[0]
            rec['user_mute_story'].append(
                {
                    "id": len(rec['user_mute_story']) + 1,
                    "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "mute_type": str(mute_type),
                    "mute_time": seconds,
                    "reason": reason,
                    "moderator": f"{message.author.name} | {message.author.id}"
                }
            )
            db.execute("UPDATE users_stats SET mutes_story = %s WHERE user_id = %s",
                        json.dumps(rec, ensure_ascii=False), target.id)
            db.commit()

        for target in targets:
            if ctx.guild.me.top_role.position < target.top_role.position or target.id == ctx.author.id:
                continue

            if mute_type is MuteTypes.ugol:
                MINUS_REP = 100
                embed = _notification_embed(
                    target,
                    f"**Нарушитель `{target.display_name}` ({target.mention}) теперь в углу.**",
                    ("Срок мута", "30 минут", True)
                )

            elif mute_type is MuteTypes.isolator:
                MINUS_REP = 250
                embed = _notification_embed(
                    target,
                    f"**Шизоид <:durka:684794973358522426> `{target.display_name}` ({target.mention}) <:durka:684794973358522426> в изоляторе. Кукуха чата в безопасности.**",
                    ("Срок мута", "3 часа", True)
                )

            elif mute_type is MuteTypes.dungeon:
                MINUS_REP = 500
                embed = _notification_embed(
                    target,
                    f"**Slave `{target.display_name}` ({target.mention}) отправлен в ♂️ Dungeon ♂️**",
                    ("Срок мута", "12 часов", True)
                )

            elif mute_type is MuteTypes.gulag:
                MINUS_REP = 1000
                embed = _notification_embed(
                    target,
                    f"**Нарушитель `{target.display_name}` ({target.mention}) отправлен в ГУЛАГ.**",
                    ("Срок мута", "24 часа", True)
                )

            else:
                MINUS_REP = 0
                embed = _notification_embed(target, None,
                        ("Срок мута", f"{seconds} {russian_plural(int(seconds),['секунда','секунды','секунд'])}", True)
                )

            await self.put_in_timeout(ctx, target, seconds)
            _extend_mute_story(ctx.message, target, seconds, reason)
            await edit_user_reputation(self.bot.pg_pool, target.id, '-', MINUS_REP)
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
    async def mute_members_command(
        self,
        ctx,
        targets: Greedy[Member],
        seconds: Optional[int] = 60,
        *,
        reason: Optional[str] = 'Не указана'
    ):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо замутить.", delete_after=10)
            return

        await self.mute_members(ctx, targets, seconds, reason, MuteTypes.timeout)


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
    async def ugol_mute_command(
        self,
        ctx,
        targets: Greedy[Member],
        *,
        reason: Optional[str] = 'Не указана'
    ):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в угол.", delete_after=10)
            return

        await self.mute_members(ctx, targets, 1800, reason, MuteTypes.ugol)


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
    async def isolator_mute_command(
        self,
        ctx,
        targets: Greedy[Member],
        *,
        reason: Optional[str] = 'Не указана'
    ):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в изолятор.", delete_after=10)
            return

        await self.mute_members(ctx, targets, 10800, reason, MuteTypes.isolator)


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
    async def dungeon_mute_command(
        self,
        ctx,
        targets: Greedy[Member],
        *,
        reason: Optional[str] = 'Не указана'
    ):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в ♂️ Dungeon ♂️", delete_after=10)
            return

        await self.mute_members(ctx, targets, 43200, reason, MuteTypes.dungeon)


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
    async def gulag_mute_command(
        self,
        ctx,
        targets: Greedy[Member],
        *,
        reason: Optional[str] = 'Не указана'
    ):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо отправить в ГУЛАГ.", delete_after=10)
            return

        await self.mute_members(ctx, targets, 86400, reason, MuteTypes.gulag)


    @logger.catch
    async def warn_member(self, ctx, target, warns, reason):
        def _warn_notification(target: Member, warns: list, time_field: tuple) -> Embed:
            embed = Embed(
                title="Участник получил warn",
                description=f"**Пользователь `{target.display_name}` ({target.mention}) получил warn и был отправлен в мут.**",
                color=Color.red(),
                timestamp=datetime.utcnow()
            )

            fields = [
                ("Причина", reason, True),
                time_field,
                ("Общее количество предупреждений", len(warns), True),
                ("Администратор", ctx.author.mention, True)
            ]

            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

            return embed

        if ctx.guild.me.top_role.position < target.top_role.position or target.id == ctx.author.id:
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
            await self.ban_members(ctx.message, [target], 1, "Максимум варнов | " + reason)
            return

        params = self._warn_mute_params(len(warns))
        embed = _warn_notification(target, warns, ("Срок мута", params[1], True))
        await self.put_in_timeout(ctx, target, params[0])
        await self.moderation_channel.send(embed=embed)


    def _warn_mute_params(self, warns_amount: int) -> tuple:
        if warns_amount == 1:
            return (21600, "6 часов")
        elif warns_amount == 2:
            return (43200, "12 часов")
        elif warns_amount == 3:
            return (86400, "24 часа")
        elif warns_amount > 3:
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
    async def warn_mute_command(
        self,
        ctx,
        target: Optional[Member],
        *,
        reason: Optional[str] = 'Не указана'
    ):
        await ctx.message.delete()

        if not target:
            await ctx.send(f"{ctx.author.mention}, укажите пользователя, которому необходимо выдать варн.", delete_after=10)
            return

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
        await self.warn_member(ctx, target, rec['user_warn_story'], reason)


    @logger.catch
    async def unmute_embed_builder(self, member: Member, reason: Optional[str] = 'Не указана'):
        embed = Embed(
            title='Участник размьючен',
            color=Color.green(),
            timestamp=datetime.utcnow()
        )

        fields = [("Пользователь", f"{member.display_name} ({member.mention})", False),
                    ("Причина", reason, False)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await self.moderation_channel.send(embed=embed)


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
    async def unmute_members_command(
        self,
        ctx,
        targets: Greedy[Member],
        *,
        reason: Optional[str] = 'Мут снят вручную администратором.'
    ):
        await ctx.message.delete()

        if not len(targets):
            await ctx.send(f"{ctx.author.mention}, укажите пользователей, которых необходимо размутить.", delete_after=10)
            return

        for target in targets:
            await self.put_in_timeout(ctx, target, seconds = 0)
            await self.unmute_embed_builder(target, reason)


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
                try:
                    if message.author.guild_permissions.administrator or self.helper_role in message.author.roles:
                        return
                except AttributeError:
                    return
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
        try:
            if message.author.guild_permissions.administrator or self.helper_role in message.author.roles:
                return
        except AttributeError:
            return

        if not (re.compile(self.URL_REGEX).search(message.clean_content)):
            return

        if 'steamcommunity.com' not in message.clean_content:
            words = ('partner=', 'token=', 'tradeoffer=')
            if any(word in message.clean_content for word in words):
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
                if rep <= -1500:
                    await self.ban_members(msg, [member], 0, 'Критический уровень репутации (<= -1500).')
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


async def setup(bot):
    await bot.add_cog(Moderation(bot))
