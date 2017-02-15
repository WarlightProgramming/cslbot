########################
# league_sheet.py
# handles a single sheet
########################

import string

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
        commands = self.commands.findEntities({TITLE_LG: "ALL"},
                                              keyLabel=TITLE_CMD)
        results = dict()
        for command in commands:
            if (commands[command]['League'] == league or 
                commands[command]['League'] == LG_ALL):
                args = commands[command][TITLE_ARG]
                if "," in args: args = args.split(",")
                results[command] = args
        return results

    ## fetchThreadCommands
    ### given a thread ID/URL (string), fetches a list of
    ### commands since the last offset (int)
    def fetchThreadCommands(self, thread, offset):
        startMarker = 'Forum/'
        if startMarker in thread:
            thread = thread[thread.find(startMarker):]
            x = 0
            while thread[x] in string.digits:
                x += 1
            thread = thread[:x]
        threadParser = CommandParser(thread)
        return threadParser.getCommands(offset)