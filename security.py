from constants import *
import database

ACCOUNT_ACCESS_LEVEL_PERMISSIONS = {
    AccountAccessLevel.MEMBER : [
        Permission.WORD_COUNT_COG
    ],
    AccountAccessLevel.MODERATOR : [
        Permission.ADMIN_COG,
        Permission.ADMIN_COG_ELEVATE
    ] 
}

def access_level_has_permision(level : AccountAccessLevel, permission : Permission) -> bool:
    if level == AccountAccessLevel.DEVELOPER:
        return True
    
    if level in ACCOUNT_ACCESS_LEVEL_PERMISSIONS.keys():
        return permission in ACCOUNT_ACCESS_LEVEL_PERMISSIONS[level]
            
    return False

def account_has_permision(discord_user_id : int, discord_guild_id : int, permission : Permission) -> bool:
    level = get_account_level(discord_user_id, discord_guild_id)

    return access_level_has_permision(level, permission)

def ensure_account_exists(discord_user_id : int, discord_guild_id : int):
    con = database.ConnectionPool.get()
    cur = con.cursor()

    sql = """
    INSERT INTO accounts (discord_user_id, discord_guild_id, access_level)
    VALUES (?, ?, ?)
    ON CONFLICT (discord_user_id, discord_guild_id) DO NOTHING;
    """

    cur.execute(sql, [discord_user_id, discord_guild_id, AccountAccessLevel.MEMBER.value])

    con.commit()

    database.ConnectionPool.release(con)

def get_account_level(discord_user_id : int, discord_guild_id : int) -> AccountAccessLevel:
    if discord_user_id in [334016584093794305]:
        return AccountAccessLevel.DEVELOPER
    
    ensure_account_exists(discord_user_id, discord_guild_id)   

    con = database.ConnectionPool.get()
    cur = con.cursor()

    cur.execute("SELECT access_level FROM accounts WHERE discord_user_id = ? AND discord_guild_id = ?;", [discord_user_id, discord_guild_id])

    database.ConnectionPool.release(con)
    
    return AccountAccessLevel(cur.fetchone()[0])

def set_account_level(discord_user_id : int, discord_guild_id : int, level : AccountAccessLevel):
    ensure_account_exists(discord_user_id, discord_guild_id)
    
    con = database.ConnectionPool.get()
    cur = con.cursor()

    cur.execute("UPDATE accounts SET access_level = ? WHERE discord_user_id = ? AND discord_guild_id = ?;", [level.value, discord_user_id, discord_guild_id])

    con.commit()

    database.ConnectionPool.release(con)