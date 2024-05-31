import datetime
import random

import traceback
import sys

import discord
from discord.ext import commands

import sqlite3

from settings import *

from discord.ext import tasks, commands

######## Globals ########
connection = None
hosting_payed = True
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
  BOT_LOGGER.log(level=logging.INFO, msg="------------------- Bot is ready -------------------")
  BOT_LOGGER.log(level=logging.INFO, msg="Loading commands...")

  bot.add_command(top)
  bot.add_command(rank)
  bot.add_command(quote)
  bot.add_command(hosting)

  bot.add_command(scan)
  bot.add_command(forget)
  bot.add_command(ping)
  bot.add_command(add_hosting)

  BOT_LOGGER.log(level=logging.INFO, msg="Connecting to database...")

  conn_string = "./Nito.db"

  global connection 
  connection = sqlite3.connect(conn_string)

  BOT_LOGGER.log(level=logging.INFO, msg="Starting tasks...")
  daily_check_task.start()


  BOT_LOGGER.log(level=logging.INFO, msg="----------------------------------------------------")

  print("Nito is online!")

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
  BOT_LOGGER.log(level=logging.DEBUG, msg=f"message event (Guild ID: {message.guild.id}) (Member ID: {message.author.id}) (Member NAME: '{message.author.name}') (Message: '{message.content}')")

  await bot.process_commands(message)

  #ignore messages comming from the bot itself
  if message.author.id == bot.user.id:
    return

  if has_nwords(message):
    BOT_LOGGER.log(level=logging.DEBUG, msg=f"nword messsage event (Guild ID: {message.guild.id}) (Member ID: {message.author.id}) (Member NAME: '{message.author.name}') (Message: '{message.content}')")

    if not is_timeout(message.guild.id, message.author.id):
      BOT_LOGGER.log(level=logging.INFO, msg=f"valid event (Guild ID: {message.guild.id}) (Member ID: {message.author.id}) (Member NAME: '{message.author.name}') (Message: '{message.content}')")

      register_message_event(message.guild.id, message.author.id)
      process_nword_message_event(message)
    else:
      BOT_LOGGER.log(level=logging.INFO, msg=f"timedout (Guild ID: {message.guild.id}) (Member ID: {message.author.id}) (Member NAME: '{message.author.name}') (Message: '{message.content}')")

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
  BOT_LOGGER.log(level=logging.INFO, msg=f"top command called (Guild ID: {ctx.guild.id}) (Member ID: {ctx.message.author.id}) (Member NAME: '{ctx.message.author.name}')")

  cursor = connection.cursor()

  cursor.execute("SELECT * FROM guild_members WHERE guild_id = ? ORDER BY nword_count DESC LIMIT 10;", [ctx.guild.id])

  rows = cursor.fetchall()

  content = ""

  for i, row in enumerate(rows):
    user_id = int(row[2])
    nword_count = row[3]

    try:
      member = await ctx.guild.fetch_member(user_id)
    except:
      continue

    name = member.nick if member.nick != None else member.name

    content += f"{i}. **{name}** ({nword_count}) \n"

  em = discord.Embed(title="NWord Rank", description=content)

  cursor.close()

  await ctx.send(embed=em)

@commands.command(brief="Show your current rank")
async def rank(ctx, member:discord.Member = None):
  BOT_LOGGER.log(level=logging.INFO, msg=f"rank command called (Guild ID: {ctx.guild.id}) (Member ID: {ctx.message.author.id}) (Member NAME: '{ctx.message.author.name}')")

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

  content = f"Total count: {nword_count}"

  # get the position on the ranking
  cursor.execute("SELECT * FROM guild_members WHERE guild_id = ? AND nword_count > ? ORDER BY nword_count", [guild_id, nword_count])
  rows = cursor.fetchall()

  position = len(rows) + 1

  # get the points away from the next rank
  if rows:
    away_from_next_rank = rows[-1][3] - nword_count

    content += f"\nAway from next rank: {away_from_next_rank}"

  member_name = member.nick if member.nick else member.name

  em = discord.Embed(title=f"{member_name} #{position}", description=content)

  await ctx.send(embed=em)

@commands.command(brief="Get a random message where someone said the nword")
async def quote(ctx, member:discord.Member = None):
  BOT_LOGGER.log(level=logging.INFO, msg=f"quote command called (Guild ID: {ctx.guild.id}) (Member ID: {ctx.message.author.id}) (Member NAME: '{ctx.message.author.name}')")

  if not member:
    member = ctx.message.author

  cursor = connection.cursor()

  # get a random message record
  sql = "SELECT * FROM nword_events WHERE guild_id = ? AND author_id = ? AND message NOT IN ('Nigger', 'nigger', 'nigga', 'Nigga', ':negro:');"

  cursor.execute(sql, [ctx.guild.id, member.id])
  
  rows = cursor.fetchall()
  
  rows_count = len(rows)

  if rows_count == 0:
    await ctx.send(f"{member.display_name} has no (real) mentions of the nword yet")
    return

  row = rows[random.randint(0, rows_count - 1)]

  # get the actual discord message
  message_id = row[1]

  try:
    channel = bot.get_channel(row[8])

    if channel == None:
      channel = ctx.channel

    message = await channel.fetch_message(message_id)

    content = message.content
    date = message.created_at
    jump_url = message.jump_url
  
  except:
    BOT_LOGGER.log(level=logging.ERROR, msg=f"message not found by discord, using local copy... (Guild ID: {ctx.guild.id}) (Message ID: {message_id})")

    content = row[4]
    date = sqlite_date_to_date(row[7])
    jump_url = row[6]

  cursor.close()

  # create the embed and send it
  description = f"_**\" {content} \"**_\n"

  em = discord.Embed(title="", description=description, timestamp=date, type='article') #title=f"{member.display_name}" url=jump_url description=description
  em.set_author(name=f"{member.display_name}", url=jump_url, icon_url=member.display_avatar.url)
  em.set_footer(text=f"")
  # em.add_field(name=" ", value="", inline=True)
  # em.add_field(name="", value=f"{content}", inline=True)

  await ctx.send(embed=em)

@commands.command(brief="Get the remaining days hosting is paid for and some more other interesting information")
async def hosting(ctx):
  BOT_LOGGER.log(level=logging.INFO, msg=f"hosting called (Guild ID: {ctx.guild.id}) (Member ID: {ctx.message.author.id}) (Member NAME: '{ctx.message.author.name}')")
  
  days_payed = get_remaining_hosting_days()

  await ctx.send(f"hosting is paid for the next {days_payed} days")

######## Dev Commands ########

@tasks.loop(time=DAILY_CHECK_TIME)
async def daily_check_task():
  BOT_LOGGER.log(level=logging.INFO, msg=f"daily check task is starting...")

  days_payed = get_remaining_hosting_days()

  cursor = connection.cursor()

  # every day we should decrease the remaining hosting days payed
  sql = "UPDATE configuration set value_integer = value_integer - 1 WHERE name = 'remaining_hosting_days_payed';"

  cursor.execute(sql)

  global hosting_payed

  if days_payed > 0 or days_payed == -1000:
    hosting_payed = True
  else:
    hosting_payed = False

  connection.commit()
  cursor.close()

  BOT_LOGGER.log(level=logging.INFO, msg=f"remaining_hosting_days_payed is now = {days_payed}")
  BOT_LOGGER.log(level=logging.INFO, msg=f"daily check task finished")

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

@commands.command(hidden=True, name="addHosting")
async def add_hosting(ctx, hostingDays : int):
  BOT_LOGGER.log(level=logging.INFO, msg=f"addHosting called (Guild ID: {ctx.guild.id}) (Member ID: {ctx.message.author.id}) (Member NAME: '{ctx.message.author.name}')")

  # this command can only be run by me
  if(ctx.message.author.id != 334016584093794305):
    await ctx.send("This command shall only be run by master Wissens")
    return 
  
  try:

    days_payed = get_remaining_hosting_days()

    if days_payed != -1000:

      if days_payed < 0:
        days_payed = 0

      days_payed += hostingDays

      cursor = connection.cursor()

      cursor.execute("UPDATE configuration SET value_integer = ? WHERE name = 'remaining_hosting_days_payed';", [days_payed])

      connection.commit()

      await ctx.send(f"{hostingDays} added. Your server now has {days_payed} days of hosting remaining")

  except connection.Error as e:
    print(repr(e))
    connection.rollback()

  finally:
    cursor.close()

@commands.command(hidden=True, brief="pong", description="test for correct bot connection")
async def ping(ctx):
  BOT_LOGGER.log(level=logging.INFO, msg=f"ping command called (Guild ID: {ctx.guild.id}) (Member ID: {ctx.message.author.id}) (Member NAME: '{ctx.message.author.name}')")

  await ctx.send("pong")

######## Utils ########
def date_to_sqlite_date(datetime : datetime.datetime):
   return datetime.strftime("%Y-%m-%d %H:%M:%S")

def sqlite_date_to_date(sqlite_date : str):
   return datetime.datetime.strptime(sqlite_date, "%Y-%m-%d %H:%M:%S")

def has_nwords(message):
  target_list = ["nigga", "nigger", "negro", "nigress"]

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
    values[6] = date_to_sqlite_date(message.created_at)
    
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

def get_remaining_hosting_days():
  cursor = connection.cursor()
  
  # now, if the days payed are less than 0, then we set this variable to false for checking on the other commands
  sql = "SELECT value_integer FROM configuration WHERE name = 'remaining_hosting_days_payed';"

  cursor.execute(sql)

  days_payed = cursor.fetchone()[0]

  cursor.close()

  return days_payed

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
    newest_date = datetime.datetime.now()

    delta = newest_date - oldest_date

    if delta.total_seconds() < 60:
      return True
  
  return False

def register_message_event(guild_id, member_id):
  ensure_storage(guild_id)
  
  nword_events = get_nword_events(guild_id, member_id)

  if len(nword_events) >= 10:
    storage[guild_id]['nword_events'][member_id].pop(0)

  storage[guild_id]['nword_events'][member_id].append(datetime.datetime.now())

bot.run(DISCORD_TOKEN, log_handler=None)