import os
from datetime import datetime

import traceback
import sys

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
storage = {}

"""
the storage has the following structure:

storage = {
  guild_id : {
    'nword_events' : {
      member_id : [(date)]
    },
  }
}

"""

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
  bot.add_command(top)

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

  if has_nwords(message):
    if not is_timeout(message.guild.id, message.author.id):
      register_message_event(message.guild.id, message.author.id)
      process_nword_message_event(message)
    else:
      author_name = message.author.nick if message.author.nick else message.author.name

      await message.channel.send(f"**{author_name}** pass is temporarly revoked")

@bot.event
async def on_command_error(ctx: commands.Context, error):

  if isinstance(error, discord.ext.commands.errors.MemberNotFound):
    await ctx.send(f"member '{error.argument}' not found")

  else:
    print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

@commands.command(brief="Show the top 10 members with more mentions of the nword")
async def top(ctx):

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

@commands.command(brief="Show your current rank")
async def rank(ctx, member:discord.Member = None):
  
  if not member:
    member = ctx.message.author

  member_id = member.id
  guild_id = ctx.guild.id

  # get the number of times the user has said the nword
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM guild_members WHERE guild_id = ? AND member_id = ?;", [guild_id, member_id])
  row = cursor.fetchone()

  if row:
    nword_count = row[3]
  else:
    nword_count = 0

  # get the position on the ranking
  cursor.execute("SELECT count(*) FROM guild_members WHERE guild_id = ? AND nword_count > ?", [guild_id, nword_count])
  row = cursor.fetchone()

  position = row[0] + 1

  content = f"Total count: {nword_count}"

  member_name = member.nick if member.nick else member.name

  em = discord.Embed(title=f"{member_name} #{position}", description=content)

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
        if (has_nwords(message)):
          occurrences += process_nword_message_event(message, False)
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

def has_nwords(message):
  target_list = ["nigga", "nigger", "negro"]

  content_lower = message.content.lower()

  word_count = 0

  for target in target_list:
    word_count += content_lower.count(target)

  if word_count > 0: 
    return True
  else:
    return False

def process_nword_message_event(message, silent=True):
  content = message.content
  word_count = 1

  if not silent:
    print(f"processing message: {message.id} by {message.author.id}", end=" ")

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

  if not silent:
    print(f"{word_count} mentions found")
  
  return word_count

######## Storage Utils ########

def ensure_storage(guild_id):
  if not guild_id in storage:
    storage[guild_id] = {
      'nword_events' : {}
    }

def get_nword_events(guild_id, member_id):
  events = storage[guild_id]['nword_events']

  if not member_id in events:
    storage[guild_id]['nword_events'][member_id] = []

  return storage[guild_id]['nword_events'][member_id]

def is_timeout(guild_id, member_id):
  ensure_storage(guild_id)
  
  nword_events = get_nword_events(guild_id, member_id)

  if len(nword_events) > 5:
    oldest_date = nword_events[-4]
    newest_date = datetime.now()

    delta = newest_date - oldest_date

    if delta.total_seconds() < 60:
      return True
  
  return False

def register_message_event(guild_id, member_id):
  ensure_storage(guild_id)
  
  nword_events = get_nword_events(guild_id, member_id)

  if len(nword_events) >= 10:
    storage[guild_id]['nword_events'][member_id].pop(0)

  storage[guild_id]['nword_events'][member_id].append(datetime.now())

bot.run(DISCORD_TOKEN)