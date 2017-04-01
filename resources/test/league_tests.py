# league_tests.py
## automated tests for the League class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import *
from mock import patch, MagicMock
from resources.league import *

# tests
## decorator tests
def test_runPhase():

    ### dummy test class
    class TestClass:
        parent = MagicMock()
        name = "test"

        @runPhase
        def testPhase(self, val):
            if val is None: raise Exception("This is an exception!")
            return val

    t = TestClass()
    assert_equals(t.testPhase(5), 5)
    t.parent.log.assert_not_called()
    assert_equals(t.testPhase(None), None)
    failStr = ("Phase testPhase failed due to "
               "Exception('This is an exception!',)")
    t.parent.log.assert_called_once_with(failStr, "test", True)

## League class tests
class TestLeague(TestCase):

    @patch('resources.league.League.checkFormat')
    @patch('resources.league.League._makeHandler')
    @patch('resources.league.League._getMods')
    def setUp(self, getMods, makeHandler, checkFormat):
        getMods.return_value = 'MODS'
        self.handler = MagicMock()
        makeHandler.return_value = self.handler
        self.games, self.teams, self.templates = (MagicMock(), MagicMock(),
                                                  MagicMock())
        self.settings, self.orders, self.parent = dict(), list(), MagicMock()
        self.league = League(self.games, self.teams, self.templates,
                             self.settings, self.orders, 'ADMIN', self.parent,
                             'NAME', 'THREADURL')

    def test_init(self):
        assert_equals(self.league.games, self.games)
        assert_equals(self.league.teams, self.teams)
        assert_equals(self.league.templates, self.templates)
        assert_equals(self.league.settings, self.settings)
        assert_equals(self.league.orders, self.orders)
        assert_equals(self.league.admin, 'ADMIN')
        assert_equals(self.league.mods, 'MODS')
        assert_equals(self.league.parent, self.parent)
        assert_equals(self.league.name, 'NAME')
        assert_equals(self.league.thread, 'THREADURL')
        assert_equals(self.league.handler, self.handler)

    @patch('resources.league.json.load')
    @patch('resources.league.APIHandler')
    @patch('resources.league.open')
    @patch('resources.league.API_CREDS')
    def test_makeHandler(self, apiCreds, openFn, handler, loadFn):
        loadFn.return_value = {'E-mail': 'dummyEmail',
                               'APIToken': 'dummyAPIToken'}
        makeHandler = League._makeHandler
        assert_equals(makeHandler(), handler.return_value)
        handler.assert_called_once_with('dummyEmail', 'dummyAPIToken')
        loadFn.assert_called_once_with(openFn.return_value)
        openFn.assert_called_once_with(apiCreds)

    @patch('resources.league.League.fetchProperty')
    def test_getMods(self, fetch):
        fetch.return_value = set()
        assert_equals(self.league._getMods(), {self.league.admin})
        fetch.assert_called_once_with(self.league.SET_MODS, set(),
                                      self.league.getIDGroup)

    def test_sysDict(self):
        assert_equals(self.league.makeRateSysDict(), None)
        assert_true(self.league.RATE_ELO in self.league.sysDict)
        assert_true(self.league.RATE_GLICKO in self.league.sysDict)
        assert_true(self.league.RATE_TRUESKILL in self.league.sysDict)
        assert_true(self.league.RATE_WINCOUNT in self.league.sysDict)
        assert_true(self.league.RATE_WINRATE in self.league.sysDict)
        assert_equals(self.league.sysDict[\
                      self.league.RATE_WINCOUNT]['prettify']("3"), "3")
        assert_equals(self.league.sysDict[\
                      self.league.RATE_WINRATE]['prettify']("3/41"), "3")

    def test_checkSheet(self):
        table = MagicMock()
        table.reverseHeader = {'Here': 1, 'There': 2}
        header = {'Here', 'There', 'Everywhere', 'Nowhere'}
        constraints = {'Here': 'UNIQUE', 'There': '', 'Everywhere': 'INT'}
        assert_raises(ImproperLeague, self.league.checkSheet, table, header,
                      constraints, reformat=False)
        expansions = table.expandHeader.call_count
        updates = table.updateConstraint.call_count
        self.league.checkSheet(table, header, constraints, reformat=True)
        assert_equals(table.expandHeader.call_count, expansions+2)
        assert_equals(table.updateConstraint.call_count, updates+4)

    @patch('resources.league.League.checkSheet')
    def test_checkTeamSheet(self, checkSheet):
        self.league.settings[self.league.SET_MIN_RATING] = None
        assert_equals(self.league.minRating, None)
        self.league.checkTeamSheet()
        expectedConstraints = {'ID': 'UNIQUE INT',
                               'Name': 'UNIQUE STRING',
                               'Players': 'STRING',
                               'Confirmations': 'STRING',
                               'Rating': 'STRING',
                               'Vetos': 'STRING',
                               'Drops': 'STRING',
                               'Rank': 'INT',
                               'History': 'STRING',
                               'Finished': 'INT',
                               'Limit': 'INT',
                               'Count': 'INT'}
        checkSheet.assert_called_once_with(self.league.teams,
                                           set(expectedConstraints),
                                           expectedConstraints,
                                           self.league.autoformat)
        self.league.settings[self.league.SET_MIN_RATING] = 5000
        assert_equals(self.league.minRating, 5000)
        self.league.checkTeamSheet()
        expectedConstraints['Probation Start'] = 'STRING'
        checkSheet.assert_called_with(self.league.teams,
                                      set(expectedConstraints),
                                      expectedConstraints,
                                      self.league.autoformat)

    @patch('resources.league.League.checkSheet')
    def test_checkGamesSheet(self, checkSheet):
        expectedConstraints = {'ID': 'UNIQUE INT',
                               'WarlightID': 'UNIQUE INT',
                               'Created': 'STRING',
                               'Sides': 'STRING',
                               'Winners': 'STRING',
                               'Vetos': 'INT',
                               'Vetoed': 'STRING',
                               'Template': 'INT'}
        self.league.checkGamesSheet()
        checkSheet.assert_called_once_with(self.league.games,
                                           set(expectedConstraints),
                                           expectedConstraints,
                                           self.league.autoformat)

    @patch('resources.league.League.checkSheet')
    def test_checkTemplatesSheet(self, checkSheet):
        expectedConstraints = {'ID': 'UNIQUE INT',
                               'Name': 'UNIQUE STRING',
                               'WarlightID': 'INT',
                               'Active': 'BOOL',
                               'Games': 'INT'}
        self.league.checkTemplatesSheet()
        checkSheet.assert_called_once_with(self.league.templates,
                                           set(expectedConstraints),
                                           expectedConstraints,
                                           self.league.autoformat)

    @patch('resources.league.League.checkTeamSheet')
    @patch('resources.league.League.checkGamesSheet')
    @patch('resources.league.League.checkTemplatesSheet')
    def test_checkFormat(self, checkTemplates, checkGames, checkTeams):
        self.league.checkFormat()
        checkTemplates.assert_called_once_with()
        checkGames.assert_called_once_with()
        checkTeams.assert_called_once_with()

    def test_fetchProperty(self):
        self.league.settings = {'label': 'default', 'intlabel': '5'}
        assert_equals(self.league.fetchProperty('label', 'DEFAULT'), 'default')
        assert_equals(self.league.fetchProperty('otherlabel', None), None)
        assert_equals(self.league.fetchProperty('otherlabel', None, int), None)
        assert_equals(self.league.fetchProperty('intlabel', 12, int), 5)
        assert_equals(self.league.fetchProperty('label', 12, float), 12)
        failStr = "Couldn't get label due to ValueError, using default of 12"
        self.league.parent.log.assert_called_once_with(failStr, 'NAME')

# run tests
if __name__ == '__main__':
    run_tests()
