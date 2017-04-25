#########################
# global_manager.py
# handles tokens and auth
#########################

# imports
import random
import string
from passlib.hash import pbkdf2_sha256 as token_hash

# exceptions
class AuthError(Exception):
    """raised for failed authentication"""
    pass

# main GlobalManager class
class GlobalManager(object):
    # constants
    ADMIN_SHEET = {'ID': 'UNIQUE INT',
                   'AUTHORIZED': 'STRING',
                   'BANNED': 'BOOL'}
    AGENT_SHEET = {'ID': 'UNIQUE INT',
                   'TOKEN HASH': 'STRING',
                   'BANNED': 'BOOL'}

    def __init__(self, database):
        """takes a sheetDB Database object"""
        self.database = database
        self.admins = self._fetchTable(self.ADMIN_SHEET, "Admins")
        self.agents = self._fetchTable(self.AGENT_SHEET, "Agents")

    @staticmethod
    def _makeHeaderAndConstraints(sheet):
        header = list(sheet)
        constraints = [sheet[x] for x in header]
        return header, constraints

    def _fetchTable(self, sheet, title):
        header, constraints = self._makeHeaderAndConstraints(sheet)
        return self.database.fetchTable(title, 1, 2, header=header,
            constraints=constraints)

    @staticmethod
    def _randStr(length):
        return ''.join(random.SystemRandom().choice(string.printable) for
            _ in xrange(length))

    def updateAgentToken(self, agentID):
        TOKEN_LEN, agentID = 64, int(agentID)
        token = self._randStr(TOKEN_LEN)
        tokenHash = token_hash.hash(token)
        self.agents.updateMatchingEntities({'ID': agentID},
            {'TOKEN HASH': tokenHash})

    def verifyAgent(self, agentID, token):
        found = self.agents.findEntities({'ID': agentID})
        if not len(found): return False
        found = found[0]
        if str(found['BANNED']).lower() == 'true': return False
        return token_hash.verify(int(agentID), found['TOKEN HASH'])
