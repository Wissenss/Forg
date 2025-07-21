import sys
import logging

import discord
import discord.ext
import discord.ext.commands

import database

# this class defines logic / methods that must be available in every cog
# all other cogs should inherith from CustomCog class

class CustomCog(discord.ext.commands.Cog):
    def __init__(self, bot):
        super().__init__()

        self.bot : discord.Client = bot
        
        # setup logger

        self.log : logging.Logger = logging.getLogger(self.__class__.__name__)
        
        handler  : logging.StreamHandler = logging.StreamHandler(sys.stderr)
        formater : logging.Formatter = logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formater)

        self.log.addHandler(handler)
        self.log.setLevel(logging.INFO)

        #