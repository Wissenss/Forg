from enum import Enum
import datetime
from typing import Optional

DISCORD_EPOCH = datetime.datetime(2015, 1, 1, 0, 0, 0, 0, tzinfo=datetime.timezone.utc) # the time discord was born

class AccountAccessLevel(Enum):
    DEVELOPER = 0
    ADMIN = 10
    MODERATOR = 20
    MEMBER = 30

class Permission(Enum):
    # permissions for the dev cog
    DEV_COG = 1000

    # permissions for the admin cog
    ADMIN_COG = 2000
    ADMIN_COG_ELEVATE = ADMIN_COG + 1

    # permissions for the word count cog
    WORD_COUNT_COG = 3000
    WORD_COUNT_COG_SCAN = WORD_COUNT_COG + 1 

    # permissions for the economy cog
    ECONOMY_COG = 4000 

class OpenTDBCategory(Enum):
    Any = (0, "Any")
    GeneralKnowledge = (9, "General Knowledge")
    EntertainmentBooks = (10, "Entertainment: Books")
    EntertainmentFilm = (11, "Entertainment: Film")
    EntertainmentMusic = (12, "Entertainment: Music")
    EntertainmentMusicalsAndTheaters = (13, "Entertainment: Musicals & Theaters")
    EntertainmentTelevision = (14, "Entertainment: Television")
    EntertainmentVideoGames = (15, "Entertainment: Video Games")
    EntertainmentBoardGames = (16, "Entertainment: Board Games")
    ScienceAndNature = (17, "Science & Nature")
    ScienceComputers = (18, "Science: Computers")
    ScienceMathematics = (19, "Science: Mathematics")
    Mythology = (20, "Mythology")
    Sports = (21, "Sports")
    Geography = (22, "Geography")
    History = (23, "History")
    Politics = (24, "Politics")
    Art = (25, "Art")
    Celebrities = (26, "Celebrities")
    Animals = (27, "Animals")
    Vehicles = (28, "Vehicles")
    EntertainmentComics = (29, "Entertainment: Comics")
    ScienceGadgets = (30, "Science: Gadgets")
    EntertainmentJapaneseAnimeAndManga = (31, "Entertainment: Japanese Anime & Manga")
    EntertainmentCartoonAndAnimations = (32, "Entertainment: Cartoon & Animations")

    def __init__(self, id: int, display: str):
        self.id : int = id
        self.display : str = display

    @classmethod
    def from_str(cls, display_value : str) -> Optional["OpenTDBCategory"]:
        for category in OpenTDBCategory:
            if category.display == display_value:
                return category
            
        return None
    
    @classmethod
    def from_int(cls, id_value : int) -> Optional["OpenTDBCategory"]:
        for category in OpenTDBCategory:
            if category.id == id_value:
                return category
            
        return None
    
class OpenTDBDifficulty(Enum):
    Any = (0, "Any")
    Easy = (1, "Easy")
    Medium = (2, "Medium")
    Hard = (3, "Hard")

    def __init__(self, id: int, display: str):
        self.id : int = id
        self.display : str = display

    @classmethod
    def from_str(cls, display_value : str) -> Optional["OpenTDBDifficulty"]:
        for difficulty in OpenTDBDifficulty:
            if difficulty.display == display_value:
                return difficulty
            
        return None
    
    @classmethod
    def from_int(cls, id_value : int) -> Optional["OpenTDBDifficulty"]:
        for difficulty in OpenTDBDifficulty:
            if difficulty.id == id_value:
                return difficulty
            
        return None