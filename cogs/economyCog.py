import sqlite3
from typing import Literal
import datetime

import discord
import discord.ext
import discord.ext.commands
from discord.app_commands import Range

import constants
import database
from cogs.customCog import CustomCog
import security

class EconomyCog(CustomCog):
    def __init__(self, bot):
        super().__init__(bot)

    @classmethod
    def get_account_balance(cls, discord_user_id, discord_guild_id) -> float:
      cur = database.ConnectionPool.get().cursor()

      balance = 0

      sql = """
        SELECT
          SUM(amount) as balance
        FROM 
          transactions
        WHERE
          discord_user_id = ?
          AND discord_guild_id = ?
        GROUP BY 
          discord_user_id, discord_guild_id; 
      """

      cur.execute(sql, [discord_user_id, discord_guild_id])

      fetch = cur.fetchone()

      if fetch:
         balance = fetch[0]

      database.ConnectionPool.release(cur.connection)

      return balance

    @classmethod
    def create_transaction(cls, cursor : sqlite3.Cursor, kind : constants.TransactionKind, discord_user_id : int, discord_guild_id : int, amount : float, related_transaction_id : int = 0, timestamp : datetime.datetime = None):
      if timestamp == None:
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc)

      sql = "INSERT INTO transactions(kind, discord_user_id, discord_guild_id, amount, related_transaction_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)"
      
      cursor.execute(sql, [kind.value, discord_user_id, discord_guild_id, amount, related_transaction_id, timestamp.isoformat()])

    @classmethod
    def create_transaction_autocommit(cls, kind : constants.TransactionKind, discord_user_id : int, discord_guild_id : int, amount : float, related_transaction_id : int = 0, timestamp : datetime.datetime = None):
      cur = database.ConnectionPool.get().cursor()

      cls.create_transaction(cur, kind, discord_user_id, discord_guild_id, amount, related_transaction_id, timestamp)

      cur.connection.commit()

      database.ConnectionPool.release(cur.connection)

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message : discord.Message):

      if message.author.id == self.bot.user.id:
        return

      reward = 0.1

      self.create_transaction_autocommit(constants.TransactionKind.REWARD_MESSAGE, message.author.id, message.guild.id, reward)

    @discord.app_commands.command(name="wallet")
    async def wallet(self, interaction : discord.Interaction, private : bool = True):
      
      em = discord.Embed(title="Your wallet", description="")

      balance = self.get_account_balance(interaction.user.id, interaction.guild.id)

      # em.description += f"\nowner: {interaction.user.display_name}"
      em.description += f"\nbalance: ${balance:.2f}"

      # TODO: show latest income (maybe...)
      # TODO: show first transaction date (maybe...)

      return await interaction.response.send_message(embed=em, ephemeral=private)
    
    @discord.app_commands.command(name="transfer")
    async def transfer(self, interaction : discord.Interaction, member : discord.Member, amount: Range[float, 0]):
      cur = database.ConnectionPool.get().cursor()

      em = discord.Embed(title="", description="")

      try:
        if amount == 0:
          em.description = f"Amount must be grater than 0."
          return await interaction.response.send_message(embed=em, ephemeral=True)

        # check there is enough income on origin account
        balance = self.get_account_balance(interaction.user.id, interaction.guild.id)

        if balance < amount:
          em.description = f"Not enough founds on your wallet. Current balance: **${balance:.2f}**"
          return await interaction.response.send_message(embed=em, ephemeral=True)

        # transfer the actual funds
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        self.create_transaction(cur, constants.TransactionKind.TRANSFER_OUTCOME, interaction.user.id, interaction.guild.id, amount * -1, 0, now)

        related_id = cur.execute("SELECT last_inserted_rowid()").fetchone()[0]

        self.create_transaction(cur, constants.TransactionKind.TRANSFER_INCOME, member.id, interaction.guild.id, amount, related_id, now)

        cur.connection.commit()

        em.description = f"${amount:.2f} transfer from **{interaction.user.display_name}** to **{member.display_name}**"
        return await interaction.response.send_message(embed=em)
      
      except:
        if cur.connection.in_transaction:
           cur.connection.rollback()
      finally:
         database.ConnectionPool.release(cur.connection)

    #@discord.app_commands.command(name="shop")
    async def shop(self, interaction : discord.Interaction):
       
       # TODO: shop command

       return

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))