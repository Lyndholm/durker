from typing import Optional
from asyncio import sleep
from datetime import datetime, timedelta
from discord import Embed, Color, Member
from discord.errors import NotFound
from discord.ext.commands import Cog, Greedy
from discord.ext.commands import CheckFailure
from discord.ext.commands import command, has_permissions, bot_has_permissions, has_any_role, guild_only

from ..utils.constants import MODERATION_PUBLIC_CHANNEL, AUDIT_LOG_CHANNEL, MUTE_ROLE_ID
from ..utils.utils import load_commands_from_json, russian_plural
from ..db import db

cmd = load_commands_from_json("moderation")


class Moderation(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pominki_url = "https://cdn.discordapp.com/attachments/774698479981297664/809142415310979082/RoflanPominki.png"

    @command(name=cmd["kick"]["name"], aliases=cmd["kick"]["aliases"], 
            brief=cmd["kick"]["brief"],
            description=cmd["kick"]["description"],
            usage=cmd["kick"]["usage"],
            help=cmd["kick"]["help"],
            hidden=cmd["kick"]["hidden"], enabled=True)
    @guild_only()
    @bot_has_permissions(kick_members=True)
    @has_permissions(kick_members=True)
    async def kick_members_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана."):
        await ctx.message.delete()

        if not len(targets):
            embed = Embed(
                description=f"{ctx.author.mention}, укажите пользователя/пользователей, которых необходимо выгнать с сервера.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after=15)

        else:
            for target in targets:
                if ctx.guild.me.top_role.position < target.top_role.position:
                    embed = Embed(
                        title='Неудачная попытка кикнуть участника', 
                        description=f"Пользователь {ctx.author.mention} пытался выгнать {target.mention}\nПричина кика: {reason}", 
                        color=Color.red()
                    )
                    await self.audit_channel.send(embed=embed)
                    return

                await target.kick(reason=reason)


                embed = Embed(
                    title="Участник выгнан с сервера",
                    color=Color.dark_red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=self.pominki_url)

                fields = [("Пользователь", f"{target.display_name} ({target.mention})", False),
                          ("Администратор", ctx.author.mention, False),
                          ("Причина", reason.capitalize(), False)]
                
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.moderation_channel.send(embed=embed)


    @command(name=cmd["ban"]["name"], aliases=cmd["ban"]["aliases"], 
            brief=cmd["ban"]["brief"],
            description=cmd["ban"]["description"],
            usage=cmd["ban"]["usage"],
            help=cmd["ban"]["help"],
            hidden=cmd["ban"]["hidden"], enabled=True)
    @guild_only()
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    async def ban_members_command(self, ctx, targets: Greedy[Member],
                                        delete_days: Optional[int] = 1, *,
                                        reason: Optional[str] = "Не указана."):
        await ctx.message.delete()

        if not len(targets):
            embed = Embed(
                description=f"{ctx.author.mention}, укажите пользователя/пользователей, которых необходимо забанить.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after=15)

        else:
            for target in targets:
                if ctx.guild.me.top_role.position < target.top_role.position:
                    embed = Embed(
                        title='Неудачная попытка забанить участника', 
                        description=f"Пользователь {ctx.author.mention} пытался забанить {target.mention}\nПричина бана: {reason}", 
                        color=Color.red()
                    )
                    await self.audit_channel.send(embed=embed)
                    return

                await target.ban(delete_message_days=delete_days, reason=reason)

                embed = Embed(
                    title="Участник забанен",
                    color=Color.dark_red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=self.pominki_url)

                fields = [("Пользователь", f"{target.display_name} ({target.mention})", False),
                          ("Администратор", ctx.author.mention, False),
                          ("Причина", reason.capitalize(), False)]
                
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.moderation_channel.send(embed=embed)


    @command(name=cmd["purge"]["name"], aliases=cmd["purge"]["aliases"], 
            brief=cmd["purge"]["brief"],
            description=cmd["purge"]["description"],
            usage=cmd["purge"]["usage"],
            help=cmd["purge"]["help"],
            hidden=cmd["purge"]["hidden"], enabled=True)
    @guild_only()
    @bot_has_permissions(manage_messages=True)
    @has_permissions(administrator=True)
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

        await ctx.message.delete()

        if not targets:
            async for message in ctx.channel.history(limit=limit):
                if message.author not in users:
                    users[message.author.id] = 0
                    
            async for message in ctx.channel.history(limit=limit):
                users[message.author.id] += 1

            deleted = await ctx.channel.purge(limit=limit)
            if ctx.channel.id in self.bot.channels_with_message_counting:
                decrease_message_counter(users)

            embed = Embed(
                title="Выполнено!",
                color=Color.random(),
                description=f"Удалено сообщений: {len(deleted)}\nУдаление выполнено пользователем {ctx.author.mention}"
            )
            await ctx.channel.send(embed=embed, delete_after=5)

            embed.title = "purge command invoked"
            embed.description = f"Удалено сообщений: {len(deleted)}\nУдаление выполнено пользователем: {ctx.author.mention}\nКанал: {ctx.channel.mention}"
            await self.bot.get_user(375722626636578816).send(embed=embed)

        else:
            deleted = await ctx.channel.purge(limit=limit, check=_check)
            msg_author_ids = [message.author.id for message in deleted]
            for entry in msg_author_ids:
                users[entry] = msg_author_ids.count(entry)

            if ctx.channel.id in self.bot.channels_with_message_counting:
                decrease_message_counter(users)

            embed = Embed(
                title="Выполнено!",
                color=Color.random(),
                description=f"Удалено сообщений: {len(deleted)}\nУдаление выполнено пользователем {ctx.message.author.mention}"
            )
            await ctx.channel.send(embed=embed, delete_after=5)

            embed.title = "purge (with targets) command invoked "
            embed.description = f"Удалено сообщений: {len(deleted)}\nУдаление выполнено пользователем: {ctx.author.mention}\nКанал: {ctx.channel.mention}"
            await self.bot.get_user(375722626636578816).send(embed=embed)


    @command(name=cmd["mute"]["name"], aliases=cmd["mute"]["aliases"], 
            brief=cmd["mute"]["brief"],
            description=cmd["mute"]["description"],
            usage=cmd["mute"]["usage"],
            help=cmd["mute"]["help"],
            hidden=cmd["mute"]["hidden"], enabled=True)
    @guild_only()
    @bot_has_permissions(manage_roles=True)
    @has_any_role(790664227706241068, 686495834241761280)
    async def mute_members_command(self, ctx, targets: Greedy[Member], hours: Optional[str],
                                   *, reason: Optional[str] = "Не указана."):
        await ctx.message.delete()

        if not len(targets):
            embed = Embed(
                description=f"{ctx.author.mention}, укажите пользователя/пользователей, которых необходимо замутить.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        unmutes = []

        for target in targets:
            if not self.mute_role in target.roles:
                if ctx.guild.me.top_role.position < target.top_role.position or target.id == ctx.author.id:
                    return

                role_ids = ",".join([str(r.id) for r in target.roles])
                managed_roles = [r for r in target.roles if r.managed]
                end_time = datetime.now() + timedelta(hours=float(hours)) if hours else None
                
                await target.edit(roles=[self.mute_role] + managed_roles)

                db.insert("mutes", {"user_id": target.id, 
                       "role_ids": role_ids,
                       "mute_end_time": end_time})

                embed = Embed(
                    title="Участник получил мут",
                    color=Color.dark_red(),
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=self.pominki_url)

                fields = [("Пользователь", f"{target.display_name} ({target.mention})", False),
                          ("Причина", reason.capitalize(), False),
                          ("Срок мута", f"{hours} {russian_plural(int(hours),['час','часа','часов'])}" if hours else "Бессрочно", False),
                          ("Администратор", ctx.author.mention, False)]
                
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.moderation_channel.send(embed=embed)

                if hours:
                    unmutes.append(target)

            else:
                embed = Embed(
                    title="Внимание!",
                    color=Color.red(), 
                    description=f"Участник `{target.display_name}` ({target.mention}) уже замьючен!"
                )            
                await ctx.send(embed=embed, delete_after=10)
                return

        if len(unmutes):
            await sleep(int(hours)*3600)
            await self.unmute(ctx, targets, "Время мута истекло.")


    async def unmute(self, ctx, targets, reason = "Мут снят вручную администратором."):
        for target in targets:
            if self.mute_role in target.roles:
                role_ids = db.fetchone(["role_ids"], "mutes", "user_id", target.id)[0]
                roles = [ctx.guild.get_role(int(id_)) for id_ in role_ids.split(",") if len (id_)]

                db.execute("DELETE FROM mutes WHERE user_id = %s", target.id)
                db.commit()

                try:
                    await target.edit(roles=roles)
                except NotFound:
                    return

                embed = Embed(
                    title="Участник размьючен",
                    color=Color.green(),
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url="https://media1.tenor.com/images/c44aff453bd34aa2f3a21ddd106ed641/tenor.gif")

                fields = [("Пользователь", f"{target.display_name} ({target.mention})", False),
                          ("Причина", reason.capitalize(), False)]
                
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await self.moderation_channel.send(embed=embed)


    @command(name=cmd["unmute"]["name"], aliases=cmd["unmute"]["aliases"], 
            brief=cmd["unmute"]["brief"],
            description=cmd["unmute"]["description"],
            usage=cmd["unmute"]["usage"],
            help=cmd["unmute"]["help"],
            hidden=cmd["unmute"]["hidden"], enabled=True)
    @guild_only()
    @bot_has_permissions(manage_roles=True)
    @has_any_role(790664227706241068,606928001669791755)
    async def unmute_members_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "Не указана."):
        await ctx.message.delete()

        if not len(targets):
            embed = Embed(
                description=f"{ctx.author.mention}, укажите пользователя/пользователей, которых необходимо размутить.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        await self.unmute(ctx, targets)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.moderation_channel = self.bot.get_channel(MODERATION_PUBLIC_CHANNEL)
            self.audit_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
            self.mute_role = self.bot.guild.get_role(MUTE_ROLE_ID)
            self.bot.cogs_ready.ready_up("moderation")


def setup(bot):
    bot.add_cog(Moderation(bot))
