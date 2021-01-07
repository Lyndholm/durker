from asyncio import sleep
from datetime import datetime
from glob import glob
from os import getenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import Color, Embed, Intents
from discord.ext.commands import Bot as BotBase, Context
from discord.ext.commands import (CommandNotFound, CommandOnCooldown, DisabledCommand, 
                                NoPrivateMessage, PrivateMessageOnly)
from discord.errors import HTTPException, Forbidden
from loguru import logger

from ..db import db
from ..utils import constants
from ..utils.utils import russian_plural

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
COGS = [path.split("\\")[-1][:-3] for path in glob("./lib/cogs/*.py")]


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f"{cog.title()} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.TOKEN = TOKEN
        self.PREFIX = PREFIX
        self.ready = False
        self.cogs_ready = Ready()
        self.guild = None
        self.scheduler = AsyncIOScheduler()

        db.autosave(self.scheduler)

        super().__init__(command_prefix=PREFIX,
                         case_insensitive=True,
                         owner_ids=OWNER_IDS,
                         intents=Intents.all())

    @logger.catch
    def setup(self):
        for cog in COGS:
            self.load_extension(f"lib.cogs.{cog}")
            print(f"{cog} cog loaded")

        print("Setup complete")


    @logger.catch
    def run(self, version):
        self.VERSION = version

        print("Running setup...")
        self.setup()

        print("Running bot...")
        super().run(self.TOKEN, reconnect=True)


    @logger.catch
    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None:
            if self.ready:
                await self.invoke(ctx)
            else:
                await ctx.send("Бот не готов принимать сообщения и обрабатывать команды. Пожалуйста, подождите.", delete_after=60)

    @logger.catch
    async def on_ready(self):
        if not self.ready:
            self.scheduler.start()

            print("\nLogged in as:", bot.user)
            print("ID:", bot.user.id)
            print("\nAvailable guilds:")
            for guild in bot.guilds:
                print(guild.name, guild.id, "\n")
            

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True
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
            embed = Embed(title=f"{str(exc.cooldown.type).split('.')[-1]}", description =f"Команда на откате. Ожидайте {int(exc.retry_after)} {russian_plural(int(exc.retry_after),['секунду','секунды','секунд'])}.", color = Color.red()) #exc.retry_after:,.2f
            await ctx.send(embed=embed, delete_after = 10)

        elif isinstance(exc, DisabledCommand):
            embed = Embed(title=':exclamation: Ошибка!', description =f"Команда отключена.", color = Color.red())
            await ctx.send(embed=embed, delete_after = 10)

        elif isinstance(exc, NoPrivateMessage):
            try:
                embed = Embed(title=':exclamation: Ошибка!', description =f"Команда `{ctx.command}` не может быть использована в личных сообщениях.", color = Color.red())
                await ctx.author.send(embed=embed, delete_after = 30)
            except HTTPException:
                pass

        elif isinstance(exc, PrivateMessageOnly):
            embed = Embed(title=':exclamation: Ошибка!', description =f"Команда `{ctx.command}` работает только в личных сообщениях. Она не может быть использована на сервере.", color = Color.red())
            await ctx.send(embed=embed, delete_after = 30)

        elif isinstance(exc.original, Forbidden):
            embed = Embed(title=':exclamation: Ошибка!', description =f"Недостаточно прав для выполнения действия.", color= Color.red())
            await ctx.send(embed=embed, delete_after = 30)

        # elif isinstance(exc.original, HTTPException):
        #     embed = Embed(title=':exclamation: Ошибка!', description =f"Невозможно отправить сообщение.", color= Color.red())
        #     await ctx.send(embed=embed, delete_after = 30)

        else:
            try:
                if hasattr(ctx.command, 'on_error'):
                    embed = Embed(title="Error.", description = "Something went wrong, an error occured.\nCheck logs.", timestamp=datetime.now(), color = Color.red())
                    await dev.send(embed=embed)
                else:
                    embed = Embed(title=f'Ошибка при выполнении команды {ctx.command}.', description=f'`{ctx.command.qualified_name} {ctx.command.signature}`\n{exc}', color = Color.red())
                    channel = self.get_channel(id=constants.AUDIT_LOG_CHANNEL)
                    await channel.send(embed=embed)
            except:
                embed = Embed(title=f'Ошибка при выполнении команды {ctx.command}.', description=f'`{ctx.command.qualified_name} {ctx.command.signature}`\n{exc}', color = Color.red())
                channel = self.get_channel(id=constants.AUDIT_LOG_CHANNEL)
                await channel.send(embed=embed)
            finally:
                raise exc


    @logger.catch
    async def on_message(self, message):
        await self.process_commands(message)


bot = Bot()
