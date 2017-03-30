#########################
# league.py
# handles a single league
#########################

# imports
import copy
import json
import math
from decimal import Decimal
from pair import group_teams, assign_templates
from elo import Elo
from glicko2.glicko2 import Player
from trueskill import TrueSkill
from datetime import datetime, timedelta
from wl_parsers import PlayerParser
from wl_api import APIHandler
from wl_api.wl_api import APIError
from sheetDB import errors as SheetErrors
from constants import API_CREDS

# decorators

def runPhase(func):
    """
    function decorator to log failures if phase fails
    """
    def func_wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            failStr = ("Phase %s failed due to %s" % (func.__name__, repr(e)))
            self.parent.log(failStr, self.name, True)
    return func_wrapper

# errors
class ImproperLeague(Exception):
    """raised for improperly formatted leagues"""
    pass

class ImproperInput(Exception):
    """raised for improperly formatted orders and commands"""
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
    :param thread: league thread
    """

    # orders
    ORD_ADD_TEAM = "add_team"
    ORD_CONFIRM_TEAM = "confirm_team"
    ORD_UNCONFIRM_TEAM = "unconfirm_team"
    ORD_SET_LIMIT = "set_limit"
    ORD_REMOVE_TEAM = "remove_team"
    ORD_DROP_TEMPLATE = "drop_template"
    ORD_UNDROP_TEMPLATE = "undrop_template"
    ORD_DROP_TEMPLATES = "drop_templates"
    ORD_UNDROP_TEMPLATES = "undrop_templates"
    ORD_ACTIVATE_TEMPLATE = "activate_template"
    ORD_DEACTIVATE_TEMPLATE = "deactivate_template"
    ORD_QUIT_LEAGUE = "quit_league"

    # commands
    SET_MODS = "MODS"
    SET_GAME_SIZE = "GAME SIZE"
    SET_TEAM_SIZE = "TEAM SIZE"
    SET_TEAMS_PER_SIDE = "TEAMS PER SIDE"
    SET_SYSTEM = "RATING SYSTEM"
    SET_BANNED_PLAYERS = "BANNED PLAYERS"
    SET_BANNED_CLANS = "BANNED CLANS"
    SET_BANNED_LOCATIONS = "BANNED LOCATIONS"
    SET_ALLOWED_PLAYERS = "ALLOWED PLAYERS"
    SET_ALLOWED_CLANS = "ALLOWED CLANS"
    SET_ALLOWED_LOCATIONS = "ALLOWED LOCATIONS"
    SET_REQUIRE_CLAN = "REQUIRE CLAN"
    SET_MAX_LIMIT = "MAX LIMIT"
    SET_MIN_LIMIT = "MIN LIMIT"
    SET_AUTOFORMAT = "AUTOFORMAT"
    SET_CONSTRAIN_LIMIT = "CONSTRAIN LIMIT"
    SET_EXP_THRESH = "EXPIRY THRESHOLD"
    SET_VETO_LIMIT = "VETO LIMIT"
    SET_VETO_PENALTY = "VETO PENALTY"
    SET_ELO_K = "ELO K"
    SET_ELO_DEFAULT = "ELO DEFAULT"
    SET_GLICKO_RD = "GLICKO RD"
    SET_GLICKO_DEFAULT = "GLICKO DEFAULT"
    SET_TRUESKILL_SIGMA = "TRUESKILL SIGMA"
    SET_TRUESKILL_DEFAULT = "TRUESKILL MU"
    SET_REVERSE_PARITY = "PREFER SKEWED MATCHUPS"
    SET_LEAGUE_MESSAGE = "MESSAGE"
    SET_SUPER_NAME = "CLUSTER NAME"
    SET_LEAGUE_ACRONYM = "SHORT NAME"
    SET_URL = "URL"
    SET_MAX_TEAMS = "PLAYER TEAM LIMIT"
    SET_REMOVE_DECLINES = "REMOVE DECLINES"
    SET_VETO_DECLINES = "COUNT DECLINES AS VETOS"
    SET_DROP_LIMIT = "DROP LIMIT"
    SET_MAX_BOOT = "MAX BOOT RATE"
    SET_MIN_LEVEL = "MIN LEVEL"
    SET_MEMBERS_ONLY = "MEMBERS ONLY"
    SET_MIN_POINTS = "MIN POINTS"
    SET_MIN_AGE = "MIN AGE" # days
    SET_MIN_MEMBER_AGE = "MIN MEMBER AGE" # days
    SET_MAX_RT_SPEED = "MAX RT SPEED" # minutes
    SET_MAX_MD_SPEED = "MAX MD SPEED" # hours
    SET_MIN_RATING = "MIN RATING"
    SET_GRACE_PERIOD = "GRACE PERIOD" # days
    SET_ALLOW_JOINS = "ALLOW JOINING"
    SET_JOIN_PERIOD_START = "JOIN PERIOD START"
    SET_JOIN_PERIOD_END = "JOIN PERIOD END"
    SET_ALLOW_REMOVAL = "ALLOW REMOVAL"
    SET_MIN_ONGOING_GAMES = "MIN ONGOING GAMES"
    SET_MAX_ONGOING_GAMES = "MAX ONGOING GAMES"
    SET_MIN_RT_PERCENT = "MIN RT PERCENT"
    SET_MAX_RT_PERCENT = "MAX RT PERCENT"
    SET_MAX_LAST_SEEN = "MAX LAST SEEN" # days
    SET_MIN_1v1_PCT = "MIN 1v1 PERCENT"
    SET_MIN_2v2_PCT = "MIN 2v2 PERCENT"
    SET_MIN_3v3_PCT = "MIN 3v3 PERCENT"
    SET_MIN_RANKED = "MIN RANKED GAMES"
    SET_MIN_GAMES = "MIN PLAYED GAMES"
    SET_MIN_ACH = "MIN ACHIEVEMENT RATE"
    SET_START_DATE = "LEAGUE START"
    SET_END_DATE = "LEAGUE END"
    SET_ACTIVE = "ACTIVE"
    SET_MIN_SIZE = "MIN TEAM COUNT"
    SET_MIN_PERCENTILE = "MIN RATING PERCENTILE"
    SET_MIN_TEMPLATES = "MIN ACTIVE TEMPLATES"
    SET_REMATCH_LIMIT = "REMATCH HORIZON"
    SET_RESTORATION_PERIOD = "RESTORATION PERIOD" # days
    SET_LEAGUE_CAPACITY = "MAX TEAMS"
    SET_ACTIVE_CAPACITY = "MAX ACTIVE TEAMS"
    SET_MIN_TO_CULL = "MIN GAMES TO CULL"
    SET_MIN_TO_RANK = "MIN GAMES TO RANK"
    SET_MAX_RANK = "MAX RANK"
    SET_MIN_LIMIT_TO_RANK = "MIN LIMIT TO RANK"
    SET_MAX_VACATION = "MAX VACATION LENGTH" # days
    SET_AUTODROP = "AUTODROP"

    # rating systems
    RATE_ELO = "ELO"
    RATE_GLICKO = "GLICKO"
    RATE_TRUESKILL = "TRUESKILL"
    RATE_WINCOUNT = "WINCOUNT"
    RATE_WINRATE = "WINRATE"
    WINRATE_SCALE = 1000

    # timeformat
    TIMEFORMAT = "%Y-%m-%d %H:%M:%S"

    # default message
    DEFAULT_MSG = """This is a game for the {{%s}} league, part of {{%s}}.

                     To view information about the league, head to {{%s}}.
                     To change your limit, add/confirm a team, etc.,
                     head to the league thread at {{%s}}.

                     Vetos so far: {{%s}}; Max: {{%s}}

                     {{%s}}

                     This league is run using the CSL framework,
                     an open-source project maintained by knyte.

                     To view the source code, head to:
                         https://github.com/knyte/cslbot

                     If you never signed up for this game or suspect abuse,
                     message knyte - tinyurl.com/mail-knyte
                     """ % ("_LEAGUE_NAME", SET_SUPER_NAME, SET_URL,
                            "_LEAGUE_THREAD", "_VETOS",
                            SET_VETO_LIMIT, "_GAME_SIDES")

    # keywords
    KW_ALL = "ALL"
    KW_TEMPSETTING = "SET_"

    # separators
    SEP_CMD = ","
    SEP_PLYR = ","
    SEP_CONF = ","
    SEP_TEAMS = ","
    SEP_SIDES = "/"
    SEP_RTG = "/"
    SEP_TEMP = ","
    SEP_VETOCT = "."
    SEP_VETOS = "/"
    SEP_DROPS = "/"
    SEP_MODS = ","
    SEP_TEMPSET = "#"

    def __init__(self, games, teams, templates, settings, orders,
                 admin, parent, name, thread):
        self.games = games
        self.teams = teams
        self.templates = templates
        self.settings = settings
        self.orders = orders
        self.admin = admin
        self.mods = self._getMods()
        self.parent = parent
        self.name = name
        self.thread = thread
        self.handler = self._makeHandler()
        self.checkFormat()
        self.makeRateSysDict()

    def makeRateSysDict(self):
        self.sysDict = {self.RATE_ELO: {'default': self.defaultElo,
                                        'update': self.getNewEloRatings,
                                        'prettify': self.getPrettyEloRating,
                                        'parity': self.getEloParity},
                        self.RATE_GLICKO: {'default': self.defaultGlicko,
                                           'update': self.getNewGlickoRatings,
                                           'prettify':
                                           self.getPrettyGlickoRating,
                                           'parity': self.getGlickoParity},
                        self.RATE_TRUESKILL: {'default': self.defaultTrueSkill,
                                              'update':
                                              self.getNewTrueSkillRatings,
                                              'prettify':
                                              self.getPrettyTrueSkillRating,
                                              'parity':
                                              self.getTrueSkillParity},
                        self.RATE_WINCOUNT: {'default': self.defaultWinCount,
                                             'update': self.getNewWinCounts,
                                             'prettify': int,
                                             'parity': self.getWinCountParity},
                        self.RATE_WINRATE: {'default': self.defaultWinRate,
                                            'update': self.getNewWinRates,
                                            'prettify': (lambda r:
                                            int(r.split(self.SEP_RTG)[0])),
                                            'parity': self.getWinRateParity}}

    @staticmethod
    def _makeHandler():
        credsFile = open(API_CREDS)
        creds = json.load(credsFile)
        email, token = creds['E-mail'], creds['APIToken']
        return APIHandler(email, token)

    def _getMods(self):
        mods = self.fetchProperty(self.SET_MODS, set(), self.getIDGroup)
        mods.add(self.admin)
        return mods

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
        for label in table_header:
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
                           'Name': 'UNIQUE STRING',
                           'Players': 'STRING',
                           'Confirmations': 'STRING',
                           'Rating': 'STRING',
                           'Vetos': 'STRING',
                           'Drops': 'STRING',
                           'Rank': 'INT',
                           'History': 'STRING',
                           'Finished': 'INT',
                           'Limit': 'INT',
                           'Count': 'INT'}
        if self.minRating is not None:
            teamConstraints['Probation Start'] = 'STRING'
        self.checkSheet(self.teams, set(teamConstraints), teamConstraints,
                        self.autoformat)

    def checkGamesSheet(self):
        gamesConstraints = {'ID': 'UNIQUE INT',
                            'WarlightID': 'UNIQUE INT',
                            'Created': 'STRING',
                            'Sides': 'STRING',
                            'Winners': 'STRING',
                            'Vetos': 'INT',
                            'Vetoed': 'STRING',
                            'Template': 'INT'}
        self.checkSheet(self.games, set(gamesConstraints), gamesConstraints,
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

    def fetchProperty(self, label, default, process_fn=None):
        cmd = self.settings.get(label, default)
        try:
            if (process_fn is None or
                cmd is default): return cmd
            return process_fn(cmd)
        except Exception as e:
            errType = type(e).__name__
            failStr = ("Couldn't get %s due to %s, using default of %s" %
                       (str(label), errType, str(default)))
            self.parent.log(failStr, self.name)
            return default

    @staticmethod
    def getBoolProperty(val):
        return (val.lower() == 'true')

    @property
    def autoformat(self):
        """whether to automatically format sheets"""
        return self.fetchProperty(self.SET_AUTOFORMAT, True,
                                  self.getBoolProperty)

    @property
    def autodrop(self):
        """whether to automatically drop templates players can't use"""
        return self.fetchProperty(self.SET_AUTODROP, (self.dropLimit > 0),
                                  self.getBoolProperty)

    @property
    def leagueAcronym(self):
        return self.fetchProperty(self.SET_LEAGUE_ACRONYM, self.clusterName)

    @property
    def clusterName(self):
        return self.fetchProperty(self.SET_SUPER_NAME, self.name)

    @property
    def leagueMessage(self):
        return self.fetchProperty(self.SET_LEAGUE_MESSAGE, self.DEFAULT_MSG)

    @property
    def leagueUrl(self):
        return self.fetchProperty(self.SET_URL, self.defaultUrl)

    @property
    def defaultUrl(self):
        sheetName = self.games.parent.sheet.ID
        return ("https://docs.google.com/spreadsheets/d/" +
                str(sheetName))

    @property
    def rematchLimit(self):
        process_fn = (lambda val: val if val == self.KW_ALL else
                      int(val) * self.teamsPerSide * self.gameSize)
        return self.fetchProperty(self.SET_REMATCH_LIMIT, 0, process_fn)

    @property
    def teamLimit(self):
        process_fn = lambda x: None if x is None else int(x)
        defaultMax = None if self.teamSize > 1 else 1
        return self.fetchProperty(self.SET_MAX_TEAMS, defaultMax, process_fn)

    @property
    def vetoLimit(self):
        """maximum number of vetos per game"""
        return self.fetchProperty(self.SET_VETO_LIMIT, 0, int)

    @property
    def dropLimit(self):
        """maximum number of templates a player can drop"""
        process_fn = lambda x: min(int(x), len(self.templateIDs) - 1)
        return self.fetchProperty(self.SET_DROP_LIMIT, 0, process_fn)

    @property
    def removeDeclines(self):
        return self.fetchProperty(self.SET_REMOVE_DECLINES, True,
                                  self.getBoolProperty)

    @property
    def countDeclinesAsVetos(self):
        return self.fetchProperty(self.SET_VETO_DECLINES, False,
                                  self.getBoolProperty)

    @property
    def vetoPenalty(self):
        """points deduction for excessive vetos"""
        if self.ratingSystem == self.RATE_WINCOUNT: default = 1
        elif self.ratingSystem == self.RATE_WINRATE: default = 50
        else: default = 25
        return self.fetchProperty(self.SET_VETO_PENALTY, default, int)

    @property
    def teamSize(self):
        """number of players per team"""
        return self.fetchProperty(self.SET_TEAM_SIZE, 1, int)

    @property
    def gameSize(self):
        """number of sides per game"""
        return self.fetchProperty(self.SET_GAME_SIZE, 2, int)

    @property
    def sideSize(self):
        """number of teams per side"""
        return self.fetchProperty(self.SET_TEAMS_PER_SIDE, 1, int)

    @property
    def expiryThreshold(self):
        """number of days until game is declared abandoned"""
        return self.fetchProperty(self.SET_EXP_THRESH, 3, int)

    @property
    def maxVacation(self):
        """maximum vacation length (in days) to remain on ladder"""
        return self.fetchProperty(self.SET_MAX_VACATION, None, int)

    def meetsVacation(self, player):
        maxVac, secsPerDay = self.maxVacation, 86400
        if maxVac is None: return True
        timeZoneDiff = timedelta(hours=5)
        ID, formatStr = int(player.ID), '%m/%d/%Y %H:%M:%S'
        validationData = self.handler.validateToken(ID)
        if 'onVacationUntil' not in validationData: return True
        if maxVac is 0: return False
        vacayTime = datetime.strptime(validationData['onVacationUntil'],
                                      formatStr)
        diff = ((vacayTime - datetime.now()) - timeZoneDiff)
        totalDays = diff.days + float(diff.seconds) / secsPerDay
        return (totalDays <= maxVac)

    @property
    def minLimit(self):
        """minimum number of max ongoing games per team"""
        process_fn = lambda x: max(int(x), 0)
        return self.fetchProperty(self.SET_MIN_LIMIT, 0, process_fn)

    @property
    def maxLimit(self):
        """maximum number of max ongoing games per team"""
        return self.fetchProperty(self.SET_MAX_LIMIT, None, int)

    @property
    def constrainLimit(self):
        """
        whether to constrain out-of-range limits
        limits outside range are set to the min or max limit
        """
        return self.fetchProperty(self.SET_CONSTRAIN_LIMIT, True,
                                  self.getBoolProperty)

    @staticmethod
    def valueInRange(val, rangeMin, rangeMax):
        return ((rangeMin is None or val >= rangeMin) and
                (rangeMax is None or val <= rangeMax))

    def limitInRange(self, limit):
        """returns True if a limit is in an acceptable range"""
        return self.valueInRange(limit, self.minLimit, self.maxLimit)

    @property
    def ratingSystem(self):
        """rating system to use"""
        system = self.fetchProperty(self.SET_SYSTEM, self.RATE_ELO,
                                    lambda x: x.upper())
        if system not in self.sysDict:
            raise ImproperInput("Unrecognized rating system. Aborting.")
        return system

    @property
    def kFactor(self):
        prop = self.fetchProperty(self.SET_ELO_K, 32, int)
        return (prop * self.sideSize)

    @property
    def defaultElo(self):
        return self.fetchProperty(self.SET_ELO_DEFAULT, 1500, int)

    @property
    def eloEnv(self):
        return Elo(initial=self.defaultElo, k_factor=self.kFactor)

    @property
    def glickoRd(self):
        return self.fetchProperty(self.SET_GLICKO_RD, 350, int)

    @property
    def glickoRating(self):
        return self.fetchProperty(self.SET_GLICKO_DEFAULT, 1500, int)

    @property
    def defaultGlicko(self):
        return self.unsplitRtg([self.glickoRating, self.glickoRd])

    @property
    def trueSkillSigma(self):
        return self.fetchProperty(self.SET_TRUESKILL_SIGMA, 500, int)

    @property
    def trueSkillMu(self):
        return self.fetchProperty(self.SET_TRUESKILL_DEFAULT, 1500, int)

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
        return self.unsplitRtg([self.trueSkillMu, self.trueSkillSigma])

    @property
    def defaultWinCount(self):
        return str(0)

    @property
    def defaultWinRate(self):
        return (self.SEP_RTG).join(str(i) for i in [0, 0])

    @property
    def reverseParity(self):
        return self.fetchProperty(self.SET_REVERSE_PARITY, False,
                                  self.getBoolProperty)

    @property
    def maxBoot(self):
        return self.fetchProperty(self.SET_MAX_BOOT, 100.0, float)

    @property
    def minLevel(self):
        return self.fetchProperty(self.SET_MIN_LEVEL, 0, int)

    @property
    def membersOnly(self):
        exp = self.fetchProperty(self.SET_MEMBERS_ONLY, False,
                                 self.getBoolProperty)
        return (exp or (self.minMemberAge > 0))

    def meetsMembership(self, player):
        return (not self.membersOnly or player.isMember)

    @property
    def minPoints(self):
        return self.fetchProperty(self.SET_MIN_POINTS, 0, int)

    @property
    def minAge(self):
        return self.fetchProperty(self.SET_MIN_AGE, 0, int)

    @property
    def minMemberAge(self):
        return self.fetchProperty(self.SET_MIN_MEMBER_AGE, 0, int)

    @property
    def maxRTSpeed(self):
        process_fn = lambda x: float(Decimal(x) / Decimal(60.0))
        return self.fetchProperty(self.SET_MAX_RT_SPEED, None, process_fn)

    @property
    def maxMDSpeed(self):
        return self.fetchProperty(self.SET_MAX_MD_SPEED, None, float)

    @property
    def minExplicitRating(self):
        return self.fetchProperty(self.SET_MIN_RATING, None, int)

    def findRatingAtPercentile(self, percentile):
        if percentile == 0: return None
        ratings = self.teams.findValue({'ID': {'value': '',
                                               'type': 'negative'}},
                                       "Rating")
        for i in xrange(len(ratings)):
            ratings[i] = int(prettifyRating(ratings[i]))
        ratings.sort()
        index = len(ratings) * float(Decimal(percentile) / Decimal(100.0))
        index = int(index) + bool(index % 1)
        return ratings[index]

    @property
    def minPercentileRating(self):
        process_fn = lambda x: self.findRatingAtPercentile(float(x))
        self.fetchProperty(self.SET_MIN_PERCENTILE, None, process_fn)

    @property
    def minRating(self):
        minPercentile = self.minPercentileRating
        if minPercentile is None: return self.minExplicitRating
        return minPercentile

    @property
    def gracePeriod(self):
        return self.fetchProperty(self.SET_GRACE_PERIOD, 0, int)

    @property
    def restorationPeriod(self):
        process_fn = lambda x: int(x) + self.gracePeriod
        return self.fetchProperty(self.SET_RESTORATION_PERIOD, None,
                                  process_fn)

    @runPhase
    def restoreTeams(self):
        restPd = self.restorationPeriod
        if self.minRating is None or restPd is None: return
        deadTeams = self.getExtantEntities(self.teams,
                                           {'Limit': {'value': '0',
                                                      'type': 'positive'},
                                            'Probation Start': {'value': '',
                                                          'type': 'negative'}})
        for team in deadTeams:
            probStart = team['Probation Start']
            probStart = datetime.strptime(probStart, self.TIMEFORMAT)
            if ((datetime.now() - probStart).days >= self.restorationPeriod):
                self.teams.updateMatchingEntities({'ID': {'value': team['ID'],
                                                          'type': 'positive'}},
                                                 {'Rating': self.defaultRating,
                                                  'Probation Start': ''})

    @property
    def allowJoins(self):
        return self.fetchProperty(self.SET_ALLOW_JOINS, True,
                                  self.getBoolProperty)

    @property
    def leagueCapacity(self):
        return self.fetchProperty(self.SET_LEAGUE_CAPACITY, None, int)

    @property
    def activeCapacity(self):
        return self.fetchProperty(self.SET_ACTIVE_CAPACITY, None, int)

    @staticmethod
    def valueBelowCapacity(value, capacity):
        return self.valueInRange(value, None, capacity-1)

    @property
    def activeFull(self):
        return (not self.valueBelowCapacity(len(self.activeTeams),
                                            self.activeCapacity))

    @property
    def leagueFull(self):
        return (not self.valueBelowCapacity(len(self.allTeams),
                                            self.leagueCapacity))

    @staticmethod
    def getDateTimeProperty(val):
        if isinstance(val, datetime): return val
        return datetime.strptime(val, self.TIMEFORMAT)

    @property
    def joinPeriodStart(self):
        return self.fetchProperty(self.SET_JOIN_PERIOD_START, None,
                                  self.getDateTimeProperty)

    @property
    def joinPeriodEnd(self):
        return self.fetchProperty(self.SET_JOIN_PERIOD_END, None,
                                  self.getDateTimeProperty)

    @staticmethod
    def currentTimeWithinRange(start, end):
        now = datetime.now()
        if (start is not None and
            now < start): return False
        if (end is not None and
            now > end): return False
        return True

    @property
    def joinsAllowed(self):
        if (self.leagueFull or self.activeFull): return False
        start, end = self.joinPeriodStart, self.joinPeriodEnd
        if self.currentDateWithinRange(start, end):
            return self.allowJoins
        return False

    @property
    def leagueActive(self):
        return self.fetchProperty(self.SET_ACTIVE, True, self.getBoolProperty)

    @property
    def minSize(self):
        return self.fetchProperty(self.SET_MIN_SIZE, (self.teamsPerSide *
                                  self.gameSize), int)

    @property
    def minToCull(self):
        return self.fetchProperty(self.SET_MIN_TO_CULL, 0, int)

    @property
    def minToRank(self):
        return self.fetchProperty(self.SET_MIN_TO_RANK, 0, int)

    @property
    def maxRank(self):
        return self.fetchProperty(self.SET_MAX_RANK, None, int)

    @property
    def minLimitToRank(self):
        return self.fetchProperty(self.SET_MIN_LIMIT_TO_RANK, 1, int)

    @staticmethod
    def getExtantEntities(table, restrictions=None):
        matchDict = {'ID': {'value': '', 'type': 'negative'}}
        if restrictions is not None:
            for restriction in restrictions:
                matchDict[restriction] = restrictions[restriction]
        return table.findEntities(matchDict)

    @property
    def activeTeams(self):
        return self.getExtantEntities(self.teams,
                                      {'Limit': {'value': '0',
                                                 'type': 'negative'}})

    @property
    def activeTemplates(self):
        return self.getExtantEntities(self.templates,
                                      {'Active': {'value': 'TRUE',
                                                  'type': 'positive'}})

    @property
    def size(self):
        return len(self.activeTeams)

    @property
    def templateSize(self):
        return len(self.activeTemplates)

    @property
    def minTemplates(self):
        return self.fetchProperty(self.SET_MIN_TEMPLATES, 1, int)

    @property
    def activityStart(self):
        return self.fetchProperty(self.SET_START_DATE, None,
                                  self.getDateTimeProperty)

    @property
    def activityEnd(self):
        return self.fetchProperty(self.SET_END_DATE, None,
                                  self.getDateTimeProperty)

    @property
    def active(self):
        if self.templateSize < self.minTemplates: return False
        if self.size < self.minSize: return False
        start, end = self.activityStart, self.activityEnd
        if self.currentDateWithinRange(start, end):
            return self.leagueActive
        return False

    @property
    def allowRemoval(self):
        return self.fetchProperty(self.SET_ALLOW_REMOVAL, False,
                                  self.getBoolProperty)

    @property
    def minOngoingGames(self):
        return self.fetchProperty(self.SET_MIN_ONGOING_GAMES, 0, int)

    @property
    def maxOngoingGames(self):
        return self.fetchProperty(self.SET_MAX_ONGOING_GAMES, None, int)

    def gameCountInRange(self, player):
        ongoing = player.currentGames
        return self.valueInRange(ongoing, self.minOngoingGames,
                                 self.maxOngoingGames)

    @property
    def minRTPercent(self):
        return self.fetchProperty(self.SET_MIN_RT_PERCENT, 0.0, float)

    @property
    def maxRTPercent(self):
        return self.fetchProperty(self.SET_MAX_RT_PERCENT, 100.0, float)

    def RTPercentInRange(self, player):
        pct = player.percentRT
        return (pct >= self.minRTPercent and pct <= self.maxRTPercent)

    @property
    def maxLastSeen(self):
        return self.fetchProperty(self.SET_MAX_LAST_SEEN, None, float)

    @property
    def min1v1Pct(self):
        return self.fetchProperty(self.SET_MIN_1v1_PCT, 0.0, float)

    @property
    def min2v2Pct(self):
        return self.fetchProperty(self.SET_MIN_2v2_PCT, 0.0, float)

    @property
    def min3v3Pct(self):
        return self.fetchProperty(self.SET_MIN_3v3_PCT, 0.0. float)

    @property
    def minRanked(self):
        return self.fetchProperty(self.SET_MIN_RANKED, 0, int)

    def meetsMinRanked(self, player):
        data = player.rankedGames
        pcts = data.get('data', dict())
        p1v1, p2v2, p3v3 = (pcts.get('1v1', 0), pcts.get('2v2', 0),
                            pcts.get('3v3', 0))
        return (p1v1 >= self.min1v1Pct and
                p2v2 >= self.min2v2Pct and
                p3v3 >= self.min3v3Pct and
                data.get('games', 0) >= self.minRanked)

    @property
    def minGames(self):
        return self.fetchProperty(self.SET_MIN_GAMES, 0, int)

    @property
    def minAchievementRate(self):
        return self.fetchProperty(self.SET_MIN_ACH, 0, float)

    def getIDGroup(self, val, process_fn=int):
        return set([process_fn(x) for x in val.split(self.SEP_CMD)])

    @staticmethod
    def getGroup(val):
        return self.getIDGroup(val, process_fn=str)

    @property
    def bannedPlayers(self):
        """set containing IDs of banned players"""
        return self.fetchProperty(self.SET_BANNED_PLAYERS, set(),
                                  self.getIDGroup)

    @property
    def bannedClans(self):
        """set containing IDs of banned clans"""
        return self.fetchProperty(self.SET_BANNED_CLANS, set(),
                                  self.getIDGroup)

    @property
    def bannedLocations(self):
        return self.fetchProperty(self.SET_BANNED_LOCATIONS, set(),
                                  self.getGroup)

    @property
    def allowedPlayers(self):
        """set containing IDs of allowed players"""
        return self.fetchProperty(self.SET_ALLOWED_PLAYERS, set(),
                                  self.getIDGroup)

    @property
    def allowedClans(self):
        """set containing IDs of allowed clans"""
        return self.fetchProperty(self.SET_ALLOWED_CLANS, set(),
                                  self.getIDGroup)

    @property
    def allowedLocations(self):
        return self.fetchProperty(self.SET_ALLOWED_LOCATIONS, set(),
                                  self.getGroup)

    @property
    def requireClan(self):
        default = (self.KW_ALL in self.bannedClans)
        return self.fetchProperty(self.SET_REQUIRE_CLAN, default,
                                  self.getBoolProperty)

    def clanAllowed(self, player):
        clan = player.clanID
        if clan is None:
            return (not self.requireClan)
        clan = int(clan)
        return ((clan in self.allowedClans or
                 (self.KW_ALL in self.allowedClans))
                 or (clan not in self.bannedClans
                     and self.KW_ALL not in self.bannedClans))

    @staticmethod
    def processLoc(location):
        tempLoc = location.split()
        return ' '.join(tempLoc)

    def checkLocation(self, location):
        location = self.processLoc(location)
        if (location in self.allowedLocations or
            self.KW_ALL in self.allowedLocations): return True
        if (location in self.bannedLocations or
            self.KW_ALL in self.bannedLocations): return False

    def locationAllowed(self, player):
        location = player.location.split(":")
        results = set()
        for loc in location:
            check = self.checkLocation(loc)
            results.add(check)
        return ((True in results) or (False not in results))

    def meetsAge(self, player):
        now = datetime.now()
        joinDate = player.joinDate
        return ((now - joinDate).days >= self.minAge)

    def meetsSpeed(self, player):
        speeds = player.playSpeed
        rtSpeed = speeds.get('Real-Time Games', None)
        mdSpeed = speeds.get('Multi-Day Games', None)
        return ((self.maxRTSpeed is None or
                 rtSpeed <= self.maxRTSpeed) and
                (self.maxMDSpeed is None or
                 mdSpeed <= self.maxMDSpeed))

    def meetsLastSeen(self, player):
        lastSeen = player.lastSeen
        return (self.maxLastSeen is None or
                lastSeen <= self.maxLastSeen)

    def checkPrereqs(self, player):
        prereqs = {self.clanAllowed(player), self.locationAllowed(player),
                   (player.bootRate <= self.maxBoot),
                   (player.level >= self.minLevel),
                   self.meetsMembership(player), self.meetsVacation(player),
                   (player.points >= self.minPoints), self.meetsAge(player),
                   self.meetsSpeed(player), self.gameCountInRange(player),
                   self.RTPercentInRange(player), self.meetsLastSeen(player),
                   self.meetsMinRanked(player),
                   (player.playedGames >= self.minGames),
                   (player.achievementRate >= self.minAchievementRate)}
        for prereq in prereqs:
            if prereq is not True: return False
        return True

    def allowed(self, playerID):
        """returns True if a player is allowed to join the league"""
        player = int(playerID)
        if player in self.allowedPlayers: return True
        parser = PlayerParser(player)
        if not self.checkPrereqs(parser):
            return False
        return (player not in self.bannedPlayers and
                self.KW_ALL not in self.bannedPlayers)

    def banned(self, playerID):
        """returns True if a player is banned from the league"""
        return not(self.allowed(playerID))

    def logFailedOrder(self, order):
        desc = ("Failed to process %s order by %d for league %s" %
                (order['type'], order['author'], order['orders'][0]))
        self.parent.log(desc, league=self.name)

    def checkTeamCreator(self, creator, members):
        if (creator not in members and
            creator not in self.mods):
            raise ImproperInput(str(creator) + " isn't able to" +
                                " add a team that excludes them")

    def checkTemplateAccess(self, playerID):
        """returns True if a player can play on all templates"""
        tempIDs = self.templateIDs
        tempWLIDs, unusables = dict(), set()
        for ID in tempIDs:
            tempWLIDs[tempIDs[ID]['WarlightID']] = ID
        tempResults = self.handler.validateToken(int(playerID),
                                                 *tempWLIDs)
        for temp in tempWLIDs:
            tempName = "template" + str(temp)
            if tempResults[tempName]['result'] != 'CannotUseTemplate':
                unusables.add(tempWLIDs[temp])
        return unusables

    def handleAutodrop(self, teamID, templates):
        teams = self.teams.findEntities({'ID': {'value': teamID,
                                                'type': 'positive'}})
        if len(teams) == 0:
            raise ImproperInput("Cannot autodrop for nonexistent team %s" %
                                (str(teamID)))
        team = teams[0]
        existingDrops = set(team['Drops'].split(self.SEP_DROPS))
        if (len(existingDrops) + len(templates)) > self.dropLimit:
            raise ImproperInput("Team %s has already reached its drop limit" %
                                (str(teamID)))
        existingDrops = existingDrops.union(str(t) for t in templates)
        drops = (self.SEP_DROPS).join(str(d) for d in existingDrops)
        self.teams.updateMatchingEntities({'ID': {'value': teamID,
                                                  'type': 'positive'}},
                                          {'Drops': drops})

    def checkTeamMember(self, member, badTemps):
        if self.banned(member):
            raise ImproperInput(str(member) + " is banned from this league")
        tempAccess = self.checkTemplateAccess(member)
        for temp in tempAccess:
            badTemplates.add(temp)

    def autodropEligible(self, badTemps):
        return (self.autodrop and (len(badTemps) <= self.dropLimit))

    def handleTeamAutodrop(self, teamID, badTemps):
        if self.autodropEligible(badTemps):
            if teamID is None:
                forcedDrops = (self.SEP_DROPS).join([str(t) for t in badTemps])
                return forcedDrops
            else:
                self.handleAutodrop(teamID, badTemps)
                return ""
        else:
            memberStr = (self.SEP_PLYR).join([str(m) for m in members])
            raise ImproperInput("Team with %s cannot play on enough templates"
                                % (memberStr))

    def checkTeam(self, members, teamID=None):
        badTemplates = set()
        for member in members: self.checkTeamMember(member, badTemplates)
        return self.handleTeamAutodrop(teamID, badTemplates)

    def checkLimit(self, limit):
        if not self.limitInRange(limit):
            if self.constrainLimit:
                if limit < self.minLimit: return self.minLimit
                return self.maxLimit
            else: raise ImproperInput()
        return limit

    @property
    def existingIDs(self):
        officialIDs = self.teams.findValue({'ID': {'value': '',
                                                   'type': 'negative'}}, 'ID')
        usedSides = self.games.findValue({'ID': {'value': '',
                                                 'type': 'negative'}}, 'Sides')
        unofficialIDs = set()
        for sideGroup in usedSides:
            for side in sideGroup.split(self.SEP_SIDES):
                for team in side.split(self.SEP_TEAMS):
                    unofficialIDs.add(int(team))
        for ID in officialIDs:
            unofficialIDs.add(int(ID))
        return unofficialIDs

    def setCurrentID(self):
        existingIDs = self.existingIDs
        if len(existingIDs) == 0:
            self.currentID = 0
        else:
            self.currentID = max(existingIDs) + 1

    @property
    def defaultRating(self):
        return self.sysDict[self.ratingSystem]['default']

    @property
    def teamPlayers(self):
        result = list()
        for team in self.allTeams:
            result[team['Players']] = team['Name']
        return result

    def checkJoins(self):
        if not self.joinsAllowed:
            raise ImproperInput("This league is not open to new teams")

    def checkAuthorAndMembers(self, order):
        author = int(order['author'])
        members = [int(member) for member in order['orders'][3:]]
        self.checkTeamCreator(author, members)
        confirms = [(m == author) for m in members]
        return self.checkTeam(members), members, confirms

    def checkTeamDuplication(self, members, teamName):
        if members in self.teamPlayers:
            orig = self.teamPlayers[members]
            raise ImproperInput("Team %s is a duplicate of existing team %s" %
                                (teamName, orig))

    def checkEligible(self, order):
        gameLimit = int(order['orders'][2])
        forcedDrops, members, confirms = self.checkAuthorAndMembers(order)
        return self.checkLimit(gameLimit), forcedDrops, members, confirms

    def addTeam(self, order):
        self.checkJoins()
        teamName = order['orders'][1]
        gameLimit, forcedDrops, members, confirms = self.checkEligible(order)
        members.sort()
        members = (self.SEP_PLYR).join([str(m) for m in members])
        confirms = (self.SEP_CONF).join([str(c).upper() for c in confirms])
        self.checkTeamDuplication(members, teamName)
        self.teams.addEntity({'ID': self.currentID,
                              'Name': teamName,
                              'Limit': gameLimit,
                              'Players': members,
                              'Confirmations': confirms,
                              'Vetos': "", 'Drops': forcedDrops,
                              'Count': 0, 'Finished': 0,
                              'Rating': self.defaultRating})
        self.currentID += 1

    def retrieveTeamWithName(self, name):
        matches = self.teams.findEntities({'Name': {'value': name,
                                                    'type': 'positive'}})
        if len(matches) < 1:
            raise NonexistentItem("Nonexistent team: " + str(name))
        return matches[0]

    def authorInTeam(self, author, team, allowMods=True):
        if (allowMods and (author in self.mods)): return True
        return (str(author) in matchingTeam['Players'].split(self.SEP_PLYR))

    def fetchMatchingTeam(self, order, checkAuthor=True,
                          allowMod=True):
        name, author, index = order['orders'][1], int(order['author']), None
        matchingTeam = self.retrieveTeamWithName(name)
        if (checkAuthor and
            not self.authorInTeam(author, matchingTeam, allowMod)):
            raise ImproperInput(str(author) + " not in " + str(name))
        try:
            index = (matchingTeam['Players'].
                     split(self.SEP_PLYR).
                     index(author))
        except ValueError: pass
        return matchingTeam, index

    def toggleConfirm(self, order, confirm=True):
        try:
            matchingTeam, index = self.fetchMatchingTeam(order, True, False)
        except ImproperInput:
            raise ImproperInput(str(player) + " not in " + str(team))
        if index is None:
            raise ImproperInput(str(player) + " not in " + str(team))
        confirms = matchingTeam['Confirmations'].split(self.SEP_CONF)
        confirms[index] = "TRUE" if confirm else "FALSE"
        self.updateConfirms(teamName, confirms, identifier='Name')

    def confirmTeam(self, order):
        if (author in self.mods and len(order['orders']) > 2):
            self.toggleConfirms(order)
        self.toggleConfirm(order)

    def unconfirmTeam(self, order):
        if (author in self.mods and len(order['orders']) > 2):
            self.toggleConfirms(order, False)
        self.toggleConfirm(order, False)

    def toggleConfirms(self, order, confirm=True):
        players = order['orders'][2:]
        teamName = order['orders'][1]
        for player in players:
            newOrder = {'author': int(player), 'orders': [self.name, teamName]}
            self.toggleConfirm(newOrder, confirm=confirm)

    def removeTeam(self, order):
        if not self.allowRemoval:
            raise ImproperInput("Team removal has been disabled.")
        matchingTeam = self.fetchMatchingTeam(order)[0]
        self.teams.removeMatchingEntities({'ID':
                                           matchingTeam['ID']})

    def checkLimitChange(self, teamID, newLimit):
        if int(newLimit) <= 0: return
        if self.activeCapacity is None: return
        if not self.activeFull: return
        oldLimit = int(self.fetchTeamData(teamID)['Limit'])
        if oldLimit == 0:
            raise ImproperInput("League has reached max active teams.")

    def setLimit(self, order):
        matchingTeam = self.fetchMatchingTeam(order, False)[0]
        players = matchingTeam['Players'].split(self.SEP_PLYR)
        if (str(order['author']) not in players and
            order['author'] not in self.mods):
            raise ImproperInput(str(order['author']) +
                                " can't set the limit for team " +
                                str(order['orders'][1]))
        self.checkLimitChange(matchingTeam['ID'], order['orders'][2])
        self.changeLimit(matchingTeam['ID'], order['orders'][2])

    @property
    def templateIDs(self):
        return self.templates.findValue({'ID': {'value': '',
                                                'type': 'negative'},
                                         'Active': {'value': ['TRUE', True],
                                                    'type': 'positive'}}, "ID")

    @property
    def gameIDs(self):
        return self.games.findValue({'ID': {'value': '',
                                            'type': 'negative'}}, 'ID')

    @property
    def templateRanks(self):
        tempData = self.activeTemplates
        tempInfo = [(int(tempData[temp]['ID']), int(tempData[temp]['Games']))
                    for temp in tempData]
        tempInfo.sort(key = lambda x: x[1])

    def findMatchingTemplate(self, templateName):
        IDs = self.templates.findValue({'ID': {'value': '',
                                               'type': 'negative'},
                                        'Name': {'value': templateName,
                                                 'type': 'positive'}},
                                       'ID')
        if len(IDs) == 0: return None
        return IDs[0]

    def getExistingDrops(self, order):
        teamData = self.fetchMatchingTeam(order)
        existingDrops = teamData['Drops']
        existingDrops = existingDrops.split(self.SEP_DROPS)
        teamID = teamData['ID']
        return teamID, existingDrops

    def updateTeamDrops(self, teamID, drops):
        dropStr = (self.SEP_DROPS).join(set(drops))
        self.teams.updateMatchingEntities({'ID': {'value': teamID,
                                                  'type': 'positive'}},
                                          {'Drops': dropStr})

    def dropTemplates(self, order):
        templateNames = order['orders'][2:]
        teamName = order['orders'][1]
        teamID, existingDrops = self.getExistingDrops(order)
        remainingDrops = (self.dropLimit - len(existingDrops))
        if remainingDrops < 1:
            raise ImproperInput("Team %s already reached its drop limit" %
                                (teamName))
        elif remainingDrops < len(templateNames):
            dataStr = ("Too many drops attempted by team %s, dropping first %d"
                       % (teamName, remainingDrops))
            self.parent.log(dataStr, self.name)
            templateNames = templateNames[:remainingDrops]
        for templateName in templateNames:
            temp = self.findMatchingTemplate(templateName)
            if temp is None: continue
            existingDrops.append(temp)
        self.updateTeamDrops(teamID, existingDrops)

    def undropTemplates(self, order):
        templateNames = order['orders'][2:]
        teamID, existingDrops = self.getExistingDrops(order)
        for templateName in templateNames:
            temp = self.findMatchingTemplate(templateName)
            if (temp is not None and temp in existingDrops):
                existingDrops.remove(temp)
        self.updateTeamDrops(teamID, existingDrops)

    def toggleActivity(self, order, setTo):
        author = int(order['author'])
        if author not in self.mods:
            raise ImproperInput("Only mods can toggle template active status")
        tempName = order['orders'][1]
        self.templates.updateMatchingEntities({'Name': {'value': tempName,
                                                        'type': 'positive'}},
                                              {'Active': setTo})

    def activateTemplate(self, order):
        self.toggleActivity(order, 'TRUE')

    def deactivateTemplate(self, order):
        if self.templateSize <= self.minTemplates:
            raise ImproperInput("Not enough active templates to deactivate")
        self.toggleActivity(order, 'FALSE')

    @property
    def allTeams(self):
        return self.getExtantEntities(self.teams)

    def getPlayersFromOrder(self, order):
        author = int(order['author'])
        if (author in self.mods and len(order['orders']) > 1):
            return set(order['orders'][1:])
        return set([str(author),])

    def updateConfirms(self, teamID, confirms, identifier='ID'):
        confirms = (self.SEP_CONF).join([str(c).upper() for c in confirms])
        self.updateEntityValue(self.teams, teamID, identifier=identifier,
                               Confirmations=confirms)

    def quitLeague(self, order):
        players = self.getPlayersFromOrder(order)
        for team in self.allTeams:
            members = team['Players'].split(self.SEP_PLYR)
            confirms = team['Confirmations'].split(self.SEP_CONF)
            for player in players:
                if player in members:
                    index = members.index(player)
                    confirms[index] = "FALSE"
            self.updateConfirms(team['ID'], confirms)

    @runPhase
    def executeOrders(self):
        self.setCurrentID()
        for order in self.orders:
            orderType = order['type'].lower()
            try:
                {self.ORD_ADD_TEAM: self.addTeam,
                 self.ORD_CONFIRM_TEAM: self.confirmTeam,
                 self.ORD_UNCONFIRM_TEAM: self.unconfirmTeam,
                 self.ORD_SET_LIMIT: self.setLimit,
                 self.ORD_REMOVE_TEAM: self.removeTeam,
                 self.ORD_DROP_TEMPLATE: self.dropTemplates,
                 self.ORD_UNDROP_TEMPLATE: self.undropTemplates,
                 self.ORD_DROP_TEMPLATES: self.dropTemplates,
                 self.ORD_UNDROP_TEMPLATES: self.undropTemplates,
                 self.ORD_ACTIVATE_TEMPLATE: self.activateTemplate,
                 self.ORD_DEACTIVATE_TEMPLATE: self.deactivateTemplate,
                 self.ORD_QUIT_LEAGUE: self.quitLeague
                }[orderType](order)
            except Exception as e:
                if len(str(e)) > 0:
                    self.parent.log(str(e), self.name)
                else:
                    self.logFailedOrder(order)
        self.updateRanks()

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
        return self.findMatchingPlayers(players, 'Invited', 'Declined')

    def handleFinished(self, gameData):
        if self.isAbandoned(gameData['players']):
            return 'ABANDONED', None, None
        else:
            return 'FINISHED', self.findWinners(gameData['players'])

    def handleWaiting(self, gameData, created):
        decliners = self.findDecliners(gameData['players'])
        if len(decliners) > 0:
            if len(decliners) == len(gameData['players']):
                return 'ABANDONED', None
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

    @staticmethod
    def fetchDataByID(table, ID, itemType):
        nonexStr = "Nonexistent %s: %s" % (str(itemType), str(ID))
        data = table.findEntities({'ID': {'value': ID,
                                          'type': 'positive'}})
        if len(data) == 0: raise NonexistentItem(nonexStr)
        return data[0]

    def fetchGameData(self, gameID):
        return self.fetchDataByID(self.games, gameID, "game")

    def fetchTeamData(self, teamID):
        return self.fetchDataByID(self.teams, teamID, "team")

    def fetchTemplateData(self, templateID):
        return self.fetchDataByID(self.templates, templateID, "template")

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

    def setWinners(self, gameID, winningSide):
        sortedWinners = sorted(team for team in winningSide)
        winStr = (self.SEP_TEAMS).join(str(team) for team in sortedWinners)
        self.games.updateMatchingEntities({'ID': {'value': gameID,
                                                  'type': 'positive'}},
                                          {'Winners': winStr})

    def adjustTeamGameCount(self, teamID, adj, totalAdj=0):
        teamData = self.fetchTeamData(teamID)
        oldCount = int(teamData['Count'])
        oldFin = int(teamData['Finished'])
        self.teams.updateMatchingEntities({'ID': {'value': teamID,
                                                  'type': 'positive'}},
                                          {'Count': str(oldCount + adj),
                                           'Finished': str(oldFin + totalAdj)})

    def adjustTemplateGameCount(self, templateID, adj):
        oldCount = int(self.fetchTemplateData(templateID)['Games'])
        self.templates.updateMatchingEntities({'ID': {'value': templateID,
                                                      'type': 'positive'}},
                                              {'Games': str(oldCount + adj)})

    def getEloDiff(self, rating, events):
        oldRating = rating
        rating = self.eloEnv.Rate(oldRating, events)
        diff = int(round((rating - oldRating) / len(events)))
        return diff

    def getEloRating(self, teamID):
        return int(self.getTeamRating(teamID))

    def getSideEloRating(self, side):
        rating = 0
        for team in side:
            rating += self.getEloRating(team)
        return rating

    def makeOpps(self, sides, i, winningSide):
        opps = list()
        for j in xrange(len(sides)):
            if i == j: continue
            other = sides[j]
            otherRtg = self.getSideEloRating(other)
            event = self.getEvent(i, j, winningSide)
            opps.append((event, otherRtg))
        return opps

    @staticmethod
    def applyEloDiff(side, diff, diffs):
        for team in side: diffs[team] = diff

    def getNewEloRatings(self, sides, winningSide):
        results, diffs = dict(), dict()
        for i in xrange(len(sides)):
            side = sides[i]
            sideRtg = self.getSideEloRating(side)
            opps = self.makeOpps(sides, i, winningSide)
            diff = self.getEloDiff(sideRtg, opps)
            self.applyEloDiff(side, diff, diffs)
        for side in sides:
            for team in side:
                results[team] = str(self.getEloRating(team) +
                                    int(round(diffs[team])))
        return results

    @staticmethod
    def getSplitRtg(dataDict, key):
        return [int(v) for v in dataDict[key].split(self.SEP_RTG)]

    @classmethod
    def unsplitRtg(cls, rating):
        return (cls.SEP_RTG).join([str(val) for val in rating])

    def getGlickoRating(self, teamID):
        return tuple([int(x) for x in
                     self.getTeamRating(teamID).split(self.SEP_RTG)])

    def getSideGlickoRating(self, side):
        rating, dev = 0, 0
        for team in side:
            glicko = self.getGlickoRating(team)
            rating, dev = (rating + glicko[0], dev + glicko[1])
        return rating, dev

    @staticmethod
    def getEvent(i, j, winner, WIN=1, LOSS=0, DRAW=0.5):
        if i == winner: return WIN
        elif j == winner: return LOSS
        else: return DRAW

    def updateGlickoMatchup(self, players, i, j, winner):
        side1, side2 = players[i], players[j]
        side1.update_player([side2.rating], [side2.rd],
                            [self.getEvent(i, j, winner)])
        side2.update_player([side1.rating], [side1.rd],
                            [self.getEvent(j, i, winner)])

    def makeGlickoPlayersFromSides(self, sides):
        players = list()
        for side in sides:
            sideRtg, sideRd = self.getSideGlickoRating(side)
            sidePlayer = Player(rating=sideRtg, rd=sideRd)
            players.append(sidePlayer)
        return players

    def updateGlickoMatchups(self, sides, players, winningSide):
        for i in xrange(len(sides)):
            for j in xrange(len(sides[(i+1):])):
                self.updateGlickoMatchup(players, i, j, winningSide)

    def getGlickoResultsFromPlayers(self, sides, players):
        results = dict()
        for i in xrange(len(sides)):
            newRtg, newRd = players[i].rating, players[i].rd
            oldRtg, oldRd = self.getSideGlickoRating(side)
            rtgDiff, rdDiff = float(newRtg - oldRtg), float(newRd - oldRd)
            rtgDiff = (rtgDiff / ((len(sides) - 1) * self.sideSize))
            rdDiff /= (rdDiff / ((len(sides) - 1) * self.sideSize))
            for team in sides[i]:
                origRtg, origRd = self.getGlickoRating(team)
                rtg = origRtg + int(round(rtgDiff))
                rd = origRd + int(round(rdDiff))
                results[team] = (self.SEP_RTG).join([str(rtg), str(rd)])
        return results

    def getNewGlickoRatings(self, sides, winningSide):
        players = self.makeGlickoPlayersFromSides(sides)
        self.updateGlickoMatchups(sides, players, winningSide)
        return self.getGlickoResultsFromPlayers(sides, players)

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
                results[team] = self.unsplitRtg([side[team].mu,
                                                 side[team].sigma])
        return results

    def getNewWinCounts(self, sides, winningSide):
        results = dict()
        winningTeams = sides[winningSide]
        for team in winningTeams:
            count = self.getTeamRating(team)
            count = str(int(count) + 1)
            results[team] = count
        return results

    def getWinRate(self, team):
        rating = self.getTeamRating(team)
        winRate, numGames = rating.split(self.SEP_RTG)
        winRate = float(winRate)
        numGames = int(numGames)
        return winRate, numGames

    def getNewWinRates(self, sides, winningSide):
        results = dict()
        for i in xrange(len(sides)):
            side = sides[i]
            for team in side:
                winRate, numGames = self.getWinRate(team)
                estimatedWins = (Decimal(numGames) * (Decimal(winRate)
                                 / Decimal(self.WINRATE_SCALE)))
                if i == winningSide:
                    estimatedWins += Decimal(1)
                numGames += 1
                newRate = round(float(estimatedWins / Decimal(numGames)), 3)
                newRate = int(Decimal(newRate) * Decimal(self.WINRATE_SCALE))
                results[team] = self.unsplitRtg([newRate, numGames])
        return results

    def getNewRatings(self, sides, winningSide):
        """
        :param sides: list[set[string]]
        :param winningSide: int (index of winning side)
        """
        return self.sysDict[self.ratingSystem]['update'](sides, winningSide)

    @staticmethod
    def updateEntityValue(table, ID, identifier='ID', **values):
        table.updateMatchingEntities({identifier: {'value': ID,
                                                   'type': 'positive'}},
                                     values)

    def updateTeamRating(self, teamID, rating):
        self.updateEntityValue(self.teams, teamID, Rating=rating)

    def updateRatings(self, newRatings):
        for team in newRatings:
            self.updateTeamRating(team, newRatings[team])

    def finishGameForTeams(self, sides):
        for side in sides:
            for team in side:
                self.adjustTeamGameCount(team, -1, 1)

    def updateResults(self, gameID, sides, winningSide):
        self.setWinners(gameID, sides[winningSide])
        newRatings = self.getNewRatings(sides, winningSide)
        self.updateRatings(newRatings)
        self.finishGameForTeams(sides)

    def updateWinners(self, gameID, winners):
        sides = self.getGameSides(gameID)
        winningTeams = self.findCorrespondingTeams(gameID, winners)
        for i in xrange(len(sides)):
            side = sides[i]
            if len(side & winningTeams) > 0:
                winningSide = i
                break
        self.updateResults(gameID, sides, winningSide)

    def handleSpecialDeclines(self, losingTeams, template):
        if self.countDeclinesAsVetos:
            self.updateGameVetos(losingTeams, template)
        if self.removeDeclines:
            for team in losingTeams:
                self.changeLimit(team, 0)

    @staticmethod
    def makeFakeSides(sides, losingTeams):
        winningSide, results, winningTeams = None, [losingTeams,], set()
        for side in sides:
            for team in side:
                if team not in losingTeams: winningTeams.add(team)
        if len(winningTeams) > 0:
            results.append(winningTeams)
            winningSide = (len(results) - 1)
        return results, winningSide

    def updateDecline(self, gameID, decliners):
        sides = self.getGameSides(gameID)
        losingTeams = self.findCorrespondingTeams(gameID, decliners)
        template = str(self.fetchGameData(gameID)['Template'])
        self.handleSpecialDeclines(losingTeams, template)
        sides, winningSide = self.makeFakeSides(sides, losingTeams)
        if winningSide == None: self.updateVeto(gameID)
        self.updateResults(gameID, sides, winningSide)

    def deleteGame(self, gameID, gameData):
        self.games.removeMatchingEntities({'ID': {'value': gameID,
                                                  'type': 'positive'}})
        sides = self.getGameSidesFromData(gameData)
        self.finishGameForTeams(sides)

    def getGameSidesFromData(self, gameData):
        results = list()
        sides = gameData['Sides'].split(self.SEP_SIDES)
        for side in sides:
            results.append(set(side.split(self.SEP_TEAMS)))
        return results

    def getGameSides(self, gameID):
        gameData = self.fetchGameData(gameID)
        return self.getGameSidesFromData(gameData)

    def getTeamRating(self, team, getDefault=True):
        searchDict = {'ID': {'value': team, 'type': 'positive'}}
        if len(searchDict) < 1:
            if getDefault:
                return self.defaultRating
            raise NonexistentItem("Nonexistent team: %s" % (str(team)))
        return self.teams.findEntities(searchDict)[0]['Rating']

    def adjustRating(self, team, adjustment):
        oldRating = self.getTeamRating(team)
        newRating = oldRating.split(self.SEP_RTG)
        newRating[0] = str(int(newRating[0]) + adjustment)
        newRating = (self.SEP_RTG).join(newRating)
        self.teams.updateMatchingEntities({'ID': {'value': team,
                                                  'type': 'positive'}},
                                          {'Rating': newRating})

    def penalizeVeto(self, gameID):
        teams = self.getGameTeams(gameID)
        for team in teams:
            self.adjustRating(team, -self.vetoPenalty)

    def vetoCurrentTemplate(self, gameData):
        vetos = gameData['Vetoed'] + self.SEP_VETOS + str(gameData['Template'])
        if vetos[0] == self.SEP_VETOS: vetos = vetos[1:]
        vetoCount = int(gameData['Vetos']) + 1
        self.updateEntityValue(self.games, gameData['ID'], Vetoed=vetos,
                               Vetos=vetoCount, Template='')
        self.adjustTemplateGameCount(gameData['Template'], -1)

    def setGameTemplate(self, gameID, tempID):
        self.updateEntityValue(self.games, gameID, Template=tempID)

    def getTeamPlayers(self, team):
        teamData = self.fetchTeamData(team)
        return [int(p) for p in teamData.split(self.SEP_PLYR)]

    def getSidePlayers(self, side):
        players = list()
        for team in side:
            players += self.getTeamPlayers(team)
        return players

    def assembleTeams(self, gameData):
        teams = list()
        sides = gameData['Sides'].split(self.SEP_SIDES)
        for side in sides:
            teams.append(tuple(self.getSidePlayers(side)))
        return teams

    def getTeamName(self, teamID):
        teamData = self.fetchTeamData(teamID)
        return teamData['Name']

    def getNameInfo(self, side):
        nameInfo, MAX_NAME_LEN = list(), 10
        for team in side.split(self.SEP_TEAMS):
            nameInfo.append("+")
            teamName = self.fitToMaxLen(self.getTeamName(team), MAX_NAME_LEN)
            nameInfo.append(teamName)
        return nameInfo

    @staticmethod
    def fitToMaxLen(val, maxLen, replace="..."):
        repLen = len(replace)
        if len(val) > maxLen:
            if val[maxLen-repLen:maxLen] != replace:
                return val[:maxLen-repLen] + replace
            return val[:maxLen]
        return val

    def getGameName(self, gameData):
        MAX_DISPLAY_LEN = 50
        start = self.leagueAcronym + " | "
        nameData = list()
        for side in gameData['Sides'].split(self.SEP_SIDES):
            nameData.append(" vs ")
            nameInfo = self.getNameInfo(side)
            nameData += nameInfo[1:]
        name = self.fitToMaxLen((start + "".join(nameData[1:])),
                                MAX_DISPLAY_LEN)
        return name

    @staticmethod
    def getPrettyEloRating(rating):
        return rating

    def getPrettyGlickoRating(self, rating):
        return rating.split(self.SEP_RTG)[0]

    def getPrettyTrueSkillRating(self, rating):
        mu, sigma = [int(i) for i in rating.split(self.SEP_RTG)]
        return str(mu - 3 * sigma)

    def prettifyRating(self, rating):
        return self.sysDict[self.ratingSystem]['prettify'](rating)

    def getPrettyRating(self, team):
        teamRating = self.getTeamRating(team)
        return self.prettifyRating(teamRating)

    def getOfficialRating(self, team):
        return int(self.getPrettyRating(team))

    def getTeamRank(self, team):
        teamData = self.fetchTeamData(team)
        return int(teamData['Rank'])

    def sideInfo(self, gameData):
        infoData = list()
        sides = gameData['Sides']
        for side in sides.split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                infoData.append('\n')
                teamRating = self.getPrettyRating(team)
                teamData = self.fetchTeamData(team)
                teamRank = teamData['Rank']
                teamName = teamData['Name']
                if teamRank is '':
                    teamStr = "%s, not ranked with rating %s" % (teamName,
                                                                 teamRating)
                else:
                    teamStr = "%s, with rank %d and rating %s" % (teamName,
                                                                  teamRank,
                                                                  teamRating)
                infoData.append(teamStr)
        infoStr = "".join(infoData[1:])
        return infoStr

    @staticmethod
    def makeThread(thread):
        if '/Forum/' in str(thread): return thread
        return ('https://www.warlight.net/Forum/' + str(thread))

    def getTemplateName(self, gameData):
        templateID = gameData['Template']
        tempData = self.fetchTemplateData(templateID)
        return tempData['Name']

    def processMessage(self, message, gameData):
        replaceDict = {'_LEAGUE_NAME': self.name,
                       self.SET_SUPER_NAME: self.clusterName,
                       self.SET_URL: self.leagueUrl,
                       self.SET_VETO_LIMIT: self.vetoLimit,
                       '_VETOS': gameData['Vetos'],
                       '_LEAGUE_THREAD': self.makeThread(self.thread),
                       '_GAME_SIDES': self.sideInfo(gameData),
                       '_TEMPLATENAME': self.getTemplateName(gameData)}
        for val in replaceDict:
            checkStr = "{{%s}}" % val
            if checkStr in message:
                message = message.replace(checkStr, str(replaceDict[val]))
        return message

    def getGameMessage(self, gameData):
        MAX_MESSAGE_LEN = 2048
        msg = self.processMessage(self.leagueMessage, gameData)
        return msg[:MAX_MESSAGE_LEN]

    def getAllGameTeams(self, gameData):
        allTeams = list()
        for side in gameData['Sides'].split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                allTeams.append(team)
        return allTeams

    @staticmethod
    def getOtherTeams(teams, team):
        return [t for t in teams if t != team]

    def updateTeamHistory(self, team, others):
        oldHistory = self.fetchTeamData(team)['History']
        newStr = (self.SEP_TEAMS).join(others)
        newHistory = (oldHistory + (self.SEP_TEAMS if len(oldHistory) else "")
                      + newStr)
        self.updateEntityValue(self.teams, team, History=newHistory)

    def updateHistories(self, gameData):
        allTeams = self.getAllGameTeams(gameData)
        for team in allTeams:
            otherTeams = self.getOtherTeams(allTeams, team)
            self.updateTeamHistory(team, otherTeams)

    def getTempSettings(self, tempID):
        tempData = self.fetchTemplateData(tempID)
        template = tempData['WarlightID']
        settingsDict, checkLen = dict(), len(self.TEMPSETTING)
        for head in tempData:
            if self.TEMPSETTING == head[:checkLen]:
                settingName = head[checkLen:]
                if (settingName.count(self.SEP_TEMPSET) == 1):
                    settingName, sVal = settingName.split(self.SEP_TEMPSET)
                    if settingName not in settingsDict:
                        settingsDict[settingName] = dict()
                    settingsDict[settingName][sVal] = tempData[head]
                else:
                    settingsDict[settingName] = tempData[head]
        return template, settingsDict

    def createGame(self, gameID):
        gameData = self.fetchGameData(gameID)
        temp = int(gameData['Template'])
        tempID, tempSettings = self.getTempSettings(temp)
        teams = assembleTeams(gameData)
        try:
            wlID = self.handler.createGame(tempID, self.getGameName(gameData),
                       teams, settingsDict=tempSettings,
                       message=self.getGameMessage(gameData))
            self.adjustTemplateGameCount(temp, 1)
            createdStr = datetime.strftime(datetime.now(), self.TIMEFORMAT)
            self.games.updateMatchingEntities({'ID': {'value': gameID,
                                                      'type': 'positive'}},
                                              {'WarlightID': wlID,
                                               'Created': createdStr})
            return gameData
        except Exception as e:
            sides = gameData['Sides']
            self.parent.log("Failed to make game with %s on %d because of %s" %
                            (sides, temp, str(e)), self.name)
            self.games.removeMatchingEntities({'ID': {'value': gameID,
                                                      'type': 'positive'}})

    def makeGame(self, gameID):
        gameData = self.createGame(gameID)
        for side in gameData['Sides'].split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                self.adjustTeamGameCount(team, 1)
        self.updateHistories(gameData)

    def getGameVetos(self, gameData):
        vetos = set([v for v in gameData['Vetoed'].split(self.SEP_TEMP)])
        for side in gameData['sides'].split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                teamData = self.fetchTeamData(team)
                self.updateConflicts(teamData, vetos)
        return set(int(v) for v in vetos)

    def updateTemplate(self, gameID, gameData):
        vetos, ranks, i = self.getGameVetos(gameData), self.templateRanks, 0
        while (i < len(ranks) and ranks[i][0] in vetos): i += 1
        if i < len(ranks):
            newTemp = ranks[i][0]
            self.setGameTemplate(gameID, newTemp)
            self.createGame(gameID)
        else:
            self.deleteGame(gameID, gameData)

    def getVetoDict(self, vetos):
        results = dict()
        for temp in vetos.split(self.SEP_VETOS):
            tempID, vetoCt = temp.split(self.SEP_VETOCT)
            results[tempID] = int(vetoCt)
        return results

    def getTeamVetoDict(self, teamID):
        teamData = self.fetchTeamData(teamID)
        return self.getVetoDict(teamData['Vetos'])

    def packageVetoDict(self, vetoDict):
        tempData = [(str(temp) + self.SEP_VETOCT + str(vetoDict[temp]))
                    for temp in vetoDict]
        return (self.SEP_VETOS).join(tempData)

    def updateVetoCt(self, oldVetos, template, adj):
        vetoDict = self.getVetoDict(oldVetos)
        vetoDict[str(template)] += int(adj)
        return self.packageVetoDict(vetoDict)

    def updateTeamVetos(self, team, template, adj):
        teamData = self.fetchTeamData(team)
        oldVetos = teamData['Vetos']
        if str(template) not in oldVetos:
            newVetos = (oldVetos + self.SEP_VETOS + str(template) +
                        self.SEP_VETOCT + str(adj))
            if len(oldVetos) == 0:
                newVetos = newVetos[1:]
        else:
            newVetos = self.updateVetoCt(oldVetos, template, adj)
        self.updateEntityValue(self.teams, team, Vetos=newVetos)

    def updateGameVetos(self, teams, template):
        for team in teams: self.updateTeamVetos(team, template, 1)

    @classmethod
    def getTeams(cls, gameData):
        results = set()
        sides = gameData['Sides'].split(cls.SEP_SIDES)
        for side in sides:
            teams = side.split(cls.SEP_TEAMS)
            for team in teams:
                results.add(int(team))
        return results

    def updateVeto(self, gameID):
        gameData = self.fetchGameData(gameID)
        if int(gameData['Vetoes']) >= self.vetoLimit:
            self.penalizeVeto(gameID)
            self.deleteGame(gameID, gameData)
        else:
            template = gameData['Template']
            self.vetoCurrentTemplate(gameData)
            self.updateGameVetos(self.getTeams(gameData), template)
            self.updateTemplate(gameID, gameData)

    def updateGame(self, warlightID, gameID, createdTime):
        created = datetime.strptime(createdTime, self.TIMEFORMAT)
        status = self.fetchGameStatus(warlightID, created)
        {'FINISHED': self.updateWinners(gameID, status[1]),
         'DECLINED': self.updateDecline(gameID, status[1]),
         'ABANDONED': self.updateVeto(gameID)}.get([status[0]])

    def wipeRank(self, teamID):
        self.updateEntityValue(self.teams, teamID, Rank='')

    def eligibleForRank(self, teamData):
        return (int(teamData['Finished']) >= self.minToRank and
                int(teamData['Limit']) >= self.minLimitToRank)

    @staticmethod
    def hasRank(teamData):
        return (teamData['Rank'] is not '')

    def rankUsingRatings(self, teamRatings):
        teamRatings.sort(key = lambda x: x[1]) # sort using ratings
        teamRatings.reverse()
        rank, previous, offset = 0, None, 0
        for team in teamRatings:
            teamID, teamRtg = team
            if teamRtg != previous:
                previous = teamRtg
                rank += offset + 1
            else: offset += 1
            self.updateEntityValue(self.teams, teamID, Rank=rank)

    def updateRanks(self):
        teamRatings = list()
        for team in self.allTeams:
            if self.eligibleForRank(team):
                teamRatings.append((team['ID'],
                                    self.getOfficialRating(team['ID'])))
            elif self.hasRank(team): self.wipeRank(team['ID'])
        self.rankUsingRatings(teamRatings)

    @runPhase
    def updateGames(self):
        gamesToCheck = self.unfinishedGames
        for game in gamesToCheck:
            try:
                self.updateGame(game, gamesToCheck[game]['ID'],
                                gamesToCheck[game]['Created'])
            except (SheetErrors.SheetError, SheetErrors.DataError):
                self.parent.log("Failed to update game: " + str(game),
                                league=self.name, error=False)

    def checkExcess(self, playerCount):
        if self.teamLimit is None: return False
        return (playerCount > teamLimit)

    def changeLimit(self, teamID, limit):
        self.updateEntityValue(self.teams, teamID, Limit=limit)

    @staticmethod
    def updatePlayerCounts(playerCounts, players):
        for player in players:
            if player not in playerCounts:
                playerCounts[player] = 0
            playerCounts[player] += 1

    def setProbation(self, teamID, start=None):
        if start is None: probStr = ''
        else: probStr = datetime.strftime(start, self.TIMEFORMAT)
        self.teams.updateMatchingEntities({'ID': {'value': teamID,
                                                  'type': 'positive'}},
                                          {'Probation Start': probStr})

    def wipeProbation(self, teamID):
        self.setProbation(teamID)

    def startProbation(self, teamID):
        self.setProbation(teamID, datetime.now())

    def meetsRetention(self, teamData):
        teamFinished = int(teamData['Finished'])
        teamRating = int(self.prettifyRating(teamData['Rating']))
        teamRank = int(teamData['Rank'])
        return (teamFinished < self.minToCull or
                (self.valueInRange(teamRating, self.minRating, None) and
                 self.valueInRange(teamRank, None, self.maxRank)))

    def checkTeamRating(self, teamID):
        teamData = self.fetchTeamData(teamID)
        start = teamData['Probation Start']
        if self.meetsRetention(teamData):
            if len(start) > 0: self.wipeProbation(teamID)
        elif len(start) == 0:
            self.startProbation(teamID)
        else: # already on probation
            start = datetime.strptime(start, self.TIMEFORMAT)
            if (datetime.now() - start).days >= self.gracePeriod:
                raise ImproperInput("Team %s has been culled" % (str(teamID)))

    def validateTeam(self, teamID, players):
        try:
            self.checkTeamRating(teamID)
            self.checkTeam(players, teamID)
            return False
        except ImproperInput as e:
            self.parent.log(("Removing %s because: %s" % (str(teamID),
                             e.message)), self.name)
            self.changeLimit(teamID, 0)
            return True

    def validatePlayer(self, playerCounts, players):
        for player in players:
            if player not in playerCounts: continue
            if playerCounts[player] >= self.teamLimit:
                self.changeLimit(team['ID'], 0)
                return True
        return False

    @runPhase
    def validatePlayers(self):
        playerCounts, allTeams = dict(), self.allTeams
        for i in xrange(len(allTeams)):
            team, dropped = allTeams[i], False
            confirmations = team['Confirmations']
            limit = int(team['Limit'])
            if ('FALSE' in confirmations or limit < 1): continue
            players = allTeams[team]['Players'].split(self.SEP_PLYR)
            dropped = self.validateTeam(team['ID'], players)
            dropped = self.validatePlayer(playerCounts, players)
            if not dropped:
                self.updatePlayerCounts(playerCounts, players)

    @classmethod
    def splitRating(cls, rating):
        return [int(x) for x in rating.split(self.SEP_RTG)]

    def updateSums(self, rating, sums):
        splitRtg = self.getSplitRating(rating)
        for i in xrange(len(splitRtg)):
            if i >= len(sums): sums.append(splitRtg[i])
            else: sums[i] += splitRtg[i]

    def addRatings(self, ratings):
        sums = list()
        for rating in ratings: self.updateSums(rating, sums)
        return (self.SEP_RTG).join(str(x) for x in sums)

    def getEloPairingParity(self, rtg1, rtg2):
        return self.eloEnv.quality_1vs1(rtg1, rtg2)

    def getEloParity(self, ratings):
        rtgs = [int(rating) for rating in ratings]
        return self.getAverageParity(rtgs, self.getEloPairingParity)

    @staticmethod
    def getAverageParity(ratings, parityFn):
        matchups = len(ratings) * float(len(ratings) - 1)
        paritySum = 0.0
        for i in xrange(len(ratings)):
            rtg1 = ratings[i]
            for j in xrange(len(ratings[(i+1):])):
                rtg2 = ratings[j]
                paritySum += parityFn(rtg1, rtg2)
        return min((paritySum / matchups), 1.0)

    @staticmethod
    def getGlickoPairingParity(rtg1, rtg2):
        rating1, rd1 = rtg1
        rating2, rd2 = rtg2
        LN10 = math.log(10, math.e)
        glickoP = ((3 * (LN10 ** 2)) / ((math.pi ** 2) * (400 ** 2)))
        glickoF = lambda rd: 1.0 / math.sqrt(1 + glickoP * rd ** 2)
        glickoE = lambda r1, s1, r2, s2: (1.0 / (1.0 + 10 ** (-(r1 - r2) *
                  glickoF(math.sqrt(s1 ** 2 + s2 ** 2)) / 400)))
        odds = glickoE(rating1, rd1, rating2, rd2)
        shortfall = abs(0.5 - odds)
        return (1.0 - (shortfall * 2))

    def getGlickoParity(self, ratings):
        rtgs = [tuple(int(r) for r in rating.split(self.SEP_RTG))
                for rating in ratings]
        return self.getAverageParity(rtgs, self.getGlickoPairingParity)

    def getTrueSkillParity(self, ratings):
        rtgs = [rating.split(self.SEP_RTG) for rating in ratings]
        players = [tuple(self.trueSkillEnv.create_rating(int(rtg[0]),
                   int(rtg[1])),) for rtg in rtgs]
        return self.trueSkillEnv.quality(players)

    @staticmethod
    def getVarianceScore(vals):
        average = Decimal(sum(vals)) / Decimal(len(vals))
        variance = Decimal(0)
        for val in vals:
            variance += ((Decimal(val) - Decimal(average)) ** 2)
        sd = math.sqrt(float(variance))
        score = max(1.0, (sd / float(average)))
        return (1.0 - score)

    def getWinCountParity(self, ratings):
        winCounts = [int(r) for r in ratings]
        return self.getVarianceScore(winCounts)

    def getWinRateParity(self, ratings):
        winRates = [int(r.split(self.SEP_RTG)[0]) for r in ratings]
        return self.getVarianceScore(winRates)

    def getParityScore(self, ratings):
        """
        given two ratings, returns a score from 0.0 to 1.0
        representing the preferability of the pairing
        """
        return self.sysDict[self.ratingSystem]['parity'](ratings)

    @classmethod
    def getPlayers(cls, team):
        players = team['Players'].split(cls.SEP_PLYR)
        players = [int(p) for p in players]
        return players

    @classmethod
    def getHistory(cls, team):
        history = team['History'].split(cls.SEP_TEAMS)
        return [int(t) for t in history]

    @staticmethod
    def addToSetWithinDict(data, label, value):
        if label not in data:
            data[label] = set()
        data[label].add(value)

    def makePlayersDict(self, teams):
        result = dict()
        for team in teams:
            players = self.getPlayers(team)
            ID = int(team['ID'])
            for player in players:
                self.addToSetWithinDict(result, player, ID)
        return result

    @property
    def teamsDict(self):
        result, allTeams = dict(), self.activeTeams
        playersDict = self.makePlayersDict(allTeams)
        for team in allTeams:
            if ('FALSE' in team['Confirmations']): continue
            teamDict = {'rating': team['Rating'],
                        'count': max(0,
                                 (int(team['Limit']) - int(team['Count'])))}
            conflicts = set()
            ID = int(team['ID'])
            players = self.getPlayers(team)
            for player in players:
                conflicts = conflicts.union(playersDict[player])
            fullHistory = self.getHistory(team)
            if self.rematchLimit == self.KW_ALL:
                history = fullHistory
            else:
                history = fullHistory[-(self.rematchLimit):]
            conflicts = conflicts.union(set(history))
            teamDict['conflicts'] = conflicts
            result[ID] = teamDict
        return result

    def makeGrouping(self, groupingDict, groupSize, groupSep):
        if self.reverseParity:
            score_fn = lambda *args: 1.0 - self.getParityScore(args)
        else:
            score_fn = lambda *args: self.getParityScore(args)
        groups = group_teams(groupingDict, score_fn=score_fn,
                             game_size=self.groupSize)
        return {groupSep.join([str(x) for x in group])
                for group in groups}

    def makeSides(self, teamsDict):
        return self.makeGrouping(teamsDict, self.sideSize, self.SEP_TEAMS)

    def getSideRating(self, side, teamsDict):
        teams = side.split(self.SEP_TEAMS)
        ratings = [teamsDict[int(team)]['rating']
                   for team in teams.split(self.SEP_TEAMS)]
        return self.addRatings(ratings)

    def makeTeamsToSides(self, sides):
        result = dict()
        for side in sides:
            teams = side.split(self.SEP_TEAMS)
            for team in teams: self.addToSetWithinDict(result, team, side)
        return result

    def getSideConflicts(self, side, teamsDict, teamsToSides):
        teams = side.split(self.SEP_TEAMS)
        conflicts = set()
        for team in teams:
            teamConflicts = teamsDict[team]['conflicts'].union({int(team),})
            for conflict in teamConflicts:
                for conflictingSide in teamsToSides.get(conflict, set()):
                    conflicts.add(conflictingSide)
        return conflicts

    def makeSidesDict(self, sides, teamsDict):
        result, teamsToSides = dict(), self.makeTeamsToSides(sides)
        for side in sides:
            sideDict = {'rating': self.getSideRating(side, teamsDict),
                        'conflicts': self.getSideConflicts(side, teamsDict,
                                                           teamsToSides),
                        'count': 1}
            result[side] = sideDict
        return result

    def makeMatchings(self, sidesDict):
        return self.makeGrouping(sidesDict, self.gameSize, self.SEP_SIDES)

    @staticmethod
    def turnNoneIntoMutable(val, mutable):
        if val is None: return mutable()
        return val

    @staticmethod
    def getTemplatesList(templateIDs, skipTemps, times, mod):
        templatesList = [temp for temp in templateIDs if temp not in skipTemps]
        templatesList.sort(key = lambda x: templateIDs[x]['Games'])
        templatesList = (templatesList * times) + templatesList[:mod]
        return templatesList

    def makeTemplatesDict(self, gameCount, skipTemps=None):
        self.turnNoneIntoMutable(skipTemps, set)
        templateIDs, result = self.templateIDs, dict()
        times, mod = gameCount / len(templateIDs), gameCount % len(templateIDs)
        templatesList = self.getTemplatesList(templateIDs, skipTemps,
                                              times, mod)
        for temp in templatesList:
            if temp not in result: result[temp] = {'count': 1}
            else: result[temp]['count'] += 1
        return result

    def updateScores(self, teamData, scores):
        vetos = teamData['Vetos'].split(self.SEP_VETOS)
        for veto in vetos:
            if veto not in scores: scores[veto] = 1
            else: scores[veto] += 1

    def updateConflicts(self, teamData, conflicts):
        drops = teamData['Drops'].split(self.SEP_DROPS)
        for drop in drops: conflicts.add(drop)

    def getScoresAndConflicts(self, matching):
        scores, conflicts = dict(), set()
        sides = matching.split(self.SEP_SIDES)
        for side in sides:
            teams = side.split(self.SEP_TEAMS)
            for team in teams:
                teamData = self.fetchTeamData(team)
                self.updateScores(teamData, scores)
                self.updateConflicts(teamData, conflicts)
        return scores, conflicts

    def makeMatchingsDict(self, matchings):
        result, numTemps = dict(), len(self.templateIDs)
        for matching in matchings:
            matchDict = {'count': 1}
            scores, conflicts = self.getScoresAndConflicts(matching)
            if (len(conflicts) == numTemps): continue
            matchDict['scores'] = scores
            matchDict['conflicts'] = conflicts
            result[matching] = matchDict
        return result

    @staticmethod
    def getUniversalConflicts(matchingsDict):
        conflicts = None
        for matching in matchingsDict:
            tempConf = matchingsDict[matching]['conflicts']
            if conflicts is None:
                conflicts = tempConf
            else:
                conflicts = conflicts.intersection(tempConf)
        return conflicts

    def makeBatch(self, matchings):
        gamesToCreate = len(matchings)
        matchingsDict = self.makeMatchingsDict(matchings)
        allConflicts = self.getUniversalConflicts(matchingsDict)
        templatesDict = self.makeTemplatesDict(gamesToCreate, allConflicts)
        unhandled, batch = copy.copy(matchings), list()
        while (len(unhandled) > 0):
            newMatchings = assign_templates(matchingsDict, templatesDict)
            for match in newMatchings:
                sides, temp = match
                if temp not in matchingsDict[sides]['conflicts']:
                    batch.append({'Sides': sides, 'Template': temp})
                    unhandled.remove(sides)
        return batch

    def createBatch(self, batch):
        currentID = max(int(ID) for ID in self.gameIDs) + 1
        for game in batch:
            try:
                self.games.addEntity({'ID': currentID, 'WarlightID': '',
                                      'Created': '', 'Winners': '',
                                      'Sides': game['Sides'], 'Vetos': 0,
                                      'Vetoed': '',
                                      'Template': game['Template']})
            except (SheetErrors.DataError, SheetErrors.SheetError) as e:
                self.parent.log(("Failed to add game to sheet due to %s" %
                                 str(e)), self.name, error=False)
            try:
                self.makeGame(currentID)
                currentID += 1
            except APIError as e:
                self.parent.log(("Failed to create game with ID %d" %
                                 (currentID)), self.name, error=False)

    @runPhase
    def createGames(self):
        teamsDict = self.teamsDict
        if self.sideSize > 1:
            sides = self.makeSides(teamsDict)
        else:
            sides = teamsDict
        sidesDict = self.makeSidesDict(sides, teamsDict)
        matchings = self.makeMatchings(sidesDict)
        batch = self.makeBatch(matchings)
        self.createBatch(batch)

    def run(self):
        """
        runs the league in four phases
        1. check on and update ongoing games
        2. execute orders from threads
        3. update teams using prereqs
        4. create new games
        """
        self.updateGames()
        self.executeOrders()
        self.validatePlayers()
        self.restoreTeams()
        if self.active:
            self.createGames()
