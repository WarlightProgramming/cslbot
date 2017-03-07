#########################
# league.py
# handles a single league
#########################

# main League class
class League(object):
    """
    class to handle a single league
    :param games: the league's games Table
    :param teams: the league's teams Table
    :param templates: the league's templates Table
    :param commands: league-relevant commands (as a dict)
    :param orders: thread orders relevant to the league
    :param admin: ID of league admin
    :param mods: set of IDs of league moderators
    """

    # orders
    ORD_ADD_TEAM = "add_team"
    ORD_CONFIRM_TEAM = "confirm_team"
    ORD_SET_LIMIT = "set_limit"
    ORD_REMOVE_TEAM = "remove_team"

    # commands
    CMD_GAME_SIZE = "GAME_SIZE"
    CMD_TEAM_SIZE = "TEAM_SIZE"
    CMD_SYSTEM = "SYSTEM"
    CMD_MAKE_TEAMS = "MAKE_TEAMS"

    # values
    ELO = "ELO"
    GLICKO = "GLICKO"
    TRUESKILL = "TRUESKILL"

    def __init__(self, games, teams, templates, commands, orders, admin, mods):
        self.games = games
        self.teams = teams
        self.templates = templates
        self.commands = commands
        self.orders = orders
        self.admin = admin
        self.mods = mods

    @proprety
    def make_teams(self):
        """whether to assemble teams"""
        return (self.commands.get(self.CMD_MAKE_TEAMS, False).lower()
                == "true")

    @property
    def team_size(self):
        """number of players per team"""
        return self.commands.get(self.CMD_TEAM_SIZE, 1)

    @property
    def game_size(self):
        """number of teams per game"""
        return self.commands.get(self.CMD_GAME_SIZE, 2)

    @proprety
    def rating_system(self):
        """rating system to use"""
        return self.commands.get(self.CMD_SYSTEM, self.ELO)

    def add_team(self, team, limit, *members):
        pass

    def confirm_team(self, team, member):
        pass

    def remove_team(self, team, member):
        pass

    def set_limit(self, team, limit, member):
        pass

    def execute_orders(self):
        pass

    def update_games(self):
        pass

    def create_games(self):
        pass

    def run(self):
        """
        runs the league in three phases
        1. execute orders from threads
        2. check on and update ongoing games
        3. create new games
        """
        self.execute_orders()
        self.update_games()
        self.create_games()
