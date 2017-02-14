########################
# league_sheet.py
# handles a single sheet
########################

COMMANDS_TITLE = "Commands"

# main LeagueSheet class
class LeagueSheet(object):

    ## constructor
    ### takes a sheetDB Database object
    def __init__(self, database):
        self.database = database