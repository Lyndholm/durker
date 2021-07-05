import os
from asyncio import sleep
from datetime import datetime
from os import getenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from better_profanity import Profanity
from discord import Color, Embed, Intents
from discord.channel import DMChannel
from discord.errors import Forbidden, HTTPException
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import (CheckAnyFailure, CheckFailure,
                                  CommandNotFound, CommandOnCooldown, Context,
                                  DisabledCommand, ExtensionAlreadyLoaded,
                                  ExtensionNotLoaded, MaxConcurrencyReached,
                                  MissingPermissions, MissingRequiredArgument,
                                  NoPrivateMessage, PrivateMessageOnly)
from dotenv import load_dotenv
from loguru import logger

from ..db import db
from ..utils.constants import AUDIT_LOG_CHANNEL, GUILD_ID
from ..utils.exceptions import (InForbiddenTextChannel, InsufficientLevel,
                                NotInAllowedTextChannel)
from ..utils.utils import (cooldown_timer_str, get_command_required_level,
                           get_command_text_channels, insert_new_user_in_db)

load_dotenv()
logger.add("logs/{time:DD-MM-YYYY---HH-mm-ss}.log",
           format="{time:DD-MM-YYYY HH:mm:ss} | {level} | {message}",
           level="DEBUG",
           enqueue=True,
           rotation="00:00",
           compression="zip")


TOKEN = getenv('DISCORD_BOT_TOKEN')
PREFIX = '+'
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
            with open('./data/txt/banlist.txt', 'r', encoding='utf-8') as f:
                self.banlist = [int(line.strip()) for line in f.readlines()]
        except FileNotFoundError:
            self.banlist = []

        self.load_music_cogs(self.scheduler)

        super().__init__(command_prefix=PREFIX,
                         case_insensitive=True,
                         owner_ids=OWNER_IDS,
                         intents=Intents.all(),
                         max_messages=10000
                        )

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
        sched.add_job(self.load_mein_radio_cog_scheduler, CronTrigger(day_of_week=0, hour=3))
        sched.add_job(self.load_mein_radio_cog_scheduler, CronTrigger(day_of_week=2, hour=3))
        sched.add_job(self.load_mein_radio_cog_scheduler, CronTrigger(day_of_week=4, hour=3))
        sched.add_job(self.load_lofi_radio_cog_scheduler, CronTrigger(day_of_week=1, hour=3))
        sched.add_job(self.load_lofi_radio_cog_scheduler, CronTrigger(day_of_week=3, hour=3))
        sched.add_job(self.load_music_player_cog_scheduler, CronTrigger(day_of_week=5, hour=3))

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
            print("\nAvailable guilds:")
            for guild in bot.guilds:
                print(guild.name, guild.id, "\n")
                if guild.id == GUILD_ID:
                    for member in guild.members:
                        if member.pending is False:
                            if rec := db.fetchone(["user_id"], "users_info", "user_id", member.id) is None:
                                insert_new_user_in_db(member)


            db.execute("DELETE FROM voice_activity;")
            db.commit()

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

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

    async def on_command_error(self, ctx, exc):
        if not ctx.command.has_error_handler():
            if isinstance(exc, CommandNotFound):
                embed = Embed(
                    title='❗ Ошибка!',
                    description=f'Команда `{ctx.message.clean_content}` не найдена.',
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=10)

            elif isinstance(exc, CommandOnCooldown):
                embed = Embed(
                    title=f"{str(exc.cooldown.type).split('.')[-1]} cooldown",
                    description=f"Команда на откате. Ожидайте {cooldown_timer_str(exc.retry_after)}",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)

            elif isinstance(exc, DisabledCommand):
                embed = Embed(
                    title='❗ Ошибка!',
                    description=f"Команда `{ctx.command}` отключена.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)

            elif isinstance(exc, NoPrivateMessage):
                try:
                    embed = Embed(
                        title='❗ Ошибка!',
                        description=f"Команда `{ctx.command}` не может быть использована в личных сообщениях.",
                        color=Color.red()
                    )
                    await ctx.reply(embed=embed, mention_author=False)
                except HTTPException:
                    pass

            elif isinstance(exc, PrivateMessageOnly):
                embed = Embed(
                    title='❗ Ошибка!',
                    description=f"Команда `{ctx.command}` работает только в личных сообщениях. Она не может быть использована на сервере.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)

            elif isinstance(exc, MissingPermissions):
                embed = Embed(
                    title='❗ MissingPermissions',
                    description=f"Недостаточно прав для выполнения действия.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)

            elif isinstance(exc, Forbidden):
                embed = Embed(
                    title='❗ Forbidden',
                    description=f"Недостаточно прав для выполнения действия.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)

            elif isinstance(exc, HTTPException):
                embed = Embed(
                    title='❗ Ошибка!',
                    description=f"Невозможно отправить сообщение. Возможно, превышен лимит символов.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)

            elif isinstance(exc, MaxConcurrencyReached):
                embed = Embed(
                    title='❗ Внимание!',
                    description=f"Команда `{ctx.command}` уже запущена.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)

            elif isinstance(exc, MissingRequiredArgument):
                if str(ctx.command) == 'knb':
                    embed = Embed(
                        title='❗ Внимание!',
                        description=f'Укажите, что вы выбрали: камень, ножницы или бумагу.\n' \
                                    f'`{ctx.command.usage}`',
                        color= Color.red()
                    )
                    await ctx.send(embed=embed, delete_after=15)
                elif str(ctx.command) == '8ball':
                    embed = Embed(
                        title='❗ Внимание!',
                        description=f"Пожалуйста, укажите вопрос.",
                        color = Color.red()
                    )
                    await ctx.reply(embed=embed, mention_author=False, delete_after=15)
                elif str(ctx.command) == 'randint':
                    embed = Embed(
                        title='❗ Внимание!',
                        description=f"Пожалуйста, укажите корректный диапазон **целых** чисел.",
                        color = Color.red()
                    )
                    await ctx.reply(embed=embed, mention_author=False, delete_after=15)
                else:
                    embed = Embed(
                        title='❗ Внимание!',
                        description=f"Пропущен один или несколько параметров. Параметры команды можно узнать в help меню.",
                        color=Color.red()
                    )
                    await ctx.reply(embed=embed, mention_author=False)

            elif isinstance(exc, InsufficientLevel):
                level = await get_command_required_level(ctx.command)
                member_level = db.fetchone(['level'], 'leveling', 'user_id', ctx.author.id)[0]
                embed = Embed(
                    title='🔒 Недостаточный уровень!',
                    description=f"Команда `{ctx.command.name}` требует наличия **{level}** уровня " \
                                f"и выше.\nВаш текущий уровень: **{member_level}**.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)

            elif isinstance(exc, NotInAllowedTextChannel) or isinstance(exc, InForbiddenTextChannel):
                txt = await get_command_text_channels(ctx.command)
                embed = Embed(
                    title='⚠️ Неправильный канал!',
                    description=f"Команда `{ctx.command.name}` {txt.lower()}",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False)

            elif isinstance(exc, CheckFailure) or isinstance(exc, CheckAnyFailure):
                embed = Embed(
                    title='❗ Ошибка!',
                    description=f"{ctx.author.mention}\nНевозможно выполнить указанную команду."
                                "\nВозможно, у вас отсутствуют права на выполнение запрошенного метода.",
                    color=Color.red()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=15)

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
                        await self.get_user(OWNER_IDS[0]).send(embed=embed)
                    else:
                        embed = Embed(
                            title=f'Ошибка при выполнении команды {ctx.command}.',
                            description=f'`{ctx.command.signature if ctx.command.signature else None}`\n{exc}',
                            color=Color.red(),
                            timestamp=datetime.utcnow()
                        )
                        if isinstance(ctx.channel, DMChannel):
                            embed.add_field(name="Additional info:", value="Exception occured in DMChannel.")
                        await channel.send(embed=embed)
                except:
                    embed = Embed(
                        title=f'Ошибка при выполнении команды {ctx.command}.',
                        description=f'`{ctx.command.signature if ctx.command.signature else None}`\n{exc}',
                        color=Color.red(),
                        timestamp=datetime.utcnow()
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
