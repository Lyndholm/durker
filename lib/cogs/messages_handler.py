from datetime import datetime

import aiofiles
from discord import Message, TextChannel
from discord.ext.commands import Cog
from discord.utils import remove_markdown

from ..db import db
from ..utils.decorators import listen_for_guilds


class MessagesHandler(Cog, name='Messages handler'):
    def __init__(self, bot):
        self.bot = bot
        self.rep_filter = []
        self.question_filter = []
        self.profanity_whitelisted_users = (
            384728793895665675, #tvoya_pechal
            342783617983840257, #lexenus
            375722626636578816, #lyndholm
        )
        self.channels_with_message_counting = (
            546404724216430602, #админы-текст
            686499834949140506, #гвардия-общение
            698568751968419850, #спонсорское-общение
            721480135043448954, #общение (главный чат)
            546408250158088192, #поддержка,
            644523860326219776, #медиа,
            # 793153650083627018, #баги
            # 640475254128640003, #творческий-режим
            # 546700132390010882, #ваши-вопросы
            # 639925210849476608, #заявки-на-рассмотрение
            # 811901577396092930, #жалобы
            708601604353556491, #консоль на dev сервере
            777979537795055636, #testing на dev сервере
        )

        bot.loop.create_task(self.parse_questions_from_txt())

    async def parse_questions_from_txt(self):
        async with aiofiles.open(f'data/question_filter.txt', mode='r', encoding='utf-8') as f:
            lines = await f.readlines()
            self.question_filter = [line.strip() for line in lines if line != '']

        async with aiofiles.open(f'data/rep_filter.txt', mode='r', encoding='utf-8') as f:
            lines = await f.readlines()
            self.rep_filter = [line.strip() for line in lines if line != '']

    async def invoke_command(self, message: Message, cmd: str):
        ctx = await self.bot.get_context(message)
        command = self.bot.get_command(cmd)
        ctx.command = command
        await self.bot.invoke(ctx)

    async def can_message_be_counted(self, message: Message) -> bool:
        message_content = remove_markdown(message.clean_content)
        ctx = await self.bot.get_context(message)

        if not message.author.bot and isinstance(message.channel, TextChannel):
            if self.bot.profanity.contains_profanity(message_content):
                if message.author.id not in self.profanity_whitelisted_users:
                    return False
            if not ctx.command:
                if message.channel.id in self.channels_with_message_counting:
                    if len(message.clean_content) > 2:
                        if message.clean_content[0] != "<" and message.clean_content[-1] != ">":
                            return True
                    elif message.attachments:
                        return True
                    else:
                        return False

    def increase_user_messages_counter(self, user_id: int):
        db.execute(f"UPDATE users_stats SET messages_count = messages_count + 1 WHERE user_id = {user_id}")
        db.execute("UPDATE users_stats SET last_message_date = %s WHERE user_id = %s",
                    datetime.now(), user_id)
        db.commit()

    def decrease_user_messages_counter(self, user_id: int):
        db.execute(f"UPDATE users_stats SET messages_count = messages_count - 1 WHERE user_id = {user_id}")
        db.commit()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("messages_handler")

    @Cog.listener()
    @listen_for_guilds()
    async def on_message(self, message):
        if await self.can_message_be_counted(message):
            self.increase_user_messages_counter(message.author.id)

        if message.clean_content.lower() in self.rep_filter:
            await self.invoke_command(message, 'rep')

        if message.clean_content.lower() in self.question_filter:
            if message.channel.id != 546700132390010882:
                await self.invoke_command(message, 'question')

        if message.channel.id == 639925210849476608 and message.author.id != 479499525921308703:
            await message.add_reaction('\N{THUMBS UP SIGN}')
            await message.add_reaction('\N{THUMBS DOWN SIGN}')

    @Cog.listener()
    @listen_for_guilds()
    async def on_message_delete(self, message):
        if await self.can_message_be_counted(message):
            self.decrease_user_messages_counter(message.author.id)


def setup(bot):
    bot.add_cog(MessagesHandler(bot))
