from constants import *
import database

ACCOUNT_ACCESS_LEVEL_PERMISSIONS = {
    AccountAccessLevel.MEMBER : [
        Permission.WORD_COUNT_COG
    ], 
}

def access_level_has_permision(level : AccountAccessLevel, permission : Permission) -> bool:
    if level in ACCOUNT_ACCESS_LEVEL_PERMISSIONS.keys():
        return permission in ACCOUNT_ACCESS_LEVEL_PERMISSIONS[level]
            
    return False

def account_has_permision(discord_user_id : int, discord_guild_id : int, permission : Permission) -> bool:
    con = database.ConnectionPool.get()
    cur = con.cursor()

    level = cur.fetchone("SELECT access_level FROM accounts WHERE discord_user_id = ? AND discord_guild_id = ?;", [discord_user_id, discord_guild_id])[0]

    database.ConnectionPool.release(con)

    return access_level_has_permision(level, permission)