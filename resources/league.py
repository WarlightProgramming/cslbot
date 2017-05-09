#########################
# league.py
# handles a single league
#########################

# imports
import math
import time
import random
import pair
from threading import Lock
from decimal import Decimal
from elo import Elo
from glicko2.glicko2 import Player
from trueskill import TrueSkill
from datetime import datetime, timedelta, date
from wl_parsers import PlayerParser
from wl_api.wl_api import APIError
from sheetDB import errors as SheetErrors
from resources.constants import TIMEFORMAT, DEBUG_KEY, LATEST_RUN
from resources.utility import isInteger, WLHandler

# global locks
teamLock, tempLock = Lock(), Lock()

# decorators
def makeFailStr(func, err):
    return ("Call to %s failed due to %s" % (func.__name__, repr(err)))

def tryOrLog(func, self, reraise=False, *args, **kwargs):
    try:
        return func(self, *args, **kwargs)
    except Exception as e:
        self.parent.log(makeFailStr(func, e), self.name, True)
        if reraise: raise

def runPhase(func):
    """
    function decorator to log failures if phase fails
    """
    def func_wrapper(self, *args, **kwargs):
        return tryOrLog(func, self, False, *args, **kwargs)
    return func_wrapper

def noisy(func):
    """
    function decorator for handling debug mode
    """
    def func_wrapper(self, *args, **kwargs):
        if not self.debug: return func(self, *args, **kwargs)
        runStr = ("Calling method %s with args %s and kwargs %s" %
                  (func.__name__, str(args), str(kwargs)))
        self.parent.log(runStr, self.name, False)
        return tryOrLog(func, self, True, *args, **kwargs)
    return func_wrapper

def checkAgent(func):
    """
    function decorator to check order interface agents
    """
    def func_wrapper(self, order):
        if not self._agentAllowed(order['agent']):
            raise ImproperInput("Agent not authorized for this league")
        return func(self, order)
    return func_wrapper

# errors
class ImproperLeague(Exception):
    """raised for improperly formatted leagues"""
    pass

class ImproperInput(Exception):
    """raised for improperly formatted orders and commands"""
    pass

class NonexistentItem(Exception):
    """raises for nonexistent items"""
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
    ORD_ADD_TEMPLATE = "add_template"
    ORD_RENAME_TEAM = "rename_team"

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
    SET_EXP_THRESH = "ABANDON THRESHOLD"
    SET_VETO_LIMIT = "VETO LIMIT"
    SET_VETO_PENALTY = "VETO PENALTY"
    SET_ELO_K = "ELO K"
    SET_ELO_DEFAULT = "ELO DEFAULT"
    SET_GLICKO_RD = "GLICKO RD"
    SET_GLICKO_DEFAULT = "GLICKO DEFAULT"
    SET_TRUESKILL_SIGMA = "TRUESKILL SIGMA"
    SET_TRUESKILL_DEFAULT = "TRUESKILL MU"
    SET_DEFAULT_NONE = "DEFAULT RATING"
    SET_REVERSE_PARITY = "PREFER SKEWED MATCHUPS"
    SET_REVERSE_GROUPING = "PREFER SKEWED GROUPINGS"
    SET_LEAGUE_MESSAGE = "MESSAGE"
    SET_SUPER_NAME = "CLUSTER NAME"
    SET_LEAGUE_ACRONYM = "SHORT NAME"
    SET_URL = "URL"
    SET_MAX_TEAMS = "PLAYER TEAM LIMIT"
    SET_REMOVE_DECLINES = "REMOVE DECLINES"
    SET_REMOVE_BOOTS = "REMOVE BOOTED PLAYERS"
    SET_PENALIZE_DECLINES = "PENALIZE DECLINES"
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
    SET_MAX_LAST_SEEN = "MAX LAST SEEN" # hours
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
    SET_REMATCH_CAP = "REMATCH CAP"
    SET_RESTORATION_PERIOD = "RESTORATION PERIOD" # days
    SET_LEAGUE_CAPACITY = "MAX TEAMS"
    SET_ACTIVE_CAPACITY = "MAX ACTIVE TEAMS"
    SET_MIN_TO_CULL = "MIN GAMES TO CULL"
    SET_MIN_TO_RANK = "MIN GAMES TO RANK"
    SET_MAX_RANK = "MAX RANK"
    SET_MIN_LIMIT_TO_RANK = "MIN LIMIT TO RANK"
    SET_MAX_VACATION = "MAX VACATION LENGTH" # days
    SET_AUTODROP = "AUTODROP"
    SET_TEAMLESS = "TEAMLESS"
    SET_NAME_LENGTH = "MAX TEAM NAME LENGTH"
    SET_CONSTRAIN_NAME = "CONSTRAIN NAME LENGTH"
    SET_PRESERVE_RECORDS = "PRESERVE RECORDS"
    SET_MAINTAIN_TOTAL = "MAINTAIN RATING TOTAL"
    SET_RATING_DECAY = "INACTIVITY PENALTY" # per day
    SET_PENALTY_FLOOR = "PENALTY FLOOR"
    SET_RETENTION_RANGE = "EXPIRE GAMES AFTER" # days
    SET_FAVOR_NEW_TEMPLATES = "FAVOR NEW TEMPLATES"
    SET_REQUIRE_SAME_CLAN = "REQUIRE CONSISTENT CLAN FOR NEW TEAMS"
    SET_MAINTAIN_SAME_CLAN = "REQUIRE CONSISTENT CLAN FOR ALL TEAMS"
    SET_FORBID_CLAN_MATCHUPS = "AVOID SAME-CLAN MATCHUPS"
    SET_ONLY_MODS_CAN_ADD = "ONLY MODS CAN ADD TEAMS"
    SET_AGENTS = "AUTHORIZED INTERFACES"
    SET_WAIT_PERIOD = "WAIT PERIOD"
    SET_LATEST_RUN = LATEST_RUN
    SET_DEBUG = DEBUG_KEY

    # rating systems
    RATE_ELO = "ELO"
    RATE_GLICKO = "GLICKO"
    RATE_TRUESKILL = "TRUESKILL"
    RATE_WINCOUNT = "WINCOUNT"
    RATE_WINRATE = "WINRATE"
    RATE_NONE = "NONE"
    WINRATE_SCALE = 1000

    # timeformat
    TIMEFORMAT = TIMEFORMAT

    # default message
    DEFAULT_MSG = ("This is a game for the {{%s}} league, part of {{%s}}.\n"
                   "\nTo view information about the league, head to {{%s}}.\n"
                   "To change your limit, add/confirm a team, etc., "
                   "head to the league interface at {{%s}}.\n\n"
                   "Vetos so far: {{%s}}; Max: {{%s}}\n"
                   "\n{{%s}}\n\n"
                   "Got questions about the league? "
                   "Contact the league admin {{%s}}.\n\n"
                   "This league is run using the CSL framework, "
                   "an open-source project maintained by knyte.\n"

                   "If you never signed up for this league or suspect abuse, "
                   "message the creator of this game.") % ("_LEAGUE_NAME",
                   SET_SUPER_NAME, SET_URL, "_LEAGUE_INTERFACE", "_VETOS",
                   SET_VETO_LIMIT, "_GAME_SIDES", "_LEAGUE_ADMIN")

    # keywords
    KW_ALL = "ALL"
    KW_TEMPSETTING = "SET_"
    KW_TEMPOVERRIDE = "OVERRIDE_"

    # separators
    SEP_CMD = ";"
    SEP_PLYR = ","
    SEP_CONF = ","
    SEP_TEAMS = ","
    SEP_SIDES = "/"
    SEP_RTG = "/"
    SEP_VETOCT = "."
    SEP_VETOS = "/"
    SEP_DROPS = "/"
    SEP_MODS = ","
    SEP_TEMPSET = "#"
    SEP_SCHEMES = ","

    # markers
    MARK_DECLINE = "!"

    def __init__(self, games, teams, templates, settings, orders,
                 admin, parent, name, thread):
        self.parent = parent
        self.games = games
        self.teams = teams
        self.templates = templates
        self.settings = settings
        self.orders = orders
        self.admin = admin
        self.name = name
        self.sysDict, self.orderDict = None, None
        self._gameSize, self._sideSize = list(), list()
        self.tempTeams = None
        self.thread = thread
        self.debug = self._fetchProperty(self.SET_DEBUG, False,
                                         self._getBoolProperty)
        self.mods = self._getMods()
        self.handler = WLHandler()
        self._checkFormat()
        self._makeRateSysDict()
        self._makeOrderDict()

    def _makeRateSysDict(self):
        self.sysDict = {self.RATE_ELO: {'default':
                                        lambda: str(self.defaultElo),
                                        'update': self._getNewEloRatings,
                                        'prettify': str,
                                        'parity': self._getEloParity},
                        self.RATE_GLICKO: {'default':
                                           lambda: self.defaultGlicko,
                                           'update': self._getNewGlickoRatings,
                                           'prettify':
                                           self._getPrettyGlickoRating,
                                           'parity': self._getGlickoParity},
                        self.RATE_TRUESKILL: {'default':
                                              lambda: self.defaultTrueSkill,
                                              'update':
                                              self._getNewTrueSkillRatings,
                                              'prettify':
                                              self._getPrettyTrueSkillRating,
                                              'parity':
                                              self._getTrueSkillParity},
                        self.RATE_WINCOUNT: {'default': lambda: str(0),
                                             'update': self._getNewWinCounts,
                                             'prettify': str,
                                             'parity': self._getWinCountParity},
                        self.RATE_WINRATE: {'default':
                                            lambda: self.defaultWinRate,
                                            'update': self._getNewWinRates,
                                            'prettify': (lambda r:
                                            str(r.split(self.SEP_RTG)[0])),
                                            'parity': self._getWinRateParity},
                        self.RATE_NONE: {'default': lambda: self.defaultNone,
                                        'update': lambda *args, **kwargs: [],
                                        'prettify': str,
                                        'parity': self._getWinCountParity}}

    def _makeOrderDict(self):
        self.orderDict =  {self.ORD_ADD_TEAM:
            {'internal': self._addTeam, 'external': self.addTeam},
            self.ORD_CONFIRM_TEAM:
            {'internal': self._confirmTeam, 'external': self.confirmTeam},
            self.ORD_UNCONFIRM_TEAM:
            {'internal': self._unconfirmTeam, 'external': self.unconfirmTeam},
            self.ORD_SET_LIMIT:
            {'internal': self._setLimit, 'external': self.setLimit},
            self.ORD_REMOVE_TEAM:
            {'internal': self._removeTeam, 'external': self.removeTeam},
            self.ORD_DROP_TEMPLATE:
            {'internal': self._dropTemplates, 'external': self.dropTemplates},
            self.ORD_UNDROP_TEMPLATE: {'internal': self._undropTemplates,
            'external': self.undropTemplates},
            self.ORD_DROP_TEMPLATES:
            {'internal': self._dropTemplates, 'external': self.dropTemplates},
            self.ORD_UNDROP_TEMPLATES: {'internal': self._undropTemplates,
            'external': self.undropTemplates},
            self.ORD_ACTIVATE_TEMPLATE: {'internal': self._activateTemplate,
            'external': self.activateTemplate},
            self.ORD_DEACTIVATE_TEMPLATE: {'internal':
                self._deactivateTemplate, 'external': self.deactivateTemplate},
            self.ORD_QUIT_LEAGUE: {'internal': self._quitLeague,
            'external': self.quitLeague},
            self.ORD_ADD_TEMPLATE: {'internal': self._addTemplate,
            'external': self.addTemplate},
            self.ORD_RENAME_TEAM: {'internal': self._renameTeam,
            'external': self.renameTeam}}

    @noisy
    def _getMods(self):
        mods = self._fetchProperty(self.SET_MODS, set(), self.getIDGroup)
        mods.add(int(self.admin))
        return mods

    @staticmethod
    def _checkSheet(table, header, constraints, reformat=True):
        """
        ensures a given table has the appropriate header/constraints
        :param table: Table object to check
        :param header: an iterable containing required header labels
        :param constraints: a dictionary mapping labels to constraints
        :param reformat: a boolean determing whether to add labels if
                         they aren't present (raises error otherwise)
        """
        for label in header:
            if label not in table.reverseHeader:
                if reformat:
                    table.expandHeader(label)
                else:
                    error_str = ("Table %s missing %s in header" %
                                 (table.sheet.title, label))
                    raise ImproperLeague(error_str)
            table.updateConstraint(label, constraints.get(label, ""),
                                   erase=True)

    @noisy
    def _checkTeamSheet(self):
        teamConstraints = {'ID': 'UNIQUE INT',
                           'Name': 'SANITIZED UNIQUE STRING',
                           'Players': 'SANITIZED UNIQUE STRING',
                           'Confirmations': 'SANITIZED STRING',
                           'Rating': 'SANITIZED STRING',
                           'Vetos': 'SANITIZED STRING',
                           'Drops': 'SANITIZED STRING',
                           'Rank': 'INT',
                           'History': 'SANITIZED STRING',
                           'Finished': 'INT',
                           'Limit': 'INT',
                           'Ongoing': 'INT'}
        if not self.cullingDisabled:
            teamConstraints['Probation Start'] = 'STRING'
        self._checkSheet(self.teams, set(teamConstraints), teamConstraints,
                         self.autoformat)

    @noisy
    def _checkGamesSheet(self):
        gamesConstraints = {'ID': 'UNIQUE INT',
                            'WarlightID': 'UNIQUE INT',
                            'Created': 'SANITIZED STRING',
                            'Finished': 'SANITIZED STRING',
                            'Sides': 'SANITIZED STRING',
                            'Winners': 'SANITIZED STRING',
                            'Vetos': 'INT',
                            'Vetoed': 'SANITIZED STRING',
                            'Template': 'INT'}
        self._checkSheet(self.games, set(gamesConstraints), gamesConstraints,
                         self.autoformat)

    @noisy
    def _checkTemplatesSheet(self):
        templatesConstraints = {'ID': 'UNIQUE INT',
                                'Name': 'SANITIZED UNIQUE STRING',
                                'WarlightID': 'INT',
                                'Active': 'BOOL',
                                'Usage': 'INT'}
        if self.multischeme: templatesConstraints['Schemes'] = 'STRING'
        self._checkSheet(self.templates, set(templatesConstraints),
                         templatesConstraints, self.autoformat)

    @runPhase
    def _checkFormat(self):
        self._checkTeamSheet()
        self._checkGamesSheet()
        self._checkTemplatesSheet()

    def _fetchProperty(self, label, default, process_fn=None):
        cmd = self.settings.get(label, default)
        try:
            if (process_fn is None or
                cmd is default): return cmd
            return process_fn(cmd)
        except Exception as e:
            errType = type(e).__name__
            failStr = ("Couldn't get %s due to %s, using default of %s" %
                       (str(label), errType, str(default)))
            self.parent.log(failStr, self.name, error=True)
            return default

    @staticmethod
    def _getBoolProperty(val):
        return {'true': True,
                'false': False}[str(val).lower()]

    @property
    def autoformat(self):
        """whether to automatically format sheets"""
        return self._fetchProperty(self.SET_AUTOFORMAT, True,
                                   self._getBoolProperty)

    @property
    def preserveRecords(self):
        """whether to keep records of abandoned games"""
        if self.retentionRange and self.vetoPenalty: return True
        return self._fetchProperty(self.SET_PRESERVE_RECORDS, True,
                                   self._getBoolProperty)

    @property
    def maintainTotal(self):
        """
        whether to maintain the total value of ratings
        to make sure that the sum of ratings in the league
        is always equal to the # of active players * the default rating
        """
        prohibited = {self.RATE_WINRATE, self.RATE_WINCOUNT}
        expVal = self._fetchProperty(self.SET_MAINTAIN_TOTAL, False,
                                     self._getBoolProperty)
        return (expVal and self.ratingSystem not in prohibited)

    @property
    def favorNewTemplates(self):
        return self._fetchProperty(self.SET_FAVOR_NEW_TEMPLATES, False,
                                   self._getBoolProperty)

    @property
    def requireSameClan(self):
        exp = self._fetchProperty(self.SET_REQUIRE_SAME_CLAN, False,
                                   self._getBoolProperty)
        return (exp or self.maintainSameClan)

    @property
    def maintainSameClan(self):
        return self._fetchProperty(self.SET_MAINTAIN_SAME_CLAN, False,
                                   self._getBoolProperty)

    @property
    def forbidClanMatchups(self):
        return self._fetchProperty(self.SET_FORBID_CLAN_MATCHUPS, False,
                                   self._getBoolProperty)

    @property
    def onlyModsCanAdd(self):
        return self._fetchProperty(self.SET_ONLY_MODS_CAN_ADD, False,
                                   self._getBoolProperty)

    @property
    def autodrop(self):
        """whether to automatically drop templates players can't use"""
        return self._fetchProperty(self.SET_AUTODROP, (self.dropLimit > 0),
                                   self._getBoolProperty)

    @property
    def teamless(self):
        return self._fetchProperty(self.SET_TEAMLESS, (self.teamSize == 1
                                   and self.sideSize == 1),
                                   self._getBoolProperty)

    @property
    def leagueAcronym(self):
        return self._fetchProperty(self.SET_LEAGUE_ACRONYM, self.clusterName)

    @property
    def clusterName(self):
        return self._fetchProperty(self.SET_SUPER_NAME, self.name)

    @property
    def nameLength(self):
        return self._fetchProperty(self.SET_NAME_LENGTH, None, int)

    @property
    def ratingDecay(self):
        return self._fetchProperty(self.SET_RATING_DECAY, 0, int)

    @property
    def penaltyFloor(self):
        return self._fetchProperty(self.SET_PENALTY_FLOOR, None, int)

    @property
    def retentionRange(self):
        return self._fetchProperty(self.SET_RETENTION_RANGE, None, int)

    @property
    def constrainName(self):
        return self._fetchProperty(self.SET_CONSTRAIN_NAME, True,
                                   self._getBoolProperty)

    @property
    def leagueMessage(self):
        return self._fetchProperty(self.SET_LEAGUE_MESSAGE, self.DEFAULT_MSG)

    @property
    def leagueUrl(self):
        return self._fetchProperty(self.SET_URL, self.defaultUrl)

    @property
    def defaultUrl(self):
        sheetName = self.games.parent.sheet.ID
        return ("https://docs.google.com/spreadsheets/d/" +
                str(sheetName))

    @property
    def rematchLimit(self):
        process_fn = (lambda val: val if val == self.KW_ALL else
                      int(val) if self.multischeme else
                      (int(val) * (self.sideSize * self.gameSize - 1)))
        return self._fetchProperty(self.SET_REMATCH_LIMIT, 0, process_fn)

    @property
    def rematchCap(self):
        return self._fetchProperty(self.SET_REMATCH_CAP, 1, int)

    @property
    def teamLimit(self):
        process_fn = lambda x: None if (x.lower() in {"none", ""}) else int(x)
        defaultMax = None if self.teamSize > 1 else 1
        return self._fetchProperty(self.SET_MAX_TEAMS, defaultMax, process_fn)

    @property
    def vetoLimit(self):
        """maximum number of vetos per game"""
        return self._fetchProperty(self.SET_VETO_LIMIT, 0, int)

    @property
    def dropLimit(self):
        """maximum number of templates a player can drop"""
        process_fn = lambda x: min(int(x), len(self.templateIDs) - 1)
        return self._fetchProperty(self.SET_DROP_LIMIT, 0, process_fn)

    @property
    def removeDeclines(self):
        return self._fetchProperty(self.SET_REMOVE_DECLINES, True,
                                   self._getBoolProperty)

    @property
    def removeBoots(self):
        return self._fetchProperty(self.SET_REMOVE_BOOTS, True,
                                   self._getBoolProperty)

    @property
    def penalizeDeclines(self):
        return self._fetchProperty(self.SET_PENALIZE_DECLINES, True,
                                   self._getBoolProperty)

    @property
    def countDeclinesAsVetos(self):
        return self._fetchProperty(self.SET_VETO_DECLINES, False,
                                   self._getBoolProperty)

    @property
    def vetoPenalty(self):
        """points deduction for excessive vetos"""
        if self.ratingSystem == self.RATE_WINCOUNT: default = 1
        elif self.ratingSystem == self.RATE_WINRATE: default = 50
        else: default = 25
        return self._fetchProperty(self.SET_VETO_PENALTY, default, int)

    @classmethod
    def _shuffleVal(cls, vals):
        vals = [int(v) for v in vals.split(cls.SEP_CMD)]
        random.shuffle(vals)
        return max(vals[0], 1)

    @property
    def teamSize(self):
        """number of players per team"""
        process_fn = lambda x: max(1, int(x))
        return self._fetchProperty(self.SET_TEAM_SIZE, 1, process_fn)

    @staticmethod
    def _setIfEmpty(prop, fn):
        if len(prop) == 0: prop.append(fn())
        return prop[0]

    @property
    def gameSize(self):
        """number of sides per game"""
        return self._setIfEmpty(self._gameSize, self._statedGameSize)

    def _statedGameSize(self):
        return self._fetchProperty(self.SET_GAME_SIZE, 2, self._shuffleVal)

    @property
    def sideSize(self):
        """number of teams per side"""
        return self._setIfEmpty(self._sideSize, self._statedSideSize)

    def _statedSideSize(self):
        return self._fetchProperty(self.SET_TEAMS_PER_SIDE, 1, self._shuffleVal)

    @property
    def multischeme(self):
        gameSpec = self._fetchProperty(self.SET_GAME_SIZE, "1")
        sideSpec = self._fetchProperty(self.SET_TEAMS_PER_SIDE, "1")
        return (self.SEP_CMD in gameSpec or self.SEP_CMD in sideSpec)

    @property
    def scheme(self):
        playerSize = self.sideSize * self.teamSize
        return ''.join('v' + str(playerSize)
                       for x in xrange(self.gameSize))[1:]

    @property
    def expiryThreshold(self):
        """number of days until game is declared abandoned"""
        return self._fetchProperty(self.SET_EXP_THRESH, 3, int)

    @property
    def maxVacation(self):
        """maximum vacation length (in days) to remain on ladder"""
        return self._fetchProperty(self.SET_MAX_VACATION, None, int)

    @staticmethod
    def _timeZoneDiff():
        offset = (time.timezone if (time.localtime().tm_isdst == 0)
                  else time.altzone)
        return timedelta(hours=(offset/3600))

    @noisy
    def _meetsVacation(self, player):
        maxVac, secsPerDay = self.maxVacation, 86400
        if maxVac is None: return True
        timeZoneDiff = self._timeZoneDiff()
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
        return self._fetchProperty(self.SET_MIN_LIMIT, 0, process_fn)

    @property
    def maxLimit(self):
        """maximum number of max ongoing games per team"""
        return self._fetchProperty(self.SET_MAX_LIMIT, None, int)

    @property
    def constrainLimit(self):
        """
        whether to constrain out-of-range limits
        limits outside range are set to the min or max limit
        """
        return self._fetchProperty(self.SET_CONSTRAIN_LIMIT, True,
                                   self._getBoolProperty)

    @staticmethod
    def _valueInRange(val, rangeMin, rangeMax):
        return ((rangeMin is None or val >= rangeMin) and
                (rangeMax is None or val <= rangeMax))

    @noisy
    def _limitInRange(self, limit):
        """returns True if a limit is in an acceptable range"""
        return self._valueInRange(limit, self.minLimit, self.maxLimit)

    @property
    def ratingSystem(self):
        """rating system to use"""
        system = self._fetchProperty(self.SET_SYSTEM, self.RATE_NONE,
                                     lambda x: x.upper())
        if system not in self.sysDict:
            raise ImproperInput("Unrecognized rating system. Aborting.")
        return system

    @property
    def kFactor(self):
        prop = self._fetchProperty(self.SET_ELO_K, 32, int)
        return (prop * self.sideSize)

    @property
    def defaultElo(self):
        return self._fetchProperty(self.SET_ELO_DEFAULT, 1500, int)

    @property
    def eloEnv(self):
        return Elo(initial=self.defaultElo, k_factor=self.kFactor)

    @property
    def glickoRd(self):
        return self._fetchProperty(self.SET_GLICKO_RD, 350, int)

    @property
    def glickoRating(self):
        return self._fetchProperty(self.SET_GLICKO_DEFAULT, 1500, int)

    @property
    def defaultGlicko(self):
        return self._unsplitRtg([self.glickoRating, self.glickoRd])

    @property
    def trueSkillSigma(self):
        return self._fetchProperty(self.SET_TRUESKILL_SIGMA, 500, int)

    @property
    def trueSkillMu(self):
        return self._fetchProperty(self.SET_TRUESKILL_DEFAULT, 1500, int)

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
        return self._unsplitRtg([self.trueSkillMu, self.trueSkillSigma])

    @property
    def defaultWinRate(self):
        return (self.SEP_RTG).join(str(i) for i in [0, 0])

    @property
    def defaultNone(self):
        return self._fetchProperty(self.SET_DEFAULT_NONE, "0")

    @property
    def reverseParity(self):
        return self._fetchProperty(self.SET_REVERSE_PARITY, False,
                                   self._getBoolProperty)

    @property
    def reverseSideParity(self):
        return self._fetchProperty(self.SET_REVERSE_GROUPING, False,
                                   self._getBoolProperty)

    @property
    def maxBoot(self):
        return self._fetchProperty(self.SET_MAX_BOOT, 100.0, float)

    @property
    def minLevel(self):
        return self._fetchProperty(self.SET_MIN_LEVEL, 0, int)

    @property
    def membersOnly(self):
        exp = self._fetchProperty(self.SET_MEMBERS_ONLY, False,
                                  self._getBoolProperty)
        return (exp or (self.minMemberAge > 0))

    @staticmethod
    def _memberAge(player):
        return (date.today() - player.memberSince).days

    @noisy
    def _meetsMembership(self, player):
        return (not self.membersOnly or (player.isMember and
                self._memberAge(player) >= self.minMemberAge))

    @property
    def minPoints(self):
        return self._fetchProperty(self.SET_MIN_POINTS, 0, int)

    @property
    def minAge(self):
        return self._fetchProperty(self.SET_MIN_AGE, 0, int)

    @property
    def minMemberAge(self):
        return self._fetchProperty(self.SET_MIN_MEMBER_AGE, 0, int)

    @property
    def maxRTSpeed(self):
        process_fn = lambda x: float(Decimal(x) / Decimal(60.0))
        return self._fetchProperty(self.SET_MAX_RT_SPEED, None, process_fn)

    @property
    def maxMDSpeed(self):
        return self._fetchProperty(self.SET_MAX_MD_SPEED, None, float)

    @property
    def minExplicitRating(self):
        return self._fetchProperty(self.SET_MIN_RATING, None, int)

    @noisy
    def _findRatingAtPercentile(self, percentile):
        if percentile == 0: return None
        ratings = self.teams.findValue({'ID': {'value': '',
                                               'type': 'negative'}},
                                       "Rating")
        for i in xrange(len(ratings)):
            ratings[i] = int(self._prettifyRating(ratings[i]))
        ratings.sort()
        index = len(ratings) * float(Decimal(percentile) / Decimal(100.0))
        index = min(int(index) + bool(index % 1), len(ratings) - 1)
        return ratings[index]

    @property
    def minPercentileRating(self):
        process_fn = lambda x: self._findRatingAtPercentile(float(x))
        return self._fetchProperty(self.SET_MIN_PERCENTILE, None, process_fn)

    @property
    def minRating(self):
        return max(self.minPercentileRating, self.minExplicitRating)

    @property
    def gracePeriod(self):
        return self._fetchProperty(self.SET_GRACE_PERIOD, 0, int)

    @property
    def restorationPeriod(self):
        process_fn = lambda x: int(x) + self.gracePeriod
        return self._fetchProperty(self.SET_RESTORATION_PERIOD, None,
                                  process_fn)

    @property
    def cullingDisabled(self):
        return (self.minRating is None and self.maxRank is None)

    @noisy
    def _restoreLeagueTeams(self):
        restPd = self.restorationPeriod
        if self.cullingDisabled: restPd = 0
        if restPd is None: return
        deadTeams = self._getExtantEntities(self.teams,
                                           {'Limit': {'value': '0',
                                                      'type': 'positive'},
                                            'Probation Start': {'value': '',
                                                          'type': 'negative'}})
        for team in deadTeams:
            probStart = team['Probation Start']
            probStart = datetime.strptime(probStart, self.TIMEFORMAT)
            if ((datetime.now() - probStart).days >= restPd):
                self._updateEntityValue(self.teams, team['ID'],
                    Rating=self.defaultRating, **{'Probation Start': ''})

    @runPhase
    def _restoreTeams(self):
        try: self._restoreLeagueTeams()
        except SheetErrors.DataError: return

    @property
    def allowJoins(self):
        return self._fetchProperty(self.SET_ALLOW_JOINS, True,
                                  self._getBoolProperty)

    @property
    def leagueCapacity(self):
        return self._fetchProperty(self.SET_LEAGUE_CAPACITY, None, int)

    @property
    def activeCapacity(self):
        return self._fetchProperty(self.SET_ACTIVE_CAPACITY, None, int)

    @classmethod
    def _valueBelowCapacity(cls, value, capacity):
        return cls._valueInRange(value, None,
                                 (capacity-1 if isinstance(capacity, int)
                                  else capacity))

    @property
    def activeFull(self):
        return (not self._valueBelowCapacity(len(self.activeTeams),
                                             self.activeCapacity))

    @property
    def leagueFull(self):
        return (not self._valueBelowCapacity(len(self.allTeams),
                                             self.leagueCapacity))

    @classmethod
    def _getDateTimeProperty(cls, val):
        if isinstance(val, datetime): return val
        return (datetime.strptime(val, cls.TIMEFORMAT) - cls._timeZoneDiff())

    @property
    def waitPeriod(self):
        return self._fetchProperty(self.SET_WAIT_PERIOD, 240, int)

    @property
    def latestRun(self):
        return self._fetchProperty(self.SET_LATEST_RUN, '',
                                   self._unpackDateTime)

    @property
    def joinPeriodStart(self):
        return self._fetchProperty(self.SET_JOIN_PERIOD_START, None,
                                   self._getDateTimeProperty)

    @property
    def joinPeriodEnd(self):
        return self._fetchProperty(self.SET_JOIN_PERIOD_END, None,
                                   self._getDateTimeProperty)

    @classmethod
    def _currentTimeWithinRange(cls, start, end):
        now = datetime.now()
        return cls._valueInRange(now, start, end)

    @property
    def joinsAllowed(self):
        if (self.leagueFull or self.activeFull): return False
        start, end = self.joinPeriodStart, self.joinPeriodEnd
        return (self._currentTimeWithinRange(start, end) and self.allowJoins)

    @property
    def leagueActive(self):
        return self._fetchProperty(self.SET_ACTIVE, True, self._getBoolProperty)

    @property
    def minSize(self):
        return self._fetchProperty(self.SET_MIN_SIZE, (self.sideSize *
                                   self.gameSize), int)

    @property
    def minToCull(self):
        return self._fetchProperty(self.SET_MIN_TO_CULL, 0, int)

    @property
    def minToRank(self):
        return self._fetchProperty(self.SET_MIN_TO_RANK, 0, int)

    @property
    def maxRank(self):
        return self._fetchProperty(self.SET_MAX_RANK, None, int)

    @property
    def minLimitToRank(self):
        return self._fetchProperty(self.SET_MIN_LIMIT_TO_RANK, 1, int)

    @staticmethod
    def _applyRestrictions(matchDict, restrictions):
        if restrictions is not None:
            for restriction in restrictions:
                matchDict[restriction] = restrictions[restriction]

    @classmethod
    def _getExtantMatchDict(cls, restrictions):
        matchDict = {'ID': {'value': '', 'type': 'negative'}}
        cls._applyRestrictions(matchDict, restrictions)
        return matchDict

    @classmethod
    def _getExtantEntities(cls, table, restrictions=None):
        """
        :param table: table to fetch entities from
        :param restrictions: dictionary matching elements to
                             sheetDB match check dict
                             (e.g.: {'value': 'x', 'type': 'positive'})
        :rtype list[dict]:
        :retval: matching entities in table
        """
        matchDict = cls._getExtantMatchDict(restrictions)
        return table.findEntities(matchDict)

    @classmethod
    def _getLabeledEntities(cls, table, restrictions, keyLabel):
        matchDict = cls._getExtantMatchDict(restrictions)
        return table.findEntities(matchDict, keyLabel=keyLabel)

    @property
    def activeTeams(self):
        teams = self._getExtantEntities(self.teams,
                                        {'Limit': {'value': '0',
                                                   'type': 'negative'}})
        return [team for team in teams if int(team['Limit']) > 0]

    @property
    def activeTemplates(self):
        return self._getExtantEntities(self.templates,
                                       {'Active': {'value': 'TRUE',
                                                   'type': 'positive'}})

    @property
    def size(self):
        return len(self.activeTeams)

    @property
    def templateCount(self):
        return len(self.activeTemplates)

    @property
    def minTemplates(self):
        return self._fetchProperty(self.SET_MIN_TEMPLATES, 1, int)

    @property
    def activityStart(self):
        return self._fetchProperty(self.SET_START_DATE, None,
                                   self._getDateTimeProperty)

    @property
    def activityEnd(self):
        return self._fetchProperty(self.SET_END_DATE, None,
                                   self._getDateTimeProperty)

    @property
    def active(self):
        if self.templateCount < self.minTemplates: return False
        if self.size < self.minSize: return False
        start, end = self.activityStart, self.activityEnd
        return (self._currentTimeWithinRange(start, end) and self.leagueActive)

    @property
    def allowRemoval(self):
        return self._fetchProperty(self.SET_ALLOW_REMOVAL, False,
                                   self._getBoolProperty)

    @property
    def minOngoingGames(self):
        return self._fetchProperty(self.SET_MIN_ONGOING_GAMES, 0, int)

    @property
    def maxOngoingGames(self):
        return self._fetchProperty(self.SET_MAX_ONGOING_GAMES, None, int)

    @noisy
    def _gameCountInRange(self, player):
        ongoing = player.currentGames
        return self._valueInRange(ongoing, self.minOngoingGames,
                                  self.maxOngoingGames)

    @property
    def minRTPercent(self):
        return self._fetchProperty(self.SET_MIN_RT_PERCENT, 0.0, float)

    @property
    def maxRTPercent(self):
        return self._fetchProperty(self.SET_MAX_RT_PERCENT, 100.0, float)

    @noisy
    def _RTPercentInRange(self, player):
        pct = player.percentRT
        return (pct >= self.minRTPercent and pct <= self.maxRTPercent)

    @property
    def maxLastSeen(self):
        return self._fetchProperty(self.SET_MAX_LAST_SEEN, None, float)

    @property
    def min1v1Pct(self):
        return self._fetchProperty(self.SET_MIN_1v1_PCT, 0.0, float)

    @property
    def min2v2Pct(self):
        return self._fetchProperty(self.SET_MIN_2v2_PCT, 0.0, float)

    @property
    def min3v3Pct(self):
        return self._fetchProperty(self.SET_MIN_3v3_PCT, 0.0, float)

    @property
    def minRanked(self):
        return self._fetchProperty(self.SET_MIN_RANKED, 0, int)

    @noisy
    def _meetsMinRanked(self, player):
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
        return self._fetchProperty(self.SET_MIN_GAMES, 0, int)

    @property
    def minAchievementRate(self):
        return self._fetchProperty(self.SET_MIN_ACH, 0.0, float)

    @classmethod
    def getIDGroup(cls, val, process_fn=int):
        return set([process_fn(x) for x in val.split(cls.SEP_CMD)
                    if x is not ""])

    @classmethod
    def getGroup(cls, val):
        return cls.getIDGroup(val, process_fn=str)

    @property
    def agents(self):
        return self._fetchProperty(self.SET_AGENTS, set(), self.getGroup)

    def _agentAllowed(self, agentID):
        """
        returns True if an Interface is authorized to execute orders
        :param agentID: Warlight ID of Interface owner
        :rtype: bool
        """
        return (str(agentID) in self.agents or self.KW_ALL in self.agents)

    @property
    def bannedPlayers(self):
        """set containing IDs of banned players"""
        return self._fetchProperty(self.SET_BANNED_PLAYERS, set(),
                                   self.getGroup)

    @property
    def bannedClans(self):
        """set containing IDs of banned clans"""
        return self._fetchProperty(self.SET_BANNED_CLANS, set(),
                                   self.getGroup)

    @property
    def bannedLocations(self):
        return self._fetchProperty(self.SET_BANNED_LOCATIONS, set(),
                                   self.getGroup)

    @property
    def allowedPlayers(self):
        """set containing IDs of allowed players"""
        return self._fetchProperty(self.SET_ALLOWED_PLAYERS, set(),
                                   self.getGroup)

    @property
    def allowedClans(self):
        """set containing IDs of allowed clans"""
        return self._fetchProperty(self.SET_ALLOWED_CLANS, set(),
                                   self.getGroup)

    @property
    def allowedLocations(self):
        return self._fetchProperty(self.SET_ALLOWED_LOCATIONS, set(),
                                   self.getGroup)

    @property
    def requireClan(self):
        default = (self.KW_ALL in self.bannedClans)
        return self._fetchProperty(self.SET_REQUIRE_CLAN, default,
                                   self._getBoolProperty)

    @noisy
    def _clanAllowed(self, player):
        clan = player.clanID
        if clan is None:
            return (not self.requireClan)
        clan = str(clan)
        return ((clan in self.allowedClans or
                 (self.KW_ALL in self.allowedClans))
                 or (clan not in self.bannedClans
                     and self.KW_ALL not in self.bannedClans))

    @staticmethod
    def _processLoc(location):
        tempLoc = location.split()
        return ' '.join(tempLoc)

    @noisy
    def _checkLocation(self, location):
        location = self._processLoc(location)
        if (location in self.allowedLocations or
            self.KW_ALL in self.allowedLocations): return True
        if (location in self.bannedLocations or
            self.KW_ALL in self.bannedLocations): return False

    @noisy
    def _locationAllowed(self, player):
        location = player.location.split(":")
        results = set()
        for loc in location:
            check = self._checkLocation(loc)
            results.add(check)
        return ((True in results) or (False not in results))

    @noisy
    def _meetsAge(self, player):
        now = date.today()
        joinDate = player.joinDate
        return ((now - joinDate).days >= self.minAge)

    @noisy
    def _meetsSpeed(self, player):
        speeds = player.playSpeed
        rtSpeed = speeds.get('Real-Time Games', None)
        mdSpeed = speeds.get('Multi-Day Games', None)
        return ((self.maxRTSpeed is None or
                 rtSpeed <= self.maxRTSpeed) and
                (self.maxMDSpeed is None or
                 mdSpeed <= self.maxMDSpeed))

    @noisy
    def _meetsLastSeen(self, player):
        lastSeen = player.lastSeen
        return (self.maxLastSeen is None or
                lastSeen <= self.maxLastSeen)

    @noisy
    def _checkPrereqs(self, player):
        prereqs = {self._clanAllowed(player), self._locationAllowed(player),
                   (player.bootRate <= self.maxBoot),
                   (player.level >= self.minLevel),
                   self._meetsMembership(player), self._meetsVacation(player),
                   (player.points >= self.minPoints), self._meetsAge(player),
                   self._meetsSpeed(player), self._gameCountInRange(player),
                   self._RTPercentInRange(player), self._meetsLastSeen(player),
                   self._meetsMinRanked(player),
                   (player.playedGames >= self.minGames),
                   (player.achievementRate >= self.minAchievementRate)}
        for prereq in prereqs:
            if prereq is not True: return False
        return True

    @noisy
    def _playerExplicitlyAllowed(self, player):
        return (str(player) in self.allowedPlayers or
                self.KW_ALL in self.allowedPlayers)

    @noisy
    def _allowed(self, playerID):
        """returns True if a player is allowed to join the league"""
        player = int(playerID)
        if self._playerExplicitlyAllowed(player): return True
        parser = PlayerParser(player)
        if not self._checkPrereqs(parser):
            return False
        return (str(player) not in self.bannedPlayers and
                self.KW_ALL not in self.bannedPlayers)

    @noisy
    def _banned(self, playerID):
        """returns True if a player is banned from the league"""
        return not(self._allowed(playerID))

    @noisy
    def _logFailedOrder(self, order):
        desc = ("Failed to process %s order by %d" %
                (order['type'], int(order['author'])))
        self.parent.log(desc, league=self.name, error=True)

    @noisy
    def _checkTeamCreator(self, creator, members):
        if (creator not in members and
            creator not in self.mods):
            raise ImproperInput(str(creator) + " isn't able to" +
                                " add a team that excludes them")

    @noisy
    def _checkTemplateAccess(self, playerID):
        """returns True if a player can play on all templates"""
        tempIDs = self.templateIDs
        tempWLIDs, unusables = dict(), set()
        for ID in tempIDs:
            self._addToSetWithinDict(tempWLIDs, tempIDs[ID]['WarlightID'], ID)
        tempResults = self.handler.validateToken(int(playerID),
                                                 *tempWLIDs)
        for temp in tempWLIDs:
            tempName = "template" + str(temp)
            if tempResults[tempName]['result'] == 'CannotUseTemplate':
                unusables.update(tempWLIDs[temp])
        return unusables

    @noisy
    def _handleAutodrop(self, teamID, templates):
        teams = self.teams.findEntities({'ID': {'value': teamID,
                                                'type': 'positive'}})
        if len(teams) == 0:
            raise ImproperInput("Cannot autodrop for nonexistent team %s" %
                                (str(teamID)))
        team = teams[0]
        existingDrops = set(team['Drops'].split(self.SEP_DROPS))
        existingDrops.update(str(t) for t in templates)
        existingDrops.discard('')
        if (len(existingDrops) > self.dropLimit):
            raise ImproperInput("Team %s has already reached its drop limit" %
                                (str(teamID)))
        drops = (self.SEP_DROPS).join(str(d) for d in existingDrops)
        self._updateEntityValue(self.teams, teamID, Drops=drops)

    @noisy
    def _checkTeamMember(self, member, badTemps):
        if self._banned(member):
            raise ImproperInput(str(member) + " is banned from this league")
        tempAccess = self._checkTemplateAccess(member)
        for temp in tempAccess:
            badTemps.add(temp)

    @noisy
    def _autodropEligible(self, badTemps):
        return (len(badTemps) == 0 or
                (self.autodrop and (len(badTemps) <= self.dropLimit)))

    @noisy
    def _handleTeamAutodrop(self, teamID, members, badTemps):
        if self._autodropEligible(badTemps):
            if teamID is None:
                forcedDrops = (self.SEP_DROPS).join([str(t) for t in badTemps])
                return forcedDrops
            else:
                self._handleAutodrop(teamID, badTemps)
                return ""
        else:
            memberStr = (self.SEP_PLYR).join(str(m) for m in members)
            raise ImproperInput("Team with %s cannot play on enough templates"
                                % (memberStr))

    @noisy
    def _checkTeam(self, members, teamID=None):
        badTemplates = set()
        for member in members: self._checkTeamMember(member, badTemplates)
        return self._handleTeamAutodrop(teamID, members, badTemplates)

    @noisy
    def _checkLimit(self, limit):
        if not self._limitInRange(limit):
            if self.constrainLimit:
                if limit < self.minLimit: return self.minLimit
                return self.maxLimit
            else: raise ImproperInput("Limit out of range")
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

    @noisy
    def _currentID(self):
        existingIDs = self.existingIDs
        if len(existingIDs) == 0: return 0
        else: return max(existingIDs) + 1

    @property
    def defaultRating(self):
        return self.sysDict[self.ratingSystem]['default']()

    @property
    def teamPlayers(self):
        result = dict()
        for team in self.allTeams:
            result[team['Players']] = team['Name']
        return result

    @noisy
    def _checkJoins(self):
        if not self.joinsAllowed:
            raise ImproperInput("This league is not open to new teams")

    @staticmethod
    def _checkConsistentClan(members, required):
        if not required: return
        clans = {PlayerParser(member).clanID for member in members}
        if len(clans) > 1:
            failStr = "All members of a team must belong to the same clan"
            raise ImproperInput(failStr)

    @noisy
    def _checkAuthorAndMembers(self, order):
        author = int(order['author'])
        if self.onlyModsCanAdd and author not in self.mods:
            raise ImproperInput("Only mods or above can add teams")
        members = [int(member) for member in order['orders'][3:]]
        self._checkTeamCreator(author, members)
        self._checkConsistentClan(members, self.requireSameClan)
        confirms = [(m == author) for m in members]
        return self._checkTeam(members), members, confirms

    @noisy
    def _checkEligible(self, order):
        gameLimit = int(order['orders'][2])
        forcedDrops, members, confirms = self._checkAuthorAndMembers(order)
        return self._checkLimit(gameLimit), forcedDrops, members, confirms

    @noisy
    def _getTeamNameFromOrder(self, order, index=1):
        teamName = order['orders'][index]
        if len(teamName) > self.nameLength:
            if self.constrainName: return teamName[:self.nameLength]
            raise ImproperInput("Team name %s is too long" % (teamName))
        return teamName

    @classmethod
    def _getMembersAndConfirms(cls, temp):
        members, confirms = [x for (x, y) in temp], [y for (x, y) in temp]
        members = (cls.SEP_PLYR).join([str(m) for m in members])
        confirms = (cls.SEP_CONF).join([str(c).upper() for c in confirms])
        return members, confirms

    @noisy
    def _addTeam(self, order):
        self._checkJoins()
        teamName = self._getTeamNameFromOrder(order)
        gameLimit, forcedDrops, members, confirms = self._checkEligible(order)
        temp = sorted(zip(members, confirms))
        members, confirms = self._getMembersAndConfirms(temp)
        with teamLock:
            self._addEntity(self.teams, {'ID': self._currentID(),
                'Name': teamName, 'Limit': gameLimit, 'Players': members,
                'Confirmations': confirms, 'Vetos': "", 'Drops': forcedDrops,
                'Ongoing': 0, 'Finished': 0, 'Rating': self.defaultRating})

    @noisy
    def _retrieveTeamWithName(self, name):
        matches = self.teams.findEntities({'Name': {'value': name,
                                                    'type': 'positive'}})
        if len(matches) < 1:
            raise NonexistentItem("Nonexistent team: " + str(name))
        return matches[0]

    @noisy
    def _authorInTeam(self, author, team, allowMods=True):
        if (allowMods and (author in self.mods)): return True
        return (str(author) in team['Players'].split(self.SEP_PLYR))

    @noisy
    def _fetchMatchingTeam(self, order, checkAuthor=True,
                          allowMod=True):
        name, author, index = order['orders'][1], int(order['author']), None
        matchingTeam = self._retrieveTeamWithName(name)
        if (checkAuthor and
            not self._authorInTeam(author, matchingTeam, allowMod)):
            raise ImproperInput(str(author) + " not in " + str(name))
        try:
            index = (matchingTeam['Players'].
                     split(self.SEP_PLYR).
                     index(str(author)))
        except ValueError: pass
        return matchingTeam, index

    @noisy
    def _toggleConfirm(self, order, confirm=True):
        matchingTeam, index = self._fetchMatchingTeam(order, True, False)
        confirms = matchingTeam['Confirmations'].split(self.SEP_CONF)
        confirms[index] = "TRUE" if confirm else "FALSE"
        self._updateConfirms(matchingTeam['ID'], confirms)

    @noisy
    def _toggleTeamConfirm(self, order, confirm=True):
        author = int(order['author'])
        if (author in self.mods and len(order['orders']) > 2):
            self._toggleConfirms(order, confirm=confirm)
        else: self._toggleConfirm(order, confirm=confirm)

    @noisy
    def _confirmTeam(self, order):
        self._toggleTeamConfirm(order)

    @noisy
    def _unconfirmTeam(self, order):
        self._toggleTeamConfirm(order, confirm=False)

    @noisy
    def _toggleConfirms(self, order, confirm=True):
        players = order['orders'][2:]
        teamName = order['orders'][1]
        for player in players:
            newOrder = {'author': int(player), 'orders': [self.name, teamName]}
            self._toggleConfirm(newOrder, confirm=confirm)

    @noisy
    def _removeTeam(self, order):
        if not self.allowRemoval:
            raise ImproperInput("Team removal has been disabled.")
        matchingTeam = self._fetchMatchingTeam(order)[0]
        self._removeEntity(self.teams, matchingTeam['ID'])

    @noisy
    def _checkLimitChange(self, teamID, newLimit):
        if int(newLimit) <= 0: return
        elif self.activeCapacity is None: return
        elif not self.activeFull: return
        oldLimit = int(self._fetchTeamData(teamID)['Limit'])
        if oldLimit == 0:
            raise ImproperInput("League has reached max active teams.")

    @noisy
    def _setLimit(self, order):
        matchingTeam = self._fetchMatchingTeam(order)[0]
        self._checkLimitChange(matchingTeam.get('ID'), order['orders'][2])
        self._changeLimit(matchingTeam.get('ID'), order['orders'][2])

    @property
    def templateIDs(self):
        return self._getLabeledEntities(self.templates,
            {'Active': {'value': 'TRUE', 'type': 'positive'}}, "ID")

    @noisy
    def _validScheme(self, tempData):
        schemes = set(tempData['Schemes'].split(self.SEP_SCHEMES))
        return (len(schemes.intersection({self.scheme, self.KW_ALL})) > 0)

    @noisy
    def _narrowToValidSchemes(self, templates):
        results = dict()
        for template in templates:
            if self._validScheme(templates[template]):
                results[template] = templates[template]
        return results

    @property
    def usableTemplateIDs(self):
        retvals = self.templateIDs
        if self.multischeme:
            return self._narrowToValidSchemes(retvals)
        return retvals

    @property
    def gameIDs(self):
        return self.games.findValue({'ID': {'value': '',
                                            'type': 'negative'}}, 'ID')

    @property
    def templateRanks(self):
        tempData = self.activeTemplates
        tempInfo = [(int(temp['ID']), int(temp['Usage'])) for temp in tempData]
        tempInfo.sort(key = lambda x: x[1])
        return tempInfo

    @noisy
    def _findMatchingTemplate(self, templateName):
        IDs = self.templates.findValue({'ID': {'value': '',
                                               'type': 'negative'},
                                        'Name': {'value': templateName,
                                                 'type': 'positive'}})
        if len(IDs) == 0: return None
        return IDs[0]

    @noisy
    def _getExistingDrops(self, order):
        teamData = self._fetchMatchingTeam(order)[0]
        existingDrops = teamData.get('Drops')
        existingDrops = set(existingDrops.split(self.SEP_DROPS))
        teamID = teamData.get('ID')
        return teamID, existingDrops

    @noisy
    def _updateTeamDrops(self, teamID, drops):
        dropStr = (self.SEP_DROPS).join(set(str(x) for x in drops))
        self._updateEntityValue(self.teams, teamID, Drops=dropStr)

    def _findAndDrop(self, templateNames, existingDrops):
        for templateName in templateNames:
            temp = self._findMatchingTemplate(templateName)
            if temp is None: continue
            existingDrops.add(str(temp.get('ID')))

    @noisy
    def _dropTemplates(self, order):
        templateNames = order['orders'][2:]
        teamName = order['orders'][1]
        teamID, existingDrops = self._getExistingDrops(order)
        remainingDrops = (self.dropLimit - len(existingDrops))
        if remainingDrops < 1:
            raise ImproperInput("Team %s already reached its drop limit" %
                                (teamName))
        elif remainingDrops < len(templateNames):
            dataStr = ("Too many drops by team %s, dropping only first %d"
                       % (teamName, remainingDrops))
            self.parent.log(dataStr, self.name, error=True)
            templateNames = templateNames[:remainingDrops]
        self._findAndDrop(templateNames, existingDrops)
        self._updateTeamDrops(teamID, existingDrops)

    @noisy
    def _undropTemplates(self, order):
        templateNames = order['orders'][2:]
        teamID, existingDrops = self._getExistingDrops(order)
        for templateName in templateNames:
            temp = self._findMatchingTemplate(templateName)
            if (temp is not None and str(temp.get('ID')) in existingDrops):
                existingDrops.remove(str(temp.get('ID')))
        self._updateTeamDrops(teamID, existingDrops)

    @noisy
    def _toggleActivity(self, order, setTo):
        author = int(order['author'])
        if author not in self.mods:
            raise ImproperInput("Only mods can toggle template active status")
        tempName = order['orders'][1]
        self._updateEntityValue(self.templates, tempName, identifier='Name',
                                Active=setTo)

    @noisy
    def _activateTemplate(self, order):
        self._toggleActivity(order, 'TRUE')

    @noisy
    def _deactivateTemplate(self, order):
        if self.templateCount <= self.minTemplates:
            raise ImproperInput("Not enough active templates to deactivate")
        self._toggleActivity(order, 'FALSE')

    @property
    def allTeams(self):
        return self._getExtantEntities(self.teams)

    @noisy
    def _getPlayersFromOrder(self, order):
        author = int(order['author'])
        if (author in self.mods and len(order['orders']) > 1):
            return set(order['orders'][1:])
        return set([str(author),])

    @noisy
    def _updateConfirms(self, teamID, confirms, identifier='ID'):
        confirms = (self.SEP_CONF).join([str(c).upper() for c in confirms])
        self._updateEntityValue(self.teams, teamID, identifier=identifier,
                                Confirmations=confirms)

    @noisy
    def _quitLeague(self, order):
        players = self._getPlayersFromOrder(order)
        for team in self.allTeams:
            members = team['Players'].split(self.SEP_PLYR)
            confirms = team['Confirmations'].split(self.SEP_CONF)
            hit = False
            for player in players:
                if player in members:
                    hit, index = True, members.index(player)
                    confirms[index] = "FALSE"
            if hit: self._updateConfirms(team['ID'], confirms)

    @property
    def usedTemplates(self):
        IDs, games = self.templateIDs, self._getExtantEntities(self.games)
        results = set()
        for ID in IDs: results.add(int(ID))
        for game in games: results.add(int(game['Template']))
        return results

    @noisy
    def _confirmAdmin(self, author, ordType):
        if author != self.admin:
            raise ImproperInput("%s orders are only usable by admins" %
                                (ordType))

    @property
    def _newTempGameCount(self):
        existingTemps = self.activeTemplates
        if (self.favorNewTemplates or len(existingTemps) == 0): return 0
        countSum = sum(t['Usage'] for t in existingTemps)
        return int(round(Decimal(countSum) / Decimal(len(existingTemps))))

    @noisy
    def _addTemplate(self, order):
        self._confirmAdmin(int(order['author']), order['type'])
        nexti, orders = 3, order['orders']
        tempName, warlightID = orders[1:3]
        with tempLock:
            used, gameCount = self.usedTemplates, self._newTempGameCount
            ID = (max(used) + 1) if len(used) else 0
            tempDict = {'ID': ID, 'Name': tempName, 'WarlightID': warlightID,
                        'Active': 'TRUE', 'Usage': gameCount}
            if self.multischeme: tempDict['Schemes'], nexti = orders[3], 4
            for i in xrange(nexti+1, len(orders), 2):
                tempDict[orders[i-1]] = orders[i]
            self._addEntity(self.templates, tempDict)

    @noisy
    def _renameTeam(self, order):
        matchingTeam = self._fetchMatchingTeam(order)[0]
        newName = self._getTeamNameFromOrder(order, 2)
        self._updateEntityValue(self.teams, matchingTeam['ID'],
                                identifier='ID', Name=newName)

    @noisy
    def _runOrderExecution(self, orders, accessType):
        for order in orders:
            orderType = order['type'].lower()
            try:
                self.orderDict[orderType][accessType](order)
            except Exception as e:
                if len(str(e)): # exception has some description string
                    self.parent.log(str(e), self.name, error=True)
                else:
                    self._logFailedOrder(order)

    @runPhase
    def _executeOrders(self):
        self._runOrderExecution(self.orders, 'internal')
        self._updateRanks()

    @property
    def unfinishedGames(self):
        return self._getLabeledEntities(self.games,
            {'Finished': {'value': '', 'type': 'positive'}}, 'WarlightID')

    @staticmethod
    def _isAbandoned(players):
        for player in players:
            if player['state'] == 'VotedToEnd': return True
            elif player['state'] == 'Won': return False
        return False

    @staticmethod
    def _findMatchingPlayers(players, *states):
        matching = list()
        for player in players:
            if player['state'] in states:
                matching.append(int(player['id']))
        matching.sort()
        return matching

    @noisy
    def _findWinners(self, players):
        return self._findMatchingPlayers(players, 'Won')

    @noisy
    def _findDecliners(self, players):
        return self._findMatchingPlayers(players, 'Declined')

    @noisy
    def _findBooted(self, players):
        return self._findMatchingPlayers(players, 'Booted')

    @noisy
    def _findWaiting(self, players):
        return self._findMatchingPlayers(players, 'Invited', 'Declined')

    @noisy
    def _handleFinished(self, gameData):
        if self._isAbandoned(gameData['players']):
            return 'ABANDONED', [int(p.get('id')) for p in gameData['players']]
        else:
            decliners = self._findDecliners(gameData['players'])
            booted = self._findBooted(gameData['players'])
            if len(decliners) > 0:
                return ('DECLINED', decliners, booted)
            return ('FINISHED', self._findWinners(gameData['players']),
                    booted)

    @noisy
    def _wrapUp(self, gameData, group):
        self.handler.deleteGame(gameData['id'])
        self._updateEntityValue(self.games, gameData['id'], 'WarlightID',
                                WarlightID='')
        if len(group) == len(gameData['players']):
            return 'ABANDONED', None
        return 'DECLINED', group, list()

    @noisy
    def _handleWaiting(self, gameData, created):
        decliners = self._findDecliners(gameData['players'])
        if len(decliners): return self._wrapUp(gameData, decliners)
        waiting = self._findWaiting(gameData['players'])
        if (((datetime.now() - created).days >= self.expiryThreshold)
            and len(waiting)):
            return self._wrapUp(gameData, waiting)

    @noisy
    def _fetchGameStatusFromData(self, gameData, created):
        if gameData.get('state') == 'Finished':
            return self._handleFinished(gameData)
        elif gameData.get('state') == 'WaitingForPlayers':
            return self._handleWaiting(gameData, created)

    @noisy
    def _fetchGameStatus(self, gameID, warlightID, created):
        try:
            gameData = self.handler.queryGame(warlightID)
            return self._fetchGameStatusFromData(gameData, created)
        except APIError:
            self._updateEntityValue(self.games, gameID, WarlightID='')
            self._deleteGameByID(gameID)
            return None

    @staticmethod
    def _fetchDataByID(table, ID, itemType):
        nonexStr = "Nonexistent %s: %s" % (str(itemType), str(ID))
        data = table.findEntities({'ID': {'value': ID,
                                          'type': 'positive'}})
        if len(data) == 0: raise NonexistentItem(nonexStr)
        return data[0]

    @noisy
    def _fetchGameData(self, gameID):
        return self._fetchDataByID(self.games, gameID, "game")

    @noisy
    def _fetchTeamData(self, teamID):
        return self._fetchDataByID(self.teams, teamID, "team")

    @noisy
    def _fetchTemplateData(self, templateID):
        return self._fetchDataByID(self.templates, templateID, "template")

    @classmethod
    def _getGameTeams(cls, gameData):
        results = list()
        for side in gameData['Sides'].split(cls.SEP_SIDES):
            results += side.split(cls.SEP_TEAMS)
        return results

    @noisy
    def _findTeamsFromData(self, gameData, players):
        players, results = set([str(player) for player in players]), set()
        gameTeams = self._getGameTeams(gameData)
        for team in gameTeams:
            teamData = self._fetchTeamData(team)
            playerData = set(teamData['Players'].split(self.SEP_PLYR))
            if len(playerData.intersection(players)) > 0:
                results.add(team)
        return results

    @noisy
    def _findCorrespondingTeams(self, gameID, players):
        gameData = self._fetchGameData(gameID)
        return self._findTeamsFromData(gameData, players)

    @noisy
    def _setWinners(self, gameID, winningSide, declined=False):
        sortedWinners = sorted(team for team in winningSide)
        winStr = (self.SEP_TEAMS).join(str(team) for team in sortedWinners)
        if declined: winStr = winStr + self.MARK_DECLINE
        finStr = datetime.strftime(datetime.now(), self.TIMEFORMAT)
        self._updateEntityValue(self.games, gameID, identifier='ID',
                                Winners=winStr, Finished=finStr)

    @noisy
    def _adjustTeamGameCount(self, teamID, adj, totalAdj=0):
        teamData = self._fetchTeamData(teamID)
        oldCount = int(teamData['Ongoing'])
        oldFin = int(teamData['Finished'])
        self._updateEntityValue(self.teams, teamID, Ongoing=str(oldCount+adj),
                                Finished=str(oldFin+totalAdj))

    @noisy
    def _adjustTemplateGameCount(self, templateID, adj):
        oldCount = int(self._fetchTemplateData(templateID)['Usage'])
        self._updateEntityValue(self.templates, templateID,
                                Usage=str(oldCount+adj))

    @noisy
    def _getEloDiff(self, rating, events, count):
        oldRating = rating
        rating = self.eloEnv.rate(oldRating, events)
        diff = int(round((rating - oldRating) / count))
        return diff

    @noisy
    def _getEloRating(self, teamID):
        return int(self._getTeamRating(teamID))

    @noisy
    def _getSideEloRating(self, side):
        rating = 0
        for team in side:
            rating += self._getEloRating(team)
        return rating

    @noisy
    def _makeOpps(self, sides, i, winningSide):
        opps = list()
        for j in xrange(len(sides)):
            if i == j: continue
            other = sides[j]
            otherRtg = self._getSideEloRating(other)
            event = self._getEvent(i, j, winningSide)
            if event is not None: opps.append((event, otherRtg))
        return opps

    @staticmethod
    def _applyEloDiff(side, diff, diffs):
        for team in side:
            diffs[team] = Decimal(diff) / Decimal(len(side))

    @noisy
    def _getNewEloRatings(self, sides, winningSide):
        results, diffs, count = dict(), dict(), len(sides) - 1
        for i in xrange(len(sides)):
            side = sides[i]
            sideRtg = self._getSideEloRating(side)
            opps = self._makeOpps(sides, i, winningSide)
            diff = self._getEloDiff(sideRtg, opps, count)
            self._applyEloDiff(side, diff, diffs)
        for side in sides:
            for team in side:
                results[team] = str(self._getEloRating(team) +
                                    int(round(diffs[team])))
        return results

    @classmethod
    def _unsplitRtg(cls, rating):
        return (cls.SEP_RTG).join([str(val) for val in rating])

    @noisy
    def _getGlickoRating(self, teamID):
        return self._splitRating(self._getTeamRating(teamID))

    @noisy
    def _getSideGlickoRating(self, side):
        rating, dev = 0, 0
        for team in side:
            glicko = self._getGlickoRating(team)
            rating, dev = (rating + glicko[0], dev + glicko[1])
        return rating, dev

    @staticmethod
    def _getEvent(i, j, winner, WIN=1, LOSS=0):
        if i == winner: return WIN
        elif j == winner: return LOSS

    @noisy
    def _updateGlickoMatchup(self, players, i, j, winner):
        side1, side2 = players[i], players[j]
        if self._getEvent(i, j, winner) is None: return
        side1.update_player([side2.rating,], [side2.rd,],
                            [self._getEvent(i, j, winner),])
        side2.update_player([side1.rating,], [side1.rd,],
                            [self._getEvent(j, i, winner),])

    @noisy
    def _makeGlickoPlayersFromSides(self, sides):
        players = list()
        for side in sides:
            sideRtg, sideRd = self._getSideGlickoRating(side)
            sidePlayer = Player(rating=sideRtg, rd=sideRd)
            players.append(sidePlayer)
        return players

    @noisy
    def _updateGlickoMatchups(self, sides, players, winningSide):
        for i in xrange(len(sides)):
            for j in xrange(i+1, len(sides)):
                self._updateGlickoMatchup(players, i, j, winningSide)

    @staticmethod
    def _preciseUpdate(vals, divisor_1, divisor_2):
        results = list()
        for val in vals:
            res = int(round(Decimal(val) /
                      (Decimal(divisor_1) * Decimal(divisor_2))))
            results.append(res)
        return tuple(results)

    @noisy
    def _getGlickoResultsFromPlayers(self, sides, players):
        results, otherSides = dict(), len(sides)-1
        for i in xrange(len(sides)):
            newRtg, newRd = players[i].rating, players[i].rd
            oldRtg, oldRd = self._getSideGlickoRating(sides[i])
            rtgDiff, rdDiff = float(newRtg - oldRtg), float(newRd - oldRd)
            rtgDiff, rdDiff = self._preciseUpdate([rtgDiff, rdDiff],
                                                   otherSides, len(sides[i]))
            for team in sides[i]:
                origRtg, origRd = self._getGlickoRating(team)
                rtg = origRtg + int(round(rtgDiff))
                rd = origRd + int(round(rdDiff))
                results[team] = self._unsplitRtg([str(rtg), str(rd)])
        return results

    @noisy
    def _getNewGlickoRatings(self, sides, winningSide):
        players = self._makeGlickoPlayersFromSides(sides)
        self._updateGlickoMatchups(sides, players, winningSide)
        return self._getGlickoResultsFromPlayers(sides, players)

    @noisy
    def _getTrueSkillRating(self, teamID):
        mu, sigma = self._splitRating(self._getTeamRating(teamID))
        return self.trueSkillEnv.create_rating(mu, sigma)

    @noisy
    def _getNewTrueSkillRatings(self, sides, winningSide):
        results, WIN, LOSS = dict(), 0, 1
        rating_groups = list()
        for side in sides:
            rating_group = dict()
            for team in side:
                rating_group[team] = self._getTrueSkillRating(team)
            rating_groups.append(rating_group)
        ranks = [LOSS,] * len(sides)
        ranks[winningSide] = WIN
        updated = self.trueSkillEnv.rate(rating_groups, ranks=[WIN, LOSS])
        for side in updated:
            for team in side:
                results[team] = self._unsplitRtg([side[team].mu,
                                                  side[team].sigma])
        return results

    @noisy
    def _getNewWinCounts(self, sides, winningSide):
        results = dict()
        winningTeams = sides[winningSide]
        for team in winningTeams:
            count = self._getTeamRating(team)
            count = str(int(count) + 1)
            results[team] = count
        return results

    @noisy
    def _getWinRate(self, team):
        rating = self._getTeamRating(team)
        winRate, numGames = rating.split(self.SEP_RTG)
        winRate = int(winRate)
        numGames = int(numGames)
        return winRate, numGames

    @noisy
    def _getNewWinRates(self, sides, winningSide):
        results = dict()
        for i in xrange(len(sides)):
            side = sides[i]
            for team in side:
                winRate, numGames = self._getWinRate(team)
                estimatedWins = (Decimal(numGames) * (Decimal(winRate)
                                 / Decimal(self.WINRATE_SCALE)))
                if i == winningSide:
                    estimatedWins += Decimal(1)
                numGames += 1
                newRate = round(float(estimatedWins / Decimal(numGames)), 3)
                newRate = int(Decimal(newRate) * Decimal(self.WINRATE_SCALE))
                results[team] = self._unsplitRtg([newRate, numGames])
        return results

    @noisy
    def _getNewRatings(self, sides, winningSide):
        """
        :param sides: list[set[string]]
        :param winningSide: int (index of winning side)
        """
        return self.sysDict[self.ratingSystem]['update'](sides, winningSide)

    @classmethod
    def _updateEntityValue(cls, table, ID, identifier='ID', **values):
        table.updateMatchingEntities({identifier: {'value': ID,
                                                   'type': 'positive'}},
                                     values)

    @noisy
    def _updateTeamRating(self, teamID, rating):
        self._updateEntityValue(self.teams, teamID, Rating=rating)

    @noisy
    def _updateRatings(self, newRatings):
        for team in newRatings:
            self._updateTeamRating(team, newRatings[team])

    @noisy
    def _finishGameForTeams(self, sides):
        for side in sides:
            for team in side:
                self._adjustTeamGameCount(team, -1, 1)

    @noisy
    def _updateResults(self, gameID, sides, winningSide, adj=True,
                      declined=False):
        adj = (adj and self.retentionRange is None)
        self._setWinners(gameID, sides[winningSide], declined)
        if adj:
            newRatings = self._getNewRatings(sides, winningSide)
            self._updateRatings(newRatings)
        self._finishGameForTeams(sides)

    @noisy
    def _removeBooted(self, gameData, booted):
        if not self.removeBoots: return
        bootedTeams = self._findTeamsFromData(gameData, booted)
        for team in bootedTeams:
            self._changeLimit(team, 0)

    @noisy
    def _handleBooted(self, gameID, groups):
        group, booted = groups
        gameData = self._fetchGameData(gameID)
        self._removeBooted(gameData, booted)
        return group, gameData

    @noisy
    def _updateWinners(self, gameID, groups):
        winners, gameData = self._handleBooted(gameID, groups)
        sides = self._getGameSidesFromData(gameData)
        winningTeams = self._findTeamsFromData(gameData, winners)
        for i in xrange(len(sides)):
            side = sides[i]
            if len(side & winningTeams) > 0:
                winningSide = i
                break
        self._updateResults(gameID, sides, winningSide)

    @noisy
    def _handleSpecialDeclines(self, losingTeams, template):
        if self.countDeclinesAsVetos:
            self._updateGameVetos(losingTeams, template)
        if self.removeDeclines:
            for team in losingTeams:
                self._changeLimit(team, 0)

    @staticmethod
    def _makeFakeSides(sides, losingTeams):
        winningSide, results, winningTeams = None, [losingTeams,], set()
        for side in sides:
            for team in side:
                if team not in losingTeams: winningTeams.add(team)
        if len(winningTeams) > 0:
            results.append(winningTeams)
            winningSide = (len(results) - 1)
        return results, winningSide

    @noisy
    def _updateDecline(self, gameID, groups):
        decliners, gameData = self._handleBooted(gameID, groups)
        sides = self._getGameSidesFromData(gameData)
        losingTeams = self._findTeamsFromData(gameData, decliners)
        template = str(gameData['Template'])
        self._handleSpecialDeclines(losingTeams, template)
        sides, winningSide = self._makeFakeSides(sides, losingTeams)
        if winningSide is None: self._updateVeto(gameID)
        self._updateResults(gameID, sides, winningSide,
                            adj=self.penalizeDeclines, declined=True)

    @staticmethod
    def _removeEntity(table, ID, identifier='ID'):
        table.removeMatchingEntities({identifier: {'value': ID,
                                                   'type': 'positive'}})

    @noisy
    def _deleteGame(self, gameData, preserve=True, adjust=True):
        if self.preserveRecords and preserve:
            finStr = datetime.strftime(datetime.now(), self.TIMEFORMAT)
            self._updateEntityValue(self.games, gameData['ID'],
                                    Finished=finStr)
        else: self._removeEntity(self.games, gameData['ID'])
        if not adjust: return
        sides = self._getGameSidesFromData(gameData)
        self._finishGameForTeams(sides)

    @noisy
    def _deleteGameByID(self, gameID, preserve=True, adjust=True):
        self._deleteGame(self._fetchGameData(gameID), preserve, adjust)

    @classmethod
    def _getGameSidesFromData(cls, gameData, processFn=str):
        results = list()
        sides = gameData['Sides'].split(cls.SEP_SIDES)
        for side in sides:
            results.append(set(processFn(t) for t in side.split(cls.SEP_TEAMS)))
        return results

    @noisy
    def _getGameSides(self, gameID):
        gameData = self._fetchGameData(gameID)
        return self._getGameSidesFromData(gameData)

    @noisy
    def _usingTempTeams(self, team):
        return (self.tempTeams is not None and str(team) in self.tempTeams)

    @noisy
    def _getTeamRating(self, team):
        team = str(team)
        if self._usingTempTeams(team): return self.tempTeams[str(team)]
        teamData = self._fetchTeamData(team)
        return teamData['Rating']

    @noisy
    def _adjustRating(self, team, adjustment):
        rating = list(self._splitRating(self._getTeamRating(team)))
        rating[0] += adjustment
        rating = self._unsplitRtg(rating)
        if self._usingTempTeams(team): self.tempTeams[str(team)] = rating
        else: self._updateEntityValue(self.teams, team, Rating=rating)

    @noisy
    def _penalizeVeto(self, gameData):
        teams = self._getGameTeams(gameData)
        for team in teams:
            self._adjustRating(team, -self.vetoPenalty)

    @noisy
    def _vetoCurrentTemplate(self, gameData):
        vetos = gameData['Vetoed'] + self.SEP_VETOS + str(gameData['Template'])
        if vetos[0] == self.SEP_VETOS: vetos = vetos[1:]
        vetoCount = int(gameData['Vetos']) + 1
        self._updateEntityValue(self.games, gameData['ID'], Vetoed=vetos,
                                Vetos=vetoCount, Template='', WarlightID='')
        self._adjustTemplateGameCount(gameData['Template'], -1)

    @noisy
    def _setGameTemplate(self, gameData, tempID):
        self._updateEntityValue(self.games, gameData['ID'], Template=tempID)
        self._adjustTemplateGameCount(tempID, 1)
        gameData['Template'] = tempID

    @classmethod
    def _getPlayersFromData(cls, data):
        return cls._unpackInts(data['Players'], cls.SEP_PLYR)

    @noisy
    def _getTeamPlayers(self, team):
        return self._getPlayersFromData(self._fetchTeamData(team))

    @noisy
    def _getSidePlayers(self, side):
        players = list()
        for team in side:
            players += self._getTeamPlayers(team)
        return players

    @noisy
    def _assembleTeams(self, gameData):
        teams = list()
        sides = gameData['Sides'].split(self.SEP_SIDES)
        for side in sides:
            sideTeams = side.split(self.SEP_TEAMS)
            teams.append(tuple(self._getSidePlayers(sideTeams)))
        return teams

    @noisy
    def _getTeamName(self, teamID):
        teamData = self._fetchTeamData(teamID)
        return teamData['Name']

    @noisy
    def _getNameInfo(self, side, maxLen=None):
        nameInfo = list()
        for team in side.split(self.SEP_TEAMS):
            nameInfo.append("+")
            teamName = self._fitToMaxLen(self._getTeamName(team), maxLen)
            nameInfo.append(teamName)
        return nameInfo[1:]

    @staticmethod
    def _fitToMaxLen(val, maxLen, replace="..."):
        if maxLen is not None and len(val) > maxLen:
            replace = replace[:maxLen]
            repLen = len(replace)
            return val[:maxLen-repLen] + replace
        return val

    @noisy
    def _getGameName(self, gameData, maxLen=50):
        start = self.leagueAcronym + " | "
        nameData = list()
        for side in gameData['Sides'].split(self.SEP_SIDES):
            nameData.append(" vs ")
            nameInfo = self._getNameInfo(side, self.nameLength)
            nameData += nameInfo
        name = self._fitToMaxLen((start + "".join(nameData[1:])),
                                maxLen)
        return name

    @noisy
    def _getPrettyGlickoRating(self, rating):
        return rating.split(self.SEP_RTG)[0]

    @noisy
    def _getPrettyTrueSkillRating(self, rating):
        mu, sigma = [int(i) for i in rating.split(self.SEP_RTG)]
        return str(mu - 3 * sigma)

    @noisy
    def _prettifyRating(self, rating):
        return self.sysDict[self.ratingSystem]['prettify'](rating)

    @noisy
    def _getPrettyRating(self, team):
        teamRating = self._getTeamRating(team)
        return self._prettifyRating(teamRating)

    @noisy
    def _getOfficialRating(self, team):
        return int(self._getPrettyRating(team))

    @noisy
    def _getTeamRank(self, team):
        teamData = self._fetchTeamData(team)
        return int(teamData['Rank'])

    @noisy
    def _sideInfo(self, gameData):
        infoData = list()
        sides = gameData['Sides']
        for side in sides.split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                teamData = self._fetchTeamData(team)
                teamRating = self._prettifyRating(teamData['Rating'])
                teamRank = teamData['Rank']
                teamName = teamData['Name']
                if teamRank is '':
                    teamStr = "%s, not ranked with rating %s" % (teamName,
                                                                 teamRating)
                else:
                    teamStr = "%s, with rank %d and rating %s" % (teamName,
                                                                 int(teamRank),
                                                                 teamRating)
                infoData.append(teamStr)
        infoStr = "\n".join(infoData)
        return infoStr

    @staticmethod
    def _makeThread(thread):
        if '/Forum/' in str(thread): return thread
        return ('https://www.warlight.net/Forum/' + str(thread))

    @noisy
    def _makeInterface(self, interface):
        if (isinstance(interface, str) and not isInteger(interface) and
            'warlight.net/Forum/' not in interface):
            return interface
        return self._makeThread(interface)

    @noisy
    def _getTemplateName(self, gameData):
        templateID = gameData['Template']
        tempData = self._fetchTemplateData(templateID)
        return tempData['Name']

    @property
    def adminName(self):
        parser = PlayerParser(self.admin)
        return str(parser.name)

    @staticmethod
    def _adaptMessage(message, replaceDict):
        for val in replaceDict:
            checkStr = "{{%s}}" % val
            if checkStr in message:
                message = message.replace(checkStr, str(replaceDict[val]()))
        return message

    @noisy
    def _processMessage(self, message, gameData):
        leagueName = lambda: self.name
        clusterName = lambda: self.clusterName
        leagueUrl = lambda: self.leagueUrl
        vetoLimit = lambda: self.vetoLimit
        vetos = lambda: gameData['Vetos']
        makeInterface = lambda: self._makeInterface(self.thread)
        sideInfo = lambda: self._sideInfo(gameData)
        tempName = lambda: self._getTemplateName(gameData)
        adminName = lambda: self.adminName
        expThresh = lambda: self.expiryThreshold
        replaceDict = {'_LEAGUE_NAME': leagueName,
                       self.SET_SUPER_NAME: clusterName,
                       self.SET_URL: leagueUrl,
                       self.SET_VETO_LIMIT: vetoLimit,
                       '_VETOS': vetos,
                       '_LEAGUE_INTERFACE': makeInterface,
                       '_GAME_SIDES': sideInfo,
                       '_TEMPLATE_NAME': tempName,
                       '_LEAGUE_ADMIN': adminName,
                       '_ABANDON_THRESHOLD': expThresh}
        return self._adaptMessage(message, replaceDict)

    @noisy
    def _getGameMessage(self, gameData):
        MAX_MESSAGE_LEN = 2048
        msg = self._processMessage(self.leagueMessage, gameData)
        return self._fitToMaxLen(msg, MAX_MESSAGE_LEN)

    @noisy
    def _getAllGameTeams(self, gameData):
        allTeams = list()
        for side in gameData['Sides'].split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                allTeams.append(team)
        return allTeams

    @staticmethod
    def _getOtherTeams(teams, team):
        return [t for t in teams if t != team]

    @noisy
    def _updateTeamHistory(self, team, others):
        oldHistory = self._fetchTeamData(team)['History']
        newStr = (self.SEP_TEAMS).join(others)
        newHistory = (oldHistory + (self.SEP_TEAMS if len(oldHistory) else "")
                      + newStr)
        self._updateEntityValue(self.teams, team, History=newHistory)

    @noisy
    def _updateHistories(self, gameData):
        allTeams = self._getAllGameTeams(gameData)
        for team in allTeams:
            otherTeams = self._getOtherTeams(allTeams, team)
            self._updateTeamHistory(team, otherTeams)

    @staticmethod
    def _strBeginsWith(val, checkStr):
        return (val[:len(checkStr)] == checkStr)

    @noisy
    def _addTempSetting(self, settings, head, data):
        head = head[len(self.KW_TEMPSETTING):]
        head, target = head.split(self.SEP_TEMPSET), settings
        for i in xrange(len(head)):
            elem = head[i]
            if i == len(head) - 1:
                target[elem] = data
            else:
                target[elem] = dict()
                target = target[elem]

    @noisy
    def _addTempOverride(self, overrides, head, data):
        head = head[len(self.KW_TEMPOVERRIDE):]
        overrides.append((head, int(data)))

    @noisy
    def _getTempSettings(self, tempID):
        tempData = self._fetchTemplateData(tempID)
        template = tempData['WarlightID']
        settingsDict, overrides = dict(), list()
        for head in tempData:
            if (tempData[head] == ''): continue
            elif self._strBeginsWith(head, self.KW_TEMPSETTING):
                self._addTempSetting(settingsDict, head, tempData[head])
            elif self._strBeginsWith(head, self.KW_TEMPOVERRIDE):
                self._addTempOverride(overrides, head, tempData[head])
        return template, settingsDict, overrides

    @noisy
    def _createGameFromData(self, gameData):
        temp = int(gameData['Template'])
        tempID, tempSettings, overrides = self._getTempSettings(temp)
        teams = self._assembleTeams(gameData)
        try:
            wlID = self.handler.createGame(tempID, self._getGameName(gameData),
                       teams, settingsDict=tempSettings,
                       overridenBonuses=overrides,
                       teamless=self.teamless,
                       message=self._getGameMessage(gameData))
            self._adjustTemplateGameCount(temp, 1)
            createdStr = datetime.strftime(datetime.now(), self.TIMEFORMAT)
            self._updateEntityValue(self.games, gameData['ID'],
                                    WarlightID=wlID, Created=createdStr)
            return gameData
        except Exception as e:
            sides = gameData['Sides']
            self.parent.log("Failed to make game with %s on %d because of %s" %
                            (sides, temp, repr(e)), self.name, error=True)
            self._deleteGame(gameData, False, False)

    @noisy
    def _createGame(self, gameID):
        gameData = self._fetchGameData(gameID)
        self._createGameFromData(gameData)
        return gameData

    @noisy
    def _makeGame(self, gameID):
        gameData = self._createGame(gameID)
        if gameData is None: return
        for side in gameData['Sides'].split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                self._adjustTeamGameCount(team, 1)
        self._updateHistories(gameData)

    @noisy
    def _getGameVetos(self, gameData):
        vetos = set([v for v in gameData['Vetoed'].split(self.SEP_VETOS)])
        for side in gameData['Sides'].split(self.SEP_SIDES):
            for team in side.split(self.SEP_TEAMS):
                teamData = self._fetchTeamData(team)
                self._updateConflicts(teamData, vetos)
        return set(int(v) for v in vetos)

    @noisy
    def _updateTemplate(self, gameData):
        vetos, ranks, i = self._getGameVetos(gameData), self.templateRanks, 0
        while (i < len(ranks) and ranks[i][0] in vetos): i += 1
        if i < len(ranks):
            newTemp = ranks[i][0]
            self._setGameTemplate(gameData, newTemp)
            self._createGameFromData(gameData)
        else:
            self._deleteGame(gameData)

    @classmethod
    def _getVetoDict(cls, vetos):
        results = dict()
        for temp in vetos.split(cls.SEP_VETOS):
            if len(temp) == 0: continue
            tempID, vetoCt = temp.split(cls.SEP_VETOCT)
            results[int(tempID)] = int(vetoCt)
        return results

    @noisy
    def _getTeamVetoDict(self, teamID):
        teamData = self._fetchTeamData(teamID)
        return self._getVetoDict(teamData['Vetos'])

    @noisy
    def _packageVetoDict(self, vetoDict):
        tempData = [(str(temp) + self.SEP_VETOCT + str(vetoDict[temp]))
                    for temp in vetoDict]
        return (self.SEP_VETOS).join(tempData)

    @noisy
    def _updateVetoCt(self, oldVetos, template, adj):
        vetoDict = self._getVetoDict(oldVetos)
        template = int(template)
        if template not in vetoDict: vetoDict[template] = int(adj)
        else: vetoDict[template] += int(adj)
        return self._packageVetoDict(vetoDict)

    @noisy
    def _updateTeamVetos(self, team, template, adj):
        teamData = self._fetchTeamData(team)
        oldVetos = teamData['Vetos']
        if str(template) not in oldVetos:
            newVetos = (oldVetos + self.SEP_VETOS + str(template) +
                        self.SEP_VETOCT + str(adj))
            if len(oldVetos) == 0: newVetos = newVetos[1:]
        else: newVetos = self._updateVetoCt(oldVetos, template, adj)
        self._updateEntityValue(self.teams, team, Vetos=newVetos)

    @noisy
    def _updateGameVetos(self, teams, template):
        for team in teams: self._updateTeamVetos(team, template, 1)

    @classmethod
    def _getTeams(cls, gameData):
        results = set()
        sides = gameData['Sides'].split(cls.SEP_SIDES)
        for side in sides:
            teams = side.split(cls.SEP_TEAMS)
            for team in teams:
                results.add(int(team))
        return results

    @noisy
    def _updateVeto(self, gameID):
        gameData = self._fetchGameData(gameID)
        if int(gameData['Vetos']) >= self.vetoLimit:
            self._penalizeVeto(gameData)
            self._deleteGame(gameData)
        else:
            template = gameData['Template']
            self._vetoCurrentTemplate(gameData)
            self._updateGameVetos(self._getTeams(gameData), template)
            self._updateTemplate(gameData)

    @staticmethod
    def _getOneArgFunc(fun, *args):
        return lambda x: fun(x, *args)

    @noisy
    def _updateGame(self, warlightID, gameID, createdTime):
        created = datetime.strptime(createdTime, self.TIMEFORMAT)
        status = self._fetchGameStatus(gameID, warlightID, created)
        if status is not None:
            updateWin = self._getOneArgFunc(self._updateWinners, status[1:])
            updateDecline = self._getOneArgFunc(self._updateDecline,
                                                status[1:])
            {'FINISHED': updateWin, 'DECLINED': updateDecline,
             'ABANDONED': self._updateVeto}.get(status[0])(gameID)

    @noisy
    def _wipeRank(self, teamID):
        self._updateEntityValue(self.teams, teamID, Rank='')

    @noisy
    def _eligibleForRank(self, teamData):
        return ('FALSE' not in teamData['Confirmations'] and
                int(teamData['Finished']) >= self.minToRank and
                int(teamData['Limit']) >= self.minLimitToRank)

    @staticmethod
    def _hasRank(teamData):
        return (teamData['Rank'] is not '')

    @noisy
    def _rankUsingRatings(self, teamRatings):
        teamRatings.sort(key = lambda x: x[1]) # sort using ratings
        teamRatings.reverse()
        rank, previous, offset = 0, None, 0
        for team in teamRatings:
            teamID, teamRtg = team
            if teamRtg != previous:
                previous = teamRtg
                rank += offset + 1
            else: offset += 1
            self._updateEntityValue(self.teams, teamID, Rank=rank)

    @noisy
    def _updateRanks(self):
        teamRatings = list()
        for team in self.allTeams:
            if self._eligibleForRank(team):
                teamRatings.append((team['ID'],
                                    self._getOfficialRating(team['ID'])))
            elif self._hasRank(team): self._wipeRank(team['ID'])
        self._rankUsingRatings(teamRatings)

    @runPhase
    def _updateGames(self):
        gamesToCheck = self.unfinishedGames
        for game in gamesToCheck:
            try:
                self._updateGame(game, gamesToCheck[game]['ID'],
                                 gamesToCheck[game]['Created'])
            except (SheetErrors.SheetError, SheetErrors.DataError):
                self.parent.log("Failed to update game: " + str(game),
                                league=self.name, error=True)
            except ValueError:
                self._makeGame(gamesToCheck[game]['ID'])

    @noisy
    def _checkExcess(self, playerCount):
        if self.teamLimit is None: return False
        return (playerCount > self.teamLimit)

    @noisy
    def _changeLimit(self, teamID, limit):
        limit = int(limit)
        limit = self._checkLimit(limit) if limit != 0 else 0
        self._updateEntityValue(self.teams, teamID, Limit=limit)

    @classmethod
    def _updatePlayerCounts(cls, playerCounts, players):
        for player in players:
            cls._updateCountInDict(playerCounts, player)

    @noisy
    def _setProbation(self, teamID, start=None):
        if start is None: probStr = ''
        else: probStr = datetime.strftime(start, self.TIMEFORMAT)
        self._updateEntityValue(self.teams, teamID,
                               **{'Probation Start': probStr})

    @noisy
    def _wipeProbation(self, teamID):
        self._setProbation(teamID)

    @noisy
    def _startProbation(self, teamID):
        self._setProbation(teamID, datetime.now())

    @noisy
    def _meetsRetention(self, teamData):
        teamFinished = int(teamData['Finished'])
        teamRating = int(self._prettifyRating(teamData['Rating']))
        teamRank = int(teamData['Rank'])
        return (teamFinished < self.minToCull or
                (self._valueInRange(teamRating, self.minRating, None) and
                 self._valueInRange(teamRank, None, self.maxRank)))

    @noisy
    def _checkTeamProbationUsingData(self, teamID, teamData):
        start = teamData['Probation Start']
        if self._meetsRetention(teamData):
            if len(start) > 0: self._wipeProbation(teamID)
        elif len(start) == 0:
            self._startProbation(teamID)
        else: # already on probation
            start = datetime.strptime(start, self.TIMEFORMAT)
            if (datetime.now() - start).days >= self.gracePeriod:
                raise ImproperInput("Team %s has been culled" % (str(teamID)))

    @noisy
    def _checkTeamRatingUsingData(self, teamID, teamData):
        if 'Probation Start' not in teamData: return
        self._checkTeamProbationUsingData(teamID, teamData)

    @noisy
    def _checkTeamRating(self, teamID):
        teamData = self._fetchTeamData(teamID)
        return self._checkTeamRatingUsingData(teamID, teamData)

    @noisy
    def _validateTeam(self, teamID, players):
        """returns True is the team has been dropped from the league"""
        teamData = self._fetchTeamData(teamID)
        if int(teamData['Limit']) < 1: return False
        try:
            self._checkTeamRatingUsingData(teamID, teamData)
            self._checkTeam(players, teamID)
            self._checkConsistentClan(players, self.maintainSameClan)
            return False
        except ImproperInput as e:
            self.parent.log(("Removing %s because: %s" % (str(teamID),
                             e.message)), self.name)
            self._changeLimit(teamID, 0)
            return True

    @noisy
    def _validatePlayerGroup(self, playerCounts, players, teamID):
        """returns True is the player's team has been dropped"""
        for player in players:
            if player not in playerCounts: continue
            if self._checkExcess(playerCounts[player]):
                self._changeLimit(teamID, 0)
                return True
        return False

    @staticmethod
    def _isInactive(team):
        confirmations, limit = team['Confirmations'], int(team['Limit'])
        return ('FALSE' in confirmations or limit < 1)

    @staticmethod
    def _wasActive(team):
        count, finished = int(team['Ongoing']), int(team['Finished'])
        return bool(count + finished)

    @runPhase
    def _validatePlayers(self):
        playerCounts, allTeams = dict(), self.allTeams
        for i in xrange(len(allTeams)):
            team = allTeams[i]
            if self._isInactive(team): continue
            ID, players = team['ID'], team['Players'].split(self.SEP_PLYR)
            if not (self._validateTeam(ID, players) or
                    self._validatePlayerGroup(playerCounts, players, ID)):
                self._updatePlayerCounts(playerCounts, players)

    @classmethod
    def _splitRating(cls, rating):
        return tuple(int(x) for x in rating.split(cls.SEP_RTG))

    @noisy
    def _updateSums(self, rating, sums):
        splitRtg = self._splitRating(str(rating))
        for i in xrange(len(splitRtg)):
            if i >= len(sums): sums.append(splitRtg[i])
            else: sums[i] += splitRtg[i]

    @noisy
    def _addRatings(self, ratings):
        sums = list()
        for rating in ratings: self._updateSums(rating, sums)
        return (self.SEP_RTG).join(str(x) for x in sums)

    @noisy
    def _getEloPairingParity(self, rtg1, rtg2):
        return (self.eloEnv.quality_1vs1(int(rtg1), int(rtg2)))

    @noisy
    def _getEloParity(self, ratings):
        rtgs = [int(rating) for rating in ratings]
        return self._getAverageParity(rtgs, self._getEloPairingParity)

    @staticmethod
    def _getAverageParity(ratings, parityFn):
        paritySum, matchups = 0.0, 0
        for i in xrange(len(ratings)):
            rtg1 = ratings[i]
            for j in xrange(i+1, len(ratings)):
                rtg2 = ratings[j]
                paritySum += parityFn(rtg1, rtg2)
                matchups += 1
        return max(min(round((Decimal(paritySum) / Decimal(matchups)), 2),
                   1.0), 0.0)

    @noisy
    def _getGlickoPairingParity(self, rtg1, rtg2):
        rating1, rd1 = rtg1
        rating2, rd2 = rtg2
        LN10 = math.log(10, math.e)
        cnst = self.glickoRating / 15.0 * 4.0
        glickoP = ((3 * (LN10 ** 2)) / ((math.pi ** 2) * (cnst ** 2)))
        glickoF = lambda rd: 1.0 / math.sqrt(1 + glickoP * rd ** 2)
        glickoE = lambda r1, s1, r2, s2: (1.0 / (1.0 + 10 ** (-(r1 - r2) *
                  glickoF(math.sqrt(s1 ** 2 + s2 ** 2)) / cnst)))
        odds = glickoE(rating1, rd1, rating2, rd2)
        shortfall = abs(0.5 - odds)
        return (1.0 - (shortfall * 2))

    @noisy
    def _getGlickoParity(self, ratings):
        rtgs = [tuple(int(r) for r in rating.split(self.SEP_RTG))
                for rating in ratings]
        return self._getAverageParity(rtgs, self._getGlickoPairingParity)

    @noisy
    def _getTrueSkillParity(self, ratings):
        rtgs = [rating.split(self.SEP_RTG) for rating in ratings]
        players = [tuple(self.trueSkillEnv.create_rating(int(rtg[0]),
                   int(rtg[1])),) for rtg in rtgs]
        return (self.trueSkillEnv.quality(players))

    @staticmethod
    def _getVarianceScore(vals):
        average = Decimal(sum(vals)) / Decimal(len(vals))
        variance = Decimal(0)
        for val in vals:
            variance += ((Decimal(val) - Decimal(average)) ** 2)
        sd = math.sqrt(float(variance))
        score = max(min(1.0, (sd / float(average))), 0.0)
        return (1.0 - score)

    @noisy
    def _getWinCountParity(self, ratings):
        winCounts = [int(r) for r in ratings]
        return self._getVarianceScore(winCounts)

    @noisy
    def _getWinRateParity(self, ratings):
        winRates = [int(r.split(self.SEP_RTG)[0]) for r in ratings]
        return self._getVarianceScore(winRates)

    @noisy
    def _getParityScore(self, ratings):
        """
        given two ratings, returns a score from 0.0 to 1.0
        representing the preferability of the pairing
        """
        return self.sysDict[self.ratingSystem]['parity'](ratings)

    @classmethod
    def _getPlayers(cls, team):
        players = team['Players'].split(cls.SEP_PLYR)
        players = [int(p) for p in players]
        return players

    @classmethod
    def _getHistory(cls, team):
        history = team['History'].split(cls.SEP_TEAMS)
        return [str(t) for t in history if len(t)]

    @staticmethod
    def _addToSetWithinDict(data, label, value):
        if label not in data:
            data[label] = set()
        data[label].add(value)

    @noisy
    def _makePlayersDict(self, teams):
        playerDict, clanDict = dict(), dict()
        for team in teams:
            players = self._getPlayers(team)
            ID = str(team['ID'])
            for player in players:
                self._addToSetWithinDict(playerDict, player, ID)
                if self.forbidClanMatchups:
                    self._addToSetWithinDict(clanDict,
                                             PlayerParser(player).clanID, ID)
        return playerDict, clanDict

    @noisy
    def _narrowHistory(self, history):
        results = set()
        for item in set(history):
            if history.count(item) >= self.rematchCap:
                results.add(str(item))
        return results

    @noisy
    def _updateClanConflicts(self, conflicts, player, clansDict):
        if not self.forbidClanMatchups: return
        playerClan = PlayerParser(player).clanID
        conflicts.update(clansDict.get(playerClan, set()))

    @property
    def teamsDict(self):
        result, allTeams = dict(), self.activeTeams
        playersDict, clansDict = self._makePlayersDict(allTeams)
        for team in allTeams:
            if ('FALSE' in team['Confirmations']): continue
            teamDict = {'rating': team['Rating'],
                        'count': max(0,
                                 (int(team['Limit']) -
                                  int(team['Ongoing'])))}
            conflicts = set()
            ID = str(team['ID'])
            players = self._getPlayers(team)
            for player in players:
                conflicts.update(playersDict[player])
                self._updateClanConflicts(conflicts, player, clansDict)
            fullHistory = self._getHistory(team)
            if self.rematchLimit == self.KW_ALL:
                history = fullHistory
            else:
                history = fullHistory[-(self.rematchLimit):]
            conflicts.update(self._narrowHistory(history))
            teamDict['conflicts'] = conflicts
            result[ID] = teamDict
        return result

    @noisy
    def _makeGrouping(self, groupingDict, groupSize, groupSep,
                      reverseParity):
        if reverseParity:
            score_fn = lambda *args: 1.0 - self._getParityScore(args)
        else:
            score_fn = lambda *args: self._getParityScore(args)
        groups = pair.group_teams(groupingDict, score_fn=score_fn,
                                  game_size=groupSize, scramble=True)
        return {groupSep.join([str(x) for x in sorted(group)])
                for group in groups}

    @noisy
    def _makeSides(self, teamsDict):
        return self._makeGrouping(teamsDict, self.sideSize, self.SEP_TEAMS,
                                  self.reverseSideParity)

    @noisy
    def _getSideRating(self, side, teamsDict):
        ratings = [teamsDict[team]['rating']
                   for team in side.split(self.SEP_TEAMS)]
        return self._addRatings(ratings)

    @noisy
    def _makeTeamsToSides(self, sides):
        result = dict()
        for side in sides:
            teams = side.split(self.SEP_TEAMS)
            for team in teams: self._addToSetWithinDict(result, team, side)
        return result

    @noisy
    def _getSideConflicts(self, side, teamsDict, teamsToSides):
        teams = side.split(self.SEP_TEAMS)
        conflicts = set()
        for team in teams:
            teamConflicts = teamsDict[team]['conflicts'].union({str(team),})
            for conflict in teamConflicts:
                for conflictingSide in teamsToSides.get(conflict, set()):
                    conflicts.add(conflictingSide)
        return conflicts

    @noisy
    def _makeSidesDict(self, sides, teamsDict):
        result, teamsToSides = dict(), self._makeTeamsToSides(sides)
        for side in sides:
            sideDict = {'rating': self._getSideRating(side, teamsDict),
                        'conflicts': self._getSideConflicts(side, teamsDict,
                            teamsToSides),
                        'count': teamsDict.get(side, {'count': 1})['count']}
            result[side] = sideDict
        return result

    @noisy
    def _makeMatchings(self, sidesDict):
        return self._makeGrouping(sidesDict, self.gameSize, self.SEP_SIDES,
                                  self.reverseParity)

    @staticmethod
    def _turnNoneIntoMutable(val, mutable):
        if val is None: return mutable()
        return val

    @property
    def templatesDict(self):
        templateIDs, result = self.usableTemplateIDs, dict()
        for ID in templateIDs:
            result[str(ID)] = {'usage': int(templateIDs[ID]['Usage'])}
        return result

    @staticmethod
    def _updateCountInDict(data, label, count=1):
        if label not in data: data[label] = count
        else: data[label] += count

    @staticmethod
    def _splitAndFilter(string, splitter):
        return [v for v in string.split(splitter) if len(v)]

    @noisy
    def _updateScores(self, teamData, scores):
        vetos = self._getVetoDict(teamData['Vetos'])
        for veto in vetos: self._updateCountInDict(scores, str(veto),
                                                   vetos[veto])

    @noisy
    def _updateConflicts(self, teamData, conflicts):
        drops = self._splitAndFilter(teamData['Drops'], self.SEP_DROPS)
        for drop in drops: conflicts.add(drop)

    @noisy
    def _getScoresAndConflicts(self, matching):
        scores, conflicts = dict(), set()
        sides = matching.split(self.SEP_SIDES)
        for side in sides:
            teams = side.split(self.SEP_TEAMS)
            for team in teams:
                teamData = self._fetchTeamData(team)
                self._updateScores(teamData, scores)
                self._updateConflicts(teamData, conflicts)
        return scores, conflicts

    @noisy
    def _makeMatchingsDict(self, matchings):
        result, numTemps = dict(), len(self.usableTemplateIDs)
        for matching in matchings:
            matchDict = {'count': 1}
            scores, conflicts = self._getScoresAndConflicts(matching)
            if (len(conflicts) == numTemps): continue
            matchDict['scores'] = scores
            matchDict['conflicts'] = conflicts
            result[matching] = matchDict
        return result

    @noisy
    def _makeBatch(self, matchings):
        templatesDict = self.templatesDict
        matchingsDict = self._makeMatchingsDict(matchings)
        assignments = pair.assign_templates(matchingsDict, templatesDict, True)
        return [{'Sides': a[0], 'Template': a[1]} for a in assignments]

    @classmethod
    def _addEntity(cls, table, entity):
        table.addEntity(entity)

    @noisy
    def _getBatchStartingID(self):
        gameIDs = self.gameIDs
        if len(gameIDs): return max(int(ID) for ID in gameIDs) + 1
        return 0

    @noisy
    def _createBatch(self, batch):
        currentID = self._getBatchStartingID()
        for game in batch:
            try:
                self._addEntity(self.games,
                    {'ID': currentID, 'WarlightID': '', 'Created': '',
                     'Winners': '', 'Sides': game['Sides'], 'Vetos': 0,
                     'Vetoed': '', 'Finished': '',
                     'Template': game['Template']})
                self._makeGame(currentID)
                currentID += 1
            except (SheetErrors.DataError, SheetErrors.SheetError) as e:
                self.parent.log(("Failed to add game to sheet due to %s" %
                                 str(e)), self.name, error=True)
            except APIError as e:
                self.parent.log(("Failed to create game with ID %d" %
                                 (currentID)), self.name, error=True)

    @runPhase
    def _createGames(self):
        teamsDict = self.teamsDict
        sides = self._makeSides(teamsDict) if self.sideSize > 1 else teamsDict
        sidesDict = self._makeSidesDict(sides, teamsDict)
        matchings = self._makeMatchings(sidesDict)
        batch = self._makeBatch(matchings)
        self._createBatch(batch)

    @classmethod
    def _reduceToActive(cls, teams):
        return [t for t in teams if not cls._isInactive(t)]

    @classmethod
    def _onceActive(cls, t):
        return ((not cls._isInactive(t) or cls._wasActive(t)))

    @classmethod
    def _reduceToOnceActive(cls, teams):
        return [t for t in teams if cls._onceActive(t)]

    @classmethod
    def _adjustAndPackage(cls, team, adj, floor=None):
        rtg = list(cls._splitRating(team['Rating']))
        rtg[0] = int(round(Decimal(rtg[0]) + Decimal(adj)))
        if floor is not None: rtg[0] = max(rtg[0], floor)
        return cls._unsplitRtg(rtg)

    @runPhase
    def _rescaleRatings(self):
        if not self.maintainTotal: return
        allTeams = self.allTeams
        actives = self._reduceToActive(allTeams)
        total, count = 0, len(actives)
        for team in actives:
            total += self._splitRating(team['Rating'])[0]
        expected = count * self._splitRating(self.defaultRating)[0]
        adjustment = (Decimal(expected) - Decimal(total)) / Decimal(count)
        for team in self._reduceToOnceActive(allTeams):
            rating = self._adjustAndPackage(team, adjustment)
            self._updateTeamRating(team['ID'], rating)

    @property
    def runTime(self):
        return (self.latestRun == '' or ((datetime.now() - self.latestRun) >=
                timedelta(minutes=self.waitPeriod)))

    @property
    def decayTime(self):
        return (self.latestRun == '' or
                ((datetime.now() - self.latestRun).days > 0))

    @noisy
    def _decayRating(self, team):
        if (self._isInactive(team) and self._wasActive(team)):
            rating = self._adjustAndPackage(team, -self.ratingDecay,
                                           self.penaltyFloor)
            self._updateTeamRating(team['ID'], rating)

    @runPhase
    def _decayRatings(self):
        if (self.ratingDecay == 0 or
            not self.decayTime): return
        allTeams = self.allTeams
        for team in allTeams: self._decayRating(team)

    @noisy
    def _dateUnexpired(self, finishDate, current):
        if finishDate == '': return False
        return ((current -
                  datetime.strptime(finishDate, self.TIMEFORMAT)) <=
                timedelta(days=self.retentionRange))

    @property
    def unexpiredGames(self):
        allGames, current = self._getExtantEntities(self.games), datetime.now()
        return [g for g in allGames if
                self._dateUnexpired(g['Finished'], current)]

    @staticmethod
    def _getAllTeams(sides):
        return set().union(*sides)

    @classmethod
    def _unpackDeclineWinners(cls, winners, sides):
        allTeams = cls._getAllTeams(sides)
        sides = [winners, allTeams-winners]
        return sides, 0, True

    @staticmethod
    def _removeMark(string, mark):
        if mark in string: return string.replace(mark, "")
        return string

    @classmethod
    def _removeDeclineMark(cls, winners):
        return cls._removeMark(winners, cls.MARK_DECLINE)

    @classmethod
    def _unpackWinners(cls, game):
        winners, sides = game['Winners'], game['Sides'].split(cls.SEP_SIDES)
        declined = cls.MARK_DECLINE in winners
        winners = cls._removeDeclineMark(winners)
        sides = [set(side.split(cls.SEP_TEAMS)) for side in sides]
        winners = set(winners.split(cls.SEP_TEAMS))
        winningSide = None
        if declined: return cls._unpackDeclineWinners(winners, sides)
        for i in xrange(len(sides)):
            if len(sides[i] & winners) > 0: winningSide = i
        return sides, winningSide, declined

    @noisy
    def _calculateVetos(self, sides):
        if not self.vetoPenalty: return
        for team in self._getAllTeams(sides):
            self._adjustRating(team, -self.vetoPenalty)

    @noisy
    def _calculateResults(self, sides, winningSide):
        newRatings = self._getNewRatings(sides, winningSide)
        for team in newRatings:
            self.tempTeams[str(team)] = newRatings[team]

    @noisy
    def _runCalculations(self):
        games = self.unexpiredGames
        for game in games:
            sides, winningSide, declined = self._unpackWinners(game)
            if winningSide is None:
                self._calculateVetos(sides)
            elif declined and not self.penalizeDeclines:
                continue
            else:
                self._calculateResults(sides, winningSide)

    @noisy
    def _updateTeamRatings(self):
        self._updateRatings(self.tempTeams)

    @runPhase
    def _calculateRatings(self):
        if self.retentionRange is None: return
        self.tempTeams = dict()
        for team in self.allTeams:
            self.tempTeams[str(team['ID'])] = self.defaultRating
        self._runCalculations()
        self._updateTeamRatings()
        self.tempTeams = None

    @noisy
    def _applyRatingAdjustments(self):
        self._rescaleRatings()
        self._decayRatings()
        self._calculateRatings()

    def run(self):
        """
        runs the league in four phases
        1. check on and update ongoing games
        2. execute orders from threads
        3. update teams using prereqs
        4. create new games
        """
        if self.runTime:
            self._updateGames()
            self._applyRatingAdjustments()
            self._restoreTeams()
            self._executeOrders()
            self._validatePlayers()
            if self.active: self._createGames()
        else: self._executeOrders()

    @classmethod
    def _unpackConfirms(cls, confirms):
        return [(c.upper() == "TRUE") for c in confirms.split(cls.SEP_CONF)]

    @classmethod
    def _unpackInts(cls, string, sep):
        if not len(string): return list()
        return [cls._unpackInt(v) for v in string.split(sep)]

    @staticmethod
    def _unpackInt(val):
        return int(val) if len(str(val)) else val

    @classmethod
    def _zipPlayers(cls, team):
        players = cls._getPlayersFromData(team)
        confirms = cls._unpackConfirms(team['Confirmations'])
        results = dict()
        for i in xrange(len(players)):
            results[players[i]] = {'confirmed': confirms[i]}
        return results

    def _packageTeam(self, team):
        res = {'ID': int(team['ID']),
               'Name': team['Name'],
               'Players': self._zipPlayers(team),
               'Rating': self._splitRating(team['Rating']),
               'Vetos': self._getVetoDict(team['Vetos']),
               'Drops': set(self._unpackInts(team['Drops'], self.SEP_DROPS)),
               'Rank': self._unpackInt(team['Rank']),
               'History': self._unpackInts(team['History'], self.SEP_TEAMS),
               'Finished': int(team['Finished']),
               'Limit': int(team['Limit']),
               'Ongoing': int(team['Ongoing'])}
        if 'Probation Start' in team:
            res['Probation Start'] = self._unpackDateTime(\
                                     team['Probation Start'])
        return res

    @classmethod
    def _unpackDateTime(cls, val):
        if val == '': return val
        return datetime.strptime(val, cls.TIMEFORMAT)

    @classmethod
    def _packageWinners(cls, winners):
        if cls.MARK_DECLINE in winners:
            winners = cls._removeDeclineMark(winners)
        return set(cls._unpackInts(winners, cls.SEP_TEAMS))

    def _packageGame(self, game):
        return {'ID': int(game['ID']),
                'WarlightID': self._unpackInt(game['WarlightID']),
                'Created': self._unpackDateTime(game['Created']),
                'Finished': self._unpackDateTime(game['Finished']),
                'Ongoing': not(len(game['Finished'])),
                'Sides': self._getGameSidesFromData(game, int),
                'Winners': self._packageWinners(game['Winners']),
                'Declined': (self.MARK_DECLINE in game['Winners']),
                'EndedInVeto': (not(len(game['Winners']))
                                and bool(len(game['Finished']))),
                'Vetos': int(game['Vetos']),
                'Vetoed': self._unpackInts(game['Vetoed'], self.SEP_VETOS),
                'Template': self._unpackInt(game['Template'])}

    def _packageTemplate(self, template):
        return {'ID': int(template['ID']),
                'Name': template['Name'],
                'WarlightID': int(template['WarlightID']),
                'Active': self._getBoolProperty(template['Active']),
                'Usage': int(template['Usage'])}

    @staticmethod
    def _packageEntities(entities, packageFn):
        results = list()
        for entity in entities:
            results.append(packageFn(entity))
        return results

    def _packageTeams(self, *teams):
        return self._packageEntities(teams, self._packageTeam)

    def _packageGames(self, *games):
        return self._packageEntities(games, self._packageGame)

    def _packageTemplates(self, *templates):
        return self._packageEntities(templates, self._packageTemplate)

    @staticmethod
    def _fetchAndPackage(fetchFn, packageFn, ID):
        return packageFn(fetchFn(ID))[0]

    def fetchTeam(self, teamID):
        return self._fetchAndPackage(self._fetchTeamData, self._packageTeams,
                                     teamID)

    def fetchAllTeams(self):
        return self._packageTeams(*self.allTeams)

    def fetchGame(self, gameID):
        return self._fetchAndPackage(self._fetchGameData, self._packageGames,
                                     gameID)

    def fetchAllGames(self):
        return self._packageGames(*self._getExtantEntities(self.games))

    def fetchTemplate(self, templateID):
        return self._fetchAndPackage(self._fetchTemplateData,
                                     self._packageTemplates, templateID)

    def fetchAllTemplates(self):
        return self._packageTemplates(*self._getExtantEntities(self.templates))

    @staticmethod
    def _depackageOrder(order, *args):
        results = list()
        for arg in args: results.append(order[arg])
        return results

    def _makeDummy(self, orderType, author, *orders):
        orders = [self.name,] + list(orders)
        return {'type': orderType, 'author': int(author), 'orders': orders}

    @checkAgent
    def addTeam(self, order):
        auth, name, limit = self._depackageOrder(order, 'author', 'teamName',
                                                 'limit')
        self._addTeam(self._makeDummy('add_team', auth, name, limit,
                                      *(order['players'])))

    def _makeConfirmationOrder(self, order, orderType='confirm_team'):
        author, teamName = self._depackageOrder(order, 'author', 'teamName')
        players = order.get('players', list())
        return self._makeDummy(orderType, author, teamName, *players)

    @checkAgent
    def confirmTeam(self, order):
        self._confirmTeam(self._makeConfirmationOrder(order, 'confirm_team'))

    @checkAgent
    def unconfirmTeam(self, order):
        self._unconfirmTeam(self._makeConfirmationOrder(order,
                            'unconfirm_team'))

    def _executeSimpleOrder(self, order, orderType, *args):
        orderFn = self.orderDict[orderType]['internal']
        vals = [order[arg] for arg in args]
        orderFn(self._makeDummy(orderType, *vals))

    @checkAgent
    def setLimit(self, order):
        self._executeSimpleOrder(order, 'set_limit', 'author',
                                 'teamName', 'limit')

    @checkAgent
    def renameTeam(self, order):
        self._executeSimpleOrder(order, 'rename_team', 'author',
                                 'teamName', 'newName')

    @checkAgent
    def removeTeam(self, order):
        self._executeSimpleOrder(order, 'remove_team', 'author', 'teamName')

    def _makeTemplateDropOrder(self, order):
        orderType = order['type']
        author, teamName = self._depackageOrder(order, 'author', 'teamName')
        return self._makeDummy(orderType, author, teamName,
                               *order.get('templates',
                               [order.get('template'),]))

    def _handleTemplateDropOrder(self, order, orderType):
        if 'type' not in order: order['type'] = orderType
        dropFn = self.orderDict[order['type']]['internal']
        dropFn(self._makeTemplateDropOrder(order))

    @checkAgent
    def dropTemplates(self, order):
        self._handleTemplateDropOrder(order, 'drop_templates')

    @checkAgent
    def undropTemplates(self, order):
        self._handleTemplateDropOrder(order, 'undrop_templates')

    @classmethod
    def _makePrefixedList(cls, data, label, prefix, separator):
        value, results = data[label], list()
        if isinstance(value, dict): # recursive case
            for label in value:
                results += cls._makePrefixedList(value, label,
                    (prefix + separator + label), separator)
        else: # base case
            results += [prefix, value]
        return results

    @classmethod
    def _disassembleSettings(cls, settings):
        results = list()
        for setting in settings:
            results += cls._makePrefixedList(settings, setting,
                (cls.KW_TEMPSETTING + str(setting)), cls.SEP_TEMPSET)
        return results

    @classmethod
    def _disassembleOverrides(cls, overrides):
        results = list()
        for override in overrides:
            results += [(cls.KW_TEMPOVERRIDE + str(override)),
                        str(overrides[override])]
        return results

    def _assembleAddOrder(self, order, templateName, warlightID):
        orders = [templateName, warlightID]
        if self.multischeme: orders.append(order['scheme'])
        orders += self._disassembleSettings(order.get('settings', dict()))
        orders += self._disassembleOverrides(order.get('overrides', dict()))
        return orders

    @checkAgent
    def addTemplate(self, order):
        author, tempName, warlightID = self._depackageOrder(order, 'author',
                                           'templateName', 'warlightID')
        orders = self._assembleAddOrder(order, tempName, warlightID)
        self._addTemplate(self._makeDummy('add_template', author, *orders))

    @checkAgent
    def activateTemplate(self, order):
        self._executeSimpleOrder(order, 'activate_template', 'author',
            'templateName')

    @checkAgent
    def deactivateTemplate(self, order):
        self._executeSimpleOrder(order, 'deactivate_template', 'author',
            'templateName')

    @checkAgent
    def quitLeague(self, order):
        author = order['author']
        self._quitLeague(self._makeDummy('quit_league', author,
                                         *(order.get('players', list()))))

    def executeOrders(self, agent, orders):
        for order in orders:
            order['agent'] = agent
        self._runOrderExecution(orders, 'external')
