from discord import Intents
from discord.ext.commands import Bot as BotBase
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from os import getenv

from loguru import logger


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
    async def on_connect(self):
        print("Bot connected")

    @logger.catch
    async def on_disconnect(self):
        print("Bot disconnected")

    @logger.catch
    async def on_ready(self):
        if not self.ready:
            self.ready = True
            print("\nLogged in as:", bot.user)
            print("ID:", bot.user.id)
            print("\nAvailable guilds:")
            for guild in bot.guilds:
                print(guild.name, guild.id)
            print("\nReady to use!\n")

        else:
            print("Bot reconnected")

    @logger.catch
    async def on_message(self, message):
        pass


bot = Bot()
