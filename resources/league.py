#########################
# league.py
# handles a single league
#########################

# imports
import skills
from resources.command_parser import CommandParser

# main League class
class League(object):

    ## takes a games Table,
    ## a teams Table,
    ## and a constants dictionary
    def __init__(self, games, teams, constants):
        self.games = games
        self.teams = teams
        self.constants = constants
        self.team_size = self.constants.get("TEAM_SIZE", 1)
        self.game_size = self.constants.get("GAME_SIZE", 2)
        self.rating_system = self.constants.get("SYSTEM", "ELO")
        self.threadID = self._getThreadID(self.constants.get("THREAD"))
        self.offset = int(self.constants.get("OFFSET"))

    ## _getThreadID
    ### retrieves thread ID from URL
    @staticmethod
    def _getThreadID(threadURL):
        baseURL = "https://www.warlight.net/Forum/"
        threadURL = threadURL.replace("?", "")
        if baseURL not in threadURL:
            return int(threadURL)
        return int(threadURL[(threadURL.find(baseURL)+len(baseURL)):])

    ## _getCommands
    ### retrieves commands from thread
    def _getCommands(self):
        thread = CommandParser(self.threadID)
        return thread._getCommands(self.offset)