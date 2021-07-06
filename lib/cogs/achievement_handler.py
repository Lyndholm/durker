from datetime import datetime
from typing import List

from discord import Member
from discord.ext import tasks
from discord.ext.commands import Cog
from discord.utils import get
from loguru import logger

from ..db import db
from ..utils.utils import joined_date


class AchievementHandler(Cog, name='AchievementHandler'):
    def __init__(self, bot):
        self.bot = bot
        self.achievements_manager.start()

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
           self.bot.cogs_ready.ready_up("achievement_handler")

    @tasks.loop(hours=6.0)
    @logger.catch
    async def achievements_manager(self):
        AS_COG = self.bot.get_cog('Система достижений')
        if not AS_COG:
            return
        for member in self.bot.guild.members:
            if member.pending:
                continue

            user_achievements = self.get_user_achievements(member)
            await self.handle_achievements(member, user_achievements, AS_COG)

    @achievements_manager.before_loop
    async def before_handle(self):
        await self.bot.wait_until_ready()

    def get_user_achievements(self, user: Member) -> List[str]:
        rec = db.fetchone(['achievements_list'], 'users_stats', 'user_id', user.id)
        data = rec[0]['user_achievements_list']
        user_achievements = [key for dic in data for key in dic.keys()]
        return user_achievements

    @logger.catch
    async def handle_achievements(self, member: Member, achievements: List[str], cog: Cog):
        await self.writer_handler(member, achievements, cog)
        await self.old_handler(member, achievements, cog)
        await self.role_master_handler(member, achievements, cog)
        await self.patron_handler(member, achievements, cog)
        await self.reputation_master_handler(member, achievements, cog)
        await self.kotleta_handler(member, achievements, cog)
        await self.philanthropist_handler(member, achievements, cog)
        await self.voice_master_handler(member, achievements, cog)
        await self.leveling_handler(member, achievements, cog)

    @logger.catch
    async def writer_handler(self, member, achievements, cog):
        data = db.fetchone(['messages_count'], 'users_stats', 'user_id', member.id)[0]
        WRITER_1 = 'AID_Writer_1'
        WRITER_2 = 'AID_Writer_2'
        WRITER_3 = 'AID_Writer_3'
        WRITER_4 = 'AID_Writer_4'
        WRITER_5 = 'AID_Writer_5'
        WRITER_6 = 'AID_Writer_6'

        if data >= 1_000:
            if WRITER_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, WRITER_1)
                #await cog.achievement_award_notification(WRITER_1, member)
        if data >= 5_000:
            if WRITER_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, WRITER_2)
                #await cog.achievement_award_notification(WRITER_2, member)
        if data >= 10_000:
            if WRITER_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, WRITER_3)
                #await cog.achievement_award_notification(WRITER_3, member)
        if data >= 25_000:
            if WRITER_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, WRITER_4)
                #await cog.achievement_award_notification(WRITER_4, member)
        if data >= 50_000:
            if WRITER_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, WRITER_5)
                #await cog.achievement_award_notification(WRITER_5, member)
        if data >= 100_000:
            if WRITER_6 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, WRITER_6)
                #await cog.achievement_award_notification(WRITER_6, member)

    @logger.catch
    async def old_handler(self, member, achievements, cog):
        diff = datetime.utcnow() - joined_date(member)
        OLD_1 = 'AID_Old_1'
        OLD_2 = 'AID_Old_2'
        OLD_3 = 'AID_Old_3'
        OLD_4 = 'AID_Old_4'
        OLD_5 = 'AID_Old_5'
        OLD_6 = 'AID_Old_6'
        OLD_7 = 'AID_Old_7'

        if diff.days >= 7:
            if OLD_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_1)
                #await cog.achievement_award_notification(OLD_1, member)
        if diff.days >= 30:
            if OLD_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_2)
                #await cog.achievement_award_notification(OLD_2, member)
        if diff.days >= 30 * 3:
            if OLD_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_3)
                #await cog.achievement_award_notification(OLD_3, member)
        if diff.days >= 30 * 6:
            if OLD_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_4)
                #await cog.achievement_award_notification(OLD_4, member)
        if diff.days >= 365:
            if OLD_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_5)
                #await cog.achievement_award_notification(OLD_5, member)
        if diff.days >= 365 * 2:
            if OLD_6 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_6)
                #await cog.achievement_award_notification(OLD_6, member)
        if diff.days >= 365 * 3:
            if OLD_7 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, OLD_7)
                #await cog.achievement_award_notification(OLD_7, member)

    @logger.catch
    async def role_master_handler(self, member, achievements, cog):
        roles = len(member.roles) - 1
        ROLE_MASTER_1 = 'AID_RoleMaster_1'
        ROLE_MASTER_2 = 'AID_RoleMaster_2'
        ROLE_MASTER_3 = 'AID_RoleMaster_3'
        ROLE_MASTER_4 = 'AID_RoleMaster_4'
        ROLE_MASTER_5 = 'AID_RoleMaster_5'

        if roles >= 3:
            if ROLE_MASTER_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, ROLE_MASTER_1)
                #await cog.achievement_award_notification(ROLE_MASTER_1, member)
        if roles >= 5:
            if ROLE_MASTER_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, ROLE_MASTER_2)
                #await cog.achievement_award_notification(ROLE_MASTER_2, member)
        if roles >= 10:
            if ROLE_MASTER_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, ROLE_MASTER_3)
                #await cog.achievement_award_notification(ROLE_MASTER_3, member)
        if roles >= 15:
            if ROLE_MASTER_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, ROLE_MASTER_4)
                #await cog.achievement_award_notification(ROLE_MASTER_4, member)
        if roles >= 20:
            if ROLE_MASTER_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, ROLE_MASTER_5)
                #await cog.achievement_award_notification(ROLE_MASTER_5, member)

    @logger.catch
    async def patron_handler(self, member, achievements, cog):
        data = db.fetchone(['purchases'], 'users_stats', 'user_id', member.id)[0]
        vbucks = sum(data['vbucks_purchases'][i]['price']
                    for i in range(len(data['vbucks_purchases'])))
        PATRON_1 = 'AID_Patron_1'
        PATRON_2 = 'AID_Patron_2'
        PATRON_3 = 'AID_Patron_3'
        PATRON_4 = 'AID_Patron_4'
        PATRON_5 = 'AID_Patron_5'
        PATRON_6 = 'AID_Patron_6'

        if vbucks > 0:
            if PATRON_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PATRON_1)
                #await cog.achievement_award_notification(PATRON_1, member)
        if vbucks >= 5_000:
            if PATRON_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PATRON_2)
                #await cog.achievement_award_notification(PATRON_2, member)
        if vbucks >= 10_000:
            if PATRON_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PATRON_3)
                #await cog.achievement_award_notification(PATRON_3, member)
        if vbucks >= 25_000:
            if PATRON_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PATRON_4)
                #await cog.achievement_award_notification(PATRON_4, member)
        if vbucks >= 50_000:
            if PATRON_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PATRON_5)
                #await cog.achievement_award_notification(PATRON_5, member)
        if vbucks >= 100_000:
            if PATRON_6 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PATRON_6)
                #await cog.achievement_award_notification(PATRON_6, member)

    @logger.catch
    async def reputation_master_handler(self, member, achievements, cog):
        rep_rank = db.fetchone(['rep_rank'], 'users_stats', 'user_id', member.id)[0]
        REP_MASTER_1 = 'AID_ReputationMaster_1'
        REP_MASTER_2 = 'AID_ReputationMaster_2'
        REP_MASTER_3 = 'AID_ReputationMaster_3'
        REP_MASTER_4 = 'AID_ReputationMaster_4'
        REP_MASTER_5 = 'AID_ReputationMaster_5'

        if rep_rank >= 1_000:
            if REP_MASTER_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, REP_MASTER_1)
                #await cog.achievement_award_notification(REP_MASTER_1, member)
        if rep_rank >= 5_000:
            if REP_MASTER_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, REP_MASTER_2)
                #await cog.achievement_award_notification(REP_MASTER_2, member)
        if rep_rank >= 10_000:
            if REP_MASTER_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, REP_MASTER_3)
                #await cog.achievement_award_notification(REP_MASTER_3, member)
        if rep_rank >= 25_000:
            if REP_MASTER_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, REP_MASTER_4)
                #await cog.achievement_award_notification(REP_MASTER_4, member)
        if rep_rank >= 50_000:
            if REP_MASTER_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, REP_MASTER_5)
                #await cog.achievement_award_notification(REP_MASTER_5, member)

    @logger.catch
    async def kotleta_handler(self, member, achievements, cog):
        esport_role = get(member.guild.roles, name='Киберспортсмен')
        KOTLETA_1 = 'AID_Kotleta_1'

        if esport_role in member.roles:
            if KOTLETA_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, KOTLETA_1)
                #await cog.achievement_award_notification(KOTLETA_1, member)

    @logger.catch
    async def philanthropist_handler(self, member, achievements, cog):
        stark_role = get(member.guild.roles, name='Филантроп')
        PHILANTHROPIST_1 = 'AID_Philanthropist_1'

        if stark_role in member.roles:
            if PHILANTHROPIST_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, PHILANTHROPIST_1)
                #await cog.achievement_award_notification(PHILANTHROPIST_1, member)

    @logger.catch
    async def voice_master_handler(self, member, achievements, cog):
        seconds = db.fetchone(['invoice_time'], 'users_stats', 'user_id', member.id)[0]
        hours = seconds//3600
        VOICE_MASTER_1 = 'AID_VoiceMaster_1'
        VOICE_MASTER_2 = 'AID_VoiceMaster_2'
        VOICE_MASTER_3 = 'AID_VoiceMaster_3'
        VOICE_MASTER_4 = 'AID_VoiceMaster_4'
        VOICE_MASTER_5 = 'AID_VoiceMaster_5'

        if hours >= 10:
            if VOICE_MASTER_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, VOICE_MASTER_1)
                #await cog.achievement_award_notification(VOICE_MASTER_1, member)
        if hours >= 25:
            if VOICE_MASTER_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, VOICE_MASTER_2)
                #await cog.achievement_award_notification(VOICE_MASTER_2, member)
        if hours >= 50:
            if VOICE_MASTER_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, VOICE_MASTER_3)
                #await cog.achievement_award_notification(VOICE_MASTER_3, member)
        if hours >= 100:
            if VOICE_MASTER_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, VOICE_MASTER_4)
                #await cog.achievement_award_notification(VOICE_MASTER_4, member)
        if hours >= 250:
            if VOICE_MASTER_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, VOICE_MASTER_5)
                #await cog.achievement_award_notification(VOICE_MASTER_5, member)

    @logger.catch
    async def leveling_handler(self, member, achievements, cog):
        level = db.fetchone(['level'], 'leveling', 'user_id', member.id)[0]
        LEVELING_1 = 'AID_Leveling_1'
        LEVELING_2 = 'AID_Leveling_2'
        LEVELING_3 = 'AID_Leveling_3'
        LEVELING_4 = 'AID_Leveling_4'
        LEVELING_5 = 'AID_Leveling_5'
        LEVELING_6 = 'AID_Leveling_6'

        if level >= 3:
            if LEVELING_1 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, LEVELING_1)
                #await cog.achievement_award_notification(LEVELING_1, member)
        if level >= 10:
            if LEVELING_2 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, LEVELING_2)
                #await cog.achievement_award_notification(LEVELING_2, member)
        if level >= 25:
            if LEVELING_3 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, LEVELING_3)
                #await cog.achievement_award_notification(LEVELING_3, member)
        if level >= 50:
            if LEVELING_4 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, LEVELING_4)
                #await cog.achievement_award_notification(LEVELING_4, member)
        if level >= 75:
            if LEVELING_5 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, LEVELING_5)
                #await cog.achievement_award_notification(LEVELING_5, member)
        if level >= 100:
            if LEVELING_6 not in achievements:
                cog.give_achievement(self.bot.guild.me.id, member.id, LEVELING_6)
                #await cog.achievement_award_notification(LEVELING_6, member)


def setup(bot):
    bot.add_cog(AchievementHandler(bot))
