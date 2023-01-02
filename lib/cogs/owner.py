import json
import os
import time
from datetime import datetime
from typing import Optional

from aiohttp import ClientSession
from discord import Color, Embed, File
from discord.ext.commands import Cog, command, dm_only, is_owner
from discord.ext.menus import ListPageSource, MenuPages
from discord.utils import get
from loguru import logger

from ..db import db
from ..utils.checks import can_manage_radio_suggestions
from ..utils.utils import (edit_user_messages_count, edit_user_reputation,
                           load_commands_from_json)

cmd = load_commands_from_json("owner")


class SuggestionsMenu(ListPageSource):
    def __init__(self, ctx, data):
        self.ctx = ctx

        super().__init__(data, per_page=3)

    async def write_page(self, menu, offset, fields=[]):
        len_data = len(self.entries)

        embed = Embed(title='🎵 Радио заявки', color=0xffc300)
        embed.set_thumbnail(url='http://pngimg.com/uploads/radio/radio_PNG19281.png')
        embed.set_footer(text=f'Заявки {offset:,} - {min(len_data, offset+self.per_page-1):,} из {len_data:,}.')

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed

    async def format_page(self, menu, entries):
        offset = (menu.current_page*self.per_page) + 1

        fields = []
        table = ('\n'.join(
            f'> Заявка №**{entry[0]}** на {"добавление" if entry[1] == "add" else "удаление"} трека.\n'
            f'**Трек:** {entry[2]}\n**Комментарий:** {entry[3] if entry[3] else "отсутствует."}\n'
            for entry in entries))

        fields.append(("Открытые заявки:", table))

        return await self.write_page(menu, offset, fields)

class Owner(Cog, name='Команды разработчика'):
    def __init__(self, bot):
        self.bot = bot
        self.modified_commands = {}

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("owner")

    @command(name=cmd["loadcog"]["name"], aliases=cmd["loadcog"]["aliases"],
            brief=cmd["loadcog"]["brief"],
            description=cmd["loadcog"]["description"],
            usage=cmd["loadcog"]["usage"],
            help=cmd["loadcog"]["help"],
            hidden=cmd["loadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def load_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            embed = Embed(title='❗ Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.reply(embed=embed, mention_author=False)
        else:
            embed = Embed(title='👍 Успешно!', description=f'Cog **`{cog}`** успешно загружен и активирован!', color = Color.green())
            await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["unloadcog"]["name"], aliases=cmd["unloadcog"]["aliases"],
            brief=cmd["unloadcog"]["brief"],
            description=cmd["unloadcog"]["description"],
            usage=cmd["unloadcog"]["usage"],
            help=cmd["unloadcog"]["help"],
            hidden=cmd["unloadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def unload_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            embed = Embed(title='❗ Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.reply(embed=embed, mention_author=False)
        else:
            embed = Embed(title='👍 Успешно!', description=f'Cog **`{cog}`** успешно деактивирован и выгружен!', color = Color.green())
            await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["reloadcog"]["name"], aliases=cmd["reloadcog"]["aliases"],
            brief=cmd["reloadcog"]["brief"],
            description=cmd["reloadcog"]["description"],
            usage=cmd["reloadcog"]["usage"],
            help=cmd["reloadcog"]["help"],
            hidden=cmd["reloadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def reload_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            embed = Embed(title='❗ Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.reply(embed=embed, mention_author=False)
        else:
            embed = Embed(title='👍 Успешно!', description=f'Cog **`{cog}`** успешно перезагружен!', color = Color.green())
            await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["disablecmd"]["name"], aliases=cmd["disablecmd"]["aliases"],
            brief=cmd["disablecmd"]["brief"],
            description=cmd["disablecmd"]["description"],
            usage=cmd["disablecmd"]["usage"],
            help=cmd["disablecmd"]["help"],
            hidden=cmd["disablecmd"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def disable_cmd_command(self, ctx, *, cmd: str):
        try:
            command = self.bot.get_command(name=cmd)
            if command.enabled:
                self.modified_commands[cmd] = command.cog.qualified_name
                command.update(enabled=False, hidden=True)
                embed = Embed(title='👍 Успешно!', description=f'Команда **`{cmd}`** отключена!', color = Color.green())
                await ctx.reply(embed=embed, mention_author=False)
            else:
                embed = Embed(title='❗ Ошибка!', description=f'Команда `{cmd}` уже отключена.', color = Color.red())
                await ctx.reply(embed=embed, mention_author=False)
        except Exception as e:
            embed = Embed(title='❗ Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["enablecmd"]["name"], aliases=cmd["enablecmd"]["aliases"],
            brief=cmd["enablecmd"]["brief"],
            description=cmd["enablecmd"]["description"],
            usage=cmd["enablecmd"]["usage"],
            help=cmd["enablecmd"]["help"],
            hidden=cmd["enablecmd"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def enable_cmd_command(self, ctx, *, cmd: str):
        try:
            command = self.bot.get_command(name=cmd)
            if not command.enabled:
                command_cog = self.bot.get_cog(self.modified_commands[cmd])
                command.update(enabled=True, hidden=False)
                command.cog = command_cog
                del self.modified_commands[cmd]
                embed = Embed(title='👍 Успешно!', description=f'Команда **`{cmd}`** включена!', color = Color.green())
                await ctx.reply(embed=embed, mention_author=False)
            else:
                embed = Embed(title='❗ Ошибка!', description=f'Команда `{cmd}` сейчас активна. Повторное включение невозможно', color = Color.red())
                await ctx.reply(embed=embed, mention_author=False)
        except Exception as e:
            embed = Embed(title='❗ Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["disabledcmds"]["name"], aliases=cmd["disabledcmds"]["aliases"],
            brief=cmd["disabledcmds"]["brief"],
            description=cmd["disabledcmds"]["description"],
            usage=cmd["disabledcmds"]["usage"],
            help=cmd["disabledcmds"]["help"],
            hidden=cmd["disabledcmds"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def show_disabled_cmds_command(self, ctx):
        disabled_cmds = [str(c) for c in self.bot.commands if not c.enabled]
        embed = Embed(
            title='⬇️ Отключённые команды.',
            description="\n".join(disabled_cmds) if disabled_cmds else "Все команды работают в штатном режиме.",
            color=Color.red(),
            timestamp=datetime.utcnow()
        )
        await ctx.reply(embed=embed, mention_author=False)

    @command(name=cmd["ping"]["name"], aliases=cmd["ping"]["aliases"],
            brief=cmd["ping"]["brief"],
            description=cmd["ping"]["description"],
            usage=cmd["ping"]["usage"],
            help=cmd["ping"]["help"],
            hidden=cmd["ping"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def ping_bot_command(self, ctx):
        start = time.monotonic()
        message = await ctx.reply(
            f'🏓 DWSP latency: {self.bot.latency*1000:,.0f} ms.',
            mention_author=False
        )
        end = time.monotonic()
        await message.edit(content=f'🏓 DWSP latency: {self.bot.latency*1000:,.0f} ms.\n📶 Responce time: {(end-start)*1000:,.0f} ms.')

    @command(name=cmd["fnping"]["name"], aliases=cmd["fnping"]["aliases"],
            brief=cmd["fnping"]["brief"],
            description=cmd["fnping"]["description"],
            usage=cmd["fnping"]["usage"],
            help=cmd["fnping"]["help"],
            hidden=cmd["fnping"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def ping_fortnite_apis_command(self, ctx):
        """Get the response time for APIs."""
        message = await ctx.reply("Response time for APIs:", mention_author=False)
        async with ClientSession() as session:
            now = time.monotonic()
            async with session.get('https://benbot.app/api/v1/status') as r:
                benbot_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://fortnite-api.com') as r:
                fnapicom_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://fortniteapi.io') as r:
                fnapiio_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://fortnitetracker.com') as r:
                fntracker_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://api.nitestats.com') as r:
                ninestats_ping = time.monotonic() - now if r.status == 200 else 0

            now = time.monotonic()
            async with session.get('https://api.peely.de') as r:
                peelyde_ping = time.monotonic() - now if r.status == 200 else 0

        await message.edit(
            embed=Embed(color=Color.random())
            .add_field(name="Discord", value=f"{round(self.bot.latency * 1000)} ms.")
            .add_field(
                name="BenBot",
                value=f"{round(benbot_ping * 1000)} ms.",
            )
            .add_field(
                name="FortniteAPI.com",
                value=f"{round(fnapicom_ping * 1000)} ms.",
            )
            .add_field(
                name="FortniteAPI.io",
                value=f"{round(fnapiio_ping * 1000)} ms.",
            )
            .add_field(
                name="FortniteTracker",
                value=f"{round(fntracker_ping * 1000)} ms.",
            )
            .add_field(
                name="NiteStats",
                value=f"{round(ninestats_ping * 1000)} ms.",
            )
            .add_field(
                name="Api.peely.de",
                value=f"{round(peelyde_ping * 1000)} ms.",
            ),
        )


    @command(name=cmd["bearer"]["name"], aliases=cmd["bearer"]["aliases"],
            brief=cmd["bearer"]["brief"],
            description=cmd["bearer"]["description"],
            usage=cmd["bearer"]["usage"],
            help=cmd["bearer"]["help"],
            hidden=cmd["bearer"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def fetch_bearer_token_command(self, ctx):
        async with ClientSession() as session:
            async with session.get('https://api.nitestats.com/v1/epic/bearer') as r:
                if r.status != 200:
                    await ctx.reply(
                        f"""```json\n{await r.text()}```""",
                        mention_author=False
                    )

                data = await r.json()
                embed = Embed(
                    title="Bearer token",
                    color=Color.random(),
                    timestamp=ctx.message.created_at,
                    description=f'**Token:** {data.get("accessToken", "Unknown")}\n'
                                f'**Updated:** {datetime.fromtimestamp(data.get("lastUpdated", 0)).strftime("%d.%m.%Y %H:%M:%S")}'
                )
                await ctx.reply(embed=embed, mention_author=False)


    @command(name=cmd["suggestions"]["name"], aliases=cmd["suggestions"]["aliases"],
            brief=cmd["suggestions"]["brief"],
            description=cmd["suggestions"]["description"],
            usage=cmd["suggestions"]["usage"],
            help=cmd["suggestions"]["help"],
            hidden=cmd["suggestions"]["hidden"], enabled=True)
    @dm_only()
    @can_manage_radio_suggestions()
    @logger.catch
    async def radio_suggestions_command(self, ctx):
        records = db.records("SELECT suggestion_id, suggestion_type, suggested_song, suggestion_comment "
                            "FROM song_suggestions WHERE curator_id IS NULL")
        if records:
            menu = MenuPages(source=SuggestionsMenu(ctx, records))
            await menu.start(ctx)
        else:
            await ctx.reply('Открытых заявок нет.', mention_author=False)


    @logger.catch
    async def pass_suggesion_decision(self, ctx, suggestion_id: int = None, decision: bool = None, comment: str = 'Отсутствует'):
        answer_text = f"Ваша заявка **№{suggestion_id}** {'одобрена' if decision else 'отклонена'}.\n" + f"Комментарий администратора: {comment}"
        attachments = ''
        if ctx.message.attachments:
            nl = '\n'
            attachments_url = [attachment for attachment in ctx.message.attachments]
            attachments += f"\n{nl.join([url.proxy_url for url in attachments_url])}"

        rec = db.fetchone(["curator_id", "curator_decision", "closed_at"], "song_suggestions", "suggestion_id", suggestion_id)
        try:
            if rec[0] is None:
                data =  db.fetchone(["suggestion_author_id", "suggestion_type", "suggested_song"], "song_suggestions", "suggestion_id", suggestion_id)
                date = datetime.now()
                db.execute("UPDATE song_suggestions SET curator_id = %s, curator_decision = %s, curator_comment = %s, closed_at = %s  WHERE suggestion_id = %s",
                            ctx.author.id, True if decision else False, comment+attachments, date, suggestion_id)
                db.commit()

                embed = Embed(
                    title = "Ответ на заявку",
                    timestamp = datetime.utcnow(),
                    color = Color.green() if decision else Color.red(),
                    description = answer_text
                )
                if ctx.message.attachments:
                    embed.set_thumbnail(url=ctx.message.attachments[0].proxy_url)

                await self.bot.get_user(data[0]).send(embed=embed)
                await ctx.message.add_reaction('✅')
            else:
                embed = Embed(
                    title="Заявка закрыта",
                    color=Color.orange(),
                    description=f"Администратор <@{rec[0]}> {'одобрил' if rec[1] else 'отклонил'} это предложение {rec[2].strftime('%d.%m.%Y %H:%M:%S')}."
                )
                await ctx.reply(embed=embed, mention_author=False)
        except TypeError:
            await ctx.message.add_reaction('❌')


    @command(name=cmd["approve"]["name"], aliases=cmd["approve"]["aliases"],
            brief=cmd["approve"]["brief"],
            description=cmd["approve"]["description"],
            usage=cmd["approve"]["usage"],
            help=cmd["approve"]["help"],
            hidden=cmd["approve"]["hidden"], enabled=True)
    @dm_only()
    @can_manage_radio_suggestions()
    @logger.catch
    async def approve_suggestion_command(self, ctx, suggestion_id: int = None, *, comment: str = 'Отсутствует.'):
        if suggestion_id is None:
            return await ctx.reply('Укажите номер заявки.', mention_author=False)

        await self.pass_suggesion_decision(ctx, suggestion_id, True, comment)

    @command(name=cmd["reject"]["name"], aliases=cmd["reject"]["aliases"],
            brief=cmd["reject"]["brief"],
            description=cmd["reject"]["description"],
            usage=cmd["reject"]["usage"],
            help=cmd["reject"]["help"],
            hidden=cmd["reject"]["hidden"], enabled=True)
    @dm_only()
    @can_manage_radio_suggestions()
    @logger.catch
    async def reject_suggestion_command(self, ctx, suggestion_id: int = None, *, comment: str = 'Отсутствует.'):
        if suggestion_id is None:
            return await ctx.reply('Укажите номер заявки.', mention_author=False)

        await self.pass_suggesion_decision(ctx, suggestion_id, False, comment)


    @command(name=cmd["blacklist"]["name"], aliases=cmd["blacklist"]["aliases"],
            brief=cmd["blacklist"]["brief"],
            description=cmd["blacklist"]["description"],
            usage=cmd["blacklist"]["usage"],
            help=cmd["blacklist"]["help"],
            hidden=cmd["blacklist"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def blacklist_user_command(self, ctx, target_id: int = None, *, reason: Optional[str] = 'Не указана'):
        if target_id is None:
            return await ctx.message.add_reaction('❌')

        self.bot.banlist.append(target_id)
        db.insert('blacklist', {'user_id':target_id,'reason':reason})

        await ctx.message.add_reaction('✅')


    @command(name=cmd["whitelist"]["name"], aliases=cmd["whitelist"]["aliases"],
            brief=cmd["whitelist"]["brief"],
            description=cmd["whitelist"]["description"],
            usage=cmd["whitelist"]["usage"],
            help=cmd["whitelist"]["help"],
            hidden=cmd["whitelist"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def whitelist_user_command(self, ctx, target_id: int = None):
        if target_id is None:
            return await ctx.message.add_reaction('❌')

        db.execute('DELETE FROM blacklist WHERE user_id = %s', target_id)
        db.commit()
        try:
            self.bot.banlist.remove(target_id)
        except ValueError:
            pass

        await ctx.message.add_reaction('✅')


    @command(name=cmd["echo"]["name"], aliases=cmd["echo"]["aliases"],
            brief=cmd["echo"]["brief"],
            description=cmd["echo"]["description"],
            usage=cmd["echo"]["usage"],
            help=cmd["echo"]["help"],
            hidden=cmd["echo"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def echo_command(self, ctx, channel_id: int = None, *, content: str = '_ _'):
        try:
            channel = self.bot.get_channel(channel_id)
        except:
            return await ctx.message.add_reaction('❌')

        if channel and content:
            await channel.send(
                content=content,
                files=[await attachment.to_file() for attachment in ctx.message.attachments] if ctx.message.attachments else None
            )
            await ctx.message.add_reaction('✅')


    @command(name=cmd["reply"]["name"], aliases=cmd["reply"]["aliases"],
            brief=cmd["reply"]["brief"],
            description=cmd["reply"]["description"],
            usage=cmd["reply"]["usage"],
            help=cmd["reply"]["help"],
            hidden=cmd["reply"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def message_reply_command(self, ctx, channel_id: int = None, message_id: int = None, *, content: str = '_ _'):
        try:
            channel = self.bot.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
        except:
            return await ctx.message.add_reaction('❌')

        if message and content:
            await message.reply(
                content=content,
                files=[await attachment.to_file() for attachment in ctx.message.attachments] if ctx.message.attachments else None,
                mention_author=False
            )
            await ctx.message.add_reaction('✅')


    @command(name=cmd["setrep"]["name"], aliases=cmd["setrep"]["aliases"],
            brief=cmd["setrep"]["brief"],
            description=cmd["setrep"]["description"],
            usage=cmd["setrep"]["usage"],
            help=cmd["setrep"]["help"],
            hidden=cmd["setrep"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def set_reputation_command(self, ctx, user_id: int, action: str, value: int):
        await edit_user_reputation(self.bot.pg_pool, user_id, action, value)
        await ctx.reply(embed=Embed(
            title='Репутация обновлена',
            color=Color.green(),
            timestamp=datetime.utcnow(),
            description=f'Репутация пользователя <@{user_id}> изменена.\n'
                        f'**Действие:** `{action}`\n**Значение:** `{value}`'
        ), mention_author=False)


    @command(name=cmd["setamount"]["name"], aliases=cmd["setamount"]["aliases"],
            brief=cmd["setamount"]["brief"],
            description=cmd["setamount"]["description"],
            usage=cmd["setamount"]["usage"],
            help=cmd["setamount"]["help"],
            hidden=cmd["setamount"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def set_amount_command(self, ctx, user_id: int, action: str, value: int):
        edit_user_messages_count(user_id, action, value)
        await ctx.reply(embed=Embed(
            title='Сообщения обновлены',
            color=Color.green(),
            timestamp=datetime.utcnow(),
            description=f'Количество сообщений пользователя <@{user_id}> изменено.\n'
                        f'**Действие:** `{action}`\n**Значение:** `{value}`'
        ), mention_author=False)


    @command(name=cmd["rolelist"]["name"], aliases=cmd["rolelist"]["aliases"],
            brief=cmd["rolelist"]["brief"],
            description=cmd["rolelist"]["description"],
            usage=cmd["rolelist"]["usage"],
            help=cmd["rolelist"]["help"],
            hidden=cmd["rolelist"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def rolelist_command(self, ctx, role_id: Optional[int]):
        if not role_id:
            await ctx.reply(
                'Укажите ID запрашиваемой роли сервера.',
                mention_author=False
            )
            return

        role = get(self.bot.guild.roles, id=role_id)
        data = {
            "created": str(datetime.now()),
            "role_name": role.name,
            "role_id": role.id,
            "members": [
                {
                    str(i.id): i.display_name
                    for i in role.members
                }
            ]
        }
        with open(f"./data/json/{role.id}.json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)

        await ctx.reply(
            f'Список участников с ролью **{role.name}**.',
            file=File(
                f'./data/json/{role.id}.json',
                filename=f'{role.id}.json'
            ),
            mention_author=False
        )
        os.remove(f"./data/json/{role.id}.json")


    @command(name=cmd["shutdown"]["name"], aliases=cmd["shutdown"]["aliases"],
            brief=cmd["shutdown"]["brief"],
            description=cmd["shutdown"]["description"],
            usage=cmd["shutdown"]["usage"],
            help=cmd["shutdown"]["help"],
            hidden=cmd["shutdown"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    @logger.catch
    async def shutdown_command(self, ctx):
        db.commit()
        self.bot.scheduler.shutdown()
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(Owner(bot))
