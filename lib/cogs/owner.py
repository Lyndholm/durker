import time
import aiofiles
from aiohttp import ClientSession
from discord import Embed, Color, User
from discord.ext.commands import Cog, Greedy
from discord.ext.commands import command
from discord.ext.commands import is_owner, dm_only
from datetime import datetime

from ..utils.utils import load_commands_from_json
from ..utils.checks import can_manage_suggestions
from ..db import db

cmd = load_commands_from_json("owner")


class Owner(Cog):
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
    async def load_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.load_extension(cog)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=':thumbsup: Успешно!', description=f'Cog **`{cog}`** успешно загружен и активирован!', color = Color.green())
            await ctx.send(embed=embed)


    @command(name=cmd["unloadcog"]["name"], aliases=cmd["unloadcog"]["aliases"], 
            brief=cmd["unloadcog"]["brief"],
            description=cmd["unloadcog"]["description"],
            usage=cmd["unloadcog"]["usage"],
            help=cmd["unloadcog"]["help"],
            hidden=cmd["unloadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def unload_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=':thumbsup: Успешно!', description=f'Cog **`{cog}`** успешно деактивирован и выгружен!', color = Color.green())
            await ctx.send(embed=embed)


    @command(name=cmd["reloadcog"]["name"], aliases=cmd["reloadcog"]["aliases"], 
            brief=cmd["reloadcog"]["brief"],
            description=cmd["reloadcog"]["description"],
            usage=cmd["reloadcog"]["usage"],
            help=cmd["reloadcog"]["help"],
            hidden=cmd["reloadcog"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def reload_cog_command(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(cog)
            self.bot.load_extension(cog)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=':thumbsup: Успешно!', description=f'Cog **`{cog}`** успешно перезагружен!', color = Color.green())
            await ctx.send(embed=embed)


    @command(name=cmd["disablecmd"]["name"], aliases=cmd["disablecmd"]["aliases"], 
            brief=cmd["disablecmd"]["brief"],
            description=cmd["disablecmd"]["description"],
            usage=cmd["disablecmd"]["usage"],
            help=cmd["disablecmd"]["help"],
            hidden=cmd["disablecmd"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def disable_cmd_command(self, ctx, *, cmd: str):
        try:
            command = self.bot.get_command(name=cmd)
            if command.enabled:
                self.modified_commands[cmd] = command.cog.qualified_name
                command.update(enabled=False, hidden=True)
                embed = Embed(title=':thumbsup: Успешно!', description=f'Команда **`{cmd}`** отключена!', color = Color.green())
                await ctx.send(embed=embed)
            else:
                embed = Embed(title=':exclamation: Ошибка!', description=f'Команда `{cmd}` уже отключена.', color = Color.red())
                await ctx.send(embed=embed)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)


    @command(name=cmd["enablecmd"]["name"], aliases=cmd["enablecmd"]["aliases"], 
            brief=cmd["enablecmd"]["brief"],
            description=cmd["enablecmd"]["description"],
            usage=cmd["enablecmd"]["usage"],
            help=cmd["enablecmd"]["help"],
            hidden=cmd["enablecmd"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def enable_cmd_command(self, ctx, *, cmd: str):
        try:
            command = self.bot.get_command(name=cmd)
            if not command.enabled:
                command_cog = self.bot.get_cog(self.modified_commands[cmd])
                command.update(enabled=True, hidden=False)
                command.cog = command_cog
                del self.modified_commands[cmd]
                embed = Embed(title=':thumbsup: Успешно!', description=f'Команда **`{cmd}`** включена!', color = Color.green())
                await ctx.send(embed=embed)
            else:
                embed = Embed(title=':exclamation: Ошибка!', description=f'Команда `{cmd}` сейчас активна. Повторное включение невозможно', color = Color.red())
                await ctx.send(embed=embed)
        except Exception as e:
            embed = Embed(title=':exclamation: Ошибка!', description=f'{type(e).__name__} - {e}', color = Color.red())
            await ctx.send(embed=embed)
    

    @command(name=cmd["disabledcmds"]["name"], aliases=cmd["disabledcmds"]["aliases"], 
            brief=cmd["disabledcmds"]["brief"],
            description=cmd["disabledcmds"]["description"],
            usage=cmd["disabledcmds"]["usage"],
            help=cmd["disabledcmds"]["help"],
            hidden=cmd["disabledcmds"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def show_disabled_cmds_command(self, ctx):
        disabled_cmds = []
        for command in self.bot.commands:
            if not command.enabled:
                disabled_cmds.append(str(command))
        embed = Embed(title=':arrow_down: Отключённые команды.', description="\n".join(disabled_cmds) if disabled_cmds else "Все команды работают в штатном режиме.", color = Color.red())
        await ctx.send(embed=embed)


    @command(name=cmd["fnping"]["name"], aliases=cmd["fnping"]["aliases"], 
            brief=cmd["fnping"]["brief"],
            description=cmd["fnping"]["description"],
            usage=cmd["fnping"]["usage"],
            help=cmd["fnping"]["help"],
            hidden=cmd["fnping"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def ping_fortnite_apis_command(self, ctx):
        """Get the response time for APIs."""
        message = await ctx.send("Response time for APIs:")
        async with ClientSession() as session:
            now = time.monotonic()
            async with session.get('https://benbotfn.tk/api/v1/status') as r:
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
        inline = True


    @command(name=cmd["bearer"]["name"], aliases=cmd["bearer"]["aliases"], 
            brief=cmd["bearer"]["brief"],
            description=cmd["bearer"]["description"],
            usage=cmd["bearer"]["usage"],
            help=cmd["bearer"]["help"],
            hidden=cmd["bearer"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def fetch_bearer_token_command(self, ctx):
        async with ClientSession() as session:
            async with session.get('https://api.nitestats.com/v1/epic/bearer') as r:
                if r.status != 200:
                    await ctx.send(f"""```json\n{await r.text()}```""")
                    return
                
                data = await r.json()
                embed = Embed(
                    title="Bearer token",
                    color=Color.random(),
                    timestamp=ctx.message.created_at,
                    description=f'**Token:** {data.get("accessToken", "Unknown")}\n'
                                f'**Updated:** {datetime.fromtimestamp(data.get("lastUpdated", 0)).strftime("%d.%m.%Y %H:%M:%S")}'
                )
                await ctx.send(embed=embed)


    async def pass_suggesion_decision(self, ctx, suggestion_id: int = None, decision: bool = None, comment: str = 'Отсутсвует'):
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

        except TypeError:
            await ctx.message.add_reaction('❌')

        else:
            embed = Embed(
                title="Заявка закрыта",
                color=Color.orange(),
                description=f"Администратор <@{rec[0]}> {'одобрил' if rec[1] else 'отклонил'} это предложение {rec[2].strftime('%d.%m.%Y %H:%M:%S')}."
            )
            return await ctx.send(embed=embed)

    @command(name=cmd["approve"]["name"], aliases=cmd["approve"]["aliases"], 
            brief=cmd["approve"]["brief"],
            description=cmd["approve"]["description"],
            usage=cmd["approve"]["usage"],
            help=cmd["approve"]["help"],
            hidden=cmd["approve"]["hidden"], enabled=True)
    @dm_only()
    @can_manage_suggestions()
    async def approve_suggestion_command(self, ctx, suggestion_id: int = None, *, comment: str = 'Отсутсвует.'):
        if suggestion_id is None:
            return await ctx.send('Укажите номер заявки.')

        await self.pass_suggesion_decision(ctx, suggestion_id, True, comment)
        
    @command(name=cmd["reject"]["name"], aliases=cmd["reject"]["aliases"], 
            brief=cmd["reject"]["brief"],
            description=cmd["reject"]["description"],
            usage=cmd["reject"]["usage"],
            help=cmd["reject"]["help"],
            hidden=cmd["reject"]["hidden"], enabled=True)
    @dm_only()
    @can_manage_suggestions()
    async def reject_suggestion_command(self, ctx, suggestion_id: int = None, *, comment: str = 'Отсутсвует.'):
        if suggestion_id is None:
            return await ctx.send('Укажите номер заявки.')

        await self.pass_suggesion_decision(ctx, suggestion_id, False, comment)


    @command(name=cmd["blacklist"]["name"], aliases=cmd["blacklist"]["aliases"], 
            brief=cmd["blacklist"]["brief"],
            description=cmd["blacklist"]["description"],
            usage=cmd["blacklist"]["usage"],
            help=cmd["blacklist"]["help"],
            hidden=cmd["blacklist"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def blacklist_user_command(self, ctx, targets: Greedy[User]):
        if not targets:
            return await ctx.message.add_reaction('❌')

        self.bot.banlist.extend([user.id for user in targets])

        async with aiofiles.open('./data/banlist.txt', 'a', encoding='utf-8') as f:
            await f.writelines([f"{user.id}\n" for user in targets])

        await ctx.message.add_reaction('✅')


    @command(name=cmd["whitelist"]["name"], aliases=cmd["whitelist"]["aliases"], 
            brief=cmd["whitelist"]["brief"],
            description=cmd["whitelist"]["description"],
            usage=cmd["whitelist"]["usage"],
            help=cmd["whitelist"]["help"],
            hidden=cmd["whitelist"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def whitelist_user_command(self, ctx, targets: Greedy[User]):
        if not targets:
            return await ctx.message.add_reaction('❌')

        async with aiofiles.open('./data/banlist.txt', 'w', encoding='utf-8') as f:
            await f.write("".join([f"{user}\n" for user in self.bot.banlist if user not in [u.id for u in targets]]))

        for target in targets:
            try:
                self.bot.banlist.remove(target.id)
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


    @command(name=cmd["shutdown"]["name"], aliases=cmd["shutdown"]["aliases"], 
            brief=cmd["shutdown"]["brief"],
            description=cmd["shutdown"]["description"],
            usage=cmd["shutdown"]["usage"],
            help=cmd["shutdown"]["help"],
            hidden=cmd["shutdown"]["hidden"], enabled=True)
    @dm_only()
    @is_owner()
    async def shutdown_command(self, ctx):
        async with aiofiles.open('./data/banlist.txt', 'w', encoding='utf-8') as f:
            await f.writelines([f"{user}\n" for user in self.bot.banlist])

        db.commit()
        self.bot.scheduler.shutdown()
        await self.bot.logout()

def setup(bot):
    bot.add_cog(Owner(bot))
