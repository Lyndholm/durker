from datetime import datetime
from discord import Embed, Color
from discord.ext.commands import Cog
from discord.ext.commands import command

from ..utils.utils import load_commands_from_json
from ..utils.checks import is_channel
from ..db import db

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


def setup(bot):
    bot.add_cog(Commands(bot))
