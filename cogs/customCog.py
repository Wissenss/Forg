import discord
import discord.ext
import discord.ext.commands

from models.account import *

import database

# this class defines logic / methods that must be available in every cog
# all other cogs should inherith from CustomCog class

class CustomCog(discord.ext.commands.Cog):
    def __init__(self, bot):
        super().__init__()

        self.bot : discord.Client = bot