from discord.ext.commands import Cog

from ..utils.utils import (delete_user_from_db, dump_user_data_in_json,
                           insert_new_user_in_db)


class Welcome(Cog, name='Greetings'):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("welcome")

    @Cog.listener()
    async def on_member_join(self, member):
        await insert_new_user_in_db(self.bot.db, self.bot.pg_pool, member)

    @Cog.listener()
    async def on_member_remove(self, member):
        if member.pending is True:
            await delete_user_from_db(self.bot.pg_pool, member.id)
        else:
            await dump_user_data_in_json(self.bot.pg_pool, member)
            await delete_user_from_db(self.bot.pg_pool, member.id)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
