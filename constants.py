from enum import Enum
import datetime

DISCORD_EPOCH = datetime.datetime(2015, 1, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc) # the time discord was born

class AccountAccessLevel(Enum):
    DEVELOPER = 0
    ADMIN = 10
    MODERATOR = 20
    MEMBER = 30

class Permission(Enum):
    # permissions for the dev cog
    DEV_COG = 1000

    # permissions for the admin cog
    ADMIN_COG = 2000
    ADMIN_COG_ELEVATE = ADMIN_COG + 1

    # permissions for the word count cog
    WORD_COUNT_COG = 3000
    WORD_COUNT_COG_SCAN = WORD_COUNT_COG + 1 

    # permissions for the economy cog
    ECONOMY_COG = 4000 