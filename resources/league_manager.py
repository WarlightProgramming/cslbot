########################
# league_manager.py
# handles a single sheet
########################

# imports
import datetime
import string
from resources.utility import isInteger
from resources.order_parser import OrderParser
from resources.league import League
from resources.constants import TIMEFORMAT
from wl_parsers import ForumThreadParser, PlayerParser

# errors
class ThreadError(Exception):
    """error for improper thread"""
    pass

class OrderError(Exception):
    """error for high-level order issues"""
    pass

# main LeagueManager class
class LeagueManager(object):

    # constants

    ## settings
    COMMANDS_TITLE = "Settings"
    TITLE_LG = "League"
    TITLE_CMD = "Command"
    TITLE_ARG = "Args"
    LG_ALL = "ALL"
    COMMANDS_HEADER = [TITLE_LG, TITLE_CMD, TITLE_ARG]
    CMD_MAKE = 'LEAGUES'
    SEP_CMD = ","
    ABUSE_THRESHOLD = 5

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

    def __init__(self, database):
        """takes a sheetDB Database object"""
        self.database = database
        self.commands = self.database.fetchTable(self.COMMANDS_TITLE,
                                         header=self.COMMANDS_HEADER)
        self.logSheet = self.database.fetchTable(self.LOG_TITLE,
                                constraints=self.LOG_CONSTRAINTS)
        self.leagues = self._fetchLeagueNames()
        self.admin = self._validateAdmin(self._getAdmin())
        self.events = {'error': False, 'events': list()}

    def _fetchLeagueNames(self):
        matches = self.commands.findEntities({self.TITLE_CMD: {'type':
            'positive', 'value': self.CMD_MAKE}})
        if len(matches): return matches[0][self.TITLE_ARG].split(',')
        else: return list()

    def _validateAdmin(self, adminID):
        adminID = int(adminID)
        parser = PlayerParser(adminID)
        if not parser.isMember:
            self.log("League admin is not a Member. Quitting.", error=True)
            return None
        return adminID

    @property
    def validationStr(self):
        name = self.database.sheet.ID
        return "!validate_league " + str(name)

    @staticmethod
    def _getUniqueAuthors(posts):
        authors = set()
        for post in posts: authors.add(post['author'])
        return authors

    def _validateThread(self, parser):
        posts = parser.getPosts()
        authorCount = len(self._getUniqueAuthors(posts))
        if authorCount < self.ABUSE_THRESHOLD:
            errStr = ("Thread must have posts by at least %d unique authors" %
                      (self.ABUSE_THRESHOLD))
            raise ThreadError(errStr)
        firstPost = posts[0]['message']
        if self.validationStr not in firstPost:
            raise ThreadError("Thread missing validation order. Quitting.")

    def _logThreadFailure(self, thread):
        self.log("Unable to scan thread %s. Quitting." % (str(thread)),
                 error=True)

    @staticmethod
    def _fetchThreadID(thread):
        if isInteger(thread): return int(thread)
        searchStr, splitter = '/Forum/', '-'
        if searchStr not in thread: raise ThreadError("Invalid forum URL")
        thread = thread.split(searchStr)[1]
        thread = thread.split('-')[0]
        if not isInteger(thread): raise ThreadError("Missing thread ID")
        return int(thread)

    def _makeForumThreadParser(self, thread):
        return ForumThreadParser(self._fetchThreadID(thread))

    def _fetchLeagueThread(self, offset=0):
        thread = self.commands.findEntities({TITLE_CMD: 'THREAD'})
        if len(thread) > 0:
            try:
                threadName = thread[0][self.TITLE_ARG]
                parser = self._makeForumThreadParser(threadName, offset)
                self._validateThread(parser)
                return parser
            except ThreadError as err:
                self.log(str(err), error=False)

    def _handleSpecifiedAdmin(self, found):
        if len(found) > 0:
            return found[0][TITLE_ARG]
        else:
            self.log("Unable to find admin", error=True)

    def _getAdmin(self):
        """fetches the league admin's ID"""
        found = self.commands.findEntities({TITLE_CMD: 'ADMIN'})
        parser = self._fetchLeagueThread()
        if ((len(found) == 0 or not isInteger(found[0][TITLE_ARG])) and
            parser is not None):
            try: return parser.getPosts()[0]['author']['ID']
            except Exception: self._logThreadFailure(parser.ID)
        else: return self._handleSpecifiedAdmin(found)

    def log(self, description, league="", error=False):
        """logs an entry onto the sheet"""
        time = datetime.datetime.strftime(datetime.datetime.now(), TIMEFORMAT)
        entity = {self.TITLE_TIME: time, self.TITLE_LEAGUE: league,
                  self.TITLE_STATUS: error, self.TITLE_DESC: description}
        self.logSheet.addEntity(entity)
        self.events['events'].append(entity)
        if error: self.events['error'] = True

    def getDefaultResults(self, league):
        if league is not LG_ALL:
            return self.fetchLeagueCommands(LG_ALL)
        return dict()

    @staticmethod
    def getCommandArgs(commands, command):
        args = commands[command][TITLE_ARG].upper()
        if len(args):
            if SEP_CMD in args: return args.split(SEP_CMD)
            return args

    def addArgToResults(self, results, commands, command):
        args = self.getCommandArgs(commands, command)
        if args is not "":
            results[command.upper()] = args

    def fetchLeagueCommands(self, league):
        """
        given a league (string), fetches a dictionary
        containing all commands for that league
        league-specific commands override commands given to all leagues
        """
        commands = self.commands.getAllEntities(keyLabel=TITLE_CMD)
        results = self.getDefaultResults(league)
        for command in commands:
            if (commands[command][TITLE_LG] == league):
                self.addArgToResults(results, commands, command)
        return results

    def fetchThreadOrderData(self, thread, offset):
        thread = self._getThreadName([{TITLE_ARG: thread},])
        threadParser = OrderParser(thread)
        self._validateThread(threadParser)
        try:
            return threadParser.getOrders(offset)
        except:
            raise ThreadError("Unable to parse thread: %s; with offset: %s"
                              % (thread, offset))

    def fetchThreadOrders(self, thread, offset):
        """
        given a thread ID/URL (string), fetches a list of
        orders since the last offset (int)
        """
        try:
            return self.fetchThreadOrderData(thread, offset)
        except ThreadError as e:
            self.log(str(e), error=False)
            return set()

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

    def _runOrders(self, orders):
        """runs orders that are not specific to any league"""
        for order in orders:
            orderType = order['type'].lower()
            try:
                {}[orderType](order)
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

    @staticmethod
    def _retrieveOffset(found):
        if len(found) == 0:
            return 0
        return found[0][TITLE_ARG]

    def _handleInterfaces(self, league, interfaces):
        if len(interfaces) == 0: return "(no league interface specified)"
        elif len(interfaces) > 1:
            return self.fetchLeagueCommands(league).get('INTERFACE',
                                                        interfaces[0])
        return interfaces[0]

    def _getInterfaceName(self, thread, league):
        if (isinstance(thread, int) or (isinstance(thread, str) and
            isInteger(thread))):
            return 'https://www.warlight.net/Forum/' + str(thread)
        interfaces = self.commands.findEntities({TITLE_CMD: 'INTERFACE'})
        return self._handleInterfaces(league, interfaces)

    def run(self):
        """runs leagues and updates"""
        thread = self.commands.findEntities({TITLE_CMD: 'THREAD'})
        offset = self.commands.findEntities({TITLE_CMD: 'OFFSET'})
        orders, offset = set(), 0
        if (len(thread) > 0):
            thread, offset = (self._getThreadName(thread),
                              self._retrieveOffset(offset))
            orders = self.fetchThreadOrders(thread, offset)
            self._runOrders(self._getNonSpecificOrders(orders, self.leagues))
        for league in self.leagues:
            games, teams, templates = self.getLeagueSheets(league)
            orders = self._narrowOrders(orders, league)
            commands = self.fetchLeagueCommands(league)
            threadName = self._getInterfaceName(thread, league)
            lgRunner = League(games, teams, templates, commands, orders,
                              self.admin, self, league, threadName)
            try:
                lgRunner.run()
            except Exception as e:
                errStr = str(e)
                failStr = "Failed to run league %s: %s" % (str(league), errStr)
                self.log(failStr, league=league, error=True)
        newOffset = offset + len(orders)
        self.commands.updateMatchingEntities({TITLE_CMD: {'value': 'OFFSET',
                                                          'type': 'positive'}},
                                             {TITLE_ARG: str(newOffset)})
