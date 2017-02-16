#########################
# league.py
# handles a single league
#########################

# imports
import skills

# main League class
class League(object):

    ## takes a games Table,
    ## a teams Table,
    ## and a commands dictionary
    def __init__(self, games, teams, commands, orders):
        self.games = games
        self.teams = teams
        self.commands = commands
        self.orders = orders
        self.team_size = self.commands.get("TEAM_SIZE", 1)
        self.game_size = self.commands.get("GAME_SIZE", 2)
        self.rating_system = self.commands.get("SYSTEM", "ELO")