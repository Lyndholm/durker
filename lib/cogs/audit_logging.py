from discord import Message, Member, User, Guild, Embed, Color, File, MessageType, VoiceState
from discord import AuditLogAction, RawMessageDeleteEvent, RawMessageUpdateEvent, RawBulkMessageDeleteEvent, RawMessageUpdateEvent
from discord.channel import DMChannel
from discord.ext.commands import Cog
from discord.ext.commands import command
from datetime import datetime, timedelta
from asyncio import sleep as asleep
from difflib import Differ
from typing import List, Tuple, Union

from ..utils.constants import AUDIT_LOG_CHANNEL, ADMINS_CHANNEL, GVARDIYA_CHANNEL


class Audit(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("audit_logging")

    @staticmethod
    def list_diff(l1: List, l2: List) -> Tuple[List, List, List]:
        """Get the items in l1 that are not in l2, vice versa, and the intersection"""
        return (list(set(l1) - set(l2)), list(set(l2) - set(l1)), list(set(l1) & set(l2)))

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if not isinstance(message.channel, DMChannel):
            await asleep(1)
            log_channel = message.guild.get_channel(AUDIT_LOG_CHANNEL)

            if message.channel.id == ADMINS_CHANNEL or message.channel.id == GVARDIYA_CHANNEL:
                return
            else:
                if message.channel == log_channel and message.author == self.bot.user:
                    for embed in message.embeds:
                        await log_channel.send("Нельзя удалять сообщения бота в аудите!", embed=embed)
                    return
                elif message.author.bot:
                    return

                embed = Embed(title="Сообщение было удалено", color=Color.red(), timestamp=datetime.now())

                if message.system_content:
                    embed.description = f"**Удалённое сообщение:**```{message.clean_content.replace('`', '`­')[:2020]}\n```"
                elif message.content:
                    embed.description =  f"**Удалённое сообщение:**```{message.clean_content.replace('`', '`­')[:2020]}\n```"

                if message.attachments:
                    attachments_url = [attachment for attachment in message.attachments]
                    embed.add_field(name=f"Вложения ({len(message.attachments)}):", 
                                    value="```" + "\n".join([url.proxy_url for url in attachments_url]) + "\n" + "\n".join([url.url for url in attachments_url]) + "```", 
                                    inline = False)

                embed.add_field(name = 'Автор:', value = f'**{message.author.display_name}** ({message.author.mention})', inline=True)
                embed.add_field(name = 'Канал:', value = f'**{message.channel.name}** ({message.channel.mention})', inline=True)
                
                async for entry in message.guild.audit_logs(action=AuditLogAction.message_delete, limit=1):
                    if int((datetime.utcnow() - entry.created_at).total_seconds()) <= 5:
                        embed.add_field(name="Модератор:", value=entry.user.mention)
                    
                if message.type != MessageType.default:
                    embed.add_field(name="Тип сообщения:", value=msg_type_fmt(message.type))

                embed.set_footer(text = f"ID сообщения: {message.id}")

                await log_channel.send(embed=embed)


    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if not payload.cached_message:
            try:
                guild = self.bot.get_guild(payload.guild_id)
                channel = self.bot.get_channel(payload.channel_id)

                if channel.id == ADMINS_CHANNEL or channel.id == GVARDIYA_CHANNEL:
                    return
                else:
                    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)
                
                    embed = Embed(title="Сообщение было удалено [raw message delete event]",
                                description="Удаленноё сообщение не найдено в кэше, отображение о нём полной информации невозможно.", 
                                color=Color.red(), timestamp=datetime.now())
                    embed.add_field(name="Канал:", value=channel.mention)
                    embed.add_field(name="ID сообщения:", value=payload.message_id)
                    await log_channel.send(embed=embed)

            except AttributeError:
                pass

    
    @Cog.listener()
    async def on_bulk_message_delete(self, messages: List[Message]):
        if not isinstance (messages[0].channel, DMChannel):
            if messages[0].channel.id == ADMINS_CHANNEL or messages[0].channel.id == GVARDIYA_CHANNEL:
                return
            else:
                log_channel = messages[0].guild.get_channel(AUDIT_LOG_CHANNEL)

                embed = Embed(title=f"Несколько ({len(messages)}) сообщений были удалены. Подробности в прикреплённом файле.", 
                            color=Color.red(), timestamp=datetime.now())
                with open(f'./data/audit/bulk-deleted-messages/{messages[0].id}.log', 'w', encoding='utf-8') as f:
                    nl = '\n'
                    time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    for msg in messages:
                        if msg.attachments:
                            attachments_url = [attachment for attachment in msg.attachments]

                            f.write(f"{time} | User = {msg.author.display_name} | UserID = {msg.author.id}" + "\n" +   
                                f"MessageID = {msg.id}\nMessage content: {msg.clean_content}" + "\n" + 
                                f"Attachments: {nl.join([url.proxy_url for url in attachments_url]) + nl + nl.join([url.url for url in attachments_url])}" "\n\n")
                        else:
                            f.write(f"{time} | User = {msg.author.display_name} | UserID = {msg.author.id}" + nl +    
                                f"MessageID = {msg.id}\nMessage content: {msg.clean_content}" + "\n\n")

                embed.add_field(name="Канал:", value=f"{messages[0].channel.name} ({messages[0].channel.mention})")

                await log_channel.send(embed=embed, file=File(f'./data/audit/bulk-deleted-messages/{messages[0].id}.log'))


    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        if not payload.cached_messages:
            try:
                guild = self.bot.get_guild(payload.guild_id)
                channel = self.bot.get_channel(payload.channel_id)

                if channel.id == ADMINS_CHANNEL or channel.id == GVARDIYA_CHANNEL:
                    return
                else:
                    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)
                
                    embed = Embed(title=f"Несколько {len(payload.message_ids)} сообщений были удалены [raw bulk message delete event]",
                                description="Несколько сообщений были удалены, они не найдены в кэше, отображение полной информации невозможно.", 
                                color=Color.red(), timestamp=datetime.now())
                    embed.add_field(name="ID удаленных сообщений:", value=f"```{', '.join([str(m.id) for m in payload.message_ids])}```", inline=False)
                    embed.add_field(name="Канал:", value=channel.mention)
                    await log_channel.send(embed=embed)

            except AttributeError:
                pass


    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if not isinstance (after.channel, DMChannel):
            log_channel = after.guild.get_channel(AUDIT_LOG_CHANNEL)
            if not before.author.bot:
                if before.content != after.content:
                    if before.channel.id == ADMINS_CHANNEL or before.channel.id == GVARDIYA_CHANNEL:
                        return
                    else:
                        d = Differ()
                        diff = d.compare(before.clean_content.splitlines(), after.clean_content.splitlines())
                        diff_str = "\n".join([x for x in diff if not x.startswith("? ")]).replace("`", "`­")

                        embed = Embed(title=f"Сообщение было отредактировано", color=Color.blurple(), timestamp=datetime.now())
                        embed.description = f"```diff\n{diff_str[:2030]}\n```"
                        embed.add_field(name='Автор:', value=f'**{after.author.display_name}** ({after.author.mention})', inline=True)
                        embed.add_field(name="Канал:", value=before.channel.mention)
                        embed.add_field(name=f"Jump url:", value=f"[Click]({before.jump_url})")
                        embed.set_footer(text=f"ID сообщения: {after.id}")
                        await log_channel.send(embed=embed)


    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        if not payload.cached_message:
            try:
                channel = self.bot.get_channel(payload.channel_id)

                if channel.id == ADMINS_CHANNEL or channel.id == GVARDIYA_CHANNEL:
                    return
                else:
                    guild = channel.guild
                    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)
                    data = payload.data

                    embed = Embed(title="Сообщение было отредактировано [raw message edit event]", color=Color.blurple(), timestamp=datetime.utcnow())

                    if "content" in data:
                        embed.description = "Поскольку сообщения нет в кэше, отображение старого содержимого невозможно.\n\n" + f"**Новое содержимое:**\n```{data['content'].replace('`', '`­')[:1940]}```"

                    if "author" in data and "id" in data["author"]:
                        author = guild.get_member(data["author"]["id"])
                        if not author:
                            author = await self.bot.fetch_user(data["author"]["id"])
                        
                        if hasattr(author, "bot") and author.bot:
                            return
                    embed.add_field(name='Автор:', value=f'**{author.display_name}** ({author.mention})')
                    embed.add_field(name="Канал", value=channel.mention)
                    embed.add_field(name=f"Jump url:", value=f"[Click](https://discordapp.com/channels/{guild.id}/{channel.id}/{payload.message_id})")
                    embed.set_footer(text=f"ID сообщения: {payload.message_id}")
                    await log_channel.send(embed=embed)

            except AttributeError:
                pass

    
    @Cog.listener()
    async def on_member_join(self, member):
        embed = Embed(title=f"Новый участник на сервере.", description=f"Пользователь **{member.display_name}** ({member.mention}) присоединился к серверу, но пока что не принял правила. Пользователь в процессе верификации.",
                    color=Color.dark_red(), timestamp=datetime.now())
        await self.bot.get_channel(AUDIT_LOG_CHANNEL).send(embed=embed)


    @Cog.listener()
    async def on_member_remove(self, member: Member):
        log_channel = member.guild.get_channel(AUDIT_LOG_CHANNEL)

        server_age = (datetime.utcnow() - member.joined_at).total_seconds()
        embed = Embed(title = "Пользователь покинул сервер", color=Color.red())
        embed.add_field(name="Пользователь:", value=f"**{member.display_name}** ({member.mention})")
        embed.add_field(name="Время, проведённое на сервере:", value=f"{timedelta(seconds=server_age)}")
        embed.set_footer(text=f"ID пользователя: {member.id}")

        async for entry in log_channel.guild.audit_logs(action=AuditLogAction.kick, limit=1):
            if int((datetime.utcnow() - entry.created_at).total_seconds()) <= 5:
                embed.title = "Пользователь был кикнут с сервера"
                embed.add_field(name="Модератор:", value=entry.user.mention)
                if entry.reason:
                    embed.add_field(name="Причина:", value=entry.reason, inline=False)

        await log_channel.send(embed=embed)


    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        log_channel = after.guild.get_channel(AUDIT_LOG_CHANNEL)

        if before.pending is True and after.pending is False:
            acc_age = (datetime.utcnow() - after.created_at).total_seconds()

            embed = Embed(title="Пользователь присоединился к серверу", color=Color.green(), timestamp=datetime.utcnow())
            embed.add_field(name="Пользователь:", value=f"**{after.display_name}** ({after.mention})")
            embed.add_field(name="Дата захода", value=after.joined_at.strftime("%d.%m.%Y %H:%M:%S"))
            embed.add_field(name="Аккаунт создан:", value=after.created_at.strftime("%d.%m.%Y %H:%M:%S"))
            embed.add_field(name="Возраст аккаунта", value=f"**{timedelta(seconds=acc_age)}**")
            embed.set_footer(text=f"ID пользователя: {after.id}")
            embed.set_thumbnail(url=after.avatar_url)

            await log_channel.send(embed=embed)
        
        if before.roles != after.roles:   
            embed = Embed(description = f"Роли участника **{after.display_name}** ({after.mention}) были изменены", 
                        color = Color.teal(), timestamp=datetime.utcnow())

            roles_removed, roles_added, _ = self.list_diff(before.roles, after.roles)

            if added := [r.mention for r in roles_added]:
                embed.add_field(name="Добавлены роли:", value=" ".join(added))
            if removed := [r.mention for r in roles_removed]:
                embed.add_field(name="Удалены роли:", value=" ".join(removed))

            async for entry in after.guild.audit_logs(action=AuditLogAction.member_role_update, limit=1):
                if int((datetime.utcnow() - entry.created_at).total_seconds()) <= 5:
                    embed.add_field(name="Модератор", value = entry.user.mention)

            embed.set_footer(text = f"ID участника: {after.id}")
            await log_channel.send(embed=embed)

        if before.display_name != after.display_name:
            embed = Embed(description = f"Никнейм участника **{before.display_name}** ({before.mention}) был изменен", 
                        color=Color.teal(), timestamp=datetime.utcnow())
            embed.add_field(name = "Старый никнейм:", value = before.display_name)
            embed.add_field(name = "Новый никнейм:", value = after.display_name)
            embed.set_footer(text = f"ID участника: {after.id}")
            await log_channel.send(embed=embed)


    @Cog.listener()
    async def on_member_ban(self, guild: Guild, user: Union[User, Member]):
        await asleep(2)
        log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)

        embed = Embed(title="Бан участника", description=f"Пользователь **{user.display_name}** ({user.mention}) был забанен.",
                    color=Color.red(), timestamp=datetime.utcnow())
        embed.set_footer(text=f"ID пользователя: {user.id}")

        async for entry in log_channel.guild.audit_logs(action=AuditLogAction.ban, limit=1):
            if int((datetime.utcnow() - entry.created_at).total_seconds()) <= 5:
                embed.add_field(name="Модератор:", value=entry.user.mention)
                if entry.reason:
                    embed.add_field(name="Причина:", value=entry.reason)

        await log_channel.send(embed=embed)


    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        log_channel = guild.get_channel(AUDIT_LOG_CHANNEL)

        embed = Embed(title="Разбан пользователя", description=f"Пользователь **{user.display_name}** ({user.mention}) был разбанен.",
                color=Color.dark_green(), timestamp=datetime.utcnow())
        embed.set_footer(text=f"ID пользователя: {user.id}")

        async for entry in log_channel.guild.audit_logs(action=AuditLogAction.unban, limit=1):
            if int((datetime.utcnow() - entry.created_at).total_seconds()) <= 5:
                embed.add_field(name="Модератор:", value=entry.user.mention)

        await log_channel.send(embed=embed)


    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        log_channel = member.guild.get_channel(AUDIT_LOG_CHANNEL)

        if before.channel is None:
            embed = Embed(description = f"Участник **{member.display_name}** ({member.mention}) зашел в голосовой канал :loud_sound: **{after.channel.name}**",
                        color=Color.purple(), timestamp=datetime.utcnow())
            embed.set_footer(text = f"ID участника: {member.id}")
            await log_channel.send(embed=embed)
              
        if after.channel is None:
            embed = Embed(description = f"Участник **{member.display_name}** ({member.mention}) покинул голосовой канал :loud_sound: **{before.channel.name}**",
                    color=Color.purple(), timestamp=datetime.utcnow())
            embed.set_footer(text = f"ID участника: {member.id}")
            await log_channel.send(embed=embed)
            
        if before.channel is not None and after.channel is not None:
            if before.channel.id != after.channel.id:
                embed = Embed(description = f"Участник **{member.display_name}** ({member.mention}) перешел в другой голосовой канал :loud_sound:",
                    color=Color.purple(), timestamp=datetime.utcnow())
                embed.add_field(name = "Новый канал:", value = f"**{after.channel.name}** (#{after.channel.name})", inline=True)
                embed.add_field(name = "Предыдущий канал:", value = f"**{before.channel.name}** ({before.channel.mention})", inline=True)
                embed.set_footer(text = f"ID участника: {member.id}")
                await log_channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Audit(bot))
