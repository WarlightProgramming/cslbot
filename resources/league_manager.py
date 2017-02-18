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
from wl_parsers import ForumThreadParser

# constants

## commands
COMMANDS_TITLE = "Commands"
TITLE_LG = "League"
TITLE_CMD = "Command"
TITLE_ARG = "Args"
LG_ALL = "ALL"
COMMANDS_HEADER = [TITLE_LG, TITLE_CMD, TITLE_ARG]
CMD_MAKE = 'LEAGUES'
CMD_STATE = 'LEAGUE_STATE'

## log
LOG_TITLE = "Log"
TITLE_TIME = "Time"
TITLE_STATUS = "Error"
TITLE_DESC = "Description"
LOG_HEADER = [TITLE_TIME, TITLE_STATUS, TITLE_DESC]
LOG_CONSTRAINTS = ["", "BOOL", ""]


# main LeagueManager class
class LeagueManager(object):

    ## constructor
    ### takes a sheetDB Database object
    def __init__(self, database):
        self.database = database
        self.commands = self.database.fetchTable(COMMANDS_TITLE,
                                         header=COMMANDS_HEADER)
        self.logSheet = self.database.fetchTable(LOG_TITLE,
                                constraints=LOG_CONSTRAINTS)
        self.leagues = self.commands.findEntities({TITLE_CMD: CMD_MAKE})\
                       [0][TITLE_ARG].split(',')
        self.admin = self._getAdmin()

    ## _getAdmin
    ### fetches the league admin's ID
    def _getAdmin(self):
        found = self.commands.findEntities({TITLE_CMD: 'ADMIN'})
        if (len(found) == 0 or not isInteger(found[0][TITLE_ARG])):
            thread = self.commands.findEntities({TITLE_CMD: 'THREAD'})
            parser = ForumThreadParser(int(thread))
            try:
                return parser.getPosts()[0]['author']['ID']
            except:
                self.log("Unable to find admin. Quitting.", True)
                raise ThreadError("Unable to parse thread: %s" % (thread))
        else:
            return found[0][TITLE_ARG]

    ## log
    ### logs an entry onto the sheet
    def log(self, description, error=False):
        time = datetime.datetime.now()
        self.logSheet.addEntity({TITLE_TIME: time,
                                 TITLE_STATUS: error,
                                 TITLE_DESC: description})

    ## fetchLeagueCommands
    ### given a league (string), fetches a dictionary
    ### containing all commands for that league
    def fetchLeagueCommands(self, league):
        commands = self.commands.getAllEntities(keyLabel=TITLE_CMD)
        results = dict()
        for command in commands:
            if (commands[command][TITLE_LG] == league or
                commands[command][TITLE_LG] == LG_ALL):
                args = commands[command][TITLE_ARG]
                if "," in args: args = args.split(",")
                results[command] = args
        return results

    ## fetchThreadOrders
    ### given a thread ID/URL (string), fetches a list of
    ### orders since the last offset (int)
    @staticmethod
    def fetchThreadOrders(thread, offset):
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

    ## _narrowOrders
    ### narrows a thread orders list to only orders that relate to a league
    @staticmethod
    def _narrowOrders(orders, league):
        return [order for order in orders if
                (order['orders'][0] == league or
                 order['orders'][0] == LG_ALL)]

    ## _getNonSpecificOrders
    ### retrieves only orders that don't specify a league
    @staticmethod
    def _getNonSpecificOrders(orders, leagues):
        return [order for order in orders if
                (order['orders'][0] not in leagues and
                 order['orders'][0] != LG_ALL)]

    ## _setLeagueState
    ### changes the global league state
    def _setLeagueState(self, newState):
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

    ## _runOrders
    ### runs orders that are not specific to any league
    def _runOrders(self, orders):
        for order in orders:
            orderType = order['type'].lower()
            orderCmds = order['orders']
            orderAuthor = order['author']
            try:
                return {}[orderType]
            except KeyError:
                self.log("Unrecognized order: %s" % (order['type']))
            except OrderError as err:
                self.log("Order Error: %s" % (str(err)))

    ## run
    ### runs leagues, updates
    def run(self):
        thread = self.commands.findEntities({TITLE_CMD: 'THREAD'})
        offset = self.commands.findEntities({TITLE_CMD: 'OFFSET'})
        if (len(offset) == 0 or len(thread) == 0):
            raise ThreadError("Improper thread link or offset!")
        thread, offset = thread[0][TITLE_ARG], offset[0][TITLE_ARG]
        orders = self.fetchThreadOrders(thread, offset)
        self._runOrders(self._getNonSpecificOrders(orders, self.leagues))
