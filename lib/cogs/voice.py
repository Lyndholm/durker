from discord import Member, VoiceState, TextChannel, VoiceChannel
from discord.utils import get
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.errors import HTTPException, NotFound


class Voice(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temporary_channels = {}

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("voice")

    async def create_temporary_channels(self, member: Member, before: VoiceState, after: VoiceState):
        voice_category = get(self.bot.guild.categories, id=814768982388506634)

        voice_channel = await voice_category.create_voice_channel(name=f'{member.display_name}')
        text_channel = await voice_category.create_text_channel(name=f'{member.display_name}')
        self.temporary_channels[voice_channel.id] = text_channel.id
        await voice_channel.set_permissions(member, manage_channels=True)
        await text_channel.set_permissions(member, manage_channels=True)
        await text_channel.set_permissions(get(member.guild.roles, name='@everyone'), view_channel=False, read_messages=False, send_messages=False)

        try:
            await member.move_to(voice_channel)
        except HTTPException:
            await self.delete_temporary_channels(voice_channel, text_channel)

        await self.bot.wait_for(
                'voice_state_update', 
                check = lambda x,y,z: len(voice_channel.members) == 0
            )
        try:
            await self.delete_temporary_channels(voice_channel, text_channel)
        except NotFound:
            return

    async def delete_temporary_channels(self, voice_channel: VoiceChannel, text_channel: TextChannel):
        await voice_channel.delete()
        await text_channel.delete()
        del self.temporary_channels[voice_channel.id]

    async def overwrite_text_channel_perms(self, member: Member, channel_id: int, access: bool):
        text_channel = self.bot.get_channel(channel_id)
        perms = text_channel.overwrites_for(member)
        perms.view_channel = access
        perms.read_messages = access
        perms.send_messages = access
        try:
            await text_channel.set_permissions(member, overwrite=perms)
        except NotFound:
            return

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if after.channel is not None:
            if after.channel.id == 814769110042411068:
                await self.create_temporary_channels(member, before, after)

        if after.channel is not None:
            if after.channel.id in self.temporary_channels:
                await self.overwrite_text_channel_perms(member, self.temporary_channels[after.channel.id], True)

        if before.channel is not None:
            if before.channel.id in self.temporary_channels:
                await self.overwrite_text_channel_perms(member, self.temporary_channels[before.channel.id], False)

        if before.channel is not None and after.channel is not None:
            if before.channel.id == 814769110042411068 or before.channel.id in self.temporary_channels:
                channels_copy = self.temporary_channels.copy()
                for k, v in channels_copy.items():
                    if k != after.channel.id:
                        await self.overwrite_text_channel_perms(member, v, False)
                    else:
                        await self.overwrite_text_channel_perms(member, v, True)

def setup(bot):
    bot.add_cog(Voice(bot))
