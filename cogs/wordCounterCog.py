import datetime
import re
from typing import Optional

import discord
import discord.ext
import discord.ext.commands

import constants
import database
import security

from cogs.customCog import CustomCog
import settings

class WordCounterCog(CustomCog):
    def __init__(self, bot):
        super().__init__(bot)

        self.ongoing_scan_message_id : int = 0
        self.ongoing_scan_channel_id : int = 0
        self.ongoing_scan : bool = False

    def clean_message_content(self, content : str) -> str:
        cleaned = content.strip().lower() 

        # Remove punctuation and symbols (keep letters, digits, underscores)
        cleaned = re.sub(r"[^\w\s]", "", cleaned)

        # Replace multiple spaces/tabs/newlines with a single space
        text = re.sub(r"\s+", " ", cleaned)

        return cleaned
    
    def save_message(self, message : discord.Message):
        con = database.ConnectionPool.get()
        cur = con.cursor()

        sql = "INSERT INTO messages(discord_message_id, discord_guild_id, discord_channel_id, discord_created_at, discord_user_id, content, content_clean) VALUES(?, ?, ?, ?, ?, ?, ?);"

        cur.execute(sql, [message.id, message.guild.id, message.channel.id, message.created_at.strftime("%Y-%m-%d %H:%M:%S"), message.author.id, message.content, self.clean_message_content(message.content)])
        con.commit()

        database.ConnectionPool.release(con)

    def save_message_word_count(self, message : discord.Message):
        con = database.ConnectionPool.get()
        cur = con.cursor()
        
        tokens = self.clean_message_content(message.content).split(" ")

        sql = """
        INSERT INTO messages_word_count(word, discord_guild_id, discord_channel_id, discord_user_id, count)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(word, discord_guild_id, discord_channel_id, discord_user_id) DO UPDATE SET
            count = count + 1;
        """
        
        for t in tokens:
            cur.execute(sql, [t, message.guild.id, message.channel.id, message.author.id])

        con.commit()

        database.ConnectionPool.release(con)

    def is_message_saved(self, message : discord.Message):
        con = database.ConnectionPool.get()
        cur = con.cursor()

        message_found = False

        cur.execute("SELECT * FROM messages WHERE discord_message_id = ?", [message.id])

        if cur.fetchone():
            message_found = True
        
        database.ConnectionPool.release(con)
        
        return message_found

    def process_message(self, message : discord.Message):
        self.save_message(message)
        self.save_message_word_count(message)

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message : discord.Message):

        if message.author.id == self.bot.user.id:
            return

        self.process_message(message)

    @discord.app_commands.command(name="wordscan")
    async def wordscan(self, interaction : discord.Interaction):
        
        em = discord.Embed(title="scanner log", description="")

        # check caller has permissions for this command
        if not security.account_has_permision(interaction.user.id, interaction.guild.id, constants.Permission.WORD_COUNT_COG_SCAN):
            em.description = "You're not allowed to use this!"
            return await interaction.response.send_message(embed=em, ephemeral=True)

        # check there is no other scan happening
        if self.ongoing_scan:
            ongoing_scan_channel = await interaction.guild.fetch_channel(self.ongoing_scan_channel_id)
            ongoing_scan_message = await ongoing_scan_channel.fetch_message(self.ongoing_scan_message_id)

            em.title = ""
            em.description += f"another scann is allready in progress at {ongoing_scan_message.jump_url}"

            return await interaction.response.send_message(embed=em, ephemeral=True)

        # start the scan
        scan_logs = []
        scan_logs_update_interval = 14

        scan_logs.append("starting message scan...")
        em.description = "\n".join(scan_logs)
        await interaction.response.send_message(embed=em)

        try:
            # fetch original message to bypass 15 min interaction limit imposed by discord
            #interaction_message = await interaction.original_response()
            #interaction_message = await interaction.channel.fetch_message(interaction_message.id)
            interaction_message = await interaction.original_response()

            # mark the scan as started
            self.ongoing_scan = True
            self.ongoing_scan_channel_id = interaction_message.channel.id
            self.ongoing_scan_message_id = interaction_message.id

            # fetch channels in the guild
            scan_logs.append("fetching channels...")
            em.description = "\n".join(scan_logs)
            await interaction.followup.edit_message(embed=em)

            guild_channels = interaction.guild.text_channels

            scan_logs[-1] = f"fetching channels... {len(guild_channels)} found"
            em.description = "\n".join(scan_logs)
            await interaction.followup.edit_message(embed=em)

            # got through every channel in the guild

            for channel in guild_channels:
                
                scan_logs.append(f"processing channel \"{channel.name}\"... ")
                em.description = "\n".join(scan_logs)
                await interaction.followup.edit_message(embed=em)
                
                # check the bot has permissions for this channel

                permissions = channel.permissions_for(interaction.guild.me)

                if not (permissions.read_messages and permissions.read_message_history and permissions.view_channel):
                    scan_logs[-1] = f"processing channel \"{channel.name}\"... lacking permisions"
                    em.description = "\n".join(scan_logs)
                    await interaction.followup.edit_message(embed=em)
                    continue

                # go through every message on the channel 

                progress = 0

                first_message_created_at = constants.DISCORD_EPOCH # this is needed to more accurately calculate percentage completion
                async for message in channel.history(limit=1, oldest_first=True):
                    first_message_created_at = message.created_at
                
                after = datetime.datetime.strptime(settings.get_value("latest_scan_message_created_at", 0, interaction.guild.id, channel.id, constants.DISCORD_EPOCH.strftime("%Y-%m-%d %H:%M:%S")), "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc) # only messages after the last stored scan time will be considered

                async for message in channel.history(limit=None, oldest_first=True, after=after):
                    
                    if not self.is_message_saved(message) and message.author.id != self.bot.user.id:
                        self.process_message(message)

                    progress += 1

                    # register progress every <scan_logs_update_interval> 

                    if progress % scan_logs_update_interval:
                        now = datetime.datetime.now(datetime.timezone.utc)
                        
                        # update the progress message
                        completion_rate = (message.created_at - first_message_created_at).total_seconds() / (now - first_message_created_at).total_seconds()
                        scan_logs[-1] = f"processing channel \"{channel.name}\"... {completion_rate:.2%}"
                        em.description = "\n".join(scan_logs)
                        em.timestamp = now
                        em.set_footer(text="last update")
                        await interaction.followup.edit_message(embed=em)

                        # save the last scan message creation time
                        settings.set_value("latest_scan_message_created_at",  0, interaction.guild.id, channel.id, message.created_at.strftime("%Y-%m-%d %H:%M:%S"))
                
                scan_logs[-1] = f"processing channel \"{channel.name}\"... 100.00%"
                em.description = "\n".join(scan_logs)
                await interaction.followup.edit_message(embed=em)

        except Exception as e:
            scan_logs.append(f"unexpected failure!")
            scan_logs.append(f"```\n{repr(e)}\n```")

        # mark the scan as finished
        self.ongoing_scan = False
        self.ongoing_scan_channel_id = 0
        self.ongoing_scan_message_id = 0

        scan_logs.append("finished!")
        em.description = "\n".join(scan_logs)
        await interaction.followup.edit_message(embed=em)

    # normal word commands

    @discord.app_commands.command(name="wordquote")
    async def wordquote(self, interaction : discord.Interaction, word : str, member : Optional[discord.Member] = None):
        if member == None:
            member = interaction.user
        
        em = discord.Embed(title="", description=f"searching **{word}** mentions...")

        await interaction.response.send_message(embed=em)
        
        con = database.ConnectionPool.get()
        cur = con.cursor()

        # this is the (somewhat) ineficient way of doing things
        # it may be worth it to take a look at https://www.sqlite.org/fts5.html if performance
        # becomes an issue

        sql = """
        SELECT * 
        FROM messages 
        WHERE deleted = False AND discord_user_id = ? AND discord_guild_id = ? AND 
        (
            content_clean LIKE ? 
            OR content_clean LIKE ?
            OR content_clean LIKE ?
            OR content_clean = ?
        ) 
        ORDER BY RANDOM()
        LIMIT 1
        """

        result = cur.execute(sql, [member.id, interaction.guild.id, f"% {word} %", f"%{word} %", f"% {word}%", f"{word}"])
        message = result.fetchone()

        database.ConnectionPool.release(con)

        if not message:
            em.description = f"no mention of **{word}** found for member **{member.display_name}**"
            return await interaction.edit_original_response(embed=em)

        discord_message_channel = interaction.guild.get_channel(message[2])
        
        if not discord_message_channel:
            em.description = "channel not found"
            return await interaction.edit_original_response(embed=em)

        try:
            discord_message = await discord_message_channel.fetch_message(message[0])

            if not discord_message:
                em.description = "message not found"
                return await interaction.edit_original_response(embed=em)

            em.description = f"_\"{discord_message.content}\"_"

            if discord_message.author:
                em.set_author(name=discord_message.author.display_name, icon_url=discord_message.author.avatar.url)
            
            em.timestamp = discord_message.created_at
            em.url = discord_message.jump_url

            return await interaction.edit_original_response(embed=em) 
        
        except discord.NotFound:
            
            # if the message is not found we mark it as deleted so it wont be shown again

            cur = database.ConnectionPool.get().cursor()

            cur.execute("UPDATE messages SET deleted = True WHERE discord_message_id = ?;", [message[0]])

            cur.connection.commit()

            database.ConnectionPool.release(cur.connection)

            em.description = "message deleted"

            return await interaction.edit_original_response(embed=em)

    @discord.app_commands.command(name="wordcount")
    async def wordcount(self, interaction : discord.Interaction, word : str, member : Optional[discord.Member] = None):
        if member == None:
            member = interaction.user
        
        cleaned_word = self.clean_message_content(word)
        
        em = discord.Embed(title="", description=f"searching **{cleaned_word}** mentions...")

        await interaction.response.send_message(embed=em)

        con = database.ConnectionPool.get()
        cur = con.cursor()

        sql = """
        SELECT SUM(count) 
        FROM messages_word_count 
        WHERE word = ? AND discord_guild_id = ? AND discord_user_id = ? 
        GROUP BY word, discord_guild_id, discord_user_id;
        """

        cur.execute(sql, [cleaned_word, interaction.guild.id, member.id])

        # TODO: show graph (maybe...)

        result = cur.fetchone()

        if result == None:
            em.description = f"**{member.display_name}** has never mention **{cleaned_word}** before"
        else:
            count = result[0]

            em.description = f"**{member.display_name}** has mention **{cleaned_word}** **{count} {"time" if count == 1 else "times"}**"

        await interaction.edit_original_response(embed=em)

    @discord.app_commands.command(name="wordtop")
    async def wordtop(self, interaction : discord.Interaction, word : str):
        cleaned_word = self.clean_message_content(word)

        em = discord.Embed(title="", description=f"searching **{cleaned_word}** mentions...")

        await interaction.response.send_message(embed=em)

        # get top members
        con = database.ConnectionPool.get()
        cur = con.cursor()

        sql = "SELECT discord_guild_id, discord_user_id, SUM(count) as total_count FROM messages_word_count WHERE word = ? AND discord_guild_id = ? GROUP BY discord_guild_id, discord_user_id ORDER BY total_count DESC LIMIT 10;"

        cur.execute(sql, [cleaned_word, interaction.guild.id])

        top_counts = cur.fetchall()

        # create table
        table = ""
        table += f"#  | Member            |   Mentions\n"
        table += f"{"".ljust(35, "-")}\n"

        for i, count in enumerate(top_counts):
            discord_guild_id = count[0]
            discord_user_id  = count[1]
            total_count = count[2]

            author = interaction.guild.get_member(discord_user_id)

            table += f"{str(i+1).zfill(2)} | {str(author.display_name if author else "unknown").ljust(17)} | {str(total_count).zfill(5).rjust(10)}\n"

        em.description = ""
        em.add_field(name=f"Top members that have mention {cleaned_word}", value=f"```{table}```", inline=False)

        await interaction.edit_original_response(embed=em)

    # TODO: n-word commands

async def setup(bot):
    await bot.add_cog(WordCounterCog(bot))