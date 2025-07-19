import discord

import database

# this file defines helpers to read / write a value to the settings table

def get_value(name : str, discord_user_id : int = 0, discord_guild_id : int = 0, discord_channel_id : int = 0, default : str = ""):
    cur = database.ConnectionPool.get().cursor()

    sql = "SELECT value FROM settings WHERE name = ? AND discord_user_id = ? AND discord_guild_id = ? AND discord_channel_id = ?;"

    cur.execute(sql, [name, discord_user_id, discord_guild_id, discord_channel_id])

    value = default

    result = cur.fetchone()

    if result:
        value = result[0]
    
    database.ConnectionPool.release(cur.connection)

    return value

def set_value(name : str, discord_user_id : int = 0, discord_guild_id : int = 0, discord_channel_id : int = 0, value : str = ""):
    cur = database.ConnectionPool.get().cursor()

    sql = """
    INSERT INTO settings (name, discord_user_id, discord_guild_id, discord_channel_id, value)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT (name, discord_user_id, discord_guild_id, discord_channel_id) DO UPDATE SET value = ?
    """

    cur.execute(sql, [name, discord_user_id, discord_guild_id, discord_channel_id, value, value])

    cur.connection.commit()

    database.ConnectionPool.release(cur.connection)

# TODO: convenient wrappers: to take a discord.Interaction, to parse from string to type, to cast from type to string (also known as "talacha")

def get_value_from_interaction(name : str, interaction : discord.Interaction, default : str = ""):
    return get_value(name, interaction.user.id, interaction.guild.id, interaction.channel.id, default)

def set_value_from_interaction(name : str, interaction : discord.Interaction, value : str = ""):
    return set_value(name, interaction.user.id, interaction.guild.id, interaction.channel.id, value)

if __name__ == "__main__":
    database.ConnectionPool.init()

    print("testing read_value")

    database.ConnectionPool.finish()