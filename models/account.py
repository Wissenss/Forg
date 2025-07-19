import constants

class Account():
    def __init__(self):
        self.id : int = 0
        self.discord_user_id : int = 0
        self.discord_guild_id : int = 0
        self.access_level : constants.AccountAccessLevel = constants.AccountAccessLevel.MEMBER