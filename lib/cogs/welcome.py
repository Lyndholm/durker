from discord import Embed, Color, Member, Forbidden
from discord.utils import get
from discord.ext.commands import Cog
from datetime import datetime
from ..utils.constants import WELCOME_CHANNEL, GOODBYE_CHANNEL, AUDIT_LOG_CHANNEL, MUTE_ROLE_ID
from ..utils.utils import insert_new_user_in_db, dump_user_data_in_json, delete_user_from_db
from ..db import db


class Welcome(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.mute_role = self.bot.guild.get_role(MUTE_ROLE_ID)
            self.bot.cogs_ready.ready_up("welcome")


    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.pending is True and after.pending is False:
            rec = db.fetchone(["user_id"], "mutes", "user_id", after.id)
            try:
                if rec is not None:
                    embed = Embed(
                        title="Перезашёл, чтобы обойти мут?",
                        color=Color.random(),
                        description="**Ха-ха. Перезаход не спасает от мута.**"
                    )
                    await after.send(embed=embed)
                else:
                    embed = Embed(title=f"Добро пожаловать!", color=Color.orange(),
                    description = f"Здравствуй, **{after.display_name}**! Приветствуем тебя в фортнайтерском логове сайта [FORTNITEFUN.RU](https://fortnitefun.ru) :tada::hugging:"
                    "\nСпасибо, что заглянул к нам! Мы рады каждому новому участнику. "
                    "Настоятельно рекомендуем ознакомиться с разделом 'Для новичков'. "
                    "\nВ канале <#546409230127595544> ты узнаешь много полезной информации, включая правила, которые необходимо соблюдать. "
                    "\nВ канале <#547390000120070152> представлен полный список ролей сервера, а также возможности их получения.")

                    embed.add_field(name="Хочешь поговорить?", value="Местечко для общения на разные темы: <#721480135043448954>", inline=False)
                    embed.add_field(name="Ищешь напарника для игры?", value="Тебе в <#546416181871902730>", inline=False)
                    embed.add_field(name="Есть вопросы?", value="Пиши в <#546700132390010882>", inline=False)
                    embed.add_field(name="Сделали покупку с нашим тегом?", value="Присылайте скрин в <#546408250158088192>", inline=False)
                    embed.set_thumbnail(url=after.guild.icon_url)
                    embed.set_footer(text="Это автоматическое сообщение, отвечать на него не нужно.")
                    await after.send(embed=embed)

            except Forbidden:
                pass

            finally:
                insert_new_user_in_db(after)

                embed = Embed(description=f"Привет, **{after.display_name}** ({after.mention})!\nДобро пожаловать на сервер **{after.guild.name}** :tada::hugging:!",
                            color=Color.green(), timestamp=datetime.now())
                embed.set_author(name=f"Новый участник на сервере!", icon_url=f"{after.guild.icon_url}")
                await self.bot.get_channel(WELCOME_CHANNEL).send(embed=embed)

            if rec is None:
                await after.add_roles(get(after.guild.roles, name = 'Новичок'))
            else:
                managed_roles = [r for r in after.roles if r.managed]
                await after.edit(roles=[self.mute_role] + managed_roles)


    @Cog.listener()
    async def on_member_remove(self, member):
        if member.pending is True:
            embed = Embed(description=f"Пользователь **{member.display_name}** ({member.mention}) не завершил процесс верификации, не принял правила и покинул сервер.",
                        color=Color.dark_red(), timestamp=datetime.now())
            embed.set_author(name=f"Пользователь покинул сервер", icon_url=f"{member.guild.icon_url}")

            await self.bot.get_channel(AUDIT_LOG_CHANNEL).send(embed=embed)

        else:
            dump_user_data_in_json(member)
            delete_user_from_db(member.id)

            embed = Embed(description=f"К сожалению, пользователь **{member.display_name}** ({member.mention}) покинул сервер:disappointed:",
                        color=Color.gold(), timestamp=datetime.now())
            embed.set_author(name=f"Участник покинул сервер", icon_url=f"{member.guild.icon_url}")

            await self.bot.get_channel(GOODBYE_CHANNEL).send(embed=embed)


def setup(bot):
    bot.add_cog(Welcome(bot))
