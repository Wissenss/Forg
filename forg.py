import discord 
from discord.ext import commands

import environment
import constants
import database

class Forg(commands.Bot):
    def __init__(self, *args, **kwargs):
        database.ConnectionPool.init()
        super().__init__(*args, **kwargs)

    async def close(self):
        database.ConnectionPool.finish()
        await super().close()

# this is the enty point of the bot

intents =  discord.Intents.default()
intents.message_content = True
intents.members = True

bot = Forg(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("ready!")

@bot.event
async def setup_hook():
    await bot.load_extension("cogs.adminCog")
    await bot.load_extension("cogs.generalCog")
    await bot.load_extension("cogs.wordCounterCog")
    await bot.load_extension("cogs.triviaCog")

    for guild in bot.guilds:
        if guild.id in [constants.DEV_GUILD_ID, constants.KUVA_GUILD_ID, constants.BUTTHOLE_LOVERS_GUILD_ID, constants.ROLLING_WAVES_REPUBLIC_GUILD_ID]:
            await bot.tree.sync(guild=discord.Object(id=guild.id))

    await bot.tree.sync()

    print("setup finished!")


bot.run(environment.DISCORD_TOKEN)