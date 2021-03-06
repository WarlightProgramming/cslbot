########################
# league_manager.py
# handles a single sheet
########################

# imports
import datetime
from resources.utility import isInteger
from resources.order_parser import OrderParser
from resources.league import League
from resources.constants import TIMEFORMAT, LATEST_RUN
from wl_parsers import ForumThreadParser, PlayerParser

# errors
class ThreadError(Exception):
    """error for improper thread"""
    pass

class LeagueError(Exception):
    """error for leagues"""
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
    SEP_CMD = ";"
    ABUSE_THRESHOLD = 5
    PREFIX = "[CSL]"

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

    def __init__(self, database, manager):
        """takes a sheetDB Database object and a GlobalManager object"""
        self.events = {'error': False, 'events': list()}
        self.database = database
        self.manager = manager
        self.commands = self.database.fetchTable(self.COMMANDS_TITLE,
                                         header=self.COMMANDS_HEADER)
        self.logSheet = self.database.fetchTable(self.LOG_TITLE,
                                constraints=self.LOG_CONSTRAINTS)
        self.leagues = self._fetchLeagueNames()
        self.admin = self._validateAdmin(self._getAdmin())

    def _fetchLeagueNames(self):
        matches = self.commands.findEntities({self.TITLE_CMD: {'type':
            'positive', 'value': self.CMD_MAKE}})
        if len(matches): return matches[0][self.TITLE_ARG].split(self.SEP_CMD)
        else: return list()

    def _validateAdmin(self, adminID):
        adminID = int(adminID) if adminID is not None else adminID
        if not (self.manager.verifyAdmin(adminID, self.database.sheet.ID) and
                PlayerParser(adminID).isMember):
            self.log("League admin is not authorized", error=True)
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
        firstPost = posts[0]
        if (self.validationStr not in firstPost['message'] or
            self.PREFIX != firstPost['title'][:len(self.PREFIX)]):
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
        thread = thread.split(splitter)[0]
        if not isInteger(thread): raise ThreadError("Missing thread ID")
        return int(thread)

    def _makeForumThreadParser(self, thread):
        return ForumThreadParser(self._fetchThreadID(thread))

    def _fetchLeagueThread(self):
        thread = self.commands.findEntities({self.TITLE_CMD: 'THREAD'})
        if len(thread) > 0:
            try:
                threadName = thread[0][self.TITLE_ARG]
                parser = self._makeForumThreadParser(threadName)
                self._validateThread(parser)
                return parser
            except ThreadError as err:
                self.log(str(err), error=True)

    def _handleSpecifiedAdmin(self, found):
        if len(found):
            foundAdmin = found[0][self.TITLE_ARG]
            if isInteger(foundAdmin): return foundAdmin
        self.log("Unable to find admin", error=True)

    def _getAdmin(self):
        """fetches the league admin's ID"""
        found = self.commands.findEntities({self.TITLE_CMD: 'ADMIN'})
        parser = self._fetchLeagueThread()
        if (len(found) == 0 and parser is not None):
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

    def _getDefaultResults(self, league):
        if league is not self.LG_ALL:
            return self._fetchLeagueCommands(self.LG_ALL)
        return dict()

    @classmethod
    def _getCommandArgs(cls, commands, command, i):
        return commands[command][i][cls.TITLE_ARG]

    def _addArgToResults(self, results, commands, command, i):
        args = self._getCommandArgs(commands, command, i)
        results[command.upper()] = args

    def _fetchLeagueCommands(self, league):
        """
        given a league (string), fetches a dictionary
        containing all commands for that league
        league-specific commands override commands given to all leagues
        """
        commands = self.commands.getAllEntities(keyLabel=self.TITLE_CMD,
                                                allowDuplicates=True)
        results = self._getDefaultResults(league)
        for command in commands:
            for i in xrange(len(commands[command])):
                if (commands[command][i][self.TITLE_LG] == league):
                    self._addArgToResults(results, commands, command, i)
        return results

    def _fetchThreadOrderData(self, thread, offset):
        thread = self._fetchThreadID(thread)
        threadParser = OrderParser(thread)
        self._validateThread(threadParser)
        try: return threadParser.getOrders(offset)
        except Exception:
            raise ThreadError("Unable to parse thread: %s; with offset: %s"
                              % (thread, offset))

    def _fetchThreadOrders(self, thread, offset):
        """
        given a thread ID/URL (string), fetches a list of
        orders since the last offset (int)
        """
        try: return self._fetchThreadOrderData(thread, offset)
        except ThreadError as e:
            self.log(str(e), error=False)
            return set()

    @classmethod
    def _narrowOrders(cls, orders, league):
        """
        narrows a thread orders list to only orders that relate to a league
        """
        return [order for order in orders if
                len(order.get('orders', list())) and
                (order['orders'][0] == league or
                 order['orders'][0] == cls.LG_ALL)]

    def _getLeagueSheets(self, league):
        suffix = " (%s)" % (league)
        gamesTitle = self.SHEET_GAMES + suffix
        teamsTitle = self.SHEET_TEAMS + suffix
        templatesTitle = self.SHEET_TEMPLATES + suffix
        gamesSheet = self.database.fetchTable(gamesTitle)
        teamsSheet = self.database.fetchTable(teamsTitle)
        templatesSheet = self.database.fetchTable(templatesTitle)
        return gamesSheet, teamsSheet, templatesSheet

    @classmethod
    def _retrieveOffset(cls, found):
        if len(found) == 0: return 0
        return int(found[0][cls.TITLE_ARG])

    def _handleInterfaces(self, league, interface):
        if interface is None: interface = "(no league interface specified)"
        return self._fetchLeagueCommands(league).get('INTERFACE',
                                                     interface)

    def _getInterfaceName(self, thread, league):
        if (isinstance(thread, int) or (isinstance(thread, str) and
            isInteger(thread))):
            return 'https://www.warlight.net/Forum/' + str(thread)
        elif len(thread): return thread
        interfaces = self._fetchLeagueCommands("").get('INTERFACE')
        return self._handleInterfaces(league, interfaces)

    def _checkLeagueExists(self, league):
        if str(league) not in self.leagues:
            raise LeagueError("Nonexistent league")

    def _agentAuthorized(self, agent, league):
        authorized = self.commands.findEntities({self.TITLE_CMD:
            'AUTHORIZED INTERFACES', self.TITLE_LG: league})
        if not len(authorized): return False
        authorized = authorized[0][self.TITLE_ARG].split(self.SEP_CMD)
        return (str(agent) in authorized or str(self.LG_ALL) in authorized)

    def fetchLeague(self, league, threadName=None, orders=None):
        """
        fetches a League object for a league within this cluster
        :param league: (str) name of the league to fetch
        :param thread: (str) URL of League thread
        """
        self._checkLeagueExists(league)
        if orders is None: orders = set()
        if threadName is None: threadName = self._fetchThread()
        interface = self._getInterfaceName(threadName, league)
        games, teams, templates = self._getLeagueSheets(league)
        commands = self._fetchLeagueCommands(league)
        orders = self._narrowOrders(orders, league)
        lgRunner = League(games, teams, templates, commands, orders,
                          self.admin, self, league, interface)
        return lgRunner

    def fetchAllLeagues(self, threadName=None, orders=None):
        results = list()
        for league in self.leagues:
            results.append(self.fetchLeague(league, threadName, orders))
        return results

    def fetchLeagueOrLeagues(self, league, threadName=None, orders=None):
        if league == self.LG_ALL:
            return self.fetchAllLeagues(threadName, orders)
        return [self.fetchLeague(league, threadName, orders),]

    def fetchCommands(self):
        result = dict()
        for league in self.leagues + [self.LG_ALL,]:
            result[league] = self._fetchLeagueCommands(league)
        return result

    def _setCommand(self, league, command, value):
        self.commands.updateMatchingEntities({self.TITLE_CMD: command,
            self.TITLE_LG: league}, {self.TITLE_ARG: value}, True)

    def _checkAgent(self, agent, league):
        if not self._agentAuthorized(agent, league):
            raise LeagueError("Agent not authorized for this league")

    def setCommand(self, agent, league, command, value):
        self._checkAgent(agent, league)
        self._setCommand(league, command, value)

    def _fetchThread(self):
        threadData = self.commands.findEntities({self.TITLE_CMD: 'THREAD'})
        thread = threadData[0][self.TITLE_ARG] if len(threadData) else ""
        return thread

    def _runLeague(self, league, thread=None, orders=None):
        lgRunner = self.fetchLeague(league, thread, orders)
        try:
            lgRunner.run()
            latestTime = datetime.datetime.strftime(datetime.datetime.now(),
                                                    TIMEFORMAT)
            self._setCommand(league, LATEST_RUN, latestTime)
        except Exception as e:
            errStr = str(e)
            failStr = "Failed to run league %s: %s" % (str(league), errStr)
            self.log(failStr, league=league, error=True)

    def runLeague(self, agent, league):
        self._checkAgent(agent, league)
        self._runLeague(league)

    def run(self):
        """runs leagues and updates"""
        if self.admin is None: return
        thread = self._fetchThread()
        offsetData = self.commands.findEntities({self.TITLE_CMD: 'OFFSET'})
        offset = self._retrieveOffset(offsetData)
        orders = (self._fetchThreadOrders(thread, offset) if len(thread)
                  else set())
        for league in self.leagues: self._runLeague(league, thread, orders)
        newOffset = offset + len(orders)
        self.commands.updateMatchingEntities({self.TITLE_CMD:
            {'value': 'OFFSET', 'type': 'positive'}},
            {self.TITLE_ARG: str(newOffset)}, True)
