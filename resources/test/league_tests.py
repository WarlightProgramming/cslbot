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

    def test_getBoolProperty(self):
        getBool = self.league.getBoolProperty
        assert_true(getBool("TRUE"))
        assert_true(getBool("true"))
        assert_true(getBool("tRUE"))
        assert_true(getBool("True"))
        assert_false(getBool("FALSE"))
        assert_false(getBool("False"))
        assert_false(getBool("false"))
        assert_false(getBool("fALSE"))
        assert_raises(KeyError, getBool, "None")
        assert_raises(KeyError, getBool, "")
        assert_raises(KeyError, getBool, "someOtherValue")

    def _propertyTest(self, prop, label, default, values):
        if label in self.league.settings:
            self.league.settings.pop(label)
        evalStr = "self.league." + prop
        assert_equals(eval(evalStr), default)
        for value in values:
            self.league.settings[label] = value
            assert_equals(eval(evalStr), values[value])

    def _boolPropertyTest(self, prop, label, default):
        values = {"TRUE": True, "FALSE": False, "": default,
                  "None": default, "someRandomValue": default,
                  "True": True, "true": True, "tRuE": True,
                  "False": False, "false": False, "fALSE": False}
        self._propertyTest(prop, label, default, values)

    def _strPropertyTest(self, prop, label, default):
        inputs = {"testString", "other test string", "    spaces   ",
                  "IPL", "Fizzer Appreciation Infinity League", "",
                  "\nThis\nIs a multi\nline string"}
        values = dict()
        for i in inputs:
            values[i] = i
        self._propertyTest(prop, label, default, values)

    def _intPropertyTest(self, prop, label, default):
        values = {"0": 0, "-1": -1, "490": 490, "": default,
                  "string": default, "None": default, "r4nd0M!1!": default,
                  "10": 10, "5": 5, "3334": 3334}
        self._propertyTest(prop, label, default, values)

    def test_autoformat(self):
        self._boolPropertyTest("autoformat", self.league.SET_AUTOFORMAT, True)

    def test_autodrop(self):
        self._boolPropertyTest("autodrop", self.league.SET_AUTODROP,
                               (self.league.dropLimit > 0))

    def test_teamless(self):
        self._boolPropertyTest("teamless", self.league.SET_TEAMLESS,
                               (self.league.teamSize == 1 and
                                self.league.sideSize == 1))

    def test_leagueAcronym(self):
        self._strPropertyTest("leagueAcronym", self.league.SET_LEAGUE_ACRONYM,
                              self.league.clusterName)

    def test_clusterName(self):
        self._strPropertyTest("clusterName", self.league.SET_SUPER_NAME,
                              self.league.name)

    def test_leagueMessage(self):
        self._strPropertyTest("leagueMessage", self.league.SET_LEAGUE_MESSAGE,
                              self.league.DEFAULT_MSG)

    def test_leagueUrl(self):
        self._strPropertyTest("leagueUrl", self.league.SET_URL,
                              self.league.defaultUrl)

    def test_defaultUrl(self):
        self.league.games.parent.sheet.ID = "ID"
        assert_equals(self.league.defaultUrl,
                      "https://docs.google.com/spreadsheets/d/ID")

    def test_rematchLimit(self):
        mul = self.league.sideSize * self.league.gameSize
        processVal = lambda val: val * mul
        values = {self.league.KW_ALL: self.league.KW_ALL,
                  "10": processVal(10), "40": processVal(40),
                  "490": processVal(490), "0": 0, "": 0, "Five": 0}
        self._propertyTest("rematchLimit", self.league.SET_REMATCH_LIMIT,
                           0, values)

    def test_teamLimit(self):
        values = {"10": 10, "0": 0, "": None, "None": None, "NONE": None,
                  "none": None, "1": 1, "90840984": 90840984}
        self._propertyTest("teamLimit", self.league.SET_MAX_TEAMS,
                           (None if self.league.teamSize > 1 else 1),
                           values)

    def test_vetoLimit(self):
        self._intPropertyTest("vetoLimit", self.league.SET_VETO_LIMIT, 0)

    def test_dropLimit(self):
        maxVal = len(self.league.templateIDs) - 1
        processVal = lambda val: min(val, maxVal)
        values = {"10": processVal(10), "-1": processVal(-1),
                  "0": processVal(0), "40": processVal(40),
                  "f": 0, "random": 0, "": 0, "STRING": 0, "tEsT": 0}
        self._propertyTest("dropLimit", self.league.SET_DROP_LIMIT, 0, values)

    def test_removeDeclines(self):
        self._boolPropertyTest("removeDeclines",
                               self.league.SET_REMOVE_DECLINES, True)

    def test_countDeclinesAsVetos(self):
        self._boolPropertyTest("countDeclinesAsVetos",
                               self.league.SET_VETO_DECLINES, False)

    def _changeRatingSystem(self, system):
        self.league.settings[self.league.SET_SYSTEM] = system

    def test_vetoPenalty(self):
        defaultVals = {"", "string", "random", " ", "NONE", "4chan"}
        values = {"40": 40, "0": 0, "-10": -10, "2357": 2357}
        systemsDict = {self.league.RATE_WINCOUNT: 1,
                       self.league.RATE_WINRATE: 50,
                       self.league.RATE_ELO: 25}
        for system in systemsDict:
            self._changeRatingSystem(system)
            for val in defaultVals:
                values[val] = systemsDict[system]
            self._propertyTest("vetoPenalty", self.league.SET_VETO_PENALTY,
                               systemsDict[system], values)

    def test_teamSize(self):
        self._intPropertyTest("teamSize", self.league.SET_TEAM_SIZE, 1)

    def test_gameSize(self):
        self._intPropertyTest("gameSize", self.league.SET_GAME_SIZE, 2)

    def test_sideSize(self):
        self._intPropertyTest("sideSize", self.league.SET_TEAMS_PER_SIDE, 1)

    def test_expiryThreshold(self):
        self._intPropertyTest("expiryThreshold", self.league.SET_EXP_THRESH, 3)

    def test_maxVacation(self):
        self._intPropertyTest("maxVacation", self.league.SET_MAX_VACATION,
                              None)

# run tests
if __name__ == '__main__':
    run_tests()
