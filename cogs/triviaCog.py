from typing import Literal
import random

import discord
import discord.ext
import discord.ext.commands

import requests

import constants
import database
from cogs.customCog import CustomCog
import security

class TriviaView(discord.ui.View):
  def __init__(self, options: list[str], correct_answer: str, original_embed : discord.Embed):
    super().__init__(timeout=180)

    self.response : discord.InteractionCallbackResponse = None
    self.correct_answer = correct_answer
    self.original_embed = original_embed

    for o in options:
        self.add_item(TriviaButton(o, self.correct_answer, original_embed))

  async def on_timeout(self):
    self.original_embed.description += "\n\n ⏱️ Time runed out."

    await self.response.resource.edit(view=self, embed=self.original_embed)

class TriviaButton(discord.ui.Button):
  def __init__(self, option: str, correct_answer: str, original_embed : discord.Embed):
    super().__init__(label=option, style=discord.ButtonStyle.secondary)

    self.option = option
    self.correct_answer = correct_answer
    self.embed = original_embed

  async def callback(self, interaction: discord.Interaction):
    # TODO: check the responder is the same as the creator
    
    if self.option == self.correct_answer:
      self.embed.description += f"\n\n ✅ Correct. **{interaction.user.display_name}** choosed **{self.option}**."
    else:
      self.embed.description += f"\n\n ❌ Incorrect. **{interaction.user.display_name}** choosed **{self.option}**."

    self.view.stop()

    await interaction.response.edit_message(view=self.view, embed=self.embed)     

class TriviaCog(CustomCog):
    def __init__(self, bot):
        super().__init__(bot)

    def decode_html_char_codes_in_str(self, encoded_str : str) -> str:
      decoded_str = encoded_str

      # '
      decoded_str = decoded_str.replace("&#039;", "'")

      # áéíóú
      decoded_str = decoded_str.replace("&aacute;", "á")
      decoded_str = decoded_str.replace("&eacute;", "é")
      decoded_str = decoded_str.replace("&iacute;", "í")
      decoded_str = decoded_str.replace("&oacute;", "ó")
      decoded_str = decoded_str.replace("&uacute;", "ú")

      # &
      decoded_str = decoded_str.replace("&amp;", "&")

      return decoded_str

    @discord.app_commands.command(name="trivia")
    async def trivia(self, interaction : discord.Interaction, 
      difficulty: Literal[
        constants.OpenTDBDifficulty.Any.display, # type: ignore
        constants.OpenTDBDifficulty.Easy.display, # type: ignore
        constants.OpenTDBDifficulty.Medium.display, # type: ignore
        constants.OpenTDBDifficulty.Hard.display # type: ignore
      ] = constants.OpenTDBDifficulty.Any.display, 

      category: Literal[
        constants.OpenTDBCategory.Any.display, # type: ignore
        constants.OpenTDBCategory.GeneralKnowledge.display, # type: ignore
        constants.OpenTDBCategory.History.display, # type: ignore
        constants.OpenTDBCategory.EntertainmentBooks.display, # type: ignore
        constants.OpenTDBCategory.EntertainmentVideoGames.display, # type: ignore
        constants.OpenTDBCategory.EntertainmentFilm.display, # type: ignore
        constants.OpenTDBCategory.EntertainmentJapaneseAnimeAndManga.display, # type: ignore
        constants.OpenTDBCategory.EntertainmentMusic.display, # type: ignore
        constants.OpenTDBCategory.ScienceMathematics.display # type: ignore
      ] = constants.OpenTDBCategory.Any.display               
    ):
      
      response = requests.get("https://opentdb.com/api.php", params={
          "amount" : 1,
          "category" : constants.OpenTDBCategory.from_str(category).id,
          "difficulty": str(difficulty).lower()
      })

      if response.status_code != 200:
        return
      
      data = response.json()

      _difficulty        = data["results"][0]["difficulty"]
      _type              = data["results"][0]["type"]
      _category          = data["results"][0]["category"]
      _question          = data["results"][0]["question"]
      _correct_answer    = data["results"][0]["correct_answer"]
      _incorrect_answers = data["results"][0]["incorrect_answers"]

      # cleanup incoming html encoded characters

      _question = self.decode_html_char_codes_in_str(_question)
      _category = self.decode_html_char_codes_in_str(_category)
      _correct_answer = self.decode_html_char_codes_in_str(_correct_answer)
      _incorrect_answers = [self.decode_html_char_codes_in_str(answer) for answer in _incorrect_answers]
      
      #

      em = discord.Embed()
      em.description = _question
      em.set_footer(text=f"{_category} - {_difficulty}")

      _options : list[str] = _incorrect_answers
      _options.append(_correct_answer)
      
      random.shuffle(_options)

      vi = TriviaView(options=_options, correct_answer=_correct_answer, original_embed=em)
      vi.response = await interaction.response.send_message(view=vi, embed=em)

async def setup(bot):
    await bot.add_cog(TriviaCog(bot))