from discord.ext import commands
from cogs.utils import dataIO
from cogs.utils import checks
import discord
import asyncio


class Status:
    """A cog to persist your status and game."""
    def __init__(self, liara):
        self.liara = liara
        self.db = dataIO.load('pandentia.status')
        if 'status' not in self.db:
            self.db['status'] = 'online'
        if 'game' not in self.db:
            self.db['game'] = None
        self.task = self.liara.loop.create_task(self.update_loop())

    def _unload(self):
        self.db.die = True
        self.task.cancel()

    async def update_loop(self):
        await self.liara.wait_until_ready()
        while True:
            try:
                game = self.db['game']
                await self.liara.change_presence(status=discord.Status(self.db['status']),
                                                 game=discord.Game(name=game) if game else None, afk=True)
            except:
                pass
            await asyncio.sleep(60)

    @commands.command()
    @checks.is_owner()
    async def statusset(self, ctx, status: str, *, game: str=None):
        """Sets the status and game to persist."""
        try:
            status = discord.Status(status)
        except ValueError:
            await ctx.send('Invalid status. Valid statuses: `online`, `idle`, `dnd` and `offline`.')
            return
        self.db['status'] = str(status)
        self.db['game'] = game
        await ctx.send('Status and game set.')


def setup(liara):
    liara.add_cog(Status(liara))
