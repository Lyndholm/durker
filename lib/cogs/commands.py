from datetime import datetime, timedelta
from platform import python_version
from time import time

from discord import Color, Embed, Member
from discord import __version__ as discord_version
from discord.ext.commands import Cog, Greedy, command, guild_only
from psutil import Process, cpu_percent, virtual_memory

from ..db import db
from ..utils.checks import is_channel
from ..utils.utils import load_commands_from_json

cmd = load_commands_from_json("commands")


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("commands")

    @command(name=cmd["suggest"]["name"], aliases=cmd["suggest"]["aliases"],
            brief=cmd["suggest"]["brief"],
            description=cmd["suggest"]["description"],
            usage=cmd["suggest"]["usage"],
            help=cmd["suggest"]["help"],
            hidden=cmd["suggest"]["hidden"], enabled=True)
    @is_channel(708601604353556491)
    async def suggest_song_command(self, ctx, *, song: str = None):
        if song is None:
            return await ctx.send('Пожалуйста, укажите название трека, который вы хотите предложить добавить в плейлист радио.')

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
        await ctx.send(embed=embed)

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
        value="Потратив с тегом 10 000 и 25 000 в-баксов, вы получите роль <@&730017005029294121> и <@&774686818356428841> соответственно.",
        inline=False
        )
        embed.add_field(
        name="История покупок",
        value="Узнать количество потраченных с тегом в-баксов можно в канале <#604621910386671616> по команде `+me`\nПросмотреть историю покупок: `+purchases`",
        inline=False
        )
        embed.add_field(
        name="P.S.",
        value="Новичкам недоступен просмотр истории канала <#546408250158088192>, но это не мешает отправлять скрины поддержки.",
        inline=False
        )
        embed.add_field(
        name="P.S.S.",
        value="Все покупки засчитываются вручную. Время засчитывания может составлять от пары минут до нескольких дней. Это зависит от нагруженности модератора.",
        inline=False
        )

        await ctx.send(content=content, embed=embed, delete_after=90)

    @command(name=cmd["question"]["name"], aliases=cmd["question"]["aliases"],
            brief=cmd["question"]["brief"],
            description=cmd["question"]["description"],
            usage=cmd["question"]["usage"],
            help=cmd["question"]["help"],
            hidden=cmd["question"]["hidden"], enabled=True)
    async def redirect_to_question_channel_command(self, ctx, targets: Greedy[Member]):
        users = " ".join([member.mention for member in targets]) or ctx.author.mention
        await ctx.send(
            f"{users}\nВопросы по игре следует задавать в канале <#546700132390010882>."
            " Так они не потеряются в общем чате, вследствие чего их увидет большее количество людей. Участники сервера постараются дать вам ответ.\n"
            "Также в этом канале вы можете задать вопрос администрации сервера.",
            delete_after=90
        )

    @command(name=cmd["info"]["name"], aliases=cmd["info"]["aliases"],
            brief=cmd["info"]["brief"],
            description=cmd["info"]["description"],
            usage=cmd["info"]["usage"],
            help=cmd["info"]["help"],
            hidden=cmd["info"]["hidden"], enabled=True)
    @guild_only()
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
            "**Dungeon Durker** — многофункциональный Discord бот, имеющий большое количество полезных утилит и команд. " \
            "Бот создан специально для [сервера](https://discord.gg/XpM58CK) [FortniteFun](https://fortnitefun.ru/). "\
            "Он призван занять должность менеджера сервера, облегчить взаимодействие с пользователями, автоматизировать рутинную работу.\n" \
            "Модерация (автоматическая и ручная); аудит; cистема уровней, достижений, репутации; выдача ролей; кастомные команды; музыкальный плеер; " \
            "радио; взаимодействие с различными API — всё это и не только присутствует в данном боте.\n" \
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n" \
            "**Информация о проекте**\n" \
            "▫️ **Название:** Dungeon Durker\n" \
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
