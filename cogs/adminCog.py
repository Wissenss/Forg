from typing import Literal

import discord
import discord.ext
import discord.ext.commands

import constants
import database
from cogs.customCog import CustomCog
import security

class AdminCog(CustomCog):
    def __init__(self, bot):
        super().__init__(bot)

    @discord.app_commands.command(name="elevate")
    async def ping(self, interaction : discord.Interaction, member : discord.Member, level: Literal["admin", "moderator", "member"]):
      em = discord.Embed(title="", description="")

      if not security.account_has_permision(interaction.user.id, interaction.guild.id, constants.Permission.ADMIN_COG_ELEVATE):
        em.description = "You're not allowed to use this!"
        return await interaction.response.send_message(embed=em, ephemeral=True)
       
      level_parsed = constants.AccountAccessLevel.MEMBER

      if level == "admin"     : level_parsed = constants.AccountAccessLevel.ADMIN
      if level == "moderator" : level_parsed = constants.AccountAccessLevel.MODERATOR
      if level == "member"    : level_parsed = constants.AccountAccessLevel.MEMBER

      security.set_account_level(interaction.user.id, interaction.guild.id, level_parsed)

      em.description = f"**{member.display_name}** is now **{level}**"

      return await interaction.response.send_message(embed=em, ephemeral=True)
    
async def setup(bot):
    await bot.add_cog(AdminCog(bot))