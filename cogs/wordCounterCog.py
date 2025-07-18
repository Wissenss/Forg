import datetime
import re

import discord
import discord.ext
import discord.ext.commands

import database
import security
from models.account import *

from cogs.customCog import CustomCog

class WordCounterCog(CustomCog):
    def __init__(self, bot):
        super().__init__(bot)

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

    def is_message_saved(discord_message_id):
        con = database.ConnectionPool.get()
        cur = con.cursor()

        message_found = False

        if cur.fetchone("SELECT * FROM messages WHERE discord_message_id = ?", [discord_message_id]):
            message_found = True
        
        database.ConnectionPool.release(con)
        
        return message_found

    def process_message(self, message : discord.Message):
        self.save_message(message)
        self.save_message_word_count(message)

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message : discord.Message):

        if message.author == message.guild.me:
            return

        self.process_message(message)

    @discord.app_commands.command(name="wordscan")
    async def wordscan(self, interaction : discord.Interaction):
        
        em = discord.Embed(title="", description="")

        # TODO: check caller has permissions for this command
        if not security.account_has_permision(interaction.user.id, interaction.guild.id, constants.Permission.WORD_COUNT_COG_SCAN):
            em.description = "invalid action for your user"
            return await interaction.response.send_message(embed=em)

        scan_logs = []
        scan_logs_update_interval = 14

        scan_logs.append("starting message scan...")
        em.description = "\n".join(scan_logs)
        response = await interaction.response.send_message(embed=em)

        scan_logs.append("fetching channels...")
        em.description = "\n".join(scan_logs)
        await interaction.response.edit_message(embed=em)

        guild_channels = await interaction.guild.fetch_channels()

        scan_logs.append(f"{len(guild_channels)} found")
        em.description = "\n".join(scan_logs)
        await interaction.response.edit_message(embed=em)

        for channel in await guild_channels:
            
            scan_logs.append(f"processing channel \"{channel.name}\"... 0 / {channel.message_count}")
            em.description = "\n".join(scan_logs)
            await interaction.response.edit_message(embed=em)
            
            # TODO: check the bot has permissions for this channel
            
            progress = 0

            for message in await channel.fetch_messages():
                
                if not self.is_message_saved(message):
                    self.process_message(message)

                progress += 1

                if progress % scan_logs_update_interval or progress == channel.message_count:
                    scan_logs[-1] = f"processing channel \"{channel.name}\"... {progress} / {channel.message_count}"
                    em.description = "\n".join(scan_logs)
                    await interaction.response.edit_message(embed=em)

        scan_logs.append("finished!")
        em.description = "\n".join(scan_logs)
        await interaction.response.edit_message(embed=em)

    # normal word commands

    @discord.app_commands.command(name="wordquote")
    async def wordquote(self, interaction : discord.Interaction, word : str, member : discord.User):
        em = discord.Embed(title="", description=f"searching **{word}** mentions...")

        await interaction.response.send_message(embed=em)
        
        con = database.ConnectionPool.get()
        cur = con.cursor()

        sql = """
        SELECT * 
        FROM messages 
        WHERE deleted = False AND discord_user_id = ? AND discord_guild_id = ? AND content_clean LIKE ? 
        ORDER BY RANDOM()
        LIMIT 1
        """

        result = cur.execute(sql, [member.id, interaction.guild.id, f"%{word}%"])
        message = result.fetchone()

        database.ConnectionPool.release(con)

        if not message:
            em.description = f"no mention of **{word}** found for the given user"
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

            return await interaction.edit_original_response(embed=em) 
        
        except discord.NotFound:
            
            # if the message is not found we mark it as deleted so it wont be shown again

            con = database.ConnectionPool.get()
            cur = con.cursor()

            cur.execute("UPDATE messages SET deleted = True WHERE discord_message_id = ?;", [message[0]])

            database.ConnectionPool.release(con)

            em.description = "message deleted"

            return await interaction.edit_original_response(embed=em)

    @discord.app_commands.command(name="wordcount")
    async def wordcount(self, interaction : discord.Interaction, word : str, member : discord.User):
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

        cur.execute(sql, [cleaned_word, interaction.guild.id, interaction.user.id])

        # TODO: show graph (maybe...)

        result = cur.fetchone()

        if result == None:
            em.description = f"**{interaction.user.display_name}** has never mention **{cleaned_word}** before"
        else:
            count = result[0]

            em.description = f"**{interaction.user.display_name}** has mention **{cleaned_word}** **{count} {"time" if count == 1 else "times"}**"

        await interaction.edit_original_response(embed=em)

    @discord.app_commands.command(name="wordtop")
    async def wordtop(self, interaction : discord.Interaction, word : str):
        em = discord.Embed(title="", description=f"searching \"{word}\" mentions...")

        await interaction.response.send_message(embed=em)

        con = database.ConnectionPool.get()
        cur = con.cursor()

        sql = "SELECT TOP 10 discord_guild_id, discord_user_id, SUM(count) as total_count FROM messages_word_count WHERE word = ? AND discord_guild_id = ? GROUP BY discord_guild_id, discord_user_id ORDER BY total_count;"

        top_counts = cur.fetchall(sql, [word, interaction.guild.id])

        em.description = ""
        em.description += f"\n*Top members that have mention \"{word}\" before*"
        em.description += f"\n# \tmentions \tmember"

        for i, count in enumerate(top_counts):

            author = interaction.guild.get_member(count[1])

            em.description += f"\n{i}\t{count[2]}\t{author.display_name if author else "unknown"}"

    # TODO: n-word commands

async def setup(bot):
    await bot.add_cog(WordCounterCog(bot))