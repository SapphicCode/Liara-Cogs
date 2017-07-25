import asyncio
import datetime

import dateparser
import discord
from discord.ext import commands

from cogs.utils import checks
from cogs.utils.storage import RedisDict


class TempBans:
    def __init__(self, liara):
        self.loaded = True
        self.liara = liara
        self.banlist = RedisDict('pandentia.tempbans', liara.redis)
        if 'bans' not in self.banlist:
            self.banlist['bans'] = []
        self.task = self.liara.loop.create_task(self.unban_task())

    def __unload(self):
        self.loaded = False
        self.banlist.close()

    async def get_user(self, uid):
        return self.liara.get_user(uid) or await self.liara.get_user_info(uid)

    async def unban_task(self):
        while self.loaded:
            for ban in list(self.banlist['bans']):
                if ban['time'] > datetime.datetime.utcnow():
                    continue
                guild = self.liara.get_guild(ban['guild'])
                if guild is None:
                    continue
                try:
                    user = await self.get_user(ban['member'])
                    self.liara.dispatch('pandentia_tempbans_unban', guild, user)
                    await guild.unban(user, reason='Temporary ban expired.')
                except discord.DiscordException:
                    pass
                finally:
                    self.banlist['bans'].remove(ban)
                    self.banlist.commit('bans')
                await asyncio.sleep(0.05)
            await asyncio.sleep(5)

    @commands.command(no_pm=True)
    @checks.mod_or_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member, *, time: str):
        """Temporarily bans a member."""
        parsed = dateparser.parse('in '+time, settings={'TIMEZONE': 'UTC', 'PREFER_DATES_FROM': 'future'})
        if parsed is None:
            await ctx.send('That date couldn\'t be parsed. Try again.')
            return
        delta = (parsed - datetime.datetime.utcnow()).total_seconds()
        if delta < 0:
            await ctx.send('Sorry, I can\'t time travel.')
            return
        if delta < 120:  # 2 minutes
            await ctx.send('Sorry, that duration is a bit too short.')
            return
        if delta > 2628000:  # 1 month
            await ctx.send('Sorry, that duration is a bit too long.')
            return

        try:
            await member.ban(reason='Temporary ban: Banned by {} until {}.'.format(ctx.author, parsed))
            self.banlist['bans'].append({'time': parsed, 'member': member.id, 'guild': ctx.guild.id})
            self.banlist.commit('bans')
        except discord.Forbidden:
            await ctx.send('I don\'t have permission to ban that person here.')
            return

        await ctx.send('Banned. That member will be unbanned on {}.'.format(parsed))


def setup(liara):
    liara.add_cog(TempBans(liara))
