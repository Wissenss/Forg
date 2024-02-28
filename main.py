import os
from datetime import datetime

import discord
from discord.ext import commands

import sqlite3

from dotenv import load_dotenv

######## Settings ########
load_dotenv(override=True)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX')

######## Globals ########
connection = None

######## Discord ########
intents = discord.Intents.default()
intents.message_content = True  
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
  print("Nito is online!")

  bot.add_command(ping)
  bot.add_command(rank)

  bot.add_command(scan)
  bot.add_command(forget)

  conn_string = "./Nito.db"

  global connection 
  connection = sqlite3.connect(conn_string)

@bot.event
async def on_guild_join(guild):
  print(f"Nito just joined {guild.id}")

  # create the record for the new guild
  try:
    cursor = connection.cursor()

    cursor.execute("INSERT INTO guilds(guild_id, scanned) VALUES (?, ?)", [guild.id, False])

    connection.commit()
    cursor.close()

  except connection.Error as e:
    print(repr(e))
    connection.rollback()
    cursor.close()

@bot.event
async def on_message(message):
  await bot.process_commands(message)

  process_message_event(message)

@commands.command(brief="Show the top 10 members with more mentions of the nword")
async def rank(ctx):

  cursor = connection.cursor()

  cursor.execute("SELECT * FROM guild_members WHERE guild_id = ? ORDER BY nword_count DESC LIMIT 10;", [ctx.guild.id])

  rows = cursor.fetchall()

  content = ""

  for i, row in enumerate(rows):
    user_id = int(row[2])
    nword_count = row[3]

    print(user_id)
    print(ctx.message.author.id)
    member = await ctx.guild.fetch_member(user_id)

    print(member)

    #[TODO] handle the case in which a member has abandon the server
    if not member: 
      continue

    name = member.nick if member.nick != None else member.name

    content += f"{i}. **{name}** ({nword_count}) \n"

  em = discord.Embed(title="NWord Rank", description=content)

  cursor.close()

  await ctx.send(embed=em)

@commands.command(hidden=True, brief="pong", description="test for correct bot connection")
async def ping(ctx):
  print("ping called!")
  await ctx.send("pong")

@commands.command(hidden=True, brief="scanner", description="scan all the server channels for previous mentions of the nword, it will scan at most the las 5000 messages of each channel")
async def scan(ctx):
  
  # check if the server has been scanned before
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM guilds WHERE guild_id=? LIMIT 1;", [ctx.guild.id])

  record = cursor.fetchone()

  if (record[1] == str(ctx.guild.id) and record[2] == 1):
    await ctx.send("this server has been scanned already!")
    cursor.close()
    return

  cursor.close()

  await ctx.send("scaning the server for previous mentions of the nword, this might take a while...")

  occurrences = 0

  for channel in ctx.guild.text_channels:
    print(f"scanning channel: {channel.name}")
    await ctx.send(f"scanning channel: {channel.name}")

    try:
      async for message in channel.history(limit=None):
        occurrences += process_message_event(message)
    except discord.errors.Forbidden:
      await ctx.send(f"Nito lacks permisions to scan channel: {channel.name}")
  
  await ctx.send(f"scan completed! {occurrences} mentions found")

  # set the guild as scanned
  try:
    cursor = connection.cursor()

    cursor.execute("UPDATE guilds SET scanned=? WHERE guild_id=?;", [True, ctx.guild.id])

    connection.commit()
    cursor.close()

  except connection.Error as e:
    print(repr(e))
    connection.rollback()
    cursor.close()

  pass

@commands.command(hidden=True)
async def forget(ctx):
  print(f"forget called (Guild ID: {ctx.guild.id})")

  # this command can only be run by me
  if(ctx.message.author.id != 334016584093794305):
    await ctx.send("This command shall only be run by master Wissens")
    return 
  
  # clear all records from this server
  try:
    cursor = connection.cursor()

    cursor.execute("DELETE FROM nword_events WHERE guild_id = ?;", [ctx.guild.id])
    cursor.execute("DELETE FROM guild_members WHERE guild_id = ?;", [ctx.guild.id])
    cursor.execute("UPDATE guilds SET scanned = ? WHERE guild_id = ?;", [False, ctx.guild.id])

    connection.commit()

  except connection.Error as e:
    print(repr(e))
    connection.rollback()

  finally:
    cursor.close()

  await ctx.send("All message history for this server has been deleted!")

######## Utils ########
def date_to_sqlite_date(datetime):
   return datetime.strftime("%Y-%m-%d %H:%M:%S")

def sqlite_date_to_date(sqlite_date):
   return datetime.strptime(sqlite_date, "%Y-%m-%d %H:%M:%S")

def process_message_event(message):
  target_list = ["nigga", "nigger", "negro"]

  content = message.content
  content_lower = content.lower()
  word_count = 0

  print(f"processing message: {message.id} by {message.author.id}", end=" ")

  for target in target_list:
    word_count += content_lower.count(target)

  if word_count == 0:
    print("0 metions found")
    return word_count

  try:
    # if there is 1 or more ocurrence of the nword we create a registry of the event
    cursor = connection.cursor()
    
    values = [None] * 7

    values[0] = message.id
    values[1] = message.author.id
    values[2] = message.guild.id
    values[3] = content
    values[4] = word_count
    values[5] = message.jump_url
    values[6] = date_to_sqlite_date(datetime.today())
    
    cursor.execute("INSERT INTO nword_events(message_id, author_id, guild_id, message, word_count, jump_url, date) VALUES(?, ?, ?, ?, ?, ?, ?);", values)

    # if the user doesn't exists we create it
    cursor.execute("SELECT * FROM guild_members WHERE guild_id = ? AND member_id = ? LIMIT 1;", [message.guild.id, message.author.id])

    rows = cursor.fetchall()

    if(len(rows) == 0):
      cursor.execute("INSERT INTO guild_members(guild_id, member_id, nword_count) VALUES(?, ?, ?)", [message.guild.id, message.author.id, word_count])
    else:
      cursor.execute("UPDATE guild_members SET nword_count=? WHERE guild_id=? AND member_id=?;", [word_count + rows[0][3], message.guild.id, message.author.id])

    connection.commit()
    cursor.close()

  except connection.Error as e:
    print(repr(e))
    connection.rollback()
    cursor.close()

  print(f"{word_count} mentions found")
  return word_count

bot.run(DISCORD_TOKEN)