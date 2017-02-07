#########################
# league.py
# handles a single league
#########################

# imports
import skills

# utility functions

# constants


class League(object):

    # main League class
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