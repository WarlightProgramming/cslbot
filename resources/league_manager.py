########################
# league_manager.py
# handles a single sheet
########################

# imports
import string
import datetime
from errors import *
from utility import *
from order_parser import OrderParser
from wl_parsers import ForumThreadParser, PlayerParser
from league import League

# constants

## settings
COMMANDS_TITLE = "Settings"
TITLE_LG = "League"
TITLE_CMD = "Command"
TITLE_ARG = "Args"
LG_ALL = "ALL"
COMMANDS_HEADER = [TITLE_LG, TITLE_CMD, TITLE_ARG]
CMD_MAKE = 'LEAGUES'

## log
LOG_TITLE = "Log"
TITLE_TIME = "Time"
TITLE_STATUS = "Error"
TITLE_LEAGUE = "League"
TITLE_DESC = "Description"
LOG_HEADER = [TITLE_TIME, TITLE_STATUS, TITLE_DESC]
LOG_CONSTRAINTS = ["", "BOOL", ""]

## sheets
SHEET_GAMES = "Game Data"
SHEET_TEMPLATES = "Template Data"
SHEET_TEAMS = "Team Data"

# errors
class ThreadError(Exception):
    """error for improper thread"""
    pass

class OrderError(Exception):
    """error for high-level order issues"""
    pass

class LeagueError(Exception):
    """catch-all"""
    pass

# main LeagueManager class
class LeagueManager(object):

    def __init__(self, database):
        """takes a sheetDB Database object"""
        self.database = database
        self.commands = self.database.fetchTable(COMMANDS_TITLE,
                                         header=COMMANDS_HEADER)
        self.logSheet = self.database.fetchTable(LOG_TITLE,
                                constraints=LOG_CONSTRAINTS)
        self.leagues = self.commands.findEntities({TITLE_CMD: CMD_MAKE})\
                       [0][TITLE_ARG].split(',')
        self.admin = self_validateAdmin(self._getAdmin())

    def _validateAdmin(self, adminID):
        adminID = int(adminID)
        parser = PlayerParser(adminID)
        if not parser.isMember:
            self.log("League admin is not a member. Quitting.", error=True)
            raise LeagueError("League admin is not a Member")
        return adminID

    @property
    def validationStr(self):
        name = self.database.sheet.ID
        return "!validate_league " + str(name)

    def _validateThread(self, thread):
        firstPost = parser.getPosts()[0]['message']
        if self.validationStr not in firstPost:
            raise ThreadError("Thread does not confirm league. Quitting.",
                              error=True)

    def _getAdmin(self):
        """fetches the league admin's ID"""
        found = self.commands.findEntities({TITLE_CMD: 'ADMIN'})
        thread = self.commands.findEntities({TITLE_CMD: 'THREAD'})
        parser = ForumThreadParser(int(thread))
        self._validateThread(parser)
        if (len(found) == 0 or not isInteger(found[0][TITLE_ARG])):
            try:
                return parser.getPosts()[0]['author']['ID']
            except:
                self.log("Unable to find admin. Quitting.", error=True)
                raise ThreadError("Unable to parse thread: %s" % (thread))
        else:
            return found[0][TITLE_ARG]

    def log(self, description, league="", error=False):
        """logs an entry onto the sheet"""
        time = datetime.datetime.now()
        self.logSheet.addEntity({TITLE_TIME: time,
                                 TITLE_LEAGUE: league,
                                 TITLE_STATUS: error,
                                 TITLE_DESC: description})

    def fetchLeagueCommands(self, league):
        """
        given a league (string), fetches a dictionary
        containing all commands for that league
        league-specific commands override commands given to all leagues
        """
        commands = self.commands.getAllEntities(keyLabel=TITLE_CMD)
        if league is not LG_ALL:
            results = self.fetchLeagueCommands(LG_ALL)
        else: results = dict()
        for command in commands:
            if (commands[command][TITLE_LG] == league):
                args = commands[command][TITLE_ARG]
                if "," in args: args = args.split(",")
                results[command] = args
        return results

    @staticmethod
    def fetchThreadOrders(thread, offset):
        """
        given a thread ID/URL (string), fetches a list of
        orders since the last offset (int)
        """
        startMarker = 'Forum/'
        if startMarker in thread:
            thread = thread[thread.find(startMarker):]
            x = 0
            while thread[x] in string.digits:
                x += 1
            thread = thread[:x]
        threadParser = OrderParser(thread)
        try:
            return threadParser.getOrders(offset)
        except:
            raise ThreadError("Unable to parse thread: %s; with offset: %s"
                              % (thread, offset))

    @staticmethod
    def _narrowOrders(orders, league):
        """
        narrows a thread orders list to only orders that relate to a league
        """
        return [order for order in orders if
                (order['orders'][0] == league or
                 order['orders'][0] == LG_ALL)]

    @staticmethod
    def _getNonSpecificOrders(orders, leagues):
        """
        retrieves only orders that don't specify a league
        """
        return [order for order in orders if
                (order['orders'][0] not in leagues and
                 order['orders'][0] != LG_ALL)]

    def _setLeagueState(self, newState):
        """changes the global league state"""
        if newState not in ["RUNNING", "NO_GAMES", "NO_COMMANDS",
                            "ENDING", "ENDED"]:
            raise OrderError("Invalid league state: %s" % (newState))
        self.commands.updateMatchingEntities({TITLE_CMD: CMD_STATE,
                                              TITLE_LG: LG_ALL},
                                             {TITLE_ARG: newState})
        if (len(self.commands.findEntities({TITLE_CMD: CMD_STATE,
                                            TITLE_LG: LG_ALL})) == 0):
            self.commands.addEntity({TITLE_CMD: CMD_STATE, TITLE_LG: LG_ALL,
                                     TITLE_ARG: newState})
        self.log("Set global league state to %s" % (newState))

    def _runOrders(self, orders):
        """runs orders that are not specific to any league"""
        for order in orders:
            orderType = order['type'].lower()
            orderCmds = order['orders']
            orderAuthor = order['author']
            try:
                {}[orderType]
            except KeyError:
                self.log("Unrecognized order: %s" % (order['type']))
            except OrderError as err:
                self.log("Order Error: %s" % (str(err)))

    def getLeagueSheets(self, league):
        suffix = " (%s)" % (self.league)
        gamesTitle = SHEET_GAMES + suffix
        teamsTitle = SHEET_TEAMS + suffix
        templatesTitle = SHEET_TEMPLATES + suffix
        gamesSheet = self.database.fetchTable(gamesTitle)
        teamsSheet = self.database.fetchTable(teamsTitle)
        templatesSheet = self.databse.fetchTable(templatesTitle)
        return gamesSheet, teamsSheet, templatesSheet

    def run(self):
        """runs leagues and updates"""
        thread = self.commands.findEntities({TITLE_CMD: 'THREAD'})
        offset = self.commands.findEntities({TITLE_CMD: 'OFFSET'})
        if (len(offset) == 0 or len(thread) == 0):
            raise ThreadError("Improper thread link or offset!")
        thread, offset = thread[0][TITLE_ARG], offset[0][TITLE_ARG]
        orders = self.fetchThreadOrders(thread, offset)
        self._runOrders(self._getNonSpecificOrders(orders, self.leagues))
        for league in self.leagues:
            games, teams, templates = self.getLeagueSheets(league)
            orders = self._narrowOrders(orders, league)
            commands = self.fetchLeagueCommands(league)
            threadID = thread = self.commands.findEntities({TITLE_CMD:
                                                            'THREAD'})
            threadName = 'https://www.warlight.net/Forum/' + str(threadID)
            lgRunner = League(games, teams, templates, commands, orders,
                              self.admin, self, league, threadName)
            try:
                lgRunner.run()
            except Exception as e:
                errStr = str(e)
                failStr = "Failed to run league %s: %s" % (str(league), errStr)
                self.log(failStr, league=league, error=True)
