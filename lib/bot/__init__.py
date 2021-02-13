from asyncio import sleep
from datetime import datetime
from glob import glob
from os import getenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import Color, Embed, Intents
from discord.ext.commands import Bot as BotBase, Context
from discord.ext.commands import (CommandNotFound, CommandOnCooldown, DisabledCommand, 
                                NoPrivateMessage, PrivateMessageOnly)
from discord.ext.commands.errors import CheckFailure, CheckAnyFailure, MissingPermissions
from discord.channel import DMChannel
from discord.errors import HTTPException, Forbidden

from loguru import logger

from ..db import db
from ..utils.constants import GUILD_ID, AUDIT_LOG_CHANNEL
from ..utils.utils import russian_plural, insert_new_user_in_db

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
        print(f"{cog.capitalize()} cog ready")

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
        self.channels_with_message_counting = [
            546404724216430602, #админка
            686499834949140506, #гвардия
            698568751968419850, #спонсорка
            721480135043448954, #общение
            546408250158088192, #поддержка
            644523860326219776, #медиа
            546700132390010882, #ваши-вопросы
            546700132390010882, #заявки-на-рассмотрение
            809519845707743272  #spam (dev server)
        ]

        db.autosave(self.scheduler)

        super().__init__(command_prefix=PREFIX,
                         case_insensitive=True,
                         owner_ids=OWNER_IDS,
                         intents=Intents.all()
                        )

    @logger.catch
    def setup(self):
        for cog in COGS:
            self.load_extension(f"lib.cogs.{cog}")
            #print(f"{cog} cog loaded")

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
            self.guild = self.get_guild(GUILD_ID)
            self.scheduler.start()

            print("\nLogged in as:", bot.user)
            print("ID:", bot.user.id)
            print("\nAvailable guilds:")
            for guild in bot.guilds:
                print(guild.name, guild.id, "\n")
                if guild.id == GUILD_ID:
                    for member in guild.members:
                        if member.pending is False:
                            if rec := db.fetchone(["user_id"], "users_info", "user_id", member.id) is None:
                                insert_new_user_in_db(member)

            

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True

            self.load_extension("jishaku")
            print("Jishaku loaded")
                
            
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
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f'Команда `{ctx.message.clean_content}` не найдена.', 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 10)

        elif isinstance(exc, CommandOnCooldown):
            embed = Embed(
                title=f"{str(exc.cooldown.type).split('.')[-1]} cooldown", 
                description=f"Команда на откате. Ожидайте {int(exc.retry_after)+1} {russian_plural(int(exc.retry_after)+1,['секунду','секунды','секунд'])}.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 10)

        elif isinstance(exc, DisabledCommand):
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f"Команда `{ctx.command}` отключена.", 
                color=Color.red
            )
            await ctx.send(embed=embed, delete_after = 10)

        elif isinstance(exc, NoPrivateMessage):
            try:
                embed = Embed(
                    title=':exclamation: Ошибка!', 
                    description=f"Команда `{ctx.command}` не может быть использована в личных сообщениях.", 
                    color=Color.red()
                )
                await ctx.author.send(embed=embed, delete_after = 30)
            except HTTPException:
                pass

        elif isinstance(exc, PrivateMessageOnly):
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f"Команда `{ctx.command}` работает только в личных сообщениях. Она не может быть использована на сервере.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 30)

        elif isinstance(exc, MissingPermissions):
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f"У бота недостаточно прав для выполнения действия.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 30)

        elif isinstance(exc, Forbidden):
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f"Недостаточно прав для выполнения действия.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 30)

        elif isinstance(exc, HTTPException):
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f"Невозможно отправить сообщение. Возможно, превышен лимит символов.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 30)

        elif isinstance(exc, CheckFailure) or isinstance(exc, CheckAnyFailure):
            embed = Embed(
                title=':exclamation: Ошибка!', 
                description=f"{ctx.author.mention}\nНевозможно выполнить указанную команду."
                             "\nВозможно, вы используете неправильный канал, у вас недостаточный уровень или отсутсвуют права на выполнение запрошенной команды.", 
                color=Color.red()
            )
            await ctx.send(embed=embed, delete_after = 15)

        else:
            channel = self.get_channel(id=AUDIT_LOG_CHANNEL)
            try:
                if hasattr(ctx.command, 'on_error'):
                    embed = Embed(
                        title="Error.", 
                        description="Something went wrong, an error occured.\nCheck logs.", 
                        timestamp=datetime.utcnow(), 
                        color=Color.red()
                    )
                    await dev.send(embed=embed)
                else:
                    embed = Embed(
                        title=f'Ошибка при выполнении команды {ctx.command}.', 
                        description=f'`{ctx.command.signature}`\n{exc}', 
                        color=Color.red()
                    )
                    if isinstance(ctx.channel, DMChannel):
                        embed.add_field(name="Additional info:", value="Exception occured in DMChannel.")
                    await channel.send(embed=embed)
            except:
                embed = Embed(
                    title=f'Ошибка при выполнении команды {ctx.command}.', 
                    description=f'`{ctx.command.signature}`\n{exc}', 
                    color=Color.red()
                )
                if isinstance(ctx.channel, DMChannel):
                    embed.add_field(name="Additional info:", value="Exception occured in DMChannel.")
                await channel.send(embed=embed)
            finally:
                raise exc


    @logger.catch
    async def on_message(self, message):
        await self.process_commands(message)


bot = Bot()
