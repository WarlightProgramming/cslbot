#########################
# league.py
# handles a single league
#########################

# imports
import copy
import json
import mpmath
from elo import Rating, Elo
from glicko2.glicko2 import Player
from trueskill import TrueSkill
from datetime import datetime
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

class NonexistentItem(Exception):
    """raises for nonexistent games"""
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
    SET_TEAMS_PER_SIDE = "TEAMS_PER_SIDE"
    SET_SYSTEM = "SYSTEM"
    SET_BANNED_PLAYERS = "BANNED_PLAYERS"
    SET_BANNED_CLANS = "BANNED_CLANS"
    SET_ALLOWED_PLAYERS = "ALLOWED_PLAYERS"
    SET_ALLOWED_CLANS = "ALLOWED_CLANS"
    SET_MAX_LIMIT = "MAX_LIMIT"
    SET_MIN_LIMIT = "MIN_LIMIT"
    SET_AUTOFORMAT = "AUTOFORMAT"
    SET_CONSTRAIN_LIMIT = "CONSTRAIN_LIMIT"
    SET_EXP_THRESH = "EXPIRY_THRESHOLD"
    SET_VETO_LIMIT = "VETO_LIMIT"
    SET_VETO_PENALTY = "VETO_PENALTY"
    SET_ELO_K = "ELO_K"
    SET_ELO_DEFAULT = "ELO_DEFAULT"
    SET_GLICKO_RD = "GLICKO_RD"
    SET_GLICKO_DEFAULT = "GLICKO_DEFAULT"
    SET_TRUESKILL_SIGMA = "TRUESKILL_SIGMA"
    SET_TRUESKILL_DEFAULT = "TRUESKILL_MU"

    # rating systems
    RATE_ELO = "ELO"
    RATE_GLICKO = "GLICKO"
    RATE_TRUESKILL = "TRUESKILL"

    # timeformat
    TIMEFORMAT = "%Y-%m-%d %H:%M:%S"

    # keywords
    KW_ALL = "ALL"

    # separators
    SEP_CMD = ","
    SEP_PLYR = ","
    SEP_CONF = ","
    SEP_TEAMS = ","
    SEP_SIDES = "/"
    SEP_RTG = "."
    SEP_TEMP = ","

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
        creds = json.load(credsFile)
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
                           'Limit': 'INT',
                           'Count': 'INT'}
        self.checkSheet(self.teams, set(teamConstraints), teamConstraints,
                        self.autoformat)

    def checkGamesSheet(self):
        gamesConstraints = {'ID': 'UNIQUE INT',
                            'WarlightID': 'UNIQUE INT',
                            'Created': 'STRING',
                            'Sides': 'STRING',
                            'Ratings': 'STRING',
                            'Winners': 'STRING',
                            'Vetos': 'INT',
                            'Vetoed': 'STRING',
                            'Template': 'INT'}
        self.checkSheet(self.games, set(gamesConstraints, gamesConstraints,
                        self.autoformat)

    def checkTemplatesSheet(self):
        templatesConstraints = {'ID': 'UNIQUE INT',
                                'Name': 'UNIQUE STRING',
                                'WarlightID': 'INT',
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
    def vetoLimit(self):
        """maximum number of vetos per game"""
        return int(self.commands.get(self.SET_VETO_LIMIT, 1))

    @property
    def vetoPenalty(self):
        """points deduction for excessive vetos"""
        return int(self.commands.get(self.SET_VETO_PENALTY, 25))

    @property
    def teamSize(self):
        """number of players per team"""
        return int(self.commands.get(self.SET_TEAM_SIZE, 1))

    @property
    def gameSize(self):
        """number of sides per game"""
        return int(self.commands.get(self.SET_GAME_SIZE, 2))

    @property
    def teamsPerSide(self):
        """number of teams per side"""
        return int(self.commands.get(self.SET_TEAMS_PER_SIDE, 1))

    @property
    def expiryThreshold(self):
        """number of days until game is declared abandoned"""
        return int(self.commands.get(self.SET_EXP_THRESH, 3))

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

    @property
    def kFactor(self):
        return int(self.commands.get(self.SET_ELO_K, 32)) * self.teamsPerSide

    @property
    def defaultElo(self):
        return self.commands.get(self.SET_ELO_DEFAULT, 1500)

    @property
    def eloEnv(self):
        return Elo(initial=self.defaultElo, k_factor=self.kFactor)

    @property
    def glickoRd(self):
        return self.commands.get(self.SET_GLICKO_RD, 350)

    @property
    def glickoRating(self):
        return self.commands.get(self.SET_GLICKO_DEFAULT, 1500)

    @property
    def defaultGlicko(self):
        return str(self.glickoRating) + "." + str(self.glickoRd)

    @property
    def trueSkillSigma(self):
        return self.commands.get(self.SET_TRUESKILL_SIGMA, 500)

    @property
    def trueSkillMu(self):
        return self.commands.get(self.SET_TRUESKILL_DEFAULT, 1500)

    @property
    def trueSkillBeta(self):
        return self.trueSkillSigma / 2.0

    @property
    def trueSkillTau(self):
        return self.trueSkillSigma / 100.0

    @property
    def trueSkillEnv(self):
        return TrueSkill(mu = self.trueSkillMu,
                         sigma = self.trueSkillSigma,
                         beta = self.trueSkillBeta,
                         tau = self.trueSkillTau,
                         draw_probability = 0.0,
                         backend = 'mpmath')

    @property
    def defaultTrueSkill(self):
        return str(self.trueSkillMu) + "." + str(self.trueSkillSigma)

    def getIDGroup(self, label):
        groupList = self.commands.get(label, "").split(self.SEP_CMD)
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
        existingIDs = self.teams.findValue(dict(), 'ID')
        if len(existingIDs) == 0:
            self.currentID = 0
        else:
            self.currentID = max(existingIDs) + 1

    @property
    def defaultRating(self):
        return {self.RATE_ELO: self.defaultElo,
                self.RATE_GLICKO: self.defaultGlicko,
                self.RATE_TRUESKILL, self.defaultTrueSkill}[self.ratingSystem]

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
                              'Count': 0,
                              'Rating': self.defaultRating})
        self.currentID += 1

    def fetchMatchingTeam(self, order, checkAuthor=True,
                          allowMod=True):
        name = order['order'][1]
        author = int(order['author'])
        matchingTeam = self.teams.findEntities({'Name': {'value': name,
                                                         'type': 'positive'}})
        if len(matchingTeam) < 1:
            raise NonexistentItem("Nonexistent team: " + str(name))
        matchingTeam = matchingTeam[0]
        index = None
        if (checkAuthor and (author not in self.mods or not allowMod)
            and str(author) not in
            matchingTeam['Players'].split(self.SEP_PLYR)):
            raise ImproperOrder(str(author) + " not in " +
                                str(name))
            try:
                index = (matchingTeam['Players'].
                         split(self.SEP_PLYR).
                         index(author))
            except ValueError: pass
        return matchingTeam, index

    def confirmTeam(self, order):
        author = int(order['author'])
        if (author in self.mods and len(order['order']) > 2):
            self.confirmAsMod(self, order)
        try:
            matchingTeam, index = self.fetchMatchingTeam(order, True,
                                                         False)
        except:
            raise ImproperOrder(str(order['author']) + " not in " +
                                str(order['order'][1]))
        confirms = matchingTeam['Confirmations'].split(self.SEP_CONF)
        confirms[index] = "TRUE"
        confirms = ",".join([str(c).upper() for c in confirms])
        self.teams.updateMatchingEntities({'Name': teamName},
                                          {'Confirmations': confirms})

    def confirmAsMod(self, order):
        players = order['order'][2:]
        for player in players:
            newOrder = dict()
            newOrder['author'] = player
            newOrder['order'] = order['order'][:2]
            self.confirmTeam(newOrder)

    def removeTeam(self, order):
        matchingTeam = self.fetchMatchingTeam(order)[0]
        self.teams.removeMatchingEntities({'ID':
                                           matchingTeam['ID']})

    def setLimit(self, order):
        matchingTeam = self.fetchMatchingTeam(order, False)[0]
        players = matchingTeam['Players'].split(self.SEP_PLYR)
        if (str(order['author']) not in players and
            order['author'] not in self.mods):
            raise ImproperOrder(str(order['author']) +
                                " can't set the limit for team " +
                                str(order['order'][1]))
        self.teams.updateMatchingEntities({'ID':
                                           {'value': matchingTeam['ID'],
                                            'type': 'positive'}},
                                          {'Limit':
                                           order['order'][2]})

    @property
    def templateIDs(self):
        return self.templates.findValue({'ID': {'value': '',
                                                'type': 'negative'},
                                         'Active': {'value': ['TRUE', True],
                                                    'type': 'positive'}}, "ID")

    @property
    def templateRanks(self):
        tempData = self.templates.findEntities({'ID': {'value': '',
                                                       'type': 'negative'},
                                                'Active': {'values':
                                                           ['TRUE', True],
                                                       'type': 'positive'}})
        tempInfo = [(int(tempData[temp]['ID']), int(tempData[temp]['Games']))
                    for temp in tempData]
        tempInfo.sort(key = lambda x: x[1])

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
                    self.parent.log(str(e), self.name, error=True)
                else:
                    self.logFailedOrder(order)

    @property
    def unfinishedGames(self):
        return self.games.findEntities({'ID': {'value': '',
                                               'type': 'negative'},
                                        'Winner': {'value': '',
                                                   'type': 'positive'}},
                                       keyLabel='WarlightID')

    @staticmethod
    def isAbandoned(players):
        for player in players:
            if player['state'] == 'VotedToEnd':
                return True
            elif player['state'] == 'Won':
                return False
        return False

    @staticmethod
    def findMatchingPlayers(players, *states):
        matching = list()
        for player in players:
            if player['state'] in states:
                matching.append(int(player['id']))
        matching.sort()
        return matching

    def findWinners(self, players):
        return self.findMatchingPlayers(players, 'Won')

    def findDecliners(self, players):
        return self.findMatchingPlayers(players, 'Declined')

    def findWaiting(self, players):
        return self.findMatchingPlayers(players, 'Waiting', 'Declined')

    def handleFinished(self, gameData):
        if self.isAbandoned(gameData['players']):
            return 'ABANDONED', None, None
        else:
            return 'FINISHED', self.findWinners(gameData['players'])

    def handleWaiting(self, gameData, created):
        decliners = self.findDecliners(gameData['players'])
        if len(decliners) > 0:
            return 'DECLINED', decliners
        waiting = self.findWaiting(gameData['players'])
        if (len(waiting) == len(gameData['players']) and
            (datetime.now() - created).days > self.expiryThreshold):
            return 'ABANDONED', None

    def fetchGameStatus(self, gameID, created):
        gameData = self.handler.queryGame(gameID)
        if gameData['state'] == 'Finished':
            return self.handleFinished(gameData)
        elif gameData['state'] == 'WaitingForPlayers':
            return self.handleWaiting(gameData, created)

    def fetchDataByID(self, table, ID, nonexStr=""):
        data = table.findEntities({'ID': {'value': ID,
                                          'type': 'positive'}})
        if len(data) == 0: raise NonexistentItem(nonexStr)
        return data[0]

    def fetchGameData(self, gameID):
        nonexStr = "Nonexistent game: %s" % (str(gameID))
        return self.fetchDataByID(self.games, gameID, nonexStr)

    def fetchTeamData(self, teamID):
        nonexStr = "Nonexistent team: %s" % (str(teamID))
        return self.fetchDataByID(self.teams, teamID, nonexStr)

    def fetchTemplateData(self, templateID):
        nonexStr = "Nonexistent template: %s" % (str(templateID))
        return self.fetchDataByID(self.templates, templateID, nonexStr)

    def findCorrespondingTeams(self, gameID, players):
        players = set([str(player) for player in players])
        results = set()
        gameData = self.games.findEntities({'ID': {'value': gameID,
                                                   'type': 'positive'}})
        gameTeams = gameData[0]['Teams'].split(self.SEP_TEAMS)
        for team in gameTeams:
            teamData = self.teams.findEntities({'ID': {'value': team,
                                                       'type': 'positive'}})
            playerData = set(teamData['Players'].split(self.SEP_PLYR))
            if len(playerData.intersection(players)) > 0:
                results.add(team)
        return results

    def getRatingsDict(self, teams):
        ratings = dict()
        teamData = self.teams.findEntities({'ID': {'values': teams,
                                                   'type': 'positive'}})
        for team in teamData:
            ratings[team['ID']] = team['Rating']
        return ratings

    def setWinners(self, gameID, winTeams):
        winStr = ",".join(sorted(str(team) for team in winTeams))
        self.games.updateMatchingEntities({'ID': {'value': gameID,
                                                  'type': 'positive'}},
                                          {'Winners': winStr})

    def adjustTeamGameCount(self, teamID, adj):
        oldCount = int(self.fetchTeamData(teamID)['Count'])
        self.teams.updateMatchingEntities({'ID': {'value': teamID,
                                                  'type': 'positive'}},
                                          {'Count': str(oldCount + adj)})

    def adjustTemplateGameCount(self, templateID, adj):
        oldCount = int(self.fetchTemplateData(templateID)['Games'])
        self.templates.updateMatchingEntities({'ID': {'value': templateID,
                                                      'type': 'positive'}},
                                              {'Count': str(oldCount + adj)})

    def getEloRatingAfterEvent(self, rating, opponents, event):
        oldRating = rating
        for opp in opponents:
            rating = self.eloEnv.Rate(oldRating, [(event, opp)])
        diff = int(round((rating - oldRating) / len(opponents)))
        return oldRating + diff

    def getNewEloRatings(self, winnersDict, losersDict):
        WIN, LOSS, DRAW = 1, 0, 0.5
        results = dict()
        winners = [winner for winner in winnersDict]
        losers = [loser for loser in losersDict]
        winRating = sum([int(winnersDict[winner]) for winner in winnersDict])
        lossRating = sum([int(losersDict[loser]) for loser in losersDict])
        winRtg = self.getEloRatingAfterEvent(winRating, [lossRating,], WIN)
        lossRtg = self.getEloRatingAfterEvent(lossRating, [winRating,], LOSS)
        winDiff = int(round((winRtg - winRating) / len(winners)))
        lossDiff = int(round((lossRtg - lossRating) / len(losers)))
        for winner in winners:
            results[winner] = str(int(winnersDict[winner]) + winDiff)
        for loser in losers:
            results[loser] = str(int(losersDict[loser]) + lossDiff)
        return results

    @staticmethod
    def getSplitRtg(dataDict, key):
        return [int(v) for v in dataDict[key].split(self.SEP_RTG)]

    @staticmethod
    def unsplitRtg(rating):
        return (self.SEP_RTG).join([str(val) for val in rating])

    def getNewGlickoRatings(self, winnersDict, losersDict):
        WIN, LOSS, DRAW = 1, 0, 0.5
        winners = [winner for winner in winnersDict]
        losers = [loser for loser in losersDict]
        winRating = sum([self.getSplitRtg(winnersDict, winner)[0] for
                         winner in winnersDict])
        winRd = sum([self.getSplitRtg(winnersDict, winner)[1] for
                     winner in winnersDict])
        lossRating = sum([self.getSplitRtg(losersDict, loser)[0] for
                          loser in losersDict])
        lossRd = sum([self.getSplitRtg(losersDict, loser)[1] for
                      loser in losersDict])
        winPlayer = Player(rating=winRating, rd=winRd)
        lossPlayer = Player(rating=lossRating, rd=lossRd)
        winPlayer.update_rating([lossRating], [lossRd], [WIN])
        lossPlayer.update_rating([winRating], [winRd], [LOSS])
        winRtg, winDev = winPlayer.getRating(), winPlayer.getRd()
        lossRtg, lossDev = lossPlayer.getRating(), lossPlayer.getRd()
        winDiff = int(round((winRtg - winRating) / len(winners)))
        wDevDiff = int(round((winDev - winRd) / len(winners)))
        lossDiff = int(round((lossRtg - lossRating) / len(losers)))
        lDevDiff = int(round((lossDev - lossRd) / len(losers)))
        for winner in winners:
            rat, dev = self.getSplitRtg(winnersDict, winner)
            newRat, newDev = rat + winDiff, dev + wDevDiff
            results[winner] = self.unsplitRtg([newRat, newDev])
        for loser in losers:
            rat, dev = self.getSplitRtg(losersDict, loser)
            newRat, newDev = rat + lossDiff, dev + lDevDiff
            results[loser] = self.unsplitRtg([newRat, newDev])
        return results

    def getTrueSkillRating(self, teamID):
        mu, sigma = self.getTeamRating(teamID).split(self.SEP_RTG)
        return self.trueSkillEnv.create_rating(mu, sigma)

    def getNewTrueSkillRatings(self, sides, winningSide):
        results, WIN, LOSS = dict(), 0, 1
        rating_groups = list()
        for side in sides:
            rating_group = dict()
            for team in side:
                rating_group[team] = self.getTrueSkillRating(team)
            rating_groups.append(rating_group)
        ranks = [LOSS,] * len(sides)
        ranks[winningSide] = WIN
        updated = self.trueSkillEnv.rate(rating_groups, ranks=[WIN, LOSS])
        for side in updated:
            for team in side:
                results[team] = side[team]
        return results

    def getNewRatings(self, sides, winningSide):
        return {self.RATE_ELO: self.getNewEloRatings,
                self.RATE_GLICKO: self.getNewGlickoRatings,
                self.RATE_TRUESKILL: self.getNewTrueskillRatings}[
                self.ratingSystem](sides, winningSide)

    def updateTeamRating(self, teamID, rating):
        self.teams.updateMatchingEntities({'ID': {'value': teamID,
                                                  'type': 'positive'}},
                                          {'Rating': rating})

    def updateRatings(self, newRatings):
        for team in newRatings:
            self.updateTeamRating(team, newRatings[team])

    def updateResults(self, winTeams, lossTeams):
        winRatings = self.getRatingsDict(winTeams)
        lossRatings = self.getRatingsDict(lossTeams)
        newRatings = self.getNewRatings(self, winRatings, lossRatings)
        self.updateRatings(newRatings)
        for team in winTeams+lossTeams:
            self.adjustTeamGameCount(team, -1)

    def updateWinners(self, gameID, winners):
        winTeams = self.findCorrespondingTeams(winners)
        lossTeams = self.getGameTeams(teamID) - winTeams
        self.setWinners(gameID, winTeams)
        self.updateResults(winTeams, lossTeams)

    def updateDecline(self, gameID, decliners):
        lossTeams = self.findCorrespondingTeams(decliners)
        winTeams = self.getGameTeams(teamID) - lossTeams
        self.setWinners(gameID, winTeams)
        self.updateResults(winTeams, lossTeams)

    def deleteGame(self, gameID):
        self.games.removeMatchingEntities({'ID': {'value': gameID,
                                                  'type': 'positive'}})

    def getGameTeams(self, gameID):
        gameData = self.fetchGameData(gameID)
        return self(gameData['Teams'].split(self.SEP_TEAMS)

    def getTeamRating(self, team):
        searchDict = {'ID': {'value': team, 'type': 'positive'}}
        if len(searchDict) < 1:
            raise NonexistentItem("Nonexistent team: %s" % (str(team)))
        return self.teams.findEntities(searchDict)[0]['Rating']

    def adjustRating(self, team, adjustment):
        oldRating = self.getTeamRating(team)
        newRating = oldRating.split(self.SEP_RTG)
        newRating[0] = str(int(newRating[0]) + adjustment)
        newRating = ".".join(newRating)
        self.teams.updateMatchingEntities({'ID': {'value': team,
                                                  'type': 'positive'}},
                                          {'Rating': newRating})

    def penalizeVeto(self, gameID):
        teams = self.getGameTeams(gameID)
        for team in teams:
            self.adjustRating(team, -self.vetoPenalty)

    def vetoCurrentTemplate(self, gameData):
        vetos = gameData['Vetoed'] + "," + str(gameData['Template'])
        if vetos[0] == ",": vetos = vetos[1:]
        vetoCount = int(gameData['Vetos']) + 1
        self.games.updateMatchingEntities({'ID': {'value': gameData['ID'],
                                                  'type': 'positive'},
                                          {'Vetoed': vetos,
                                           'Vetos': vetoCount}})
        self.adjustTemplateGameCount(gameData['Template'], -1)

    def setGameTemplate(self, gameID, tempID):
        self.games.updateMatchingEntities({'ID': {'value': gameID,
                                                  'type': 'positive'}},
                                          {'Template': tempID})

    def makeGame(self, gameID):
        pass

    def updateTemplate(self, gameID, gameData):
        vetos = set([int(v) for v in gameData['Vetoed'].split(self.SEP_TEMP)])
        ranks, i = self.templateRanks, 0
        while (i < len(ranks) and ranks[i][0] in vetos): i += 1
        if i < len(ranks):
            newTemp = ranks[i][0]
            self.setGameTemplate(gameID, newTemp)
            self.makeGame(gameID)
        else:
            self.deleteGame(gameID)

    def updateVeto(self, gameID):
        gameData = self.fetchGameData(gameID)
        if int(gameData['Vetoes']) >= self.vetoLimit:
            self.penalizeVeto(gameID)
            self.deleteGame(gameID)
        else:
            self.vetoCurrentTemplate(gameData)
            self.updateTemplate(gameID, gameData)

    def updateGame(self, warlightID, gameID, createdTime):
        created = datetime.strptime(createdTime, self.TIMEFORMAT)
        status = self.fetchGameStatus(warlightID, created)
        {'FINISHED': self.updateWinners(gameID, status[1]),
         'DECLINED': self.updateDecline(gameID, status[1]),
         'ABANDONED': self.updateVeto(gameID)}.get([status[0]])

    def updateGames(self):
        gamesToCheck = self.unfinishedGames
        for game in gamesToCheck:
            try:
                self.updateGame(game, gamesToCheck[game]['ID'],
                                gamesToCheck[game]['Created'])
            except:
                self.parent.log("Failed to update game: " + str(game),
                                league=self.name, error=True)

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
