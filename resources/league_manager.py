########################
# league_sheet.py
# handles a single sheet
########################

# imports
import string
from errors import *

# constants
COMMANDS_TITLE = "Commands"
TITLE_LG = "League"
TITLE_CMD = "Command"
TITLE_ARG = "Args"
LG_ALL = "ALL"
COMMANDS_HEADER = [TITLE_LG, TITLE_CMD, TITLE_ARG]

# main LeagueSheet class
class LeagueSheet(object):

    ## constructor
    ### takes a sheetDB Database object
    def __init__(self, database):
        self.database = database
        self.commands = self.database.fetchTable(COMMANDS_TITLE, 
                                         header=COMMANDS_HEADER)

    ## fetchLeagueCommands
    ### given a league (string), fetches a dictionary
    ### containing all commands for that league
    def fetchLeagueCommands(self, league):
        commands = self.commands.getAllEntities(keyLabel=TITLE_CMD)
        results = dict()
        for command in commands:
            if (commands[command]['League'] == league or 
                commands[command]['League'] == LG_ALL):
                args = commands[command][TITLE_ARG]
                if "," in args: args = args.split(",")
                results[command] = args
        return results

    ## fetchThreadOrders
    ### given a thread ID/URL (string), fetches a list of
    ### orders since the last offset (int)
    def fetchThreadOrders(self, thread, offset):
        startMarker = 'Forum/'
        if startMarker in thread:
            thread = thread[thread.find(startMarker):]
            x = 0
            while thread[x] in string.digits:
                x += 1
            thread = thread[:x]
        threadParser = CommandParser(thread)
        try:
            return threadParser.getCommands(offset)
        except:
            raise ThreadError("Unable to parse thread: %s; with offset: %s"
                              % (thread, offset))

    ## _narrowOrders
    ### narrows a thread orders list to only commands that relate to a league
    def _narrowOrders(self, orders, league):
        return [order for order in orders if 
                (order['orders'][0] == league or
                 order['orders'][0] == LG_ALL)]

    ## _getNonSpecificOrders
    ### retrieves only orders that don't specify a league
    def _getNonSpecificOrders(self, orders, leagues):
        return [order for order in orders if
                (order['orders'][0] not in leagues and
                 order['orders'][0] != LG_ALL)]

    ## _runOrders
    ### runs orders that are not specific to any league
    def _runOrders(self, orders):
        pass

    ## run
    ### runs leagues, updates
    def run(self):
        thread = self.commands.findEntities({TITLE_CMD: 'THREAD',
                                             TITLE_LG: LG_ALL})
        offset = self.commands.findEntities({TITLE_CMD: 'OFFSET',
                                             TITLE_LG: LG_ALL})
        if (len(offset) == 0 or len(thread) == 0):
            raise ThreadError("Improper thread link or offset!")
        thread, offset = thread[0][TITLE_ARG], offset[0][TITLE_ARG]
        orders = self.fetchThreadCommands(thread, offset)
        self._runOrders(self._getNonSpecificOrders(orders))