from typing import Optional
from datetime import datetime
from discord import Embed, Color, Member
from discord.ext.commands import Cog, Greedy
from discord.ext.commands import CheckFailure
from discord.ext.commands import command, has_permissions, bot_has_permissions, guild_only

from ..utils.constants import MODERATION_PUBLIC_CHANNEL, AUDIT_LOG_CHANNEL
from ..utils.utils import load_commands_from_json
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
                if ctx.guild.me.top_role.position <= target.top_role.position:
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
    async def ban_members_command(self, ctx, targets: Greedy[Member], *, 
                                        delete_days: Optional[int] = 1,
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
                if ctx.guild.me.top_role.position <= target.top_role.position:
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


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.moderation_channel = self.bot.get_channel(MODERATION_PUBLIC_CHANNEL)
            self.audit_channel = self.bot.get_channel(AUDIT_LOG_CHANNEL)
            self.bot.cogs_ready.ready_up("moderation")


def setup(bot):
    bot.add_cog(Moderation(bot))
