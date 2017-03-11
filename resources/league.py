#########################
# league.py
# handles a single league
#########################

# imports
import copy
import json
from wl_parsers import PlayerParser
from wl_api import APIHandler
from constants import API_CREDS

# errors
class ImproperLeague(Exception):
    """raised for improperly formatted leagues"""
    pass

class ImproperOrder(Exception):
    """raised for improperly formatted orders"""
    pass

# main League class
class League(object):
    """
    class to handle a single league
    :param games: the league's games Table
    :param teams: the league's teams Table
    :param templates: the league's templates Table
    :param settings: league-relevant settings (as a dict)
    :param orders: thread orders relevant to the league
    :param admin: ID of league admin
    :param mods: set of IDs of league moderators
    :param parent: parent LeagueManager object
    :param name: name of this league
    """

    # orders
    ORD_ADD_TEAM = "add_team"
    ORD_CONFIRM_TEAM = "confirm_team"
    ORD_SET_LIMIT = "set_limit"
    ORD_REMOVE_TEAM = "remove_team"

    # settings
    SET_GAME_SIZE = "GAME_SIZE"
    SET_TEAM_SIZE = "TEAM_SIZE"
    SET_SYSTEM = "SYSTEM"
    SET_MAKE_TEAMS = "MAKE_TEAMS"
    SET_BANNED_PLAYERS = "BANNED_PLAYERS"
    SET_BANNED_CLANS = "BANNED_CLANS"
    SET_ALLOWED_PLAYERS = "ALLOWED_PLAYERS"
    SET_ALLOWED_CLANS = "ALLOWED_CLANS"
    SET_MAX_LIMIT = "MAX_LIMIT"
    SET_MIN_LIMIT = "MIN_LIMIT"
    SET_AUTOFORMAT = "AUTOFORMAT"
    SET_CONSTRAIN_LIMIT = "CONSTRAIN_LIMIT"
    SET_RTG_DEFAULT = "DEFAULT_RATING"

    # rating systems
    RATE_ELO = "ELO"
    RATE_GLICKO = "GLICKO"
    RATE_TRUESKILL = "TRUESKILL"

    # keywords
    KW_ALL = "ALL"

    def __init__(self, games, teams, templates, settings, orders,
                 admin, mods, parent, name):
        self.games = games
        self.teams = teams
        self.templates = templates
        self.settings = settings
        self.orders = orders
        self.admin = admin
        self.mods = copy.deepcopy(mods)
        self.mods.add(admin)
        self.parent = parent
        self.name = name
        self.handler = self._makeHandler()
        self.checkFormat()

    def _makeHandler(self):
        credsFile = open("../" + API_CREDS)
        creds = open(credsFile).read()
        email, token = creds['E-mail'], creds['APIToken']
        return APIHandler(email, token)

    @staticmethod
    def checkSheet(table, header, constraints, reformat=True):
        """
        ensures a given table has the appropriate header/constraints
        :param table: Table object to check
        :param header: an iterable containing required header labels
        :param constraints: a dictionary mapping labels to constraints
        :param reformat: a boolean determing whether to add labels if
                         they aren't present (raises error otherwise)
        """
        table_header = table.reverseHeader()
        for label in header:
            if label not in header:
                if reformat:
                    table.expandHeader(label)
                else:
                    error_str = ("Table %s missing %s in header" %
                                 (table.sheet.title, label))
                    raise ImproperLeague(error_str)
            table.updateConstraint(label, constraints.get(label, ""),
                                   erase=True)

    def checkTeamSheet(self):
        teamConstraints = {'ID': 'UNIQUE INT',
                           'Name': 'UNIQUE ALPHANUMERIC',
                           'Players': 'STRING',
                           'Confirmations': 'STRING',
                           'Rating': 'STRING',
                           'Limit': 'INT'}
        self.checkSheet(self.teams, set(teamConstraints), teamConstraints,
                        self.autoformat)

    def checkGamesSheet(self):
        gamesConstraints = {'ID': 'UNIQUE INT',
                            'Teams': 'STRING',
                            'Ratings': 'STRING',
                            'Winner': 'INT',
                            'Template': 'INT'}
        self.checkSheet(self.games, set(gamesConstraints, gamesConstraints,
                        self.autoformat)

    def checkTemplatesSheet(self):
        templatesConstraints = {'ID': 'UNIQUE INT',
                                'Name': 'UNIQUE STRING',
                                'Active': 'BOOL',
                                'Games': 'INT'}
        self.checkSheet(self.templates, set(templatesConstraints),
                        templatesConstraints, self.autoformat)

    def checkFormat(self):
        self.checkTeamSheet()
        self.checkGamesSheet()
        self.checkTemplatesSheet()

    def getBoolProperty(self, label, default=True):
        return (self.commands.get(label, default).lower() == 'true')

    @property
    def autoformat(self):
        """whether to automatically format sheets"""
        return self.getBoolProperty(self.SET_AUTOFORMAT, True)

    @property
    def makeTeams(self):
        """whether to assemble teams"""
        return self.getBoolProperty(self.SET_MAKE_TEAMS, False)

    @property
    def teamSize(self):
        """number of players per team"""
        return self.commands.get(self.SET_TEAM_SIZE, 1)

    @property
    def gameSize(self):
        """number of teams per game"""
        return self.commands.get(self.SET_GAME_SIZE, 2)

    @property
    def minLimit(self):
        """minimum number of max ongoing games per team"""
        return int(self.commands.get(self.SET_MIN_LIMIT, 0))

    @property
    def maxLimit(self):
        """maximum number of max ongoing games per team"""
        lim = self.commands.get(self.SET_MAX_LIMIT, None)
        if lim is not None:
            return int(lim)
        return None

    @property
    def constrainLimit(self):
        """whether to constrain out-of-range limits"""
        return self.getBoolProperty(self.SET_CONSTRAIN_LIMIT, True)

    def limitInRange(self, limit):
        """returns True if a limit is in an acceptable range"""
        return (limit >= self.minLimit and
                (self.maxLimit is None or limit <= self.maxLimit))

    @property
    def ratingSystem(self):
        """rating system to use"""
        return self.commands.get(self.SET_SYSTEM, self.RATE_ELO)

    def getIDGroup(self, label):
        groupList = self.commands.get(label, "").split(",")
        return set([int(x) for x in groupList])

    @property
    def bannedPlayers(self):
        """set containing IDs of banned players"""
        return self.getIDGroup(self.SET_BANNED_PLAYERS)

    @property
    def bannedClans(self):
        """set containing IDs of banned clans"""
        return self.getIDGroup(self.SET_BANNED_CLANS)

    @property
    def allowedPlayers(self):
        """set containing IDs of allowed players"""
        return self.getIDGroup(self.SET_ALLOWED_PLAYERS)

    @property
    def allowedClans(self)
        """set containing IDs of allowed clans"""
        return self.getIDGroup(self.SET_ALLOWED_CLANS)

    def allowed(self, playerID):
        """returns True if a player is allowed to join the league"""
        checkClans = (len(self.bannedClans) > 0)
        if checkClans:
            parser = PlayerParser(playerID)
            clan = int(parser.clanID)
            if (clan in self.bannedClans or
                self.KW_ALL in self.bannedClans and
                clan not in self.allowedClans):
                return False
        return (player in self.allowedPlayers or
                player not in self.bannedPlayers and
                self.KW_ALL not in self.bannedPlayers)

    def banned(self, playerID):
        """returns True if a player is banned from the league"""
        return not(self.allowed(playerID))

    def logFailedOrder(self, order):
        desc = ("Failed to process %s order by %d for league %s" %
                (order['type'], order['author'], order['orders'][0]))
        self.parent.log(desc, league=self.name, error=True)

    def checkTeamCreator(self, creator, members):
        if (creator not in members and
            creator not in self.mods):
            raise ImproperOrder(str(creator) + " isn't able to" +
                                " add a team that excludes them")

    def hasTemplateAccess(self, playerID):
        """returns True if a player can play on all templates"""
        tempResults = self.handler.validateToken(int(playerID),
                                                 *self.templateIDs)
        for temp in self.templateIDs:
            tempName = "template" + str(temp)
            if tempResults[tempName]['result'] != 'CannotUseTemplate':
                return False
        return True

    def checkTeam(self, members):
        for member in members:
            if self.banned(member):
                raise ImproperOrder(str(member) +
                                    " is banned from this league")
            elif not self.hasTemplateAccess(member):
                raise ImproperOrder(str(member) +
                                    " cannot access all templates")

    def checkLimit(self, limit):
        if not self.limitInRange(limit):
            if self.constrainLimit:
                if limit < self.minLimit: return self.minLimit
                return self.maxLimit
            else: raise ImproperOrder()
        return limit

    def setCurrentID(self):
        existingIDs = self.templates.findValue(dict(), 'ID')
        if len(existingIDs) == 0:
            self.currentID = 0
        else:
            self.currentID = max(existingIDs) + 1

    @property
    def defaultRating(self):
        defRtg = self.settings.get(self.SET_RTG_DEFAULT, None)
        if defRtg is None:
            return {self.RATE_ELO: "1500",
                    self.RATE_GLICKO: "1500.350",
                    self.RATE_TRUESKILL: "1500.500"}[self.ratingSystem]
        else: return defRtg

    def addTeam(self, order):
        teamName = order['order'][1]
        gameLimit = int(order['order'][2])
        members = [int(member) for member in order['order'][3:]]
        author = int(order['author'])
        self.checkTeamCreator(author, members)
        self.checkTeam(members)
        gameLimit = self.checkLimit(gameLimit)
        members.sort()
        confirms = [(m == author) for m in members]
        members = ",".join([str(m) for m in members])
        confirms = ",".join([str(c).upper() for c in confirms])
        self.teams.addEntity({'ID': self.currentID,
                              'Name': teamName,
                              'Limit': gameLimit,
                              'Players': members,
                              'Confirmations': confirms,
                              'Rating': self.defaultRating})
        self.currentID += 1

    def fetchMatchingTeam(self, order, checkAuthor=True,
                          allowMod=True):
        name = order['order'][1]
        author = int(order['author'])
        matchingTeam = self.teams.findEntities({'Name': name})
        if len(matchingTeam) < 1:
            raise ImproperOrder("Nonexistent team: " + str(name))
        matchingTeam = matchingTeam[0]
        index = None
        if (checkAuthor and (author not in self.mods or not allowMod)
            and str(author) not in
            matchingTeam['Players'].split(",")):
            raise ImproperOrder(str(author) + " not in " +
                                str(name))
            try:
                index = matchingTeam['Players'].split(",").index(author)
            except ValueError: pass
        return matchingTeam, index

    def confirmTeam(self, order):
        try:
            matchingTeam, index = self.fetchMatchingTeam(order, True,
                                                         False)
        except:
            raise ImproperOrder(str(order['author']) + " not in " +
                                str(order['order'][1]))
        confirms = matchingTeam['Confirmations'].split(",")
        confirms[index] = "TRUE"
        confirms = ",".join([str(c).upper() for c in confirms])
        self.teams.updateMatchingEntities({'Name': teamName},
                                          {'Confirmations': confirms})

    def removeTeam(self, order):
        matchingTeam = self.fetchMatchingTeam(order)[0]
        self.teams.removeMatchingEntities({'ID':
                                           matchingTeam['ID']})

    def setLimit(self, order):
        matchingTeam = self.fetchMatchingTeam(order, False)[0]
        players = matchingTeam['Players'].split(",")
        if (str(order['author']) not in players and
            order['author'] not in self.mods):
            raise ImproperOrder(str(order['author']) +
                                " can't set the limit for team " +
                                str(order['order'][1]))
        self.teams.updateMatchingEntities({'ID':
                                           matchingTeam['ID']},
                                          {'Limit':
                                           order['order'][2]})

    @proprety
    def templateIDs(self):
        return self.templates.findValue(dict(), "ID")

    def executeOrders(self):
        self.setCurrentID()
        for order in self.orders:
            orderType = order['type']
            try:
                {self.ORD_ADD_TEAM: self.addTeam,
                 self.ORD_CONFIRM_TEAM: self.confirmTeam,
                 self.ORD_SET_LIMIT: self.setLimit,
                 self.ORD_REMOVE_TEAM: self.removeTeam
                }[orderType](order)
            except Exception as e:
                if len(str(e)) > 0:
                    self.parent.log(str(e), error=True)
                else:
                    self.logFailedOrder(order)

    def updateGames(self):
        pass

    def createGames(self):
        pass

    def run(self):
        """
        runs the league in three phases
        1. execute orders from threads
        2. check on and update ongoing games
        3. create new games
        """
        self.executeOrders()
        self.updateGames()
        self.createGames()
