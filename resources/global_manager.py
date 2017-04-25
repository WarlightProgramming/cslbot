#########################
# global_manager.py
# handles tokens and auth
#########################

# imports
import random
import string
from passlib.hash import pbkdf2_sha256 as token_hash

# main GlobalManager class
class GlobalManager(object):
    # constants
    ADMIN_SHEET = {'ID': 'UNIQUE INT',
                   'AUTHORIZED': 'STRING',
                   'BANNED': 'BOOL'}
    SEP_ID = ";"
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
        TOKEN_LEN = 64
        token = self._randStr(TOKEN_LEN)
        tokenHash = token_hash.hash(token)
        self.agents.updateMatchingEntities({'ID': agentID},
            {'TOKEN HASH': tokenHash}, True)
        return token

    def verifyAgent(self, agentID, token):
        found = self.agents.findEntities({'ID': agentID})
        if (len(found) and str(found[0]['BANNED']).lower() != 'true'):
            return token_hash.verify(token, found[0]['TOKEN HASH'])
        return False

    def _authorizeExistingAdmin(self, data, clusterID):
        clusters = [v for v in data['AUTHORIZED'].split(self.SEP_ID) if len(v)]
        clusters.append(str(clusterID))
        self.admins.updateMatchingEntities({'ID': data['ID']},
            {'AUTHORIZED': (self.SEP_ID).join(c for c in clusters)})

    def _createNewAdmin(self, adminID, clusterID):
        self.admins.addEntity({'ID': adminID, 'AUTHORIZED': str(clusterID)})

    def updateAdmin(self, adminID, clusterID):
        found = self.admins.findEntities({'ID': adminID})
        if len(found): self._authorizeExistingAdmin(found[0], clusterID)
        else: self._createNewAdmin(adminID, clusterID)

    def verifyAdmin(self, adminID, clusterID):
        found = self.admins.findEntities({'ID': adminID, 'BANNED': {'values':
            [True, 'TRUE'], 'type': 'negative'}})
        return (len(found) and
                str(clusterID) in found[0]['AUTHORIZED'].split(self.SEP_ID))
