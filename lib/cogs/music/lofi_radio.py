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

        self.queue = asyncio.Queue()
        self.controller = None

        self.waiting = False
        self.updating = False

    async def do_next(self) -> None:
        if self.is_playing or self.waiting:
            return

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


class LofiRadio(commands.Cog, wavelink.WavelinkMixin, name='Lofi Radio'):
    """LofiRadio music Cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        if not hasattr(bot, 'wavelink'):
            bot.wavelink = wavelink.Client(bot=bot)

        bot.loop.create_task(self.start_nodes())
        bot.loop.create_task(self.launch_lofi_radio())

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

    async def launch_lofi_radio(self):
        context = await self.fetch_context(546411393239220233, 855180960106676254)
        player: Player = self.bot.wavelink.get_player(
            guild_id=context.message.guild.id,
            cls=Player,
            context=context
        )
        player.queue._queue.clear()

        await self.remove_previous_controller()
        await discord.utils.get(context.guild.voice_channels, id=683251990284730397).edit(name="Lofi Radio")

        if not player.is_connected:
            await context.invoke(self.connect)

        playlists = ('https://www.youtube.com/playlist?list=PLofht4PTcKYnaH8w5olJCI-wUVxuoMHqM',
                     'https://www.youtube.com/playlist?list=PLfMqck7-0P5IYRckqAmvnqKfGpt5SN8oz')

        for uri in playlists:
            tracks = await self.bot.wavelink.get_tracks(uri)
            if not tracks:
                return await self.bot.logs_channel.send(
                    f'{datetime.datetime.now()} | Не удалось загрузить один из плейлистов `Lofi Radio`.\n'
                    f'`{uri}`')

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
            self.bot.cogs_ready.ready_up("lofi_radio")

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
                "identifier": "LofiRadio",
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

    def is_privileged(self, ctx: commands.Context):
        """Check whether the user is whitelisted or an Admin."""
        return ctx.author.guild_permissions.administrator or ctx.author.id in radio_whitelisted_users

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
    async def pause(self, ctx: commands.Context):
        """Pause the currently playing song."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** остановил воспроизведение.', delete_after=10)
            return await player.set_pause(True)

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
    async def resume(self, ctx: commands.Context):
        """Resume a currently paused player."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** продолжил воспроизведение.', delete_after=10)
            return await player.set_pause(False)

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
    async def skip(self, ctx: commands.Context):
        """Skip the currently playing song."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** пропустил трек.', delete_after=10)
            return await player.stop()

        if ctx.author == player.current.requester:
            await ctx.send('Автор трека пропустил композицию.', delete_after=10)
            return await player.stop()

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
    async def stop(self, ctx: commands.Context):
        """Stop the player and clear all internal states."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** остановил плеер.', delete_after=10)
            return await player.teardown()

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
    async def volume(self, ctx: commands.Context, *, vol: int):
        """Change the players volume, between 1 and 100."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Только администраторы могут менять громкость выходного сигнала.')

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
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the players queue."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return

        if player.queue.qsize() < 3:
            return await ctx.send('Добавьте в очередь больше треков, чтобы перемешать очередь.', delete_after=10)

        if self.is_privileged(ctx):
            await ctx.send(f'**{ctx.author.display_name}** перемешал очередь.', delete_after=10)
            return random.shuffle(player.queue._queue)

    @commands.command(
        name=cmd["queue"]["name"],
        aliases=cmd["queue"]["aliases"],
        brief=cmd["queue"]["brief"],
        description=cmd["queue"]["description"],
        usage=cmd["queue"]["usage"],
        help=cmd["queue"]["help"],
        hidden=False, enabled=True)
    @is_channel(MUSIC_COMMANDS_CHANNEL)
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
    async def nowplaying(self, ctx: commands.Context):
        """Update the player controller."""
        player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, context=ctx)

        if not player.is_connected:
            return
        try:
            await player.invoke_controller()
        except discord.errors.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(LofiRadio(bot))
