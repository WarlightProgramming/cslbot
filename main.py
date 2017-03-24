####################
# main.py
# handles everything
####################

# imports
from sheetDB import Credentials
from resources.constants import GOOGLE_CREDS
from resources.league_manager import LeagueManager

if __name__ == '__main__':
    creds = Credentials(GOOGLE_CREDS)
    allLeagues = creds.getAllDatabases(checkFormat=False)
    for league in allLeagues:
        manager = LeagueManager(league)
        manager.run()
