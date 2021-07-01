import re

from discord import Role, TextChannel
from discord.ext.commands import Cog, command, guild_only, has_permissions
from discord.utils import get
from loguru import logger

from ..db import db
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json('reactions')


class ReactionRole(Cog, name='Роли за реакции'):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    @logger.catch
    async def init_vars(self):
        self.mod_cog = self.bot.get_cog('Модерация')

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.mod_cog = self.bot.get_cog('Модерация')
            self.bot.cogs_ready.ready_up("reactions")

    @logger.catch
    async def edit_member_roles(self, guild_id: int, role_id: int, user_id: int, action: str):
        guild = self.bot.get_guild(guild_id)
        role = get(guild.roles, id=role_id)
        member = guild.get_member(user_id)
        if not member.bot:
            if action == '+':
                if not self.mod_cog.is_member_muted(member):
                    await member.add_roles(role)
            elif action == '-':
                await member.remove_roles(role)

    @Cog.listener()
    async def on_raw_reaction_add(self, reaction):
        cursor = db.get_cursor()
        if '<:' in str(reaction.emoji):
            cursor.execute(f"SELECT emoji, role, message_id, channel_id FROM reactions WHERE guild_id = '{reaction.guild_id}' and message_id = '{reaction.message_id}' and emoji = '{reaction.emoji.id}'")
            record = cursor.fetchone()
            if record is not None:
                if str(reaction.emoji.id) in str(record[0]):
                    await self.edit_member_roles(reaction.guild_id, int(record[1]), reaction.user_id, '+')
        elif '<:' not in str(reaction.emoji):
            cursor.execute(f"SELECT emoji, role, message_id, channel_id FROM reactions WHERE guild_id = '{reaction.guild_id}' and message_id = '{reaction.message_id}' and emoji = '{reaction.emoji}'")
            record = cursor.fetchone()
            if record is not None:
                await self.edit_member_roles(reaction.guild_id, int(record[1]), reaction.user_id, '+')

    @Cog.listener()
    async def on_raw_reaction_remove(self, reaction):
        cursor = db.get_cursor()
        if '<:' in str(reaction.emoji):
            cursor.execute(f"SELECT emoji, role, message_id, channel_id FROM reactions WHERE guild_id = '{reaction.guild_id}' and message_id = '{reaction.message_id}' and emoji = '{reaction.emoji.id}'")
            record = cursor.fetchone()
            if record is not None:
                if str(reaction.emoji.id) in str(record[0]):
                    await self.edit_member_roles(reaction.guild_id, int(record[1]), reaction.user_id, '-')
        elif '<:' not in str(reaction.emoji):
            cursor.execute(f"SELECT emoji, role, message_id, channel_id FROM reactions WHERE guild_id = '{reaction.guild_id}' and message_id = '{reaction.message_id}' and emoji = '{reaction.emoji}'")
            record = cursor.fetchone()
            if record is not None:
                await self.edit_member_roles(reaction.guild_id, int(record[1]), reaction.user_id, '-')


    @command(name=cmd["addreactionrole"]["name"], aliases=cmd["addreactionrole"]["aliases"],
            brief=cmd["addreactionrole"]["brief"],
            description=cmd["addreactionrole"]["description"],
            usage=cmd["addreactionrole"]["usage"],
            help=cmd["addreactionrole"]["help"],
            hidden=cmd["addreactionrole"]["hidden"], enabled=True)
    @has_permissions(administrator=True)
    @guild_only()
    @logger.catch
    async def add_reaction_role_command(self, ctx, channel: TextChannel, message_id: int, emoji: str, role: Role):
        cursor = db.get_cursor()
        cursor.execute(f"SELECT emoji, role, message_id, channel_id FROM reactions WHERE guild_id = '{ctx.guild.id}' and message_id = '{message_id}'")
        record = cursor.fetchone()
        data = {
            "role": role.id,
            "message_id": message_id,
            "channel_id": channel.id,
            "guild_id": ctx.guild.id
        }
        if '<:' in emoji:
            emn = re.sub(':.*?:', '', emoji).strip('<>')
            if record is None or str(message_id) not in str(record[3]):
                data["emoji"] = emn
                msg = await channel.fetch_message(message_id)
                em = self.bot.get_emoji(int(emn))
                await msg.add_reaction(em)
        elif '<:' not in emoji:
            if record is None or str(message_id) not in str(record[3]):
                data["emoji"] = emoji
                msg = await channel.fetch_message(message_id)
                await msg.add_reaction(emoji)
        db.insert("reactions", data)

    @command(name=cmd["removereactionrole"]["name"], aliases=cmd["removereactionrole"]["aliases"],
            brief=cmd["removereactionrole"]["brief"],
            description=cmd["removereactionrole"]["description"],
            usage=cmd["removereactionrole"]["usage"],
            help=cmd["removereactionrole"]["help"],
            hidden=cmd["removereactionrole"]["hidden"], enabled=True)
    @has_permissions(administrator=True)
    @guild_only()
    @logger.catch
    async def remove_reaction_role_command(self, ctx, message_id: int, emoji: str):
        cursor = db.get_cursor()
        cursor.execute(f"SELECT emoji, role, message_id, channel_id FROM reactions WHERE guild_id = '{ctx.guild.id}' and message_id = '{message_id}'")
        record = cursor.fetchone()

        if '<:' in emoji:
            emm = re.sub(':.*?:', '', emoji).strip('<>')
            if record is None:
                await ctx.send('Реакция не найдена в базе данных.', delete_after=5)
            elif str(message_id) in str(record[2]):
                cursor.execute(f"DELETE FROM reactions WHERE guild_id = '{ctx.guild.id}' and message_id = '{message_id}' and emoji = '{emm}'")
                msg = await ctx.fetch_message(message_id)
                await msg.remove_reaction(emoji, ctx.guild.me)
                await ctx.send('Реакция удалена.', delete_after=5)
            else:
                await ctx.send('Реакция не найдена.', delete_after=5)
        elif '<:' not in emoji:
            if record is None:
                await ctx.send('Реакция не найдена в базе данных.', delete_after=5)
            elif str(message_id) in str(record[2]):
                cursor.execute(f"DELETE FROM reactions WHERE guild_id = '{ctx.guild.id}' and message_id = '{message_id}' and emoji = '{emoji}'")
                msg = await ctx.fetch_message(message_id)
                await msg.remove_reaction(emoji, ctx.guild.me)
                await ctx.send('Реакция удалена.', delete_after=5)
            else:
                await ctx.send('Реакция не найдена.', delete_after=5)
        db.commit()


def setup(bot):
    bot.add_cog(ReactionRole(bot))
