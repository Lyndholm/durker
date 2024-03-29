from os import listdir
from random import choice, randint

import aiofiles
from discord import File, Member, NotFound, RawMessageUpdateEvent, TextChannel
from discord.ext.commands import (Cog, check_any, command, dm_only, guild_only,
                                  has_any_role, has_permissions, is_owner)
from discord.utils import remove_markdown
from loguru import logger

from ..db import db
from ..utils.constants import CHASOVOY_ROLE_ID
from ..utils.decorators import listen_for_guilds
from ..utils.utils import (edit_user_reputation,
                           find_n_term_of_arithmetic_progression,
                           load_commands_from_json, russian_plural)

cmd = load_commands_from_json("profanity")


class Profanity(Cog, name='Мат-фильтр'):
    def __init__(self, bot):
        self.bot = bot
        self.whitelisted_users = (
            384728793895665675, #tvoya_pechal
            342783617983840257, #lexenus
            375722626636578816, #lyndholm
        )
        self.whitelisted_channels = (
            546404724216430602, #админка
            686499834949140506, #гвардия
        )

    def increase_user_profanity_counter(self, user_id: int):
        db.execute("UPDATE users_stats SET profanity_triggers = profanity_triggers + 1 WHERE user_id = %s",
                    user_id)
        db.commit()

    def fetch_user_profanity_counter(self, user_id: int) -> int:
        rec = db.fetchone(["profanity_triggers"], "users_stats", "user_id", user_id)
        return rec[0] if rec is not None else 0

    async def reply_profanity(self, channel: TextChannel, member: Member, lost_rep: int):
        profanity_replies = (
            f"{member.mention}, будь добр, следи за языком.",
            f"Следи за языком, {member.mention}.",
            f"{member.mention}, следи за языком, пожалуйста.",
            f"{member.mention}, думай, что говоришь.",
            f"{member.mention}, общайся, пожалуйста, без нецензурной лексики.",
            f"{member.mention}, уменьши количество нецензурной лексики.",
            f"{member.mention}, общайся, пожалуйста, без мата.",
            f"{member.mention}, выбирай выражения.",
            f"{member.mention}, меньше мата, пожалуйста.",
            f"{member.mention}, пожалуйста, давай общаться без мата.",
            f"{member.mention}, у нас обсценная лексика не приветсвуется.",
            f"{member.mention}, не используй, пожалуйста, обсценную лексику.",
            f"{member.mention}, на сервере нет места брани.",
        )
        reply = choice(profanity_replies) + f"\nТвоя репутация была уменьшена на **{lost_rep}** {russian_plural(lost_rep, ['единицу','единицы','единиц'])}."
        if 10 <= randint(1, 100) <= 25:
            images = listdir('./data/images/bez_mata')
            await channel.send(reply, file=File(f'./data/images/bez_mata/{choice(images)}'))
        else:
            await channel.send(reply)

    async def process_profanity(self, channel: TextChannel, member: Member):
        self.increase_user_profanity_counter(member.id)
        profanity_counter = self.fetch_user_profanity_counter(member.id)
        minus_rep = find_n_term_of_arithmetic_progression(5, 3, profanity_counter)
        await edit_user_reputation(self.bot.pg_pool, member.id, '-', minus_rep)
        await self.reply_profanity(channel, member, minus_rep)

    @Cog.listener()
    @listen_for_guilds()
    @logger.catch
    async def on_message(self, message):
        content = remove_markdown(message.clean_content)
        if isinstance(message.channel, TextChannel) and not message.author.bot:
            if self.bot.profanity.contains_profanity(content):
                if message.author.id not in self.whitelisted_users:
                    if message.channel.id not in self.whitelisted_channels:
                        await self.process_profanity(message.channel, message.author)

    @Cog.listener()
    @logger.catch
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        data = payload.data
        channel = self.bot.get_channel(payload.channel_id)
        if isinstance(channel, TextChannel):
            if 'author' in data:
                if 'id' in data['author']:
                    try:
                        member = await self.bot.fetch_user(data['author']['id'])
                    except NotFound:
                        return
                    if not member.bot and self.bot.profanity.contains_profanity(remove_markdown(data['content'])):
                        if member.id not in self.whitelisted_users:
                            if channel.id not in self.whitelisted_channels:
                                await self.process_profanity(channel, member)

    @command(name=cmd["swear"]["name"], aliases=cmd["swear"]["aliases"],
            brief=cmd["swear"]["brief"],
            description=cmd["swear"]["description"],
            usage=cmd["swear"]["usage"],
            help=cmd["swear"]["help"],
            hidden=cmd["swear"]["hidden"], enabled=True)
    @check_any(
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True)
    )
    @guild_only()
    @logger.catch
    async def swear_command(self, ctx, target: Member = None):
        await ctx.message.delete()
        if target:
            if not target.bot:
                if target.id not in self.whitelisted_users:
                    await self.process_profanity(ctx.channel, target)

    @command(name=cmd["addprofanity"]["name"], aliases=cmd["addprofanity"]["aliases"],
            brief=cmd["addprofanity"]["brief"],
            description=cmd["addprofanity"]["description"],
            usage=cmd["addprofanity"]["usage"],
            help=cmd["addprofanity"]["help"],
            hidden=cmd["addprofanity"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def addprofanity_command(self, ctx, *words):
        async with aiofiles.open(f'./data/txt/profanity.txt', mode='a', encoding='utf-8') as f:
            await f.write("".join([f"{w}\n" for w in words]))

        self.bot.profanity.load_censor_words_from_file("./data/txt/profanity.txt")
        await ctx.reply("Словарь обновлён!", mention_author=False)


    @command(name=cmd["delprofanity"]["name"], aliases=cmd["delprofanity"]["aliases"],
            brief=cmd["delprofanity"]["brief"],
            description=cmd["delprofanity"]["description"],
            usage=cmd["delprofanity"]["usage"],
            help=cmd["delprofanity"]["help"],
            hidden=cmd["delprofanity"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def delprofanity_command(self, ctx, *words):
        async with aiofiles.open(f'./data/txt/profanity.txt', mode='r', encoding='utf-8') as f:
            lines = await f.readlines()
            stored = [w.strip() for w in lines]

        async with aiofiles.open(f'./data/txt/profanity.txt', mode='w', encoding='utf-8') as f:
            await f.write("".join([f"{w}\n" for w in stored if w not in words]))

        self.bot.profanity.load_censor_words_from_file("./data/txt/profanity.txt")
        await ctx.reply("Словарь обновлён!", mention_author=False)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("profanity")

def setup(bot):
    bot.add_cog(Profanity(bot))
