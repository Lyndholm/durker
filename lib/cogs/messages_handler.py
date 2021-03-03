from discord import Message
from discord.ext.commands import Cog
from discord.ext.commands import command
import aiofiles


class MessagesHandler(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rep_filter = []
        self.question_filter = []

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

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("messages_handler")

    @Cog.listener()
    async def on_message(self, message):
        if message.clean_content.lower() in self.rep_filter:
            await self.invoke_command(message, 'rep')

        if message.clean_content.lower() in self.question_filter:
            if message.channel.id != 546700132390010882
                await self.invoke_command(message, 'question')


def setup(bot):
    bot.add_cog(MessagesHandler(bot))
