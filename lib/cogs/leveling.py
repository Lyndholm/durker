from datetime import datetime, timedelta
from io import BytesIO
from math import floor
from random import randint
from typing import Optional, Tuple

from aiohttp import ClientSession
from discord import Embed, File, Member, Message, Status, TextChannel
from discord.ext.commands import Cog, command, guild_only
from discord.utils import remove_markdown
from jishaku.functools import executor_function
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from ..db import db
from ..utils.checks import is_channel
from ..utils.constants import STATS_CHANNEL
from ..utils.decorators import listen_for_guilds
from ..utils.utils import (check_member_privacy, edit_user_reputation,
                           find_n_term_of_arithmetic_progression,
                           load_commands_from_json)

cmd = load_commands_from_json("leveling")


class RankCardImage():
    """Class for generating rank card image."""
    def __init__(self, member: Member) -> None:
        self.member = member
        self.bar_offset_x = 320
        self.bar_offset_y = 160
        self.bar_offset_x_1 = 950
        self.bar_offset_y_1 = 200
        self.big_font = ImageFont.FreeTypeFont(
            "./data/fonts/JovannyLemonad-Bender.otf", 75)
        self.medium_font = ImageFont.FreeTypeFont(
            "./data/fonts/JovannyLemonad-Bender.otf", 55)
        self.small_font = ImageFont.FreeTypeFont(
            "./data/fonts/JovannyLemonad-Bender.otf", 40)

    def get_member_rank_data(self) -> Tuple[int, int, int, int]:
        xp, level = db.fetchone(
            ['xp', 'level'], 'leveling', 'user_id', self.member.id)
        xp_end = floor(5 * (level ^ 2) + 50 * level + 100)
        rank = self.rank_position()
        return level, xp, xp_end, rank

    def rank_position(self) -> int:
        cursor = db.get_cursor()
        cursor.execute("SELECT user_id FROM leveling ORDER BY xp_total DESC")
        data = cursor.fetchall()
        position = [i for sub in data for i in sub].index(self.member.id)+1
        return position

    def get_status_color(self) -> str:
        if self.member.status is Status.online:
            color = "#57F287"
        elif self.member.status is Status.idle:
            color = "#FEE75C"
        elif self.member.status in (Status.dnd, Status.do_not_disturb):
            color = "#ED4245"
        elif self.member.status in (Status.offline, Status.invisible):
            color = "#FFFFFF"
        else:
            color = "#57F287"
        return color

    async def paste_rank_background(self, image: Image, bg_url: str) -> None:
        async with ClientSession() as session:
            async with session.get(bg_url) as r:
                if r.status == 200:
                    bg = Image.open(BytesIO(await r.read())).convert("RGBA").resize((1000, 240))
                    image.paste(bg, (0, 0))

    async def paste_member_avatar(self) -> None:
        async with ClientSession() as session:
            async with session.get(str(self.member.avatar_url)) as response:
                avatar = await response.read()
        icon = Image.open(BytesIO(avatar)).convert("RGBA").resize((200, 200))
        big_size = (icon.size[0] * 3, icon.size[1] * 3)
        mask = Image.new("L", big_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + big_size, 255)
        draw.ellipse((140 * 3, 140 * 3, 189 * 3, 189 * 3), 0)
        mask = mask.resize(icon.size, Image.ANTIALIAS)
        icon.putalpha(mask)
        self.image.paste(icon, (20, 20), mask=icon)

    @executor_function
    def draw_progress_bar(self, bar_background: str, bar_color: str, xp: int, xp_end: int) -> None:
        bar_length = self.bar_offset_x_1 - self.bar_offset_x
        circle_size = self.bar_offset_y_1 - self.bar_offset_y
        progress = (xp_end - xp) * 100 / xp_end
        progress = 100 - progress
        progress_bar_length = round(bar_length * progress / 100)

        self.draw.rectangle(
            (self.bar_offset_x, self.bar_offset_y,
             self.bar_offset_x_1, self.bar_offset_y_1),
            fill=bar_background
        )
        self.draw.ellipse(
            (self.bar_offset_x - circle_size // 2, self.bar_offset_y,
             self.bar_offset_x + circle_size // 2, self.bar_offset_y_1),
            fill=bar_background
        )
        self.draw.ellipse(
            (self.bar_offset_x_1 - circle_size // 2, self.bar_offset_y,
             self.bar_offset_x_1 + circle_size // 2, self.bar_offset_y_1),
            fill=bar_background
        )

        bar_offset_x_1 = self.bar_offset_x + progress_bar_length
        self.draw.rectangle(
            (self.bar_offset_x, self.bar_offset_y, bar_offset_x_1, self.bar_offset_y_1), fill=bar_color)
        self.draw.ellipse(
            (self.bar_offset_x - circle_size // 2, self.bar_offset_y,
             self.bar_offset_x + circle_size // 2, self.bar_offset_y_1),
            fill=bar_color
        )
        self.draw.ellipse(
            (bar_offset_x_1 - circle_size // 2, self.bar_offset_y,
             bar_offset_x_1 + circle_size // 2, self.bar_offset_y_1),
            fill=bar_color
        )

    @executor_function
    def draw_username(self, name_color: str, discriminator_color: str) -> None:
        username = self.member.name
        discriminator = f'#{self.member.discriminator}'

        text_size = self.draw.textsize(username, font=self.medium_font)
        offset_x = self.bar_offset_x
        offset_y = 10
        self.draw.text((offset_x, offset_y), username,
                       font=self.medium_font, fill=name_color)
        offset_x += text_size[0] + 5
        offset_y += 10
        self.draw.text((offset_x, offset_y), discriminator,
                       font=self.small_font, fill=discriminator_color)

    @executor_function
    def draw_level(self, level: int, level_str_color: str, level_int_color: str) -> None:
        text_size = self.draw.textsize("Уровень", font=self.medium_font)
        offset_x = self.bar_offset_x
        offset_y = self.bar_offset_y - text_size[1] - 10
        self.draw.text((offset_x, offset_y), "Уровень",
                       font=self.medium_font, fill=level_str_color)

        offset_x += text_size[0] + 5
        text_size = self.draw.textsize(str(level), font=self.big_font)
        offset_y = self.bar_offset_y - text_size[1] - 10
        self.draw.text((offset_x, offset_y), str(level),
                       font=self.big_font, fill=level_int_color)

    @executor_function
    def draw_xp(self, xp_start: int, xp_end: int, xp_start_color: str, xp_end_color: str) -> None:
        text_size = self.draw.textsize(
            f"/ {xp_end} XP", font=self.small_font)
        offset_x = self.bar_offset_x_1 - text_size[0]
        offset_y = self.bar_offset_y - text_size[1] - 9
        self.draw.text(
            (offset_x, offset_y), f"/ {xp_end:,} XP", font=self.small_font, fill=xp_end_color)
        text_size = self.draw.textsize(f"{xp_start:,}", font=self.small_font)
        offset_x -= text_size[0] + 8
        self.draw.text((offset_x, offset_y),
                       f"{xp_start:,}", font=self.small_font, fill=xp_start_color)

    @executor_function
    def draw_rank(self, rank: int, placement_int_color: str, placement_str_color: str) -> None:
        text_size = self.draw.textsize(f"#{rank}", font=self.medium_font)
        offset_x = self.bar_offset_x_1 - text_size[0] + 15
        offset_y = 10
        self.draw.text((offset_x, offset_y),
                       f"#{rank}", font=self.medium_font, fill=placement_int_color)
        text_size = self.draw.textsize("Ранг", font=self.small_font)
        offset_x -= text_size[0] + 5
        self.draw.text((offset_x, offset_y + 15), "Ранг",
                       font=self.small_font, fill=placement_str_color)

    async def generate_rank_card(self) -> File:
        level, xp, xp_end, rank = self.get_member_rank_data()

        customization = db.record('SELECT * FROM stats_customization WHERE user_id = %s',
                                  self.member.id)
        background_color, background_image, bar_color, bar_background, level_int_color, \
        level_str_color, username_color, discriminator_color, xp_start_color, xp_end_color, \
        placement_int_color, placement_str_color = customization[1:]

        self.image = Image.new("RGB", (1000, 240), background_color)
        if background_image:
            await self.paste_rank_background(image=self.image, bg_url=background_image)

        self.draw = ImageDraw.Draw(self.image, "RGB")
        self.draw.ellipse((162, 162, 206, 206), fill=self.get_status_color())

        await self.paste_member_avatar()
        await self.draw_progress_bar(bar_background, bar_color, xp, xp_end)
        await self.draw_username(username_color, discriminator_color)
        await self.draw_level(level, level_str_color, level_int_color)
        await self.draw_xp(xp, xp_end, xp_start_color, xp_end_color)
        await self.draw_rank(rank, placement_int_color, placement_str_color)

        byte_io = BytesIO()
        self.image.save(byte_io, format='PNG')
        card_file = File(BytesIO(byte_io.getvalue()), filename="rank.png")
        return card_file


class Leveling(Cog, name='Система уровней'):
    def __init__(self, bot):
        self.bot = bot
        self.profanity_whitelisted_users = (
            384728793895665675,  # tvoya_pechal
            342783617983840257,  # lexenus
            375722626636578816,  # lyndholm
        )
        self.channels_with_xp_counting = (
            546404724216430602,  # админы-текст
            686499834949140506,  # гвардия-общение
            698568751968419850,  # спонсорское-общение
            721480135043448954,  # общение (главный чат)
            546408250158088192,  # поддержка,
            644523860326219776,  # медиа,
            708601604353556491,  # консоль на dev сервере
            777979537795055636,  # testing на dev сервере
        )

    @logger.catch
    async def can_message_be_counted(self, message: Message) -> bool:
        message_content = remove_markdown(message.clean_content)
        ctx = await self.bot.get_context(message)

        if not message.author.bot and isinstance(message.channel, TextChannel):
            if self.bot.profanity.contains_profanity(message_content):
                if message.author.id not in self.profanity_whitelisted_users:
                    return False
            if not ctx.command:
                if message.channel.id in self.channels_with_xp_counting:
                    if len(message.clean_content) > 2:
                        if message.clean_content[0] != "<" and message.clean_content[-1] != ">":
                            return True
                    elif message.attachments:
                        return True
                    else:
                        return False

    @logger.catch
    async def process_xp(self, message: Message):
        level, xp, xp_total, xp_lock = db.fetchone(
            ['level', 'xp', 'xp_total', 'xp_lock'], 'leveling', 'user_id', message.author.id)

        if datetime.now() > xp_lock:
            await self.add_xp(message, xp, xp_total, level)

    @logger.catch
    async def add_xp(self, message: Message, xp: int, xp_total: int, level: int):
        xp_to_add = randint(5, 15)
        xp_end = floor(5 * (level ^ 2) + 50 * level + 100)

        db.execute("UPDATE leveling SET xp = xp + %s, xp_total = xp_total + %s WHERE user_id = %s",
                   xp_to_add, xp_to_add, message.author.id)
        db.commit()

        if xp_end < xp + xp_to_add:
            await self.increase_user_level(message, xp, xp_total, xp_to_add, xp_end, level)

        db.execute("UPDATE leveling SET xp_lock = %s WHERE user_id = %s",
                   datetime.now() + timedelta(seconds=60), message.author.id)
        db.commit()

    @logger.catch
    async def increase_user_level(self,  message: Message, xp: int, xp_total: int, xp_to_add: int, xp_end: int, level: int):
        db.execute(
            "UPDATE leveling SET level = %s, xp = %s, xp_total = xp_total - %s WHERE user_id = %s",
            level+1, 0, (xp + xp_to_add) - xp_end, message.author.id
        )
        db.commit()

        rep_reward = find_n_term_of_arithmetic_progression(10, 10, level+1)
        edit_user_reputation(message.author.id, '+', rep_reward)

        embed = Embed(
            title='🎉 GG 🎉',
            color=message.author.color,
            description=f'Участник {message.author.mention} достиг нового уровня: **{level + 1}** 🥳'
                        f'\nРепутация пользователя увеличена на **{rep_reward}** очков.'
        )
        await message.channel.send(embed=embed, delete_after=30)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("leveling")

    @Cog.listener()
    @listen_for_guilds()
    async def on_message(self, message):
        if message.author.id in self.bot.banlist:
            return

        if await self.can_message_be_counted(message):
            await self.process_xp(message)

    @command(name=cmd["rank"]["name"], aliases=cmd["rank"]["aliases"],
             brief=cmd["rank"]["brief"],
             description=cmd["rank"]["description"],
             usage=cmd["rank"]["usage"],
             help=cmd["rank"]["help"],
             hidden=cmd["rank"]["hidden"], enabled=True)
    @is_channel(STATS_CHANNEL)
    @guild_only()
    @logger.catch
    async def newrank_command(self, ctx, *, member: Optional[Member]):
        if member and member != ctx.author:
            if (await check_member_privacy(ctx, member)) is False:
                return
            else:
                target = member
        else:
            target = ctx.author

        async with ctx.typing():
            rank_card = RankCardImage(target)
            card = await rank_card.generate_rank_card()
            await ctx.send(file=card)


def setup(bot):
    bot.add_cog(Leveling(bot))
