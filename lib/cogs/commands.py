from datetime import datetime, timedelta
from os import listdir
from platform import python_version
from random import choice, randint
from time import time
from typing import Optional

from discord import Color, Embed, File, Member
from discord import __version__ as discord_version
from discord.ext.commands import (BucketType, Cog, Greedy, check_any, command,
                                  cooldown, guild_only, has_any_role,
                                  has_permissions)
from loguru import logger
from psutil import Process, cpu_percent, virtual_memory

from ..db import db
from ..utils.checks import is_channel, required_level
from ..utils.constants import (CHASOVOY_ROLE_ID, CONSOLE_CHANNEL,
                               MUSIC_COMMANDS_CHANNEL)
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("commands")


class Commands(Cog, name='Базовые команды'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("commands")
           self.chasovoy = self.bot.guild.get_role(CHASOVOY_ROLE_ID)

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
            await self.bot.get_user(i).send(embed=embed)

    @command(name=cmd["support"]["name"], aliases=cmd["support"]["aliases"],
            brief=cmd["support"]["brief"],
            description=cmd["support"]["description"],
            usage=cmd["support"]["usage"],
            help=cmd["support"]["help"],
            hidden=cmd["support"]["hidden"], enabled=True)
    @guild_only()
    @logger.catch
    async def redirect_to_support_channel_command(self, ctx, targets: Greedy[Member]):
        content = " ".join([member.mention for member in targets]) or ctx.author.mention
        embed = Embed(
            title="Поддержка автора",
            color=ctx.author.color
        )
        embed.add_field(
            name="Сделали покупку с нашим тегом автора?",
            value="Присылайте скриншот в канал <#546408250158088192>. За это вы получите роль <@&731241570967486505>",
            inline=False
        )
        embed.add_field(
            name="Больше ролей",
            value="Потратив с тегом 10 000 и 25 000 В-Баксов, вы получите роль <@&730017005029294121> и <@&774686818356428841> соответственно.",
            inline=False
        )
        embed.add_field(
            name="История покупок",
            value="Узнать количество потраченных с тегом В-Баксов можно в канале <#604621910386671616> по команде " \
                f"`{ctx.prefix or self.bot.PREFIX}stats`\nПросмотреть историю покупок: " \
                f"`{ctx.prefix or self.bot.PREFIX}purchases`",
            inline=False
        )
        embed.add_field(
            name="P.S.",
            value="Новичкам недоступен просмотр истории канала <#546408250158088192>, но это не мешает отправлять скрины поддержки.",
            inline=False
        )

        await ctx.reply(content=content, embed=embed, mention_author=False)
        if ctx.author.top_role.position >= self.chasovoy.position:
            ctx.command.reset_cooldown(ctx)

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
    @cooldown(cmd["media"]["cooldown_rate"], cmd["media"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def redirect_to_media_channel_command(self, ctx, targets: Greedy[Member]):
        await ctx.message.delete()
        await ctx.send(' '.join(member.mention for member in targets) +  f' Изображениям и прочим медиафайлам, '
                       'не относящимся к теме разговора, нет места в чате! Пожалуйста, используйте канал <#644523860326219776>')
        if ctx.author.top_role.position >= self.chasovoy.position:
            ctx.command.reset_cooldown(ctx)

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
    @cooldown(cmd["poisk"]["cooldown_rate"], cmd["poisk"]["cooldown_per_second"], BucketType.member)
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
        if ctx.author.top_role.position >= self.chasovoy.position:
            ctx.command.reset_cooldown(ctx)

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

    @command(name=cmd["code"]["name"], aliases=cmd["code"]["aliases"],
            brief=cmd["code"]["brief"],
            description=cmd["code"]["description"],
            usage=cmd["code"]["usage"],
            help=cmd["code"]["help"],
            hidden=cmd["code"]["hidden"], enabled=True)
    @required_level(cmd["code"]["required_level"])
    @guild_only()
    @cooldown(cmd["code"]["cooldown_rate"], cmd["code"]["cooldown_per_second"], BucketType.guild)
    @logger.catch
    async def sac_command(self, ctx):
        await ctx.message.delete()
        await ctx.send('<:UseCodeFNFUN:681878310107480068> Лучший тег автора: **FNFUN** <:UseCodeFNFUN:681878310107480068>',
                        file=File('./data/images/fnfun.png'))

    @command(name=cmd["avatar"]["name"], aliases=cmd["avatar"]["aliases"],
            brief=cmd["avatar"]["brief"],
            description=cmd["avatar"]["description"],
            usage=cmd["avatar"]["usage"],
            help=cmd["avatar"]["help"],
            hidden=cmd["avatar"]["hidden"], enabled=True)
    @required_level(cmd["avatar"]["required_level"])
    @guild_only()
    @cooldown(cmd["avatar"]["cooldown_rate"], cmd["avatar"]["cooldown_per_second"], BucketType.member)
    @logger.catch
    async def display_member_avatar(self, ctx, member: Optional[Member]):
        await ctx.message.delete()
        if not member:
            await ctx.send(f'{ctx.author.mention}, укажите пользователя, чей аватар вы хотите увидеть.', delete_after=10)
            ctx.command.reset_cooldown(ctx)
            return

        embed = Embed(
            title=f'Аватар {member.display_name}',
            color=member.color,
            timestamp=datetime.utcnow()
        ).set_image(url=member.avatar_url).set_footer(text=f'Запрос от {ctx.author}', icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

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
            "▫️ **Веб сайт:** [click](https://youtu.be/dQw4w9WgXcQ)\n" \
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


def setup(bot):
    bot.add_cog(Commands(bot))
