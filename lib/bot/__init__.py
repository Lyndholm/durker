from datetime import datetime
from os import getenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import Color, Embed, Intents
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import CommandNotFound, CommandOnCooldown
from loguru import logger

from ..utils import constants
from ..utils.utils import russian_plural
from ..db import db

logger.add("logs/{time:DD-MM-YYYY---HH-mm-ss}.log",
           format="{time:DD-MM-YYYY HH:mm:ss} | {level} | {message}",
           level="DEBUG",
           enqueue=True,
           rotation="00:00",
           compression="zip")


TOKEN = getenv('DISCORD_BOT_TOKEN')
PREFIX = "+"
GUILD = 490181820353347584
OWNER_IDS = [375722626636578816]


class Bot(BotBase):
    def __init__(self):
        self.TOKEN = TOKEN
        self.PREFIX = PREFIX
        self.ready = False
        self.guild = None
        self.scheduler = AsyncIOScheduler()

        db.autosave(self.scheduler)

        super().__init__(command_prefix=PREFIX,
                         case_insensitive=True,
                         owner_ids=OWNER_IDS,
                         intents=Intents.all())

    @logger.catch
    def run(self, version):
        self.VERSION = version

        print("Running bot...")
        super().run(self.TOKEN, reconnect=True)


    @logger.catch
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            print("\nLogged in as:", bot.user)
            print("ID:", bot.user.id)
            print("\nAvailable guilds:")
            for guild in bot.guilds:
                print(guild.name, guild.id)
            self.scheduler.start()
            print("\nReady to use!\n")
            #await self.get_user(OWNER_IDS[0]).send("I am online!\nReady to use!")

        else:
            print("Bot reconnected")


    async def on_connect(self):
        print("Bot connected")

    async def on_disconnect(self):
        print("Bot disconnected")

    async def on_command_error(self, ctx, exc):
        if isinstance(exc, CommandNotFound):
            embed = Embed(title=':exclamation: Ошибка!', description=f'Команда `{ctx.message.content}` не найдена.', color = Color.red())
            await ctx.send(embed=embed, delete_after = 10)
        elif isinstance(exc, CommandOnCooldown):
            embed = Embed(title=f"{str(exc.cooldown.type).split('.')[-1]}", description =f"Команда на откате. Ожидайте {int(exc.retry_after)} {russian_plural(int(exc.retry_after),['секунду','секунды','секунд'])}.") #exc.retry_after:,.2f
            await ctx.send(embed)
        else:
            try:
                if hasattr(ctx.command, 'on_error'):
                    embed = Embed(title="Error.", description = "Something went wrong, an error occured.\nCheck logs.", timestamp=datetime.now(), color = Color.red())
                    await dev.send(embed=embed)
                else:
                    embed = Embed(title=f'Ошибка при выполнении команды {ctx.command}.', description=f'`{ctx.command.qualified_name} {ctx.command.signature}`\n{error}', color = Color.red())
                    channel = self.get_channel(id=constants.AUDIT_LOG_CHANNEL)
                    await channel.send(embed=embed)
            except:
                embed = Embed(title=f'Ошибка при выполнении команды {ctx.command}.', description=f'`{ctx.command.qualified_name} {ctx.command.signature}`\n{error}', color = Color.red())
                channel = self.get_channel(id=constants.AUDIT_LOG_CHANNEL)
                await channel.send(embed=embed)
            finally:
                raise exc


    @logger.catch
    async def on_message(self, message):
        await self.process_commands(message)


bot = Bot()
