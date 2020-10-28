import os

import discord
from discord.ext import commands
from loguru import logger

from database import db

logger.add("logs/{time:DD-MM-YYYY---HH-mm-ss}.log",
           format="{time:DD-MM-YYYY HH:mm:ss} | {level} | {message}",
           level="DEBUG",
           enqueue=True,
           rotation="00:00",
           compression="zip")

token = os.environ.get('DISCORD_BOT_TOKEN')

bot = commands.Bot(
    command_prefix="_",
    case_insensitive=True,
    intents=discord.Intents.all()
)


@bot.event
@logger.catch
async def on_ready():
    print("\nLogged in as:", bot.user.name)
    print("ID:", bot.user.id)
    print("\nAvailable guilds:")
    for guild in bot.guilds:
        print(guild.name, guild.id)
        for member in guild.members:
            rec = db.fetchone(["user_id"], "users_info", 'user_id', member.id)
            if rec is None:
                db.insert("users_info", {
                    "user_id": member.id,
                    "nickname": str(member.display_name),
                    "mention": str(member.mention),
                    "joined_at": member.joined_at
                })

    print("\nReady to use!\n")


@bot.event
async def on_message(message):
    print(message.content)
    await bot.process_commands(message)


bot.run(token)
