import asyncio
import os
from datetime import datetime
from os import getenv

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from better_profanity import Profanity
from discord import Intents
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import (Context, ExtensionAlreadyLoaded,
                                  ExtensionNotLoaded)
from dotenv import load_dotenv
from loguru import logger

from ..db import db
from ..utils.constants import GUILD_ID
from ..utils.utils import insert_new_user_in_db

load_dotenv()
logger.add("logs/{time:DD-MM-YYYY---HH-mm-ss}.log",
           format="{time:DD-MM-YYYY HH:mm:ss} | {level} | {message}",
           level="DEBUG",
           enqueue=True,
           rotation="00:00",
           compression="zip")


TOKEN = getenv('DISCORD_BOT_TOKEN')
PREFIX = ('+', 'var ')
OWNER_IDS = [375722626636578816]
COGS = [path[:-3] for path in os.listdir('./lib/cogs') if path[-3:] == '.py']


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
        self.pg_pool = None
        self.scheduler = AsyncIOScheduler()
        self.profanity = Profanity()
        self.channels_with_message_counting = [
            546404724216430602, #админка
            686499834949140506, #гвардия
            698568751968419850, #спонсорка
            721480135043448954, #общение
            546408250158088192, #поддержка
            644523860326219776, #медиа
        ]
        try:
            data = db.records('SELECT user_id FROM blacklist')
            self.banlist = [i[0] for i in data]
        except:
            self.banlist = []

        self.load_music_cogs(self.scheduler)

        super().__init__(command_prefix=PREFIX,
                         case_insensitive=True,
                         strip_after_prefix=True,
                         owner_ids=OWNER_IDS,
                         intents=Intents.all(),
                         max_messages=10000
                        )


    def create_db_pool(self, loop: asyncio.BaseEventLoop) -> None:
        db_credentials = {
            "database": os.getenv('DB_NAME'),
            "user": os.getenv('DB_USER'),
            "password": os.getenv('DB_PASS'),
            "host": os.getenv('DB_HOST')
        }
        try:
            self.pg_pool = loop.run_until_complete(
                asyncpg.create_pool(**db_credentials)
            )
            print('Connected to the database')
        except Exception as e:
            raise e

    @logger.catch
    def setup(self):
        for cog in COGS:
            self.load_extension(f"lib.cogs.{cog}")

        print("Setup complete")


    @logger.catch
    def run(self, version):
        self.VERSION = version

        print("Running setup...")
        self.setup()

        print('Attempting to connect to the database...')
        self.create_db_pool(self.loop)

        print("Running bot...")
        super().run(self.TOKEN, reconnect=True)

    @logger.catch
    async def load_mein_radio_cog_scheduler(self):
        try:
            cogs = (
                "lib.cogs.music.lofi_radio",
                "lib.cogs.music.music_player",
                "lib.cogs.music.gachi_radio"
            )
            for c in cogs:
                try:
                    self.unload_extension(c)
                except ExtensionNotLoaded:
                    continue
            self.load_extension("lib.cogs.music.mein_radio")
        except ExtensionAlreadyLoaded:
            pass

    @logger.catch
    async def load_gachi_radio_cog_scheduler(self):
        try:
            cogs = (
                "lib.cogs.music.lofi_radio",
                "lib.cogs.music.music_player",
                "lib.cogs.music.mein_radio"
            )
            for c in cogs:
                try:
                    self.unload_extension(c)
                except ExtensionNotLoaded:
                    continue
            self.load_extension("lib.cogs.music.gachi_radio")
        except ExtensionAlreadyLoaded:
            pass

    @logger.catch
    async def load_lofi_radio_cog_scheduler(self):
        try:
            cogs = (
                "lib.cogs.music.music_player",
                "lib.cogs.music.mein_radio",
                "lib.cogs.music.gachi_radio"
            )
            for c in cogs:
                try:
                    self.unload_extension(c)
                except ExtensionNotLoaded:
                    continue
            self.load_extension("lib.cogs.music.lofi_radio")
        except ExtensionAlreadyLoaded:
            pass

    @logger.catch
    async def load_music_player_cog_scheduler(self):
        try:
            cogs = (
                "lib.cogs.music.lofi_radio",
                "lib.cogs.music.mein_radio",
                "lib.cogs.music.gachi_radio"
            )
            for c in cogs:
                try:
                    self.unload_extension(c)
                except ExtensionNotLoaded:
                    continue
            self.load_extension("lib.cogs.music.music_player")
        except ExtensionAlreadyLoaded:
            pass

    @logger.catch
    def load_music_cogs(self, sched):
        sched.add_job(self.load_mein_radio_cog_scheduler, CronTrigger(day_of_week=0, hour=3), misfire_grace_time=300)
        sched.add_job(self.load_mein_radio_cog_scheduler, CronTrigger(day_of_week=2, hour=3), misfire_grace_time=300)
        sched.add_job(self.load_mein_radio_cog_scheduler, CronTrigger(day_of_week=4, hour=3), misfire_grace_time=300)
        sched.add_job(self.load_lofi_radio_cog_scheduler, CronTrigger(day_of_week=1, hour=3), misfire_grace_time=300)
        sched.add_job(self.load_lofi_radio_cog_scheduler, CronTrigger(day_of_week=3, hour=3), misfire_grace_time=300)
        sched.add_job(self.load_music_player_cog_scheduler, CronTrigger(day_of_week=5, hour=3), misfire_grace_time=300)

    @logger.catch
    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None:
            if message.author.id in self.banlist:
                return
            elif not self.ready:
                await ctx.reply(
                    "Бот не готов принимать сообщения и обрабатывать команды. Пожалуйста, подождите.",
                    mention_author=False, delete_after=60
                )
            else:
                await self.invoke(ctx)

    @logger.catch
    async def on_ready(self):
        if not self.ready:
            self.guild = self.get_guild(GUILD_ID)
            self.scheduler.start()
            self.profanity.load_censor_words_from_file("./data/txt/profanity.txt")
            print("\nLogged in as:", bot.user)
            print("ID:", bot.user.id)
            for member in self.guild.members:
                if member.pending is False:
                    rec = await self.pg_pool.fetchval('SELECT user_id FROM users_info WHERE user_id = $1', member.id)
                    if rec is None:
                        await insert_new_user_in_db(member)


            db.execute("DELETE FROM voice_activity;")
            db.commit()

            while not self.cogs_ready.all_ready():
                await asyncio.sleep(0.5)

            self.ready = True

            self.load_extension("jishaku")
            self.get_command("jishaku").hidden = True
            print("Jishaku loaded")


            print("\nReady to use!\n")
            await self.get_user(OWNER_IDS[0]).send(
                "I am online!\nReady to use!\nStart time: "
                f"{datetime.now().strftime('%d.%m.%Y %H.%M.%S')}"
            )

        else:
            print("Bot reconnected")


    async def on_connect(self):
        print("Bot connected")

    async def on_disconnect(self):
        print("Bot disconnected")

    @logger.catch
    async def on_message(self, message):
        await self.process_commands(message)


bot = Bot()
