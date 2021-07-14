import asyncio
import copy
import datetime
import math
import random
import re
import typing

import async_timeout
import discord
import wavelink
from discord.ext import commands, menus
from discord.ext.commands.errors import CheckFailure
from loguru import logger

from ...db import db
from ...utils.checks import (can_manage_radio, is_channel,
                             radio_whitelisted_users)
from ...utils.constants import MUSIC_COMMANDS_CHANNEL
from ...utils.utils import load_commands_from_json

cmd = load_commands_from_json('music_player')

# URL matching REGEX...
URL_REG = re.compile(r'https?://(?:www\.)?.+')

class NoChannelProvided(commands.CommandError):
    """Error raised when no suitable voice channel was supplied."""
    pass


class IncorrectChannelError(commands.CommandError):
    """Error raised when commands are issued outside of the players session channel."""
    pass


class Track(wavelink.Track):
    """Wavelink Track object with a requester attribute."""

    __slots__ = ('requester', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get('requester')


class Player(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.context: commands.Context = kwargs.get('context', None)
        if self.context:
            self.dj: discord.Member = self.context.author

        self.queue = asyncio.Queue()
        self.controller = None

        self.waiting = False
        self.updating = False

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

        # Clear the votes for a new song...
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        try:
            self.waiting = True
            with async_timeout.timeout(300):
                track = await self.queue.get()
        except asyncio.TimeoutError:
            # No music has been played for 5 minutes, cleanup and disconnect...
            return await self.teardown()

        await self.play(track)
        try:
            self.queue._queue.insert(random.randint(self.queue.qsize()//2, self.queue.qsize()-1), track)
        except ValueError:
            pass

        self.waiting = False

        # Invoke our players controller...
        await self.invoke_controller()

    async def invoke_controller(self) -> None:
        """Method which updates or sends a new player controller."""
        if self.updating:
            return

        self.updating = True

        if not self.controller:
            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        elif not await self.is_position_fresh():
            try:
                await self.controller.message.delete()
            except discord.HTTPException:
                pass

            self.controller.stop()

            self.controller = InteractiveController(embed=self.build_embed(), player=self)
            await self.controller.start(self.context)

        else:
            embed = self.build_embed()
            await self.controller.message.edit(content=None, embed=embed)

        self.updating = False

    def build_embed(self) -> typing.Optional[discord.Embed]:
        """Method which builds our players controller embed."""
        track = self.current
        if not track:
            return

        channel = self.bot.get_channel(int(self.channel_id))
        qsize = self.queue.qsize()

        embed = discord.Embed(title=f'Радио FNFUN | {channel.name}', colour=0x00ff00)
        embed.description = f'**Сейчас играет:**\n```ini\n{track.author} — {track.title}\n```'
        embed.set_thumbnail(url=track.thumb if track.thumb else "https://cdn.discordapp.com/attachments/774698479981297664/813684421370314772/radio_placeholder.jpg")

        try:
            embed.add_field(name='Продолжительность', value=str(datetime.timedelta(milliseconds=int(track.length))))
        except OverflowError:
            embed.add_field(name='Продолжительность', value="Неизвестна")
        embed.add_field(name='Видео URL', value=f'[Клик]({track.uri})')
        embed.add_field(name='Треков в плейлисте', value=str(qsize), inline=False)

        return embed

    async def is_position_fresh(self) -> bool:
        """Method which checks whether the player controller should be remade or updated."""
        try:
            async for message in self.context.channel.history(limit=5):
                if message.id == self.controller.message.id:
                    return True
        except (discord.HTTPException, AttributeError):
            return False

        return False

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        try:
            await self.controller.message.delete()
        except discord.HTTPException:
            pass

        self.controller.stop()

        try:
            await self.destroy()
        except KeyError:
            pass


class InteractiveController(menus.Menu):
    """The Players interactive controller menu class."""

    def __init__(self, *, embed: discord.Embed, player: Player):
        super().__init__(timeout=None)

        self.embed = embed
        self.player = player

    def update_context(self, payload: discord.RawReactionActionEvent):
        """Update our context with the user who reacted."""
        ctx = copy.copy(self.ctx)
        ctx.author = payload.member

        return ctx

    def reaction_check(self, payload: discord.RawReactionActionEvent):
        if payload.event_type == 'REACTION_REMOVE':
            return False

        if not payload.member:
            return False
        if payload.member.bot:
            return False
        if payload.message_id != self.message.id:
            return False
        if payload.member not in self.bot.get_channel(int(self.player.channel_id)).members:
            return False

        return payload.emoji in self.buttons

    async def send_initial_message(self, ctx: commands.Context, channel: discord.TextChannel) -> discord.Message:
        return await channel.send(embed=self.embed)


class PaginatorSource(menus.ListPageSource):
    """Player queue paginator class."""

    def __init__(self, entries, *, per_page=5):
        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu: menus.Menu, page):
        embed = discord.Embed(title='Очередь воспроизведения...', colour=0x7DA747)
        embed.description = '\n'.join(f'```\n{track}\n```' for track in page)

        return embed

    def is_paginating(self):
        # We always want to embed even on 1 page of results...
        return True


class MeinRadio(commands.Cog, wavelink.WavelinkMixin, name='Mein Radio'):
    """MeinRadio music Cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not hasattr(bot, 'wavelink'):
            bot.wavelink = wavelink.Client(bot=bot)

        bot.loop.create_task(self.start_nodes())
        bot.loop.create_task(self.launch_mein_radio())

    async def fetch_context(self, channel: discord.TextChannel, message: discord.Message) -> discord.ext.commands.Context:
        channel_context = self.bot.get_channel(channel)
        context_message = await channel_context.fetch_message(message)
        context = await self.bot.get_context(context_message)

        return context

    async def remove_previous_controller(self):
        channel = self.bot.guild.get_channel(MUSIC_COMMANDS_CHANNEL)
        async for message in channel.history(limit=10):
            if message.author == self.bot.guild.me and message.embeds:
                try:
                    if 'Radio' in message.embeds[0].title:
                        await message.delete()
                except:
                    continue

    async def launch_mein_radio(self):
        context = await self.fetch_context(546411393239220233, 855180960106676254)
        player: Player = self.bot.wavelink.get_player(
            guild_id=context.message.guild.id,
            cls=Player,
            context=context
        )
        player.queue._queue.clear()

        await self.remove_previous_controller()
        await discord.utils.get(context.guild.voice_channels, id=683251990284730397).edit(name="Mein Radio")

        if not player.is_connected:
            await context.invoke(self.connect)

        tracks = await self.bot.wavelink.get_tracks("https://www.youtube.com/playlist?list=PLfMqck7-0P5LXjz7wcNgX2yMus0sfoFET")
        if not tracks:
            return await self.bot.get_user(self.bot.owner_ids[0]).send(f"{datetime.datetime.now()} | Не удалось загрузить плейлист `Mein Radio`.")

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=context.author)
                await player.queue.put(track)

        random.shuffle(player.queue._queue)

        if not player.is_playing:
            await player.do_next()


    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("mein_radio")

    async def start_nodes(self) -> None:
        """Connect and intiate nodes."""
        await self.bot.wait_until_ready()

        if self.bot.wavelink.nodes:
            previous = self.bot.wavelink.nodes.copy()

            for node in previous.values():
                await node.destroy()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MeinRadio",
                "region": "europe",
            }
        }

        for n in nodes.values():
            await self.bot.wavelink.initiate_node(**n)

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: wavelink.Node):
        print(f'Node {node.identifier} is ready!')

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.do_next()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

        if not player.channel_id or not player.context:
            player.node.players.pop(member.guild.id)
            return

        channel = self.bot.get_channel(int(player.channel_id))

        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj = m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Cog wide error handler."""
        if isinstance(error, IncorrectChannelError):
            return

        if isinstance(error, NoChannelProvided):
            return await ctx.send('Для использования музыкальных команд вы должны находиться в голосовом канале. Вы также можете указать голосовой канал.',
                                    delete_after=15)

        if isinstance(error, CheckFailure):
            return

    async def cog_check(self, ctx: commands.Context):
        """Cog wide check, which disallows commands in DMs."""
        if not ctx.guild:
            await ctx.send('Музыкальные команды не работают в личных сообщениях.')
            return False

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        """Coroutine called before command invocation.

        We mainly just want to check whether the user is in the players controller channel.
        """
        player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, context=ctx)

        if player.context:
            if player.context.channel != ctx.channel:
                await ctx.send(f'{ctx.author.mention}, ваш канал для текущей музыкальной сессии: {player.context.channel.mention}', delete_after=15)
                #raise IncorrectChannelError

        if ctx.command.name == 'connect' and not player.context:
            print(player.context)
            return
        elif self.is_privileged(ctx):
            return

        if not player.channel_id:
            return

        channel = self.bot.get_channel(int(player.channel_id))
        if not channel:
            return

        if player.is_connected:
            if ctx.author not in channel.members:
                await ctx.send(f'{ctx.author.mention}, вы должны быть в канале `{channel.name}`, чтобы использовать команды.', delete_after=15)
                #raise IncorrectChannelError

    def required(self, ctx: commands.Context):
        """Method which returns required votes based on amount of members in a channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        channel = self.bot.get_channel(int(player.channel_id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == 'stop':
            if len(channel.members) == 3:
                required = 2

        return required

    def is_privileged(self, ctx: commands.Context):
        """Check whether the user is an Admin or DJ."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        return player.dj == ctx.author or ctx.author.guild_permissions.administrator or ctx.author.id in radio_whitelisted_users

    @commands.command(
        name=cmd["connect"]["name"],
        aliases=cmd["connect"]["aliases"],
        brief=cmd["connect"]["brief"],
        description=cmd["connect"]["description"],
        usage=cmd["connect"]["usage"],
        help=cmd["connect"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def connect(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Connect to a voice channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_connected:
            return

        channel = getattr(ctx.author.voice, 'channel', channel)
        if channel is None:
            channel = discord.utils.get(ctx.guild.voice_channels, id=683251990284730397)
            #raise NoChannelProvided

        await player.connect(channel.id)

    @commands.command(
        name=cmd["play"]["name"],
        aliases=cmd["play"]["aliases"],
        brief=cmd["play"]["brief"],
        description=cmd["play"]["description"],
        usage=cmd["play"]["usage"],
        help=cmd["play"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def play(self, ctx: commands.Context, *, query: str):
        """Play or queue a song with the given query."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            await ctx.invoke(self.connect)

        query = query.strip('<>')
        if not URL_REG.match(query):
            query = f'ytsearch:{query}'

        tracks = await self.bot.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.send('Ничего не найдено.', delete_after=15)

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                await player.queue.put(track)

            await ctx.send(f'```ini\nПлейлист {tracks.data["playlistInfo"]["name"]}'
                           f' (позиций: {len(tracks.tracks)}) добавлен в очередь.\n```', delete_after=15)
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            await ctx.send(f'```ini\nТрек {track.title} добавлен в очередь\n```', delete_after=15)
            await player.queue.put(track)

        if not player.is_playing:
            await player.do_next()

    @commands.command(
        name=cmd["pause"]["name"],
        aliases=cmd["pause"]["aliases"],
        brief=cmd["pause"]["brief"],
        description=cmd["pause"]["description"],
        usage=cmd["pause"]["usage"],
        help=cmd["pause"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def pause(self, ctx: commands.Context):
        """Pause the currently playing song."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** остановил воспроизведение.', delete_after=10)
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.required(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.send('Голосование успешно заверешно. Плеер остановлен.', delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.send(f'**{ctx.author.display_name}** проголосовал за остановку воспроизведения.', delete_after=15)

    @commands.command(
        name=cmd["resume"]["name"],
        aliases=cmd["resume"]["aliases"],
        brief=cmd["resume"]["brief"],
        description=cmd["resume"]["description"],
        usage=cmd["resume"]["usage"],
        help=cmd["resume"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def resume(self, ctx: commands.Context):
        """Resume a currently paused player."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** продолжил воспроизведение.', delete_after=10)
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.required(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.send('Голосование успешно заверешно. Плеер запущен.', delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.send(f'**{ctx.author.display_name}** проголосовал за запуск плеера.', delete_after=10)

    @commands.command(
        name=cmd["skip"]["name"],
        aliases=cmd["skip"]["aliases"],
        brief=cmd["skip"]["brief"],
        description=cmd["skip"]["description"],
        usage=cmd["skip"]["usage"],
        help=cmd["skip"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def skip(self, ctx: commands.Context):
        """Skip the currently playing song."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** пропустил трек.', delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        if ctx.author == player.current.requester:
            await ctx.send('Автор трека пропустил композицию.', delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        required = self.required(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.send('Голосование успешно заверешно. Смена трека.', delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(f'**{ctx.author.display_name}** проголосовал за смену трека.', delete_after=10)

    @commands.command(
        name=cmd["stop"]["name"],
        aliases=cmd["stop"]["aliases"],
        brief=cmd["stop"]["brief"],
        description=cmd["stop"]["description"],
        usage=cmd["stop"]["usage"],
        help=cmd["stop"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def stop(self, ctx: commands.Context):
        """Stop the player and clear all internal states."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** остановил плеер.', delete_after=10)
            return await player.teardown()

        required = self.required(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.send('Голосование успешно заверешно. Остановка воспроизведения.', delete_after=10)
            await player.teardown()
        else:
            await ctx.send(f'**{ctx.author.display_name}** проголосовал за остановку воспроизведения.', delete_after=15)

    @commands.command(
        name=cmd["volume"]["name"],
        aliases=cmd["volume"]["aliases"],
        brief=cmd["volume"]["brief"],
        description=cmd["volume"]["description"],
        usage=cmd["volume"]["usage"],
        help=cmd["volume"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def volume(self, ctx: commands.Context, *, vol: int):
        """Change the players volume, between 1 and 100."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Только администраторы и DJ могут менять громкость выходного сигнала.')

        if not 0 < vol < 101:
            return await ctx.send('Пожалуйста, укажите значение от 1 до 100.')

        await player.set_volume(vol)
        await ctx.send(f'Установлена громкость **{vol}%**', delete_after=10)

    @commands.command(
        name=cmd["shuffle"]["name"],
        aliases=cmd["shuffle"]["aliases"],
        brief=cmd["shuffle"]["brief"],
        description=cmd["shuffle"]["description"],
        usage=cmd["shuffle"]["usage"],
        help=cmd["shuffle"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the players queue."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() < 3:
            return await ctx.send('Добавьте в очередь больше треков, чтобы перемешать очередь.', delete_after=10)

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** перемешал очередь.', delete_after=10)
            player.shuffle_votes.clear()
            return random.shuffle(player.queue._queue)

        required = self.required(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.send('Голосование успешно заверешно. Очередь перемешана.', delete_after=10)
            player.shuffle_votes.clear()
            random.shuffle(player.queue._queue)
        else:
            await ctx.send(f'**{ctx.author.display_name}** проголосовал за перемешивание очереди.', delete_after=10)

    @commands.command(hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def vol_up(self, ctx: commands.Context):
        """Command used for volume up button."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected or not self.is_privileged(ctx):
            return

        vol = int(math.ceil((player.volume + 10) / 10)) * 10

        if vol > 100:
            vol = 100
            await ctx.send('Достигнута максимальная громкость', delete_after=5)

        await player.set_volume(vol)

    @commands.command(hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def vol_down(self, ctx: commands.Context):
        """Command used for volume down button."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected or not self.is_privileged(ctx):
            return

        vol = int(math.ceil((player.volume - 10) / 10)) * 10

        if vol < 0:
            vol = 0
            await ctx.send('Плеер замьючен', delete_after=5)

        await player.set_volume(vol)

    @commands.command(
        name=cmd["equalizer"]["name"],
        aliases=cmd["equalizer"]["aliases"],
        brief=cmd["equalizer"]["brief"],
        description=cmd["equalizer"]["description"],
        usage=cmd["equalizer"]["usage"],
        help=cmd["equalizer"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def equalizer(self, ctx: commands.Context, *, equalizer: str):
        """Change the players equalizer."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Только администраторы и DJ могут менять настройки эквалайзера.')

        eqs = {'flat': wavelink.Equalizer.flat(),
               'boost': wavelink.Equalizer.boost(),
               'metal': wavelink.Equalizer.metal(),
               'piano': wavelink.Equalizer.piano()}

        eq = eqs.get(equalizer.lower(), None)

        if not eq:
            joined = "\n".join(eqs.keys())
            return await ctx.send(f'Указан неверный параметр эквалайзера. Доступные параметры:\n\n{joined}')

        await ctx.send(f'Эквалайзер обновлён: **{equalizer}**', delete_after=10)
        await player.set_eq(eq)

    @commands.command(
        name=cmd["queue"]["name"],
        aliases=cmd["queue"]["aliases"],
        brief=cmd["queue"]["brief"],
        description=cmd["queue"]["description"],
        usage=cmd["queue"]["usage"],
        help=cmd["queue"]["help"],
        hidden=False, enabled=True)
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def queue(self, ctx: commands.Context):
        """Display the players queued songs."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() == 0:
            return await ctx.send('В очереди больше нет треков.', delete_after=10)

        entries = [f"{index}. {track.author} — {track.title}" for index, track in enumerate(player.queue._queue, 1)]
        pages = PaginatorSource(entries=entries)
        paginator = menus.MenuPages(source=pages, timeout=60.0, delete_message_after=True)

        await paginator.start(ctx)

    @commands.command(
        name=cmd["nowplaying"]["name"],
        aliases=cmd["nowplaying"]["aliases"],
        brief=cmd["nowplaying"]["brief"],
        description=cmd["nowplaying"]["description"],
        usage=cmd["nowplaying"]["usage"],
        help=cmd["nowplaying"]["help"],
        hidden=False, enabled=True)
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def nowplaying(self, ctx: commands.Context):
        """Update the player controller."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return
        try:
            await player.invoke_controller()
        except discord.errors.HTTPException:
            pass

    @commands.command(
        name=cmd["swap_dj"]["name"],
        aliases=cmd["swap_dj"]["aliases"],
        brief=cmd["swap_dj"]["brief"],
        description=cmd["swap_dj"]["description"],
        usage=cmd["swap_dj"]["usage"],
        help=cmd["swap_dj"]["help"],
        hidden=True, enabled=True)
    @can_manage_radio()
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def swap_dj(self, ctx: commands.Context, *, member: discord.Member = None):
        """Swap the current DJ to another member in the voice channel."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Только администраторы и DJ могут использовать эту команду.', delete_after=10)

        members = self.bot.get_channel(int(player.channel_id)).members

        if member and member not in members:
            return await ctx.send(f'{member} не в голосовом канале.', delete_after=10)

        if member and member == player.dj:
            return await ctx.send(f'{member} уже DJ', delete_after=10)

        if len(members) <= 2:
            return await ctx.send('В канале больше нет участников. Передача прав DJ невозможна.', delete_after=10)

        if member:
            player.dj = member
            return await ctx.send(f'{member.mention} стал диджеем.')

        for m in members:
            if m == player.dj or m.bot:
                continue
            else:
                player.dj = m
                return await ctx.send(f'{member.mention} стал диджеем.')

    @commands.command(name="to_delete", aliases=['удоли', 'удалить', 'убрать', 'radioremove', 'radiodelete'],
            brief="Сделайте заявку на удаление из пелейлиста радио трека, который сейчас играет.",
            description="Формирует заявку на удаление из плейлиста радио трека, который сейчас играет.",
            usage="to_delete <track> <reason>",
            help="Возможность предложить удалить трек из плейлиста радио.\n\n**Работает в канале:** <#546411393239220233>\n**Кулдаун:** отсутствует.\n**Необходимый уровень:** 0",
            hidden=False, enabled=True)
    @is_channel(MUSIC_COMMANDS_CHANNEL)
    @logger.catch
    async def to_delete_song_command(self, ctx, *, reason: str = None):
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)
        track = player.current
        if not track:
            return await ctx.send(f'Радио сейчас не играет. Заявки на удаление треков не принимаются.')

        if reason is None:
            return await ctx.send(f'Пожалуйста, укажите причину, по которой вы хотите удалить трек `{player.current.author} — {player.current.title}` из плейлиста `MeinRadio`.')

        reason = reason.replace('`', '­')
        date = datetime.datetime.now()
        song = f"{player.current.author} — {player.current.title} | {player.current.uri}"
        db.insert("song_suggestions",
                {"suggestion_author_id": ctx.author.id,
                "suggestion_type": "delete",
                "suggested_song": song,
                "suggestion_comment": reason,
                "created_at": date})

        cursor = db.get_cursor()
        cursor.execute("SELECT suggestion_id FROM song_suggestions where suggestion_author_id = %s and suggested_song = %s and created_at = %s", (ctx.author.id,song,date,))
        rec = cursor.fetchone()

        embed = discord.Embed(
            title = "✅ Выполнено",
            color = discord.Color.red(),
            timestamp = datetime.datetime.utcnow(),
            description = f'Заявка на удаление трека `{track}` отправлена администрации.\nНомер вашей заявки: {rec[0]}\n'
                        "**Пожалуйста, разрешите личные сообщения от участников сервера, чтобы вы могли получить ответ на заявку.**"
        )
        await ctx.send(embed=embed)

        embed = discord.Embed(
                title = "Новая заявка",
                color = discord.Color.red(),
                timestamp = datetime.datetime.utcnow(),
                description = f"**Заявка на удаление трека из плейлиста.**\n\n**Номер заявки:** {rec[0]}\n"
                            f"**Трек:** {song}\n**Причина удаления:** {reason}\n**Заявка сформирована:** {date.strftime('%d.%m.%Y %H:%M:%S')}")
        for i in [375722626636578816, 195637386221191170]:
            await self.bot.get_user(i).send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(MeinRadio(bot))
