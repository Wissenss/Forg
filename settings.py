# this scripts handles reading the configuration file and configuring the bot like so.
# all variables here are global

import logging
import logging.handlers
import os
from dotenv import load_dotenv

import datetime

load_dotenv(override=True)

BOT_LOGGER = None
DISCORD_LOGGER = None
LOG_LEVEL = None
DISCORD_TOKEN = None
COMMAND_PREFIX = None

""" Configuration for the logger """
LOG_LEVEL = os.getenv('LOG_LEVEL')

# logging handler
handler = logging.handlers.RotatingFileHandler(
  filename='Nito.log',
  encoding='utf-8',
  maxBytes=32*1024*1024, #32 MiB
  backupCount=10
)

# formatter
datetime_format = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', datefmt=datetime_format, style='{')
handler.setFormatter(formatter)

# loggers
discordLogger = logging.getLogger('discord')
discordLogger.setLevel(LOG_LEVEL)
discordLogger.addHandler(handler)
DISCORD_LOGGER = discordLogger

botLogger = logging.getLogger('nito.bot')
botLogger.setLevel(LOG_LEVEL) 
botLogger.addHandler(handler)
BOT_LOGGER = botLogger

from dotenv import load_dotenv

""" Configuration for Discord """
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX')

# remember, discord.py will take the utc time, so you have to account for the offset, for now 8pm mexico city is 2am utc
DAILY_CHECK_TIME = datetime.datetime.strptime(os.getenv('DAILY_CHECK_TIME'), "%H:%M:%S").time()