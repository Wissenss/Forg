from enum import Enum

class AccountAccessLevel(Enum):
    DEVELOPER = 0
    ADMIN = 1
    MODERATOR = 3
    MEMBER = 4

class Permission(Enum):
    # permissions for the dev cog
    DEV_COG = 1000

    # permissions for the admin cog
    ADMIN_COG = 2000

    # permissions for the word count cog
    WORD_COUNT_COG = 3000
    WORD_COUNT_COG_SCAN = WORD_COUNT_COG + 1 

    # permissions for the economy cog
    ECONOMY_COG = 4000 