import asyncio
from datetime import datetime, timedelta
from io import BytesIO
from os import listdir
from platform import python_version
from random import choice, randint
from time import time
from typing import Optional

from aiohttp import ClientSession
from discord import Color, Embed, File, Member
from discord import __version__ as discord_version
from discord.ext.commands import (BucketType, Cog, EmojiConverter, Greedy,
                                  check_any, command, cooldown, guild_only,
                                  has_any_role, has_permissions)
from loguru import logger
from psutil import Process, cpu_percent, virtual_memory

from ..db import db
from ..utils.checks import is_channel, required_level
from ..utils.constants import (CHASOVOY_ROLE_ID, CONSOLE_CHANNEL,
                               KAPITALIST_ROLE_ID, MAGNAT_ROLE_ID,
                               MECENAT_ROLE_ID, MUSIC_COMMANDS_CHANNEL)
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("commands")


class Commands(Cog, name='Базовые команды'):
    def __init__(self, bot):
        self.bot = bot
        if self.bot.ready:
            bot.loop.create_task(self.init_vars())

    @logger.catch
    async def init_vars(self):
        self.chasovoy = self.bot.guild.get_role(CHASOVOY_ROLE_ID)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.chasovoy = self.bot.guild.get_role(CHASOVOY_ROLE_ID)
            self.bot.cogs_ready.ready_up("commands")

    @command(name=cmd["suggest"]["name"], aliases=cmd["suggest"]["aliases"],
            brief=cmd["suggest"]["brief"],
            description=cmd["suggest"]["description"],
            usage=cmd["suggest"]["usage"],
            help=cmd["suggest"]["help"],
            hidden=cmd["suggest"]["hidden"], enabled=True)
    @required_level(cmd["suggest"]["required_level"])
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @guild_only()
    @logger.catch
    async def suggest_song_command(self, ctx, *, song: str = None):
        if song is None:
            return await ctx.reply(
                'Пожалуйста, укажите название трека, который вы хотите предложить добавить в плейлист радио.',
                mention_author=False
            )

        song = song.replace('`', '­')
        date = datetime.now()
        db.insert("song_suggestions",
                {"suggestion_author_id": ctx.author.id,
                "suggestion_type": "add",
                "suggested_song": song,
                "created_at": date}
        )
        cursor = db.get_cursor()
        cursor.execute("SELECT suggestion_id FROM song_suggestions where suggestion_author_id = %s and suggested_song = %s and created_at = %s", (ctx.author.id,song,date,))
        rec = cursor.fetchone()

        embed = Embed(
            title = "✅ Выполнено",
            color = Color.green(),
            timestamp = datetime.utcnow(),
            description = f'Заявка на добавление трека `{song}` в плейлист радио отправлена администрации.\nНомер вашей заявки: {rec[0]}\n'
                        "**Пожалуйста, разрешите личные сообщения от участников сервера, чтобы вы могли получить ответ на заявку.**"
        )
        await ctx.reply(embed=embed, mention_author=False)

        for i in [375722626636578816, 195637386221191170]:
            embed = Embed(
                title = "Новая заявка",
                color = Color.green(),
                timestamp = datetime.utcnow(),
                description = f"**Заявка на добавление трека в плейлист.**\n\n**Номер заявки:** {rec[0]}\n"
                              f"**Трек:** {song}\n**Заявка сформирована:** {date.strftime('%d.%m.%Y %H:%M:%S')}"
            )
            try:
                await self.bot.get_user(i).send(embed=embed)
            except:
                continue

    @command(name=cmd["question"]["name"], aliases=cmd["question"]["aliases"],
            brief=cmd["question"]["brief"],
            description=cmd["question"]["description"],
            usage=cmd["question"]["usage"],
            help=cmd["question"]["help"],
            hidden=cmd["question"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def redirect_to_question_channel_command(self, ctx, targets: Greedy[Member]):
        users = " ".join([member.mention for member in targets]) or ctx.author.mention
        await ctx.reply(
            f'{users}\nВопросы по игре следует задавать в канале <#546700132390010882>.'
            ' Так они не потеряются в общем чате, вследствие чего их увидет большее количество людей. '
            'Участники сервера постараются дать вам ответ.\n'
            'Также в этом канале вы можете задать вопрос администрации сервера.',
            mention_author=False, delete_after=90
        )

    @command(name=cmd["media"]["name"], aliases=cmd["media"]["aliases"],
            brief=cmd["media"]["brief"],
            description=cmd["media"]["description"],
            usage=cmd["media"]["usage"],
            help=cmd["media"]["help"],
            hidden=cmd["media"]["hidden"], enabled=True)
    @check_any(
        required_level(cmd["media"]["required_level"]),
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True))
    @guild_only()
    @cooldown(cmd["media"]["cooldown_rate"], cmd["media"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def redirect_to_media_channel_command(self, ctx, targets: Greedy[Member]):
        await ctx.message.delete()

        for member in targets:
            async for message in ctx.channel.history(limit=10):
                if message.author == member and message.attachments:
                    await message.delete()

        await ctx.send(' '.join(member.mention for member in targets) +  f' Изображениям и прочим медиафайлам, '
                       'не относящимся к теме разговора, нет места в чате! Пожалуйста, используйте канал <#644523860326219776>')

    @command(name=cmd["general"]["name"], aliases=cmd["general"]["aliases"],
            brief=cmd["general"]["brief"],
            description=cmd["general"]["description"],
            usage=cmd["general"]["usage"],
            help=cmd["general"]["help"],
            hidden=cmd["general"]["hidden"], enabled=True)
    @check_any(
        required_level(cmd["general"]["required_level"]),
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True))
    @guild_only()
    @cooldown(cmd["general"]["cooldown_rate"], cmd["general"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def redirect_to_general_channel_command(self, ctx, targets: Greedy[Member]):
        await ctx.message.delete()
        await ctx.send(' '.join(member.mention for member in targets) +  f' Пожалуйста, соблюдайте '
                       'тематику канала! Для общения используйте <#721480135043448954>')

    async def gachi_poisk_feature(self, ctx, targets):
        gachi_replies = (
            ' Slave, ты пишешь не в тот Gym, тебе нужно в next door: <#546416181871902730>. ' \
            'Поиск в этом канале будет караться изъятием three hundred bucks.',

            ' Эй, приятель. Я думаю, ты ошибся дверью. Клуб по поиску напарников в двух кварталах отсюда. ' \
            'Отправляйся в <#546416181871902730>',

            ' Leather man, ты зашёл не в тот Gym. Эта качалка не для любителей leather stuff. ' \
            'Отправляйся в <#546416181871902730>, иначе я покажу тебе, кто здесь boss of this gym.',
        )
        images = listdir('./data/images/search_for_players/gachi')
        await ctx.send(' '.join(member.mention for member in targets) + choice(gachi_replies),
                       file=File(f'./data/images/search_for_players/gachi/{choice(images)}'))

    @command(name=cmd["poisk"]["name"], aliases=cmd["poisk"]["aliases"],
            brief=cmd["poisk"]["brief"],
            description=cmd["poisk"]["description"],
            usage=cmd["poisk"]["usage"],
            help=cmd["poisk"]["help"],
            hidden=cmd["poisk"]["hidden"], enabled=True)
    @check_any(
        required_level(cmd["poisk"]["required_level"]),
        has_any_role(CHASOVOY_ROLE_ID),
        has_permissions(administrator=True))
    @guild_only()
    @cooldown(cmd["poisk"]["cooldown_rate"], cmd["poisk"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def redirect_to_poisk_channel_command(self, ctx, targets: Greedy[Member]):
        await ctx.message.delete()
        chance = randint(1, 100)
        if 50 <= chance <= 60:
            await self.gachi_poisk_feature(ctx, targets)
        else:
            images = listdir('./data/images/search_for_players/common')
            await ctx.send(
                ' '.join(member.mention for member in targets) + ' **Данный канал не предназначен для поиска игроков!** '
                'Пожалуйста, используйте соответствующий канал <#546416181871902730>. Любые сообщения с поиском игроков '
                'в данном канале будут удалены.', file=File(f'./data/images/search_for_players/common/{choice(images)}'))

    @command(name=cmd["ppo"]["name"], aliases=cmd["ppo"]["aliases"],
            brief=cmd["ppo"]["brief"],
            description=cmd["ppo"]["description"],
            usage=cmd["ppo"]["usage"],
            help=cmd["ppo"]["help"],
            hidden=cmd["ppo"]["hidden"], enabled=True)
    @required_level(cmd["ppo"]["required_level"])
    @guild_only()
    @cooldown(cmd["ppo"]["cooldown_rate"], cmd["ppo"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def ppo_command(self, ctx):
        await ctx.message.delete()
        await ctx.send('Понял Принял Обработал')

    @command(name=cmd["sp"]["name"], aliases=cmd["sp"]["aliases"],
            brief=cmd["sp"]["brief"],
            description=cmd["sp"]["description"],
            usage=cmd["sp"]["usage"],
            help=cmd["sp"]["help"],
            hidden=cmd["sp"]["hidden"], enabled=True)
    @required_level(cmd["sp"]["required_level"])
    @guild_only()
    @cooldown(cmd["sp"]["cooldown_rate"], cmd["sp"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def sp_command(self, ctx):
        await ctx.message.delete()
        await ctx.send('СП=справедливо=<:Spravedlivo:681858765158351124>')


    @command(name=cmd["avatar"]["name"], aliases=cmd["avatar"]["aliases"],
            brief=cmd["avatar"]["brief"],
            description=cmd["avatar"]["description"],
            usage=cmd["avatar"]["usage"],
            help=cmd["avatar"]["help"],
            hidden=cmd["avatar"]["hidden"], enabled=True)
    @required_level(cmd["avatar"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["avatar"]["cooldown_rate"], cmd["avatar"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def display_member_avatar(self, ctx, member: Optional[Member]):
        await ctx.message.delete()
        if not member:
            member = ctx.author
            ctx.command.reset_cooldown(ctx)

        embed = Embed(
            title=f'Аватар {member.display_name}',
            color=member.color,
            timestamp=datetime.utcnow()
        ).set_image(url=member.avatar_url).set_footer(text=f'Запрос от {ctx.author}', icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @command(name=cmd["covid"]["name"], aliases=cmd["covid"]["aliases"],
            brief=cmd["covid"]["brief"],
            description=cmd["covid"]["description"],
            usage=cmd["covid"]["usage"],
            help=cmd["covid"]["help"],
            hidden=cmd["covid"]["hidden"], enabled=True)
    @required_level(cmd["covid"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["covid"]["cooldown_rate"], cmd["covid"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def covid_stats_command(self, ctx, country: str = None):
        if not country:
            embed = Embed(
                title='❗ Внимание!',
                description =f"Пожалуйста, введите название страны на английском языке.",
                color=Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        async with ClientSession() as session:
            async with session.get("https://corona.lmao.ninja/v2/countries") as r:
                if r.status == 200:
                    data = await r.json()
                else:
                    embed = Embed(
                        title='❗ Внимание!',
                        description =f"Что-то пошло не так. API вернуло: {r.status}",
                        color=Color.red()
                    )
                    await ctx.reply(embed=embed, mention_author=False)
                    return

        for item in data:
            if item["country"].lower() == country.lower():
                date = datetime.fromtimestamp(item["updated"]/1000).strftime("%d.%m.%Y %H:%M:%S")
                embed = Embed(
                    title=f'Статистика Коронавируса | {country.upper()}',
                    description=f"Дата обновления статистики: **{date}**",
                    color = Color.red()
                )

                embed.add_field(name=f'Заболеваний:', value=f'{item["cases"]:,}')

                embed.add_field(name=f'Заболеваний за сутки:', value=f'+{item["todayCases"]:,}')

                embed.add_field(name=f'Активные зараженные:', value=f'{item["active"]:,}')

                embed.add_field(name=f'Выздоровело:', value=f'{item["recovered"]:,}')

                embed.add_field(name=f'Выздоровело за сутки:', value=f'+{item["todayRecovered"]:,}')

                embed.add_field(name=f'В тяжелом состоянии:', value=f'{item["critical"]:,}')

                embed.add_field(name=f'Погибло:', value=f'{item["deaths"]:,}')

                embed.add_field(name=f'Погибло за сутки:', value=f'{item["todayDeaths"]:,}')

                embed.add_field(name=f'Проведено тестов:', value=f'{item["tests"]:,}')

                embed.set_thumbnail(url=item["countryInfo"]['flag'])

                await ctx.reply(embed=embed, mention_author=False)
                break
        else:
            embed = Embed(
                title='❗ Внимание!',
                description=f'**{country.capitalize()}** нет в списке стран. ' \
                            'Учитывайте, что названия стран необходимо писать на '
                            'английском языке.',
                color=Color.red()
            )
            await ctx.reply(embed=embed, mention_author=False)

    @command(name=cmd["emoji"]["name"], aliases=cmd["emoji"]["aliases"],
            brief=cmd["emoji"]["brief"],
            description=cmd["emoji"]["description"],
            usage=cmd["emoji"]["usage"],
            help=cmd["emoji"]["help"],
            hidden=cmd["emoji"]["hidden"], enabled=True)
    @required_level(cmd["emoji"]["required_level"])
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @logger.catch
    async def display_emoji_png(self, ctx, emoji: Greedy[EmojiConverter] = None):
        if emoji is None:
            await ctx.reply(
                'Укажите валидный смайл. Эмодзи со сторонних серверов и unicode эмодзи не поддерживаются.',
                mention_author=False
            )
            return
        elif len(emoji) > 3:
            await ctx.reply(
                'Превышен лимит эмодзи в сообщении. Уменьшите количество смайликов до 3.',
                mention_author=False
            )
            return

        for e in emoji:
            extension = '.gif' if e.animated else '.png'
            asset = File(BytesIO(await e.url.read()), filename=e.name+extension)
            await ctx.send(f'**Эмодзи:** {e.name}', file=asset)

    @command(name=cmd["info"]["name"], aliases=cmd["info"]["aliases"],
            brief=cmd["info"]["brief"],
            description=cmd["info"]["description"],
            usage=cmd["info"]["usage"],
            help=cmd["info"]["help"],
            hidden=cmd["info"]["hidden"], enabled=True)
    @is_channel(CONSOLE_CHANNEL)
    @guild_only()
    @cooldown(cmd["info"]["cooldown_rate"], cmd["info"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def show_bot_info_command(self, ctx):
        embed = Embed(
            title="Информация о боте",
            color=ctx.author.color,
            timestamp=datetime.utcnow()).set_thumbnail(url=ctx.guild.me.avatar_url)

        proc = Process()
        with proc.oneshot():
            uptime = timedelta(seconds=int(time()-proc.create_time()))
            cpu_usage = cpu_percent()
            ram_total = virtual_memory().total / (1024**2)
            ram_of_total = proc.memory_percent()
            ram_usage = ram_total * (ram_of_total / 100)

        embed.description = \
            "**Durker** — многофункциональный Discord бот, имеющий большое количество полезных утилит и команд. " \
            "Бот создан специально для [сервера](https://discord.gg/XpM58CK) [FortniteFun](https://fortnitefun.ru/). "\
            "Он призван занять должность менеджера сервера, облегчить взаимодействие с пользователями, автоматизировать рутинную работу.\n" \
            "Модерация (автоматическая и ручная); аудит; cистема уровней, достижений, репутации; выдача ролей; кастомные команды; музыкальный плеер; " \
            "радио; взаимодействие с различными API — всё это и не только присутствует в данном боте.\n" \
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n" \
            "**Информация о проекте**\n" \
            "▫️ **Название:** Durker\n" \
            f"▫️ **Версия:** {self.bot.VERSION}\n" \
            "▫️ **Автор:** Lyndholm#7200\n" \
            "▫️ **Веб сайт:** [docs.durker.fun](https://docs.durker.fun)\n" \
            "▫️ **Поддержать проект:** [DonationAlerts](https://donationalerts.com/r/lyndholm)\n" \
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n" \
            "**Статистика сервера**\n" \
            "▫️ **OS Info:** Debian GNU/Linux 10\n" \
            f"▫️ **Python Version:** {python_version()}\n" \
            f"▫️ **Discord.py Version:** {discord_version}\n" \
            f"▫️ **Uptime:** {uptime}\n" \
            f"▫️ **CPU Usage:** {cpu_usage}%\n" \
            f"▫️ **RAM Usage:** {round(ram_of_total)}% | {round(ram_usage)}/{round(ram_total)} MB\n" \
            f"▫️ **Ping:** {self.bot.latency*1000:,.0f} ms\n" \
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"

        await ctx.send(embed=embed)


    @command(name=cmd["fix"]["name"], aliases=cmd["fix"]["aliases"],
            brief=cmd["fix"]["brief"],
            description=cmd["fix"]["description"],
            usage=cmd["fix"]["usage"],
            help=cmd["fix"]["help"],
            hidden=cmd["fix"]["hidden"], enabled=True)
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @guild_only()
    @logger.catch
    async def fix_music_player(self, ctx):
        await ctx.message.delete()
        if ctx.guild.me.voice is None:
            return

        await ctx.guild.me.edit(mute=True)
        await asyncio.sleep(1)
        await ctx.guild.me.edit(mute=False)

def setup(bot):
    bot.add_cog(Commands(bot))
