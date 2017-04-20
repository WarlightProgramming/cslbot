# league_tests.py
## automated tests for the League class

# imports
import time
import sheetDB
import wl_api
from unittest import TestCase, main as run_tests
from nose.tools import assert_equals, assert_not_equal, assert_true,\
assert_raises, assert_false, assert_almost_equal
from mock import patch, MagicMock
from resources.league import League, runPhase, noisy, ImproperLeague,\
ImproperInput, NonexistentItem
from datetime import datetime, timedelta, date
from decimal import Decimal

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
    failStr = ("Call to testPhase failed due to "
               "Exception('This is an exception!',)")
    t.parent.log.assert_called_once_with(failStr, "test", True)

def test_noisy():

    ### dummy test class
    class TestClass:
        parent = MagicMock()
        name = "name"
        debug = False

        @noisy
        def testFn(self, *args, **kwargs):
            return 9 / args[0]

    t = TestClass()
    t.testFn(5, "these", "are", "just", "args", 5)
    t.parent.log.assert_not_called()
    t.debug = True
    t.testFn(6, "these", "are", "just", "args", "and", a="kwarg")
    runStr = ("Calling method testFn with args (6, 'these', 'are', 'just',"
              " 'args', 'and') and kwargs {'a': 'kwarg'}")
    t.parent.log.assert_called_once_with(runStr, "name", False)
    assert_raises(ZeroDivisionError, t.testFn, 0)
    assert_equals(t.parent.log.call_count, 3)
    failStr = ("Call to testFn failed due to "
               "ZeroDivisionError('integer division or modulo by zero',)")
    t.parent.log.assert_called_with(failStr, "name", True)

## League class tests
class TestLeague(TestCase):

    @patch('resources.league.League._checkFormat')
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
                             self.settings, self.orders, 30221, self.parent,
                             'NAME', 'THREADURL')

    def test_init(self):
        assert_equals(self.league.games, self.games)
        assert_equals(self.league.teams, self.teams)
        assert_equals(self.league.templates, self.templates)
        assert_equals(self.league.settings, self.settings)
        assert_equals(self.league.orders, self.orders)
        assert_equals(self.league.admin, 30221)
        assert_equals(self.league.mods, 'MODS')
        assert_equals(self.league.parent, self.parent)
        assert_equals(self.league.name, 'NAME')
        assert_equals(self.league.thread, 'THREADURL')
        assert_equals(self.league.handler, self.handler)
        assert_equals(self.league.debug, False)
        assert_equals(self.league.tempTeams, None)

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

    @patch('resources.league.League._fetchProperty')
    def test_getMods(self, fetch):
        fetch.return_value = set()
        assert_equals(self.league._getMods(), {self.league.admin})
        fetch.assert_called_once_with(self.league.SET_MODS, set(),
                                      self.league.getIDGroup)

    def test_sysDict(self):
        assert_equals(self.league._makeRateSysDict(), None)
        assert_true(self.league.RATE_ELO in self.league.sysDict)
        assert_true(self.league.RATE_GLICKO in self.league.sysDict)
        assert_true(self.league.RATE_TRUESKILL in self.league.sysDict)
        assert_true(self.league.RATE_WINCOUNT in self.league.sysDict)
        assert_true(self.league.RATE_WINRATE in self.league.sysDict)
        assert_equals(self.league.sysDict[\
                      self.league.RATE_WINCOUNT]['prettify']("3"), "3")
        assert_equals(self.league.sysDict[\
                      self.league.RATE_WINRATE]['prettify']("3/41"), "3")
        self._setProp(self.league.SET_ELO_DEFAULT, "2953")
        assert_equals(self.league.sysDict[self.league.RATE_ELO]['default'](),
                      '2953')
        self._setProp(self.league.SET_GLICKO_DEFAULT, "40")
        self._setProp(self.league.SET_GLICKO_RD, "3")
        assert_equals(self.league.sysDict[\
                      self.league.RATE_GLICKO]['default'](), "40/3")
        self._setProp(self.league.SET_TRUESKILL_DEFAULT, "4903")
        self._setProp(self.league.SET_TRUESKILL_SIGMA, "400")
        assert_equals(self.league.sysDict[\
                      self.league.RATE_TRUESKILL]['default'](), "4903/400")
        assert_equals(self.league.sysDict[\
                      self.league.RATE_WINCOUNT]['default'](), "0")
        assert_equals(self.league.sysDict[\
                      self.league.RATE_WINRATE]['default'](), "0/0")

    def test_checkSheet(self):
        table = MagicMock()
        table.reverseHeader = {'Here': 1, 'There': 2}
        header = {'Here', 'There', 'Everywhere', 'Nowhere'}
        constraints = {'Here': 'UNIQUE', 'There': '', 'Everywhere': 'INT'}
        assert_raises(ImproperLeague, self.league._checkSheet, table, header,
                      constraints, reformat=False)
        expansions = table.expandHeader.call_count
        updates = table.updateConstraint.call_count
        self.league._checkSheet(table, header, constraints, reformat=True)
        assert_equals(table.expandHeader.call_count, expansions+2)
        assert_equals(table.updateConstraint.call_count, updates+4)

    @patch('resources.league.League._checkSheet')
    def test_checkTeamSheet(self, checkSheet):
        self.league.settings[self.league.SET_MIN_RATING] = None
        assert_equals(self.league.minRating, None)
        self.league._checkTeamSheet()
        expectedConstraints = {'ID': 'UNIQUE INT',
                               'Name': 'UNIQUE STRING',
                               'Players': 'UNIQUE STRING',
                               'Confirmations': 'STRING',
                               'Rating': 'STRING',
                               'Vetos': 'STRING',
                               'Drops': 'STRING',
                               'Rank': 'INT',
                               'History': 'STRING',
                               'Finished': 'INT',
                               'Limit': 'INT',
                               'Ongoing': 'INT'}
        checkSheet.assert_called_once_with(self.league.teams,
                                           set(expectedConstraints),
                                           expectedConstraints,
                                           self.league.autoformat)
        self.league.settings[self.league.SET_MIN_RATING] = 5000
        assert_equals(self.league.minRating, 5000)
        self.league._checkTeamSheet()
        expectedConstraints['Probation Start'] = 'STRING'
        checkSheet.assert_called_with(self.league.teams,
                                      set(expectedConstraints),
                                      expectedConstraints,
                                      self.league.autoformat)

    @patch('resources.league.League._checkSheet')
    def test_checkGamesSheet(self, checkSheet):
        expectedConstraints = {'ID': 'UNIQUE INT',
                               'WarlightID': 'UNIQUE INT',
                               'Created': 'STRING',
                               'Finished': 'STRING',
                               'Sides': 'STRING',
                               'Winners': 'STRING',
                               'Vetos': 'INT',
                               'Vetoed': 'STRING',
                               'Template': 'INT'}
        self.league._checkGamesSheet()
        checkSheet.assert_called_once_with(self.league.games,
                                           set(expectedConstraints),
                                           expectedConstraints,
                                           self.league.autoformat)

    @patch('resources.league.League._checkSheet')
    def test_checkTemplatesSheet(self, checkSheet):
        expectedConstraints = {'ID': 'UNIQUE INT',
                               'Name': 'UNIQUE STRING',
                               'WarlightID': 'INT',
                               'Active': 'BOOL',
                               'Usage': 'INT'}
        self.league._checkTemplatesSheet()
        checkSheet.assert_called_once_with(self.league.templates,
                                           set(expectedConstraints),
                                           expectedConstraints,
                                           self.league.autoformat)

    @patch('resources.league.League._checkTeamSheet')
    @patch('resources.league.League._checkGamesSheet')
    @patch('resources.league.League._checkTemplatesSheet')
    def test_checkFormat(self, checkTemplates, checkGames, checkTeams):
        self.league._checkFormat()
        checkTemplates.assert_called_once_with()
        checkGames.assert_called_once_with()
        checkTeams.assert_called_once_with()

    def test_fetchProperty(self):
        self.league.settings = {'label': 'default', 'intlabel': '5'}
        assert_equals(self.league._fetchProperty('label', 'DEFAULT'),
                      'default')
        assert_equals(self.league._fetchProperty('otherlabel', None), None)
        assert_equals(self.league._fetchProperty('otherlabel', None, int),
                      None)
        assert_equals(self.league._fetchProperty('intlabel', 12, int), 5)
        assert_equals(self.league._fetchProperty('label', 12, float), 12)
        failStr = "Couldn't get label due to ValueError, using default of 12"
        self.league.parent.log.assert_called_once_with(failStr, 'NAME',
                                                       error=True)

    def test_getBoolProperty(self):
        getBool = self.league._getBoolProperty
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

    def _setProp(self, label, value):
        self.league.settings[label] = value

    def _propertyTest(self, prop, label, default, values):
        if label in self.league.settings:
            self.league.settings.pop(label)
        evalStr = "self.league." + prop
        assert_equals(eval(evalStr), default)
        for value in values:
            self._setProp(label, value)
            result = eval(evalStr)
            if isinstance(result, float):
                assert_almost_equal(result, values[value])
            else:
                assert_equals(result, values[value])

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

    def _posPropertyTest(self, prop, label, default):
        values = {"0": 1, "-1": 1, "490": 490, "": default,
                  "string": default, "None": default, "r4nd0M!1!": default,
                  "10": 10, "5": 5, "3334": 3334}
        self._propertyTest(prop, label, default, values)

    def _floatPropertyTest(self, prop, label, default):
        values = {"0": 0.0, "-1": -1.0, "-1.0": -1.0, "0.0": 0.0, "210": 210.0,
                  "string": default, "None": default, "randomLOL": default,
                  "10.0": 10.0, "10": 10.0, "3334": 3334.0, "042.390": 42.390}
        self._propertyTest(prop, label, default, values)

    def _dateTimePropertyTest(self, prop, label, default):
        offset = (time.timezone if (time.localtime().tm_isdst == 0)
                  else time.altzone)
        timeDiff = timedelta(hours = (offset/3600))
        values = {"0": default, "": default, "none": default,
                  "2010-4-20": default,
                  "2010-04-20 10:30:50":
                  datetime(2010, 4, 20, 10, 30, 50) - timeDiff}
        self._propertyTest(prop, label, default, values)

    def _IDGroupPropertyTest(self, prop, label, default):
        values = {"": set(), ",": set(), "1,2,3,4,5": {1, 2, 3, 4, 5},
                  "1,2,3,4,5,": {1, 2, 3, 4, 5}, "lkfalf": default,
                  "slakfjaflkjas;l,falksjf;aslfkj": default}
        self._propertyTest(prop, label, default, values)

    def _groupPropertyTest(self, prop, label, default):
        values = {"": set(), ",": set(), "a,b,c,d,e": {"a","b","c","d","e"},
                  "ab,cde,fg,": {"ab", "cde", "fg"}}
        self._propertyTest(prop, label, default, values)

    def test_autoformat(self):
        self._boolPropertyTest("autoformat", self.league.SET_AUTOFORMAT, True)

    def test_preserveRecords(self):
        self._setProp(self.league.SET_RETENTION_RANGE, False)
        self._setProp(self.league.SET_VETO_PENALTY, 0)
        self._boolPropertyTest("preserveRecords",
                                self.league.SET_PRESERVE_RECORDS, True)
        self._setProp(self.league.SET_RETENTION_RANGE, True)
        self._boolPropertyTest("preserveRecords",
                                self.league.SET_PRESERVE_RECORDS, True)
        self._setProp(self.league.SET_VETO_PENALTY, 10)
        assert_true(self.league.preserveRecords)

    def test_maintainTotal(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        self._boolPropertyTest("maintainTotal",
                               self.league.SET_MAINTAIN_TOTAL, False)
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_WINRATE)
        values = {'TRUE': False, 'FALSE': False}
        self._propertyTest("maintainTotal", self.league.SET_MAINTAIN_TOTAL,
                           False, values)

    def test_favorNewTemplates(self):
        self._boolPropertyTest("favorNewTemplates",
                               self.league.SET_FAVOR_NEW_TEMPLATES, False)

    def test_requireSameClan(self):
        self._setProp(self.league.SET_MAINTAIN_SAME_CLAN, "FALSE")
        assert_false(self.league.maintainSameClan)
        self._boolPropertyTest('requireSameClan',
                               self.league.SET_REQUIRE_SAME_CLAN, False)
        self._setProp(self.league.SET_MAINTAIN_SAME_CLAN, "TRUE")
        assert_true(self.league.maintainSameClan)
        values = {'TRUE': True, 'FALSE': True}
        self._propertyTest('requireSameClan',
                           self.league.SET_REQUIRE_SAME_CLAN, True, values)

    def test_maintainSameClan(self):
        self._boolPropertyTest('maintainSameClan',
                               self.league.SET_MAINTAIN_SAME_CLAN, False)

    def test_forbidClanMatchups(self):
        self._boolPropertyTest('forbidClanMatchups',
                               self.league.SET_FORBID_CLAN_MATCHUPS, False)

    def test_onlyModsCanAdd(self):
        self._boolPropertyTest('onlyModsCanAdd',
                               self.league.SET_ONLY_MODS_CAN_ADD, False)

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

    def test_nameLength(self):
        self._intPropertyTest("nameLength", self.league.SET_NAME_LENGTH, None)

    def test_ratingDecay(self):
        self._intPropertyTest("ratingDecay", self.league.SET_RATING_DECAY, 0)

    def test_penaltyFloor(self):
        self._intPropertyTest("penaltyFloor", self.league.SET_PENALTY_FLOOR,
                              None)

    def test_retentionRange(self):
        self._intPropertyTest("retentionRange",
                              self.league.SET_RETENTION_RANGE, None)

    def test_constrainName(self):
        self._boolPropertyTest("constrainName", self.league.SET_CONSTRAIN_NAME,
                               True)

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

    def test_rematchCap(self):
        self._intPropertyTest("rematchCap", self.league.SET_REMATCH_CAP, 1)

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

    def test_removeBoots(self):
        self._boolPropertyTest("removeBoots",
                               self.league.SET_REMOVE_BOOTS, True)

    def test_penalizeDeclines(self):
        self._boolPropertyTest("penalizeDeclines",
                               self.league.SET_PENALIZE_DECLINES, True)

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
        self._posPropertyTest("teamSize", self.league.SET_TEAM_SIZE, 1)

    def test_gameSize(self):
        self._setProp(self.league.SET_GAME_SIZE, "3,4,5")
        assert_true(self.league.gameSize in {3,4,5})
        oldSize = self.league.gameSize
        self._posPropertyTest("_statedGameSize()",
                              self.league.SET_GAME_SIZE, 2)
        assert_equals(self.league.gameSize, oldSize)

    def test_sideSize(self):
        self._setProp(self.league.SET_TEAMS_PER_SIDE, "1,50,100")
        assert_true(self.league.sideSize in {1,50,100})
        oldSize = self.league.sideSize
        self._posPropertyTest("_statedSideSize()",
                              self.league.SET_TEAMS_PER_SIDE, 1)
        assert_equals(self.league.sideSize, oldSize)

    def test_scheme(self):
        teamSize = self.league.teamSize
        sideSize = self.league.sideSize
        gameSize = self.league.gameSize
        scheme = self.league.scheme
        assert_equals(scheme.count(str(teamSize * sideSize)), gameSize)
        assert_equals(scheme.count("v"), gameSize - 1)
        self._setProp(self.league.SET_TEAMS_PER_SIDE, "1,50,100")
        assert_true(self.league.multischeme)
        self._setProp(self.league.SET_GAME_SIZE, "2,3,4")
        assert_true(self.league.multischeme)
        self._setProp(self.league.SET_TEAMS_PER_SIDE, "5")
        assert_true(self.league.multischeme)
        self._setProp(self.league.SET_GAME_SIZE, "2")
        assert_false(self.league.multischeme)

    def test_expiryThreshold(self):
        self._intPropertyTest("expiryThreshold", self.league.SET_EXP_THRESH, 3)

    def test_maxVacation(self):
        self._intPropertyTest("maxVacation", self.league.SET_MAX_VACATION,
                              None)

    def _setMaxVacation(self, val):
        self._setProp(self.league.SET_MAX_VACATION, val)

    def _makeVacationDate(self, delta):
        return datetime.strftime((datetime.now() + timedelta(days=delta)),
                                 '%m/%d/%Y %H:%M:%S')

    def test_meetsVacation(self):
        player = MagicMock()
        player.ID = "0"
        self.handler.validateToken.return_value = dict()
        assert_true(self.league._meetsVacation(player))
        self._setMaxVacation(1)
        assert_true(self.league._meetsVacation(player))
        self._setMaxVacation(0)
        assert_true(self.league._meetsVacation(player))
        self.handler.validateToken.return_value = {'onVacationUntil':
                                                   self._makeVacationDate(1)}
        assert_false(self.league._meetsVacation(player))
        self._setMaxVacation(1)
        assert_true(self.league._meetsVacation(player))
        self._setMaxVacation(2)
        assert_true(self.league._meetsVacation(player))
        self.handler.validateToken.return_value = {'onVacationUntil':
                                                   self._makeVacationDate(3)}
        assert_false(self.league._meetsVacation(player))
        self.handler.validateToken.return_value = dict()
        assert_true(self.league._meetsVacation(player))

    def test_minLimit(self):
        values = {"-3": 0, "-5": 0, "0": 0, "10": 10, "204": 204, "None": 0}
        self._propertyTest('minLimit', self.league.SET_MIN_LIMIT, 0, values)

    def test_maxLimit(self):
        self._intPropertyTest('maxLimit', self.league.SET_MAX_LIMIT, None)

    def test_constrainLimit(self):
        self._boolPropertyTest('constrainLimit',
                               self.league.SET_CONSTRAIN_LIMIT, True)

    def test_valueInRange(self):
        assert_true(self.league._valueInRange(10, None, None))
        assert_true(self.league._valueInRange(10, 10, None))
        assert_true(self.league._valueInRange(10, None, 10))
        assert_true(self.league._valueInRange(10, 10, 10))
        assert_true(self.league._valueInRange(5, 0, 30))
        assert_true(self.league._valueInRange(5, 0, None))
        assert_true(self.league._valueInRange(5, None, 30))
        assert_true(self.league._valueInRange(0, -1, 1))
        assert_false(self.league._valueInRange(0, None, -1))
        assert_false(self.league._valueInRange(0, 1, -1))
        assert_false(self.league._valueInRange(0, 1, None))
        assert_false(self.league._valueInRange(0, 1, 2))

    def _setMinLimit(self, val):
        self._setProp(self.league.SET_MIN_LIMIT, val)

    def _setMaxLimit(self, val):
        self._setProp(self.league.SET_MAX_LIMIT, val)

    def test_limitInRange(self):
        self._setMinLimit(4)
        self._setMaxLimit(20)
        assert_true(self.league._limitInRange(20))
        assert_false(self.league._limitInRange(3))
        assert_false(self.league._limitInRange(21))

    def _setSystem(self, val):
        self._setProp(self.league.SET_SYSTEM, val)

    def test_ratingSystem(self):
        self._setSystem(self.league.RATE_ELO)
        assert_equals(self.league.ratingSystem, self.league.RATE_ELO)
        self._setSystem("elo")
        assert_equals(self.league.ratingSystem, self.league.RATE_ELO)
        self._setSystem(self.league.RATE_WINRATE)
        assert_equals(self.league.ratingSystem, self.league.RATE_WINRATE)
        self._setSystem("dr. wondertainment's magic rating system v3.5")
        fetchSys = lambda: self.league.ratingSystem
        assert_raises(ImproperInput, fetchSys)

    def test_kFactor(self):
        processVal = lambda x: x * self.league.sideSize
        values = {"32": processVal(32), "": processVal(32),
                  "None": processVal(32), "40": processVal(40),
                  "0": 0, "10": processVal(10)}
        self._propertyTest('kFactor', self.league.SET_ELO_K, 32, values)

    def test_defaultElo(self):
        self._intPropertyTest("defaultElo", self.league.SET_ELO_DEFAULT, 1500)

    @patch('resources.league.Elo')
    def test_eloEnv(self, eloFn):
        fetchVal = lambda: self.league.eloEnv
        assert_equals(fetchVal(), eloFn.return_value)
        eloFn.assert_called_once_with(initial=self.league.defaultElo,
                                      k_factor=self.league.kFactor)

    def test_glickoRd(self):
        self._intPropertyTest('glickoRd', self.league.SET_GLICKO_RD, 350)

    def test_glickoRating(self):
        self._intPropertyTest('glickoRating', self.league.SET_GLICKO_DEFAULT,
                              1500)

    def test_defaultGlicko(self):
        expVal = (str(self.league.glickoRating) + self.league.SEP_RTG +
                  str(self.league.glickoRd))
        assert_equals(self.league.defaultGlicko, expVal)

    def test_trueSkillSigma(self):
        self._intPropertyTest('trueSkillSigma',
                              self.league.SET_TRUESKILL_SIGMA, 500)

    def test_trueSkillMu(self):
        self._intPropertyTest('trueSkillMu',
                              self.league.SET_TRUESKILL_DEFAULT, 1500)

    def test_trueSkillBeta(self):
        assert_equals(self.league.trueSkillBeta,
                      (self.league.trueSkillSigma / 2.0))

    def test_trueSkillTau(self):
        assert_equals(self.league.trueSkillTau,
                      (self.league.trueSkillSigma / 100.0))

    @patch('resources.league.TrueSkill')
    def test_trueSkillEnv(self, trueSkillFn):
        assert_equals(self.league.trueSkillEnv, trueSkillFn.return_value)
        trueSkillFn.assert_called_once_with(mu = self.league.trueSkillMu,
                                            sigma = self.league.trueSkillSigma,
                                            beta = self.league.trueSkillBeta,
                                            tau = self.league.trueSkillTau,
                                            draw_probability = 0.0,
                                            backend = 'mpmath')

    def test_defaultTrueSkill(self):
        expVal = (str(self.league.trueSkillMu) + self.league.SEP_RTG +
                  str(self.league.trueSkillSigma))
        assert_equals(self.league.defaultTrueSkill, expVal)

    def test_defaultWinCount(self):
        val = self.league.sysDict[self.league.RATE_WINCOUNT]['default']()
        assert_equals(val, "0")

    def test_defaultWinRate(self):
        assert_equals(self.league.defaultWinRate, "0" + self.league.SEP_RTG +
                      "0")

    def test_reverseParity(self):
        self._boolPropertyTest('reverseParity', self.league.SET_REVERSE_PARITY,
                               False)

    def test_reverseSideParity(self):
        self._boolPropertyTest('reverseSideParity',
                               self.league.SET_REVERSE_GROUPING, False)

    def test_maxBoot(self):
        self._floatPropertyTest('maxBoot', self.league.SET_MAX_BOOT, 100.0)

    def test_minLevel(self):
        self._intPropertyTest('minLevel', self.league.SET_MIN_LEVEL, 0)

    def _setMinMemberAge(self, val):
        self._setProp(self.league.SET_MIN_MEMBER_AGE, val)

    def test_membersOnly(self):
        self._setMinMemberAge(0)
        self._boolPropertyTest('membersOnly', self.league.SET_MEMBERS_ONLY,
                               False)
        self._setMinMemberAge(1)
        assert_true(self.league.membersOnly)

    def test_meetsMembership(self):
        player = MagicMock()
        player.isMember = False
        self._setMinMemberAge(0)
        self._setProp(self.league.SET_MEMBERS_ONLY, "FALSE")
        assert_true(self.league._meetsMembership(player))
        self._setMinMemberAge(1)
        assert_false(self.league._meetsMembership(player))
        self._setProp(self.league.SET_MEMBERS_ONLY, "TRUE")
        assert_false(self.league._meetsMembership(player))
        self._setMinMemberAge(0)
        assert_false(self.league._meetsMembership(player))
        player.isMember = True
        player.memberSince = date.today() - timedelta(days=3)
        self._setMinMemberAge(4)
        assert_false(self.league._meetsMembership(player))
        self._setMinMemberAge(3)
        assert_true(self.league._meetsMembership(player))
        self._setMinMemberAge(2)
        assert_true(self.league._meetsMembership(player))

    def test_minPoints(self):
        self._intPropertyTest('minPoints', self.league.SET_MIN_POINTS, 0)

    def test_minAge(self):
        self._intPropertyTest('minAge', self.league.SET_MIN_AGE, 0)

    def test_minMemberAge(self):
        self._intPropertyTest('minMemberAge', self.league.SET_MIN_MEMBER_AGE,
                              0)

    def test_maxRTSpeed(self):
        processVal = lambda x: float(Decimal(x) / Decimal(60.0))
        values= {'5': processVal(5), '0': 0, '10': processVal(10),
                 '': None, 'lkjasfl': None, '-30.4': processVal(-30.4)}
        self._propertyTest('maxRTSpeed', self.league.SET_MAX_RT_SPEED, None,
                           values)

    def test_maxMDSpeed(self):
        self._floatPropertyTest('maxMDSpeed', self.league.SET_MAX_MD_SPEED,
                                None)

    def test_minExplicitRating(self):
        self._intPropertyTest('minExplicitRating', self.league.SET_MIN_RATING,
                              None)

    def test_findRatingAtPercentile(self):
        oldPrettify = self.league.prettifyRating
        self.league.prettifyRating = int
        assert_equals(self.league._findRatingAtPercentile(0), None)
        self.teams.findValue.return_value = ["1", "2", "3", "4", "5",
                                             "6", "7", "8", "9", "10"]
        assert_equals(self.league._findRatingAtPercentile(0), None)
        assert_equals(self.league._findRatingAtPercentile(1), 2)
        assert_equals(self.league._findRatingAtPercentile(10), 2)
        assert_equals(self.league._findRatingAtPercentile(21), 4)
        assert_equals(self.league._findRatingAtPercentile(30.5), 5)
        assert_equals(self.league._findRatingAtPercentile(99.5), 10)
        assert_equals(self.league._findRatingAtPercentile(1000), 10)
        assert_equals(self.league._findRatingAtPercentile(50), 6)
        self.league.prettifyRating = oldPrettify

    @patch('resources.league.League._findRatingAtPercentile')
    def test_minPercentileRating(self, findRating):
        values = {"0": findRating.return_value, "": None, "None": None,
                  "hi": None, "10": findRating.return_value,
                  "490": findRating.return_value,
                  "43.5902": findRating.return_value}
        self._propertyTest('minPercentileRating',
                           self.league.SET_MIN_PERCENTILE, None, values)

    @patch('resources.league.League._findRatingAtPercentile')
    def test_minRating(self, findRating):
        findRating.return_value = None
        self._setProp(self.league.SET_MIN_RATING, "50")
        assert_equals(self.league.minRating, 50)
        self._setProp(self.league.SET_MIN_PERCENTILE, "30")
        findRating.return_value = 30
        assert_equals(self.league.minRating, 50)
        self._setProp(self.league.SET_MIN_RATING, "20")
        assert_equals(self.league.minRating, 30)

    def test_gracePeriod(self):
        self._intPropertyTest('gracePeriod', self.league.SET_GRACE_PERIOD, 0)

    def test_restorationPeriod(self):
        self._setProp(self.league.SET_GRACE_PERIOD, 5)
        values = {"10": 15, "": None, "None": None, " ": None, "40": 45,
                  "0": 5}
        self._propertyTest('restorationPeriod',
                           self.league.SET_RESTORATION_PERIOD, None, values)

    @patch('resources.league.League._getExtantEntities')
    def test_restoreTeams(self, getExtant):
        self._setProp(self.league.SET_RESTORATION_PERIOD, None)
        self._setProp(self.league.SET_MIN_RATING, None)
        self._setProp(self.league.SET_MIN_PERCENTILE, None)
        assert_true(self.league.cullingDisabled)
        self.league.restoreTeams()
        assert_equals(getExtant.call_count, 1)
        self._setProp(self.league.SET_MIN_RATING, 50)
        assert_false(self.league.cullingDisabled)
        self.league.restoreTeams()
        assert_equals(getExtant.call_count, 1)
        self._setProp(self.league.SET_GRACE_PERIOD, 5)
        self._setProp(self.league.SET_RESTORATION_PERIOD, 10)
        assert_equals(self.league.restorationPeriod, 15)
        getExtant.return_value = list()
        self.league.restoreTeams()
        assert_equals(getExtant.call_count, 2)
        self.teams.updateMatchingEntities.assert_not_called()
        makeProb = lambda x: datetime.strftime(datetime.now() - timedelta(x),
                                               self.league.TIMEFORMAT)
        getExtant.return_value = [{'ID': 0, 'Probation Start': makeProb(1)},
                                  {'ID': 1, 'Probation Start': makeProb(30)},
                                  {'ID': 2, 'Probation Start': makeProb(0)},
                                  {'ID': 3, 'Probation Start': makeProb(16)},
                                  {'ID': 4, 'Probation Start': makeProb(12)}]
        self.league.restoreTeams()
        assert_equals(self.teams.updateMatchingEntities.call_count, 2)

    def test_allowJoins(self):
        self._boolPropertyTest('allowJoins', self.league.SET_ALLOW_JOINS, True)

    def test_leagueCapacity(self):
        self._intPropertyTest('leagueCapacity',
                              self.league.SET_LEAGUE_CAPACITY, None)

    def test_activeCapacity(self):
        self._intPropertyTest('activeCapacity',
                              self.league.SET_ACTIVE_CAPACITY, None)

    def test_valueBelowCapacity(self):
        assert_true(self.league._valueBelowCapacity(5, 6))
        assert_true(self.league._valueBelowCapacity(5, 10))
        assert_true(self.league._valueBelowCapacity(0, 1))
        assert_false(self.league._valueBelowCapacity(5, 5))
        assert_false(self.league._valueBelowCapacity(5, 4))
        assert_false(self.league._valueBelowCapacity(0, 0))
        assert_true(self.league._valueBelowCapacity(109303838, None))

    @patch('resources.league.League._valueBelowCapacity')
    def test_activeFull(self, belowCap):
        belowCap.return_value = False
        assert_true(self.league.activeFull)
        belowCap.return_value = True
        assert_false(self.league.activeFull)

    @patch('resources.league.League._valueBelowCapacity')
    def test_leagueFull(self, belowCap):
        belowCap.return_value = False
        assert_true(self.league.leagueFull)
        belowCap.return_value = True
        assert_false(self.league.leagueFull)

    def test_getDateTimeProperty(self):
        timeDiff = timedelta(hours=((time.timezone if
                                     (time.localtime().tm_isdst == 0) else
                                     time.altzone)/3600))
        getProp = self.league._getDateTimeProperty
        assert_equals(getProp(datetime(2000, 4, 20, 10, 30, 50)),
                      datetime(2000, 4, 20, 10, 30, 50))
        assert_equals(getProp(datetime.strftime(datetime(2000, 4, 20, 10, 30,
                                                         50),
                                                self.league.TIMEFORMAT)),
                      datetime(2000, 4, 20, 10, 30, 50) - timeDiff)

    def test_joinPeriodStart(self):
        self._dateTimePropertyTest('joinPeriodStart',
                                   self.league.SET_JOIN_PERIOD_START, None)

    def test_joinPeriodEnd(self):
        self._dateTimePropertyTest('joinPeriodEnd',
                                   self.league.SET_JOIN_PERIOD_END, None)

    def test_currentTimeWithinRange(self):
        assert_true(self.league._currentTimeWithinRange(None, None))
        start = datetime.now() - timedelta(days=1)
        end = datetime.now() + timedelta(days=1)
        assert_true(self.league._currentTimeWithinRange(start, end))
        assert_true(self.league._currentTimeWithinRange(None, end))
        assert_true(self.league._currentTimeWithinRange(start, None))
        assert_true(self.league._currentTimeWithinRange(None, None))
        assert_false(self.league._currentTimeWithinRange(None, start))
        assert_false(self.league._currentTimeWithinRange(end, None))
        assert_false(self.league._currentTimeWithinRange(end, start))

    @patch('resources.league.League._currentTimeWithinRange')
    @patch('resources.league.League._valueBelowCapacity')
    def test_joinsAllowed(self, belowCap, rangeCheck):
        self._setProp(self.league.SET_ALLOW_JOINS, "TRUE")
        belowCap.return_value = False
        assert_false(self.league.joinsAllowed)
        belowCap.return_value = True
        rangeCheck.return_value = False
        assert_false(self.league.joinsAllowed)
        rangeCheck.return_value = True
        assert_true(self.league.joinsAllowed)
        self._setProp(self.league.SET_ALLOW_JOINS, "FALSE")
        assert_false(self.league.joinsAllowed)

    def test_leagueActive(self):
        self._boolPropertyTest('leagueActive', self.league.SET_ACTIVE, True)

    def test_minSize(self):
        self._intPropertyTest('minSize', self.league.SET_MIN_SIZE,
                              (self.league.sideSize * self.league.gameSize))

    def test_minToCull(self):
        self._intPropertyTest('minToCull', self.league.SET_MIN_TO_CULL, 0)

    def test_minToRank(self):
        self._intPropertyTest('minToRank', self.league.SET_MIN_TO_RANK, 0)

    def test_maxRank(self):
        self._intPropertyTest('maxRank', self.league.SET_MAX_RANK, None)

    def test_minLimitToRank(self):
        self._intPropertyTest('minLimitToRank',
                              self.league.SET_MIN_LIMIT_TO_RANK, 1)

    def test_getExtantEntities(self):
        table = MagicMock()
        assert_equals(self.league._getExtantEntities(table),
                      table.findEntities.return_value)
        assert_equals(self.league._getExtantEntities(table,
                      {'Ra Ra': {'value': "Rasputin", 'type': 'positive'}}),
                      table.findEntities.return_value)
        table.findEntities.assert_called_with({'ID': {'value': '',
                                                      'type': 'negative'},
                                               'Ra Ra': {'value': 'Rasputin',
                                                         'type': 'positive'}},)

    @patch('resources.league.League._getExtantEntities')
    def test_activityCounts(self, getExtant):
        getExtant.return_value = [{'ID': 4, 'Limit': 3},]
        assert_equals(self.league.activeTeams, getExtant.return_value)
        assert_equals(self.league.activeTemplates, getExtant.return_value)
        getExtant.return_value = list()
        assert_equals(self.league.size, 0)
        assert_equals(self.league.templateCount, 0)

    def test_minTemplates(self):
        self._intPropertyTest('minTemplates', self.league.SET_MIN_TEMPLATES, 1)

    def test_activityStart(self):
        self._dateTimePropertyTest('activityStart', self.league.SET_START_DATE,
                                   None)

    def test_activityEnd(self):
        self._dateTimePropertyTest('activityEnd', self.league.SET_END_DATE,
                                   None)

    @patch('resources.league.League._currentTimeWithinRange')
    @patch('resources.league.League._getExtantEntities')
    def test_active(self, getExtant, rangeCheck):
        getExtant.return_value = [{'Limit': '-3'},]
        self._setProp(self.league.SET_MIN_TEMPLATES, 10)
        assert_false(self.league.active)
        getExtant.return_value = [{'Limit': '1'},] * 9
        assert_false(self.league.active)
        self._setProp(self.league.SET_MIN_TEMPLATES, 9)
        self._setProp(self.league.SET_MIN_SIZE, 10)
        assert_false(self.league.active)
        self._setProp(self.league.SET_MIN_SIZE, 3)
        rangeCheck.return_value = False
        assert_false(self.league.active)
        rangeCheck.return_value = True
        self._setProp(self.league.SET_ACTIVE, "FALSE")
        assert_false(self.league.active)
        self._setProp(self.league.SET_ACTIVE, "TRUE")
        assert_true(self.league.active)

    def test_allowRemoval(self):
        self._boolPropertyTest('allowRemoval', self.league.SET_ALLOW_REMOVAL,
                               False)

    def test_minOngoingGames(self):
        self._intPropertyTest('minOngoingGames',
                              self.league.SET_MIN_ONGOING_GAMES, 0)

    def test_maxOngoingGames(self):
        self._intPropertyTest('maxOngoingGames',
                              self.league.SET_MAX_ONGOING_GAMES, None)

    def test_gameCountInRange(self):
        self._setProp(self.league.SET_MAX_ONGOING_GAMES, 3)
        self._setProp(self.league.SET_MIN_ONGOING_GAMES, 1)
        player = MagicMock()
        for i in xrange(1, 4):
            player.currentGames = i
            assert_true(self.league._gameCountInRange(player))
        player.currentGames = 0
        assert_false(self.league._gameCountInRange(player))
        player.currentGames = 5
        assert_false(self.league._gameCountInRange(player))
        self._setProp(self.league.SET_MIN_ONGOING_GAMES, 0)
        self._setProp(self.league.SET_MAX_ONGOING_GAMES, None)
        assert_true(self.league._gameCountInRange(player))

    def test_minRTPercent(self):
        self._floatPropertyTest('minRTPercent', self.league.SET_MIN_RT_PERCENT,
                                0.0)

    def test_maxRTPercent(self):
        self._floatPropertyTest('maxRTPercent', self.league.SET_MAX_RT_PERCENT,
                                100.0)

    def test_RTPercentInRange(self):
        player = MagicMock()
        player.percentRT = 34
        self._setProp(self.league.SET_MIN_RT_PERCENT, 34)
        self._setProp(self.league.SET_MAX_RT_PERCENT, 34)
        assert_true(self.league._RTPercentInRange(player))
        self._setProp(self.league.SET_MIN_RT_PERCENT, 30)
        self._setProp(self.league.SET_MAX_RT_PERCENT, 35)
        assert_true(self.league._RTPercentInRange(player))
        player.percentRT = 35
        assert_true(self.league._RTPercentInRange(player))
        player.percentRT = 30
        assert_true(self.league._RTPercentInRange(player))
        player.percentRT = 29.9999
        assert_false(self.league._RTPercentInRange(player))
        player.percentRT = 100
        assert_false(self.league._RTPercentInRange(player))
        self._setProp(self.league.SET_MIN_RT_PERCENT, 40)
        player.percentRT = 35
        assert_false(self.league._RTPercentInRange(player))

    def test_maxLastSeen(self):
        self._floatPropertyTest('maxLastSeen', self.league.SET_MAX_LAST_SEEN,
                                None)

    def test_min1v1Pct(self):
        self._floatPropertyTest('min1v1Pct', self.league.SET_MIN_1v1_PCT, 0.0)

    def test_min2v2Pct(self):
        self._floatPropertyTest('min2v2Pct', self.league.SET_MIN_2v2_PCT, 0.0)

    def test_min3v3Pct(self):
        self._floatPropertyTest('min3v3Pct', self.league.SET_MIN_3v3_PCT, 0.0)

    def test_minRanked(self):
        self._intPropertyTest('minRanked', self.league.SET_MIN_RANKED, 0)

    def test_meetsMinRanked(self):
        player = MagicMock()
        player.rankedGames = {'data': {'1v1': 40, '2v2': 30, '3v3': 14},
                              'games': 404}
        self._setProp(self.league.SET_MIN_RANKED, 403)
        self._setProp(self.league.SET_MIN_1v1_PCT, 39)
        self._setProp(self.league.SET_MIN_2v2_PCT, 30)
        self._setProp(self.league.SET_MIN_3v3_PCT, 30)
        assert_false(self.league._meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_3v3_PCT, 5)
        assert_true(self.league._meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_RANKED, 500)
        assert_false(self.league._meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_RANKED, 400)
        self._setProp(self.league.SET_MIN_1v1_PCT, 50)
        assert_false(self.league._meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_1v1_PCT, 30)
        self._setProp(self.league.SET_MIN_2v2_PCT, 40)
        assert_false(self.league._meetsMinRanked(player))

    def test_minGames(self):
        self._intPropertyTest('minGames', self.league.SET_MIN_GAMES, 0)

    def test_minAchievementRate(self):
        self._floatPropertyTest('minAchievementRate',
                                self.league.SET_MIN_ACH, 0.0)

    def test_getIDGroup(self):
        assert_equals(self.league.getIDGroup("1,2,3,4"), {1, 2, 3, 4})
        assert_equals(self.league.getIDGroup("", str), set())
        assert_equals(self.league.getIDGroup("5.0, 4.0", float), {4.0, 5.0})
        assert_equals(self.league.getIDGroup("4.0", float), {4.0,})

    def test_getGroup(self):
        assert_equals(self.league.getGroup("a,b,c,d"), {"a","b","c","d"})
        assert_equals(self.league.getGroup("a"), {"a",})
        assert_equals(self.league.getGroup("b,"), {"b",})

    def test_agents(self):
        self._groupPropertyTest('agents', self.league.SET_AGENTS, set())

    def test_agentAllowed(self):
        self._setProp(self.league.SET_AGENTS, "ALL,12,24,36")
        assert_true(self.league.agentAllowed(12))
        assert_true(self.league.agentAllowed("24"))
        assert_true(self.league.agentAllowed("23"))
        self._setProp(self.league.SET_AGENTS, "12,24,36")
        assert_true(self.league.agentAllowed(24))
        assert_false(self.league.agentAllowed(48))

    def test_bannedPlayers(self):
        self._groupPropertyTest('bannedPlayers',
                                  self.league.SET_BANNED_PLAYERS, set())

    def test_bannedClans(self):
        self._groupPropertyTest('bannedClans',
                                  self.league.SET_BANNED_CLANS, set())

    def test_bannedLocations(self):
        self._groupPropertyTest('bannedLocations',
                                self.league.SET_BANNED_LOCATIONS, set())

    def test_allowedPlayers(self):
        self._groupPropertyTest('allowedPlayers',
                                  self.league.SET_ALLOWED_PLAYERS, set())

    def test_allowedClans(self):
        self._groupPropertyTest('allowedClans',
                                  self.league.SET_ALLOWED_CLANS, set())

    def test_allowedLocations(self):
        self._groupPropertyTest('allowedLocations',
                                self.league.SET_ALLOWED_LOCATIONS, set())

    def test_requireClan(self):
        self._setProp(self.league.SET_BANNED_CLANS, "")
        self._boolPropertyTest('requireClan', self.league.SET_REQUIRE_CLAN,
                               False)
        self._setProp(self.league.SET_BANNED_CLANS, "ALL")
        self._boolPropertyTest('requireClan', self.league.SET_REQUIRE_CLAN,
                               True)

    def test_clanAllowed(self):
        player = MagicMock()
        self._setProp(self.league.SET_BANNED_CLANS, "ALL")
        player.clanID = None
        assert_false(self.league._clanAllowed(player))
        player.clanID = 30
        self._setProp(self.league.SET_ALLOWED_CLANS, "30,40,50")
        assert_true(self.league._clanAllowed(player))
        self._setProp(self.league.SET_ALLOWED_CLANS, "ALL")
        assert_true(self.league._clanAllowed(player))
        self._setProp(self.league.SET_ALLOWED_CLANS, "")
        self._setProp(self.league.SET_BANNED_CLANS, "12,13,14")
        assert_true(self.league._clanAllowed(player))
        self._setProp(self.league.SET_BANNED_CLANS, "30,40,50")
        assert_false(self.league._clanAllowed(player))
        self._setProp(self.league.SET_BANNED_CLANS, "ALL")
        assert_false(self.league._clanAllowed(player))

    def test_processLoc(self):
        assert_equals(self.league._processLoc("    Micronesia    "),
                                             "Micronesia")
        assert_equals(self.league._processLoc(" United Haitian  Republic   \n"),
                                             "United Haitian Republic")

    def test_checkLocation(self):
        self._setProp(self.league.SET_BANNED_LOCATIONS, "")
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "")
        assert_equals(self.league._checkLocation("Texas"), None)
        self._setProp(self.league.SET_BANNED_LOCATIONS, "Texas")
        assert_false(self.league._checkLocation("Texas"))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "Texas")
        assert_true(self.league._checkLocation("Texas"))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "ALL")
        assert_false(self.league._checkLocation("California"))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "")
        assert_equals(self.league._checkLocation("California"), None)
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "ALL")
        assert_true(self.league._checkLocation("California"))

    def test_locationAllowed(self):
        player = MagicMock()
        player.location = "United States of Australia: Texas: Earth"
        self._setProp(self.league.SET_BANNED_LOCATIONS, "ALL")
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "")
        assert_false(self.league._locationAllowed(player))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "Texas")
        assert_true(self.league._locationAllowed(player))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "")
        self._setProp(self.league.SET_BANNED_LOCATIONS, "")
        assert_true(self.league._locationAllowed(player))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "United States")
        assert_true(self.league._locationAllowed(player))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "Earth")
        assert_false(self.league._locationAllowed(player))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS,
                      "United States of Australia")
        assert_true(self.league._locationAllowed(player))
        player.location = "United States of Australia"
        self._setProp(self.league.SET_BANNED_LOCATIONS, "ALL")
        assert_true(self.league._locationAllowed(player))
        player.location = ""
        assert_false(self.league._locationAllowed(player))

    def test_meetsAge(self):
        player = MagicMock()
        player.joinDate = date.today() - timedelta(30)
        self._setProp(self.league.SET_MIN_AGE, 30)
        assert_true(self.league._meetsAge(player))
        player.joinDate = date.today()
        assert_false(self.league._meetsAge(player))
        player.joinDate = date.today() - timedelta(400)
        assert_true(self.league._meetsAge(player))

    def test_meetsSpeed(self):
        player = MagicMock()
        player.playSpeed = {'Real-Time Games': 1,
                            'Multi-Day Games': 38}
        self._setProp(self.league.SET_MAX_RT_SPEED, 30)
        self._setProp(self.league.SET_MAX_MD_SPEED, 40)
        assert_false(self.league._meetsSpeed(player))
        self._setProp(self.league.SET_MAX_RT_SPEED, 60)
        assert_true(self.league._meetsSpeed(player))

    def test_meetsLastSeen(self):
        player = MagicMock()
        player.lastSeen = 30
        self._setProp(self.league.SET_MAX_LAST_SEEN, 40)
        assert_true(self.league._meetsLastSeen(player))
        player.lastSeen = 40
        assert_true(self.league._meetsLastSeen(player))
        player.lastSeen = 50
        assert_false(self.league._meetsLastSeen(player))
        self._setProp(self.league.SET_MAX_LAST_SEEN, "None")
        assert_true(self.league._meetsLastSeen(player))

    @patch('resources.league.League._meetsMinRanked')
    @patch('resources.league.League._meetsLastSeen')
    @patch('resources.league.League._RTPercentInRange')
    @patch('resources.league.League._gameCountInRange')
    @patch('resources.league.League._meetsSpeed')
    @patch('resources.league.League._meetsAge')
    @patch('resources.league.League._meetsVacation')
    def test_checkPrereqs(self, vacationCheck, ageCheck, speedCheck,
                          gameCountCheck, rtPercentCheck, lastSeenCheck,
                          minRankedCheck):
        player = MagicMock()
        player.clanID = 45
        self._setProp(self.league.SET_BANNED_CLANS, "43")
        self._setProp(self.league.SET_ALLOWED_CLANS, "")
        player.location = "United States"
        self._setProp(self.league.SET_BANNED_LOCATIONS, "Azerbaijan")
        self._setProp(self.league.SET_ALLOWED_LOCATIONS,
                      "Arizona,New Mexico,Texas")
        player.bootRate = 30
        self._setProp(self.league.SET_MAX_BOOT, "35")
        player.level = 20
        self._setProp(self.league.SET_MIN_LEVEL, "19")
        self._setProp(self.league.SET_MIN_MEMBER_AGE, "0")
        self._setProp(self.league.SET_MEMBERS_ONLY, "FALSE")
        player.isMember = False
        vacationCheck.return_value = True
        player.points = 4000
        self._setProp(self.league.SET_MIN_POINTS, "0")
        ageCheck.return_value = True
        speedCheck.return_value = True
        gameCountCheck.return_value = True
        rtPercentCheck.return_value = True
        lastSeenCheck.return_value = True
        minRankedCheck.return_value = True
        player.playedGames = 30
        self._setProp(self.league.SET_MIN_GAMES, 30)
        self._setProp(self.league.SET_MIN_ACH, 20)
        player.achievementRate = 25
        assert_true(self.league._checkPrereqs(player))
        player.playedGames = 10
        assert_false(self.league._checkPrereqs(player))

    @patch('resources.league.League._checkPrereqs')
    def test_allowed(self, check):
        check.return_value = True
        self._setProp(self.league.SET_ALLOWED_PLAYERS, "40")
        self._setProp(self.league.SET_BANNED_PLAYERS, "40")
        assert_true(self.league._allowed(40))
        check.return_value = False
        assert_true(self.league._allowed(40))
        assert_false(self.league._allowed(43))
        check.return_value = True
        assert_true(self.league._allowed(43))
        self._setProp(self.league.SET_BANNED_PLAYERS, "40,ALL")
        assert_false(self.league._allowed(43))
        self._setProp(self.league.SET_ALLOWED_PLAYERS, "ALL,40")
        assert_true(self.league._allowed(43))

    @patch('resources.league.League._allowed')
    def test_banned(self, allowed):
        allowed.return_value = False
        assert_true(self.league._banned(40))
        allowed.return_value = True
        assert_false(self.league._banned(40))

    def test_logFailedOrder(self):
        order = {'type': 'OrderType', 'author': 3940430, 'orders': ['12','13']}
        self.league._logFailedOrder(order)
        expDesc = "Failed to process OrderType order by 3940430"
        self.parent.log.assert_called_once_with(expDesc,
                                                league=self.league.name,
                                                error=True)

    def test_checkTeamCreator(self):
        self.league.mods = {12,}
        assert_raises(ImproperInput, self.league.checkTeamCreator,
                      43, {44, 45, 46})
        assert_equals(self.league.checkTeamCreator(43, {43,44,45}), None)
        self.league.mods = {43,12}
        assert_equals(self.league.checkTeamCreator(43, {44,45,46}), None)

    def test_checkTemplateAccess(self):
        self.templates.findEntities.return_value = {14: {'WarlightID': 41},
                                                    23: {'WarlightID': 32},
                                                    24: {'WarlightID': 32},
                                                    5: {'WarlightID': 50}}
        self.handler.validateToken.return_value = {'template41': {'result':
                'A'},
                'template32': {'result': "CannotUseTemplate"},
                'template50': {'result': 'B'}}
        assert_equals(self.league.checkTemplateAccess(12), {23,24})

    def test_handleAutodrop(self):
        self.templates.findEntities.return_value = {14: {'WarlightID': 41},
                                                    23: {'WarlightID': 32},
                                                    32: {'WarlightID': 23},
                                                    41: {'WarlightID': 14},
                                                    50: {'WarlightID': 5},
                                                    5: {'WarligtID': 50}}
        self.teams.findEntities.return_value = list()
        assert_raises(ImproperInput, self.league.handleAutodrop, 40, [12, 13])
        self.teams.findEntities.return_value = [{"ID": 2, "Drops": "10/11/12"}]
        self._setProp(self.league.SET_DROP_LIMIT, 4)
        assert_raises(ImproperInput, self.league.handleAutodrop, 2, [13,14])
        self.league.handleAutodrop(2, [12,13])
        self.teams.updateMatchingEntities.assert_called_once_with({'ID':
            {'value': 2, 'type': 'positive'}}, {'Drops': '11/10/13/12'})

    @patch('resources.league.League.checkTemplateAccess')
    @patch('resources.league.League._banned')
    def test_checkTeamMember(self, banCheck, checkTemp):
        banCheck.return_value = True
        assert_raises(ImproperInput, self.league.checkTeamMember, 12, {1,2,3})
        banCheck.return_value = False
        checkTemp.return_value = {40,12,31}
        badTemps = {1, 2, 3}
        self.league.checkTeamMember(12, badTemps)
        assert_equals(badTemps, {1, 2, 3, 12, 31, 40})

    def test_autodropEligible(self):
        self._setProp(self.league.SET_AUTODROP, "FALSE")
        assert_false(self.league.autodropEligible({1,2,3}))
        self._setProp(self.league.SET_AUTODROP, "TRUE")
        self.templates.findEntities.return_value = {10: {'WarlightID': 1},
                                                    11: {'WarlightID': 12},
                                                    12: {'WarlightID': 13}}
        self._setProp(self.league.SET_DROP_LIMIT, "1")
        assert_false(self.league.autodropEligible({1,2,3,4,5}))
        assert_true(self.league.autodropEligible({2,}))

    @patch('resources.league.League.handleAutodrop')
    @patch('resources.league.League.autodropEligible')
    def test_handleTeamAutodrop(self, eligible, handle):
        eligible.return_value = False
        assert_raises(ImproperInput, self.league.handleTeamAutodrop, 12,
                      {1,2,3}, {1,2})
        eligible.return_value = True
        assert_equals(self.league.handleTeamAutodrop(None, {1}, {1,2}), "1/2")
        assert_equals(self.league.handleTeamAutodrop(12, {1,2,3}, {1,2}), "")
        handle.assert_called_once_with(12, {1,2})

    @patch('resources.league.League.handleTeamAutodrop')
    @patch('resources.league.League.checkTeamMember')
    def test_checkTeam(self, check, handle):
        assert_equals(self.league.checkTeam({49,94,20,38}),
                      handle.return_value)
        assert_equals(check.call_count, 4)

    def test_checkLimit(self):
        self._setProp(self.league.SET_MIN_LIMIT, 8)
        self._setProp(self.league.SET_MAX_LIMIT, 12)
        self._setProp(self.league.SET_CONSTRAIN_LIMIT, False)
        assert_equals(self.league.checkLimit(10), 10)
        assert_raises(ImproperInput, self.league.checkLimit, 13)
        assert_raises(ImproperInput, self.league.checkLimit, 4)
        self._setProp(self.league.SET_CONSTRAIN_LIMIT, True)
        assert_equals(self.league.checkLimit(13), 12)
        assert_equals(self.league.checkLimit(4), 8)
        assert_equals(self.league.checkLimit(10), 10)

    def test_existingIDs(self):
        self.teams.findValue.return_value = ["1","2","3","4","5"]
        self.games.findValue.return_value = ["12,13/1,2", "3,4/5"]
        assert_equals(self.league.existingIDs, {1, 2, 3, 4, 5, 12, 13})
        self.league.setCurrentID()
        assert_equals(self.league.currentID, 14)
        self.teams.findValue.return_value = list()
        self.games.findValue.return_value = list()
        assert_equals(self.league.existingIDs, set())
        self.league.setCurrentID()
        assert_equals(self.league.currentID, 0)

    def test_defaultRating(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        assert_equals(self.league.defaultRating,
                      self.league.sysDict[self.league.RATE_ELO]['default']())
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_WINRATE)
        assert_equals(self.league.defaultRating,
                      self.league.sysDict[self.league.RATE_WINRATE][
                         'default']())

    def test_teamPlayers(self):
        self.teams.findEntities.return_value = [{'Name': "A",
                                                 'Players': "1,2"},
                                               {'Name': "b", 'Players': "3,4"},
                                               {'Name': "C D", 'Players': "5"}]
        assert_equals(self.league.allTeams,
                      self.teams.findEntities.return_value)
        assert_equals(self.league.teamPlayers, {'1,2': 'A', '3,4': 'b',
                                                '5': 'C D'})

    def test_checkJoins(self):
        self._setProp(self.league.SET_ALLOW_JOINS, "TRUE")
        self._setProp(self.league.SET_JOIN_PERIOD_START,
                      date.today() - timedelta(1))
        self._setProp(self.league.SET_JOIN_PERIOD_END,
                      date.today() + timedelta(1))
        self._setProp(self.league.SET_LEAGUE_CAPACITY, None)
        self._setProp(self.league.SET_ACTIVE_CAPACITY, None)
        assert_equals(self.league.checkJoins(), None)
        self._setProp(self.league.SET_ALLOW_JOINS, "FALSE")
        assert_raises(ImproperInput, self.league.checkJoins)

    @patch('resources.league.PlayerParser')
    def test_checkConsistentClan(self, parser):
        parser.return_value.clanID = None
        assert_equals(self.league.checkConsistentClan([1, 2, 3, 4, 5], False),
                      None)
        assert_equals(self.league.checkConsistentClan([1, 2, 3, 4, 5], True),
                      None)
        class FakeParser(object):
            def __init__(self, val):
                self.clanID = val
        parser.side_effect = [FakeParser(x) for x in xrange(5)]
        assert_equals(self.league.checkConsistentClan([1, 2, 3, 4, 5], False),
                      None)
        assert_raises(ImproperInput, self.league.checkConsistentClan,
                      [1, 2, 3, 4, 5], True)

    @patch('resources.league.League.checkConsistentClan')
    @patch('resources.league.League.checkTeam')
    def test_checkAuthorAndMembers(self, check, checkClan):
        self._setProp(self.league.SET_ONLY_MODS_CAN_ADD, "FALSE")
        order = {'author': 1403, 'orders': ['1v1', 'teamName', '3', '40', '2']}
        self.league.mods = {1403,}
        assert_equals(self.league.checkAuthorAndMembers(order),
                      (check.return_value, [40, 2], [False, False]))
        self.league.mods = set()
        assert_raises(ImproperInput, self.league.checkAuthorAndMembers, order)
        order['author'] = 40
        assert_equals(self.league.checkAuthorAndMembers(order),
                      (check.return_value, [40, 2], [True, False]))
        self._setProp(self.league.SET_ONLY_MODS_CAN_ADD, "TRUE")
        assert_raises(ImproperInput, self.league.checkAuthorAndMembers, order)
        assert_equals(checkClan.call_count, 2)

    @patch('resources.league.League.checkLimit')
    @patch('resources.league.League.checkAuthorAndMembers')
    def test_checkEligible(self, check, limCheck):
        order = {'author': 1403, 'orders': ['1v1', 'teamName', '3', '40', '2']}
        check.return_value = [1, 2, 3]
        assert_equals(self.league.checkEligible(order),
                      (limCheck.return_value, 1, 2, 3))
        limCheck.assert_called_once_with(3)

    def test_getTeamNameFromOrder(self):
        order = {'orders': ['', 'TeamName',]}
        self._setProp(self.league.SET_NAME_LENGTH, 5)
        self._setProp(self.league.SET_CONSTRAIN_NAME, "FALSE")
        assert_raises(ImproperInput, self.league.getTeamNameFromOrder, order)
        self._setProp(self.league.SET_CONSTRAIN_NAME, "TRUE")
        assert_equals(self.league.getTeamNameFromOrder(order), "TeamN")
        self._setProp(self.league.SET_NAME_LENGTH, "")
        assert_equals(self.league.getTeamNameFromOrder(order), "TeamName")
        self._setProp(self.league.SET_NAME_LENGTH, 8)
        assert_equals(self.league.getTeamNameFromOrder(order), "TeamName")

    @patch('resources.league.League.checkEligible')
    @patch('resources.league.League.checkJoins')
    def test_addTeam(self, joinCheck, eligible):
        order = {'author': 1403, 'type': 'add_team',
                 'orders': ['1v1', 'name', '3', '41', '4042', '3905', '12']}
        eligible.return_value = (5, "", [41, 4042, 3905, 12], [False,
                                 True, False, True])
        oldCurr = self.league.currentID
        self.league.addTeam(order)
        self.teams.addEntity.assert_called_with({'ID': oldCurr,
                                                 'Name': 'name',
                                                 'Limit': 5,
                                                 'Players': '12,41,3905,4042',
                                                 'Confirmations':
                                                 'TRUE,FALSE,FALSE,TRUE',
                                                 'Vetos': "", 'Drops': "",
                                                 'Ongoing': 0, 'Finished': 0,
                                                 'Rating':
                                                 self.league.defaultRating})
        assert_equals(self.league.currentID, oldCurr + 1)

    def test_retrieveTeamWithName(self):
        self.teams.findEntities.return_value = list()
        assert_raises(NonexistentItem, self.league.retrieveTeamWithName,
                      'Lugia')
        self.teams.findEntities.return_value = [{'ID': 4, 'Name': 'ho oh'},]
        assert_equals(self.league.retrieveTeamWithName('ho oh'),
                      {'ID': 4, 'Name': 'ho oh'})

    def test_authorInTeam(self):
        self.league.mods = {1,2,3}
        team = {'ID': 4, 'Players': '49,50,54'}
        assert_true(self.league.authorInTeam(2, team))
        assert_false(self.league.authorInTeam(2, team, False))
        assert_true(self.league.authorInTeam(50, team))
        assert_true(self.league.authorInTeam(50, team, False))

    @patch('resources.league.League.retrieveTeamWithName')
    def test_fetchMatchingTeam(self, retrieve):
        retrieve.return_value = {'Players': '11,13,14'}
        order = {'author': 12, 'orders': 'teamName'}
        self.league.mods = {12,}
        assert_raises(ImproperInput, self.league.fetchMatchingTeam, order,
                      True, False)
        assert_equals(self.league.fetchMatchingTeam(order),
                      ({'Players': '11,13,14'}, None))
        order['author'] = 11
        assert_equals(self.league.fetchMatchingTeam(order),
                      ({'Players': '11,13,14'}, 0))

    @patch('resources.league.League.updateConfirms')
    @patch('resources.league.League.fetchMatchingTeam')
    def test_toggleConfirm(self, fetch, update):
        fetch.return_value = ({'Players': '11,13,14', 'ID': 24,
                               'Confirmations': 'TRUE,FALSE,FALSE'}, 0)
        self.league.toggleConfirm('order')
        update.assert_called_once_with(24, ["TRUE", "FALSE", "FALSE"])
        self.league.toggleConfirm('order', False)
        update.assert_called_with(24, ["FALSE", "FALSE" , "FALSE"])

    @patch('resources.league.League.toggleConfirms')
    @patch('resources.league.League.toggleConfirm')
    def test_toggleTeamConfirm(self, toggle, toggles):
        self.league.mods = {1,2,3}
        order = {'author': "1", 'orders': ('1', '2', '3')}
        self.league.confirmTeam(order)
        toggles.assert_called_once_with(order, confirm=True)
        self.league.unconfirmTeam(order)
        toggles.assert_called_with(order, confirm=False)
        order['author'] = '12'
        self.league.confirmTeam(order)
        toggle.assert_called_once_with(order, confirm=True)
        self.league.unconfirmTeam(order)
        toggle.assert_called_with(order, confirm=False)

    @patch('resources.league.League.toggleConfirm')
    def test_toggleConfirms(self, toggle):
        order = {'type': 'confirm_team', 'author': 3022124041,
                 'orders': ['1v1', 'St. Louis Blues', '12', '13', '14']}
        self.league.toggleConfirms(order)
        assert_equals(toggle.call_count, 3)
        toggle.assert_called_with({'author': 14, 'orders': ['NAME',
                                   'St. Louis Blues']}, confirm=True)

    @patch('resources.league.League.fetchMatchingTeam')
    def test_removeTeam(self, fetch):
        self._setProp(self.league.SET_ALLOW_REMOVAL, "FALSE")
        order = {'type': 'remove_team', 'author': '30',
                 'orders': ('1v1', 'The Harambes')}
        assert_raises(ImproperInput, self.league.removeTeam, order)
        self._setProp(self.league.SET_ALLOW_REMOVAL, "TRUE")
        self.league.removeTeam(order)
        self.teams.removeMatchingEntities.assert_called_once_with({'ID':
            {'value': fetch.return_value[0]['ID'], 'type': 'positive'}})

    @patch('resources.league.League._fetchTeamData')
    def test_checkLimitChange(self, fetch):
        assert_equals(self.league.checkLimitChange(400, -3), None)
        assert_equals(self.league.checkLimitChange(100, 0), None)
        self._setProp(self.league.SET_ACTIVE_CAPACITY, "")
        assert_equals(self.league.checkLimitChange(100, 3), None)
        self._setProp(self.league.SET_ACTIVE_CAPACITY, 2)
        self.teams.findEntities.return_value = [{'ID': 1, 'Limit': 1},]
        assert_equals(self.league.checkLimitChange(42, 20), None)
        self.teams.findEntities.return_value = [{'ID': 1, 'Limit': 3},
                                                {'ID': 2, 'Limit': 2}]
        fetch.return_value = {'Limit': 3}
        assert_equals(self.league.checkLimitChange(42, 20), None)
        fetch.return_value = {'Limit': 0}
        assert_raises(ImproperInput, self.league.checkLimitChange, 2, 2)
        assert_equals(self.league.checkLimitChange(42, 0), None)
        self.teams.findEntities.return_value = [{'ID': 1, 'Limit': 1},
            {'ID': 2, 'Limit': 3}, {'ID': 3, 'Limit': 2}]
        assert_raises(ImproperInput, self.league.checkLimitChange, 24, 2)

    @patch('resources.league.League.changeLimit')
    @patch('resources.league.League.checkLimitChange')
    @patch('resources.league.League.fetchMatchingTeam')
    def test_setLimit(self, fetch, check, change):
        order = {'type': 'set_limit', 'author': 3022124041,
                 'orders': ['1v1', 'The Harambes', '3']}
        fetch.return_value = ({'Players': '12,14,15', 'ID': 4}, None)
        assert_equals(self.league.setLimit(order), None)
        check.assert_called_once_with(4, '3')
        change.assert_called_once_with(4, '3')

    def test_templateIDs(self):
        self.templates.findEntities.return_value = "retval"
        assert_equals(self.league.templateIDs, "retval")

    def test_validScheme(self):
        tempData = {'Schemes': '1v1,2v2,4v4'}
        self.league._gameSize = list()
        self.league._sideSize = list()
        self._setProp(self.league.SET_GAME_SIZE, '5')
        self._setProp(self.league.SET_TEAMS_PER_SIDE, '2')
        self._setProp(self.league.SET_TEAM_SIZE, '2')
        assert_false(self.league.validScheme(tempData))
        self.league._gameSize = list()
        self._setProp(self.league.SET_GAME_SIZE, '2')
        assert_true(self.league.validScheme(tempData))
        self.league._gameSize = list()
        self.league._sideSize = list()
        self._setProp(self.league.SET_GAME_SIZE, '3')
        self._setProp(self.league.SET_TEAMS_PER_SIDE, '3')
        self._setProp(self.league.SET_TEAM_SIZE, '4')
        assert_false(self.league.validScheme(tempData))
        tempData['Schemes'] = '1v1,2v2,3v3,4v4,12v12v12'
        assert_true(self.league.validScheme(tempData))
        tempData['Schemes'] = '1v1,2v2,ALL'
        assert_true(self.league.validScheme(tempData))

    def test_narrowToValidSchemes(self):
        templates = {1: {'Schemes': '1v1,2v2,ALL'}, 2: {'Schemes': '3v3'},
                3: {'Schemes': '1v1,ALL'}, 4: {'Schemes': '2v2,4v4'},
                5: {'Schemes': '2v2'}, 6: {'Schemes': '3v3v3v3v3,4v4v4v4v4'}}
        self.league._gameSize, self.league._sideSize = list(), list()
        self._setProp(self.league.SET_GAME_SIZE, '2,2,2,2,2')
        self._setProp(self.league.SET_TEAMS_PER_SIDE, '1,1')
        self._setProp(self.league.SET_TEAM_SIZE, '2')
        assert_equals(self.league.scheme, '2v2')
        assert_true(self.league.multischeme)
        assert_equals(len(self.league.narrowToValidSchemes(templates)), 4)
        self.templates.findEntities.return_value = templates
        assert_equals(len(self.league.usableTemplateIDs), 4)
        self.league._gameSize, self.league._sideSize = list(), list()
        self._setProp(self.league.SET_GAME_SIZE, '2')
        self._setProp(self.league.SET_TEAMS_PER_SIDE, '1')
        assert_equals(self.league.usableTemplateIDs, templates)

    def test_gameIDs(self):
        assert_equals(self.league.gameIDs, self.games.findValue.return_value)

    def test_templateRanks(self):
        self.templates.findEntities.return_value = [{'ID': 3, 'Usage': 3},
                                                    {'ID': 4, 'Usage': 4},
                                                    {'ID': 5, 'Usage': 2},
                                                    {'ID': 1, 'Usage': 0}]
        assert_equals(self.league.templateRanks, [(1,0), (5,2), (3,3), (4,4)])

    def test_findMatchingTemplate(self):
        self.templates.findValue.return_value = list()
        assert_equals(self.league.findMatchingTemplate('name'), None)
        self.templates.findValue.return_value = [1, 2, 3, 4, 5]
        assert_equals(self.league.findMatchingTemplate('name'), 1)

    @patch('resources.league.League.fetchMatchingTeam')
    def test_getExistingDrops(self, fetch):
        fetch.return_value = ({'Drops': '12/13/14', 'ID': 43}, None)
        assert_equals(self.league.getExistingDrops('order'),
                      (43, {'12','13','14'}))

    @patch('resources.league.League._updateEntityValue')
    def test_updateTeamDrops(self, update):
        drops = {'14', '23', '12', '43', '4053', 12}
        self.league.updateTeamDrops(1249, drops)
        update.assert_called_once_with(self.teams, 1249,
                                       Drops='43/12/4053/14/23')

    @patch('resources.league.League.updateTeamDrops')
    @patch('resources.league.League.findMatchingTemplate')
    @patch('resources.league.League.getExistingDrops')
    def test_dropTemplates(self, getExisting, find, update):
        order = {'type': 'drop_templates', 'author': 3022124041,
                 'orders': ['1v1', 'The Harambes', 'North Korea 1v1',
                            'Sanctuary 3v3', 'Cincinnati Zoo FFA']}
        getExisting.return_value = 4032, {'12', '13', '14'}
        self.templates.findEntities.return_value = xrange(200)
        self._setProp(self.league.SET_DROP_LIMIT, 3)
        assert_raises(ImproperInput, self.league.dropTemplates, order)
        self._setProp(self.league.SET_DROP_LIMIT, 4)
        assert_equals(self.league.dropLimit, 4)
        find.return_value = {'ID': 3}
        self.league.dropTemplates(order)
        dataStr = "Too many drops by team The Harambes, dropping only first 1"
        self.parent.log.assert_called_with(dataStr, 'NAME', error=True)
        update.assert_called_once_with(4032, {'12', '13', '14', '3'})
        self._setProp(self.league.SET_DROP_LIMIT, 40)
        assert_equals(self.league.dropLimit, 40)
        oldCount = self.parent.log.call_count
        getExisting.return_value = 4033, {'12', '13', '14', '15'}
        self.league.dropTemplates(order)
        assert_equals(self.parent.log.call_count, oldCount)
        update.assert_called_with(4033, {'12', '13', '14', '15', '3'})
        find.return_value = None
        getExisting.return_value = 4033, {'12', '13', '14', '15'}
        self.league.dropTemplates(order)
        update.assert_called_with(4033, {'12', '13', '14', '15'})

    @patch('resources.league.League.updateTeamDrops')
    @patch('resources.league.League.findMatchingTemplate')
    @patch('resources.league.League.getExistingDrops')
    def test_undropTemplates(self, getExisting, find, update):
        order = {'type': 'undrop_templates', 'author': 3022124041,
                 'orders': ['1v1', 'The Harambes', 'North Korea 1v1',
                           'Sanctuary 3v3', 'Cincinnati Zoo FFA']}
        getExisting.return_value = 4032, {'12', '13', '14'}
        find.return_value = {'ID': 12}
        self.league.undropTemplates(order)
        update.assert_called_once_with(4032, {'13', '14'})
        find.return_value = None
        getExisting.return_value = 4032, {'12', '13', '14'}
        self.league.undropTemplates(order)
        update.assert_called_with(4032, {'12', '13', '14'})

    def test_toggleActivity(self):
        order = {'author': 12, 'orders': ['1v1', 'tempName',]}
        self.league.mods = {10, 11}
        assert_raises(ImproperInput, self.league.activateTemplate, order)
        self.league.mods.add(12)
        self.league.templates.findEntities.return_value = xrange(200)
        self._setProp(self.league.SET_MIN_TEMPLATES, 1)
        assert_equals(self.league.deactivateTemplate(order), None)
        self.league.templates.updateMatchingEntities.assert_called_with({
            'Name': {'value': 'tempName', 'type': 'positive'}},
            {'Active': 'FALSE'})
        self._setProp(self.league.SET_MIN_TEMPLATES, 210)
        assert_raises(ImproperInput, self.league.deactivateTemplate, order)

    def test_allTeams(self):
        assert_equals(self.league.allTeams,
                      self.teams.findEntities.return_value)

    def test_getPlayersFromOrder(self):
        order = {'author': 12, 'orders': ['1v1', '1204', '902', '671']}
        self.league.mods = set()
        assert_equals(self.league.getPlayersFromOrder(order), {'12',})
        self.league.mods.add(12)
        assert_equals(self.league.getPlayersFromOrder(order),
                      {'1204','902','671'})

    def test_updateConfirms(self):
        self.league.updateConfirms(13804, [True, False, False])
        self.teams.updateMatchingEntities.assert_called_with({'ID': {'value':
            13804, 'type': 'positive'}}, {'Confirmations': 'TRUE,FALSE,FALSE'})

    @patch('resources.league.League.updateConfirms')
    @patch('resources.league.League.getPlayersFromOrder')
    def test_quitLeague(self, getPlayers, update):
        getPlayers.return_value = {'11', '13', '15'}
        self.teams.findEntities.return_value = [{'ID': 1, 'Players': '1,2,3',
            'Confirmations': 'TRUE,TRUE,FALSE'}, {'ID': 2, 'Players': '11,0,2',
            'Confirmations': 'TRUE,FALSE,FALSE'}, {'ID': 3, 'Players': '11,13',
            'Confirmations': 'FALSE,TRUE'}]
        self.league.quitLeague('order')
        assert_equals(update.call_count, 2)
        update.assert_called_with(3, ['FALSE', 'FALSE'])

    def test_newTempGameCount(self):
        self.templates.findEntities.return_value = [{'Usage': 8},
            {'Usage': 12}, {'Usage': 12}, {'Usage': 8}, {'Usage': 11}]
        assert_equals(self.league.newTempGameCount, 10)
        self._setProp(self.league.SET_FAVOR_NEW_TEMPLATES, "TRUE")
        assert_equals(self.league.newTempGameCount, 0)

    def test_addTemplate(self):
        self._setProp(self.league.SET_FAVOR_NEW_TEMPLATES, "TRUE")
        self.league.admin = 43
        self.games.findEntities.return_value = [{'Template': '12'},
            {'Template': '43'}, {'Template': '91'}]
        self.templates.findEntities.return_value = range(39)
        assert_equals(self.league.usedTemplates,
                      set(range(39)).union([12, 43, 91]))
        order = {'type': 'add_template', 'author': 41,
                 'orders': ['1v1', 'Template Name', '4902494',
                            'SET_Setting#Sub', 'Val', 'OVERRIDE_Mexico', 3]}
        self._setProp(self.league.SET_GAME_SIZE, "3")
        self._setProp(self.league.SET_TEAMS_PER_SIDE, "4")
        assert_false(self.league.multischeme)
        assert_raises(ImproperInput, self.league.addTemplate, order)
        order['author'] = 43
        self.league.addTemplate(order)
        self.templates.addEntity.assert_called_with({'ID': 92,
            'Name': 'Template Name', 'WarlightID': '4902494',
            'Active': 'TRUE', 'Usage': 0, 'SET_Setting#Sub': 'Val',
            'OVERRIDE_Mexico': 3})
        self._setProp(self.league.SET_GAME_SIZE, "5,7,6")
        assert_true(self.league.multischeme)
        order['orders'] = ['1v1', 'Template Name', '4902494', '1v1,2v2,3v3',
                           'SET_Setting#Sub', 'Val', 'OVERRIDE_Mexico', 3]
        self.league.addTemplate(order)
        self.templates.addEntity.assert_called_with({'ID': 92,
            'Name': 'Template Name', 'WarlightID': '4902494',
            'Active': 'TRUE', 'Usage': 0, 'SET_Setting#Sub': 'Val',
            'OVERRIDE_Mexico': 3, 'Schemes': '1v1,2v2,3v3'})

    @patch('resources.league.League.fetchMatchingTeam')
    def test_renameTeam(self, fetch):
        fetch.return_value = [{'ID': 3},]
        self._setProp(self.league.SET_NAME_LENGTH, None)
        self.league.renameTeam({'orders': ['1v1', 'Old Name', 'New Name']})
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 3, 'type': 'positive'}}, {'Name': 'New Name'})

    @patch('resources.league.League.updateRanks')
    @patch('resources.league.League._logFailedOrder')
    @patch('resources.league.League.renameTeam')
    @patch('resources.league.League.addTemplate')
    @patch('resources.league.League.quitLeague')
    @patch('resources.league.League.deactivateTemplate')
    @patch('resources.league.League.activateTemplate')
    @patch('resources.league.League.undropTemplates')
    @patch('resources.league.League.dropTemplates')
    @patch('resources.league.League.removeTeam')
    @patch('resources.league.League.setLimit')
    @patch('resources.league.League.unconfirmTeam')
    @patch('resources.league.League.confirmTeam')
    @patch('resources.league.League.addTeam')
    def test_executeOrders(self, addTeam, confirmTeam, unconfirmTeam,
                           setLimit, removeTeam, dropTemplates,
                           undropTemplates, activateTemplate,
                           deactivateTemplate, quitLeague, addTemplate,
                           renameTeam, logFailedOrder, updateRanks):
        existingLogs = self.parent.log.call_count
        self.league.orders = [{'type': 'ADD_team'}, {'type': 'add_team'},
            {'type': 'confirm_team'}, {'type': 'CONFIRM_TEAM'},
            {'type': 'unconfirm_team'}, {'type': 'sEt_lImIt'},
            {'type': 'remove_team'}, {'type': 'drop_templates'},
            {'type': 'drop_template'}, {'type': 'undrop_template'},
            {'type': 'undrop_templates'}, {'type': 'activate_template'},
            {'type': 'deactivate_template'}, {'type': 'quit_league'},
            {'type': 'subtract_team'}, {'type': 'add_template'},
            {'type': 'rename_team'}]
        self.league.executeOrders()
        updateRanks.assert_called_once_with()
        assert_equals(self.parent.log.call_count, existingLogs+1)
        quitLeague.side_effect = IOError
        self.league.executeOrders()
        logFailedOrder.assert_called_once_with({'type': 'quit_league'})

    def test_unfinishedGames(self):
        assert_equals(self.league.unfinishedGames,
                      self.games.findEntities.return_value)

    def test_isAbandoned(self):
        players = [{'state': 'VotedToEnd'}, {'state': 'Waiting'},
                   {'state': 'Declined'}, {'state': 'Wyoming'}]
        assert_true(self.league._isAbandoned(players))
        players = [{'state': 'Declined'}, {'state': 'Won'},
                   {'state': 'Declined'}, {'state': 'Wyoming'}]
        assert_false(self.league._isAbandoned(players))
        players = list()
        assert_false(self.league._isAbandoned(players))
        players = [{'state': 'Duck'}, {'state': 'Duck'},
                   {'state': 'Duck'}, {'state': 'Goose'}]
        assert_false(self.league._isAbandoned(players))

    def test_findMatchingPlayers(self):
        players = [{'id': 4, 'state': 'VotedToEnd'},
            {'id': 12, 'state': 'Velociraptor'}, {'id': 1, 'state': 'Won'},
            {'id': 39, 'state': 'Velociraptor'}, {'id': 5, 'state': 'Wyoming'},
            {'id': 40, 'state': 'Won'}, {'id': 3, 'state': 'Velociraptor'}]
        assert_equals(self.league._findMatchingPlayers(players), list())
        assert_equals(self.league._findMatchingPlayers(players, 'Won'), [1, 40])
        assert_equals(self.league._findMatchingPlayers(players, 'Velociraptor'),
                      [3, 12, 39])
        assert_equals(self.league._findMatchingPlayers(players, 'Won',
                      'Wyoming'), [1, 5, 40])
        assert_equals(self.league._findWinners(players), [1, 40])
        assert_equals(self.league._findDecliners(players), list())
        assert_equals(self.league._findWaiting(players), list())
        assert_equals(self.league._findBooted(players), list())

    @patch('resources.league.League._findBooted')
    @patch('resources.league.League._findDecliners')
    @patch('resources.league.League._findWinners')
    @patch('resources.league.League._isAbandoned')
    def test_handleFinished(self, abandon, find, declines, boots):
        abandon.return_value = True
        gameData = {'players': [{'id': 5, 'state': 'Declined'},
            {'id': 10, 'state': 'Eliminated'}, {'id': 15, 'state': 'Won'}]}
        assert_equals(self.league._handleFinished(gameData),
                      ('ABANDONED', [5, 10, 15]))
        abandon.return_value = False
        declines.return_value = range(3)
        assert_equals(self.league._handleFinished(gameData),
                      ('DECLINED', declines.return_value))
        declines.return_value = list()
        assert_equals(self.league._handleFinished(gameData),
                      ('FINISHED', find.return_value, boots.return_value))

    @patch('resources.league.League._findWaiting')
    @patch('resources.league.League._findDecliners')
    def test_handleWaiting(self, decliners, waiting):
        self._setProp(self.league.SET_EXP_THRESH, 3)
        assert_equals(self.league.expiryThreshold, 3)
        gameData = {'players': [1, 2, 3, 4, 5], 'id': '3'}
        created = datetime.now() - timedelta(5)
        decliners.return_value = range(3)
        assert_equals(self.league._handleWaiting(gameData, created),
                      ('DECLINED', range(3)))
        decliners.return_value = xrange(1, 6)
        assert_equals(self.league._handleWaiting(gameData, created),
                      ('ABANDONED', None))
        waiting.return_value = range(3)
        decliners.return_value = list()
        assert_false(len(waiting.return_value) == len(gameData['players']))
        assert_equals(self.league._handleWaiting(gameData, created),
                      ('DECLINED', range(3)))
        waiting.return_value = xrange(1, 6)
        assert_equals(self.league._handleWaiting(gameData, created),
                      ('ABANDONED', None))
        created = datetime.now() - timedelta(1)
        assert_false((datetime.now() - created).days >
                     self.league.expiryThreshold)
        assert_equals(self.league._handleWaiting(gameData, created), None)
        assert_equals(self.handler.deleteGame.call_count, 4)

    @patch('resources.league.League._handleWaiting')
    @patch('resources.league.League._handleFinished')
    def test_fetchGameStatus(self, finished, waiting):
        self.handler.queryGame.return_value = {'state': 'Finished'}
        assert_equals(self.league._fetchGameStatus(3, 'created'),
                      finished.return_value)
        self.handler.queryGame.return_value = {'state': 'WaitingForPlayers'}
        assert_equals(self.league._fetchGameStatus(4, 'created'),
                      waiting.return_value)
        self.handler.queryGame.return_value = {'state': 'Massachusetts'}
        assert_equals(self.league._fetchGameStatus(5, 'created'), None)

    def test_fetchDataByID(self):
        table = MagicMock()
        table.findEntities.return_value = list()
        assert_raises(NonexistentItem, self.league._fetchDataByID, table, 'ID',
            'itemType')
        table.findEntities.return_value = [1, 2, 3]
        assert_equals(self.league._fetchDataByID(table, 'ID', 'type'), 1)
        self.games.findEntities.return_value = [2, 4, 6]
        assert_equals(self.league._fetchGameData('gameID'), 2)
        self.teams.findEntities.return_value = [3,]
        assert_equals(self.league._fetchTeamData('gameID'), 3)
        self.templates.findEntities.return_value = range(30, 500)
        assert_equals(self.league._fetchTemplateData('templateID'), 30)

    def test_findCorrespondingTeams(self):
        self.games.findEntities.return_value = [{'Sides': '12,43/49,13,11'},]
        findEntities = (lambda x: [{'Players': '1,2,3'},]
            if int(x['ID']['value']) < 15 else [{'Players': '43,45,48'},])
        self.teams.findEntities = findEntities
        assert_equals(self.league._findCorrespondingTeams(12, [1, 2, 3]),
            {'11', '12', '13'})

    @patch('resources.league.datetime')
    def test_setWinners(self, time):
        time.strftime.return_value = ''
        self.league._setWinners(48, {12, 13, 43})
        self.games.updateMatchingEntities.assert_called_with({'ID': {'value':
            48, 'type': 'positive'}}, {'Winners': '12,13,43', 'Finished': ''})
        self.league._setWinners(48, {12, 13, 14}, True)
        self.games.updateMatchingEntities.assert_called_with({'ID': {'value':
            48, 'type': 'positive'}}, {'Winners': '12,13,14!', 'Finished': ''})

    @patch('resources.league.League._fetchTeamData')
    def test_adjustTeamGameCount(self, fetch):
        fetch.return_value = {'Ongoing': 3, 'Finished': 5}
        self.league._adjustTeamGameCount(3, 5, 4)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 3, 'type': 'positive'}}, {'Ongoing': '8',
             'Finished': '9'})

    @patch('resources.league.League._fetchTemplateData')
    def test_adjustTemplateGameCount(self, fetch):
        fetch.return_value = {'Usage': 8}
        self.league._adjustTemplateGameCount(12, 43)
        self.templates.updateMatchingEntities.assert_called_with({'ID':
            {'value': 12, 'type': 'positive'}}, {'Usage': '51'})

    @patch('resources.league.League.eloEnv')
    def test_getEloDiff(self, eloEnv):
        eloEnv.rate.return_value = 30
        assert_equals(self.league._getEloDiff(40, xrange(5), 5), -2)

    @patch('resources.league.League.getTeamRating')
    def test_getEloRating(self, getRtg):
        getRtg.return_value = '4098'
        assert_equals(self.league._getEloRating(43), 4098)

    @patch('resources.league.League._getEloRating')
    def test_getSideEloRating(self, getElo):
        getElo.return_value = 12
        assert_equals(self.league._getSideEloRating({1, 2, 3}), 36)

    @patch('resources.league.League._getEvent')
    @patch('resources.league.League._getSideEloRating')
    def test_makeOpps(self, getSide, getEvent):
        getSide.return_value = 49
        getEvent.return_value = 'LOSS'
        assert_equals(self.league._makeOpps([{12, 14, 19}, {49, 4}, {1, 2, 3}],
            1, 2), [('LOSS', 49), ('LOSS', 49)])

    def test_applyEloDiff(self):
        diffs = {12: 94, 13: 49}
        self.league._applyEloDiff({12, 15, 390}, 43, diffs)
        expVal = Decimal(43) / Decimal(3)
        assert_equals(diffs, {12: expVal, 13: 49, 15: expVal, 390: expVal})

    @patch('resources.league.League._getEloRating')
    @patch('resources.league.League._getEloDiff')
    @patch('resources.league.League._makeOpps')
    @patch('resources.league.League._getSideEloRating')
    def test_getNewEloRatings(self, rtg, opps, diff, teamRtg):
        teamRtg.return_value = 12
        diff.return_value = 3
        assert_equals(self.league._getNewEloRatings([{1, 2}, {3, 4}, {5,}], 0),
                {1: '14', 2: '14', 3: '14', 4: '14', 5: '15'})

    def test_unsplitRtg(self):
        assert_equals(self.league._unsplitRtg((43, 44, 56, 90)), '43/44/56/90')

    @patch('resources.league.League.getTeamRating')
    def test_getGlickoRating(self, getRtg):
        getRtg.return_value = '5/3'
        assert_equals(self.league._getGlickoRating(43), (5, 3))
        assert_equals(self.league._getSideGlickoRating({1, 2, 3}), (15, 9))

    def test_getEvent(self):
        assert_equals(self.league._getEvent(1, 2, 3), None)
        assert_equals(self.league._getEvent(1, 2, 1), 1)
        assert_equals(self.league._getEvent(1, 2, 2), 0)

    def test_updateGlickoMatchup(self):
        side1, side2 = MagicMock(), MagicMock()
        players = [side1, 4, 3, side2, 9]
        self.league._updateGlickoMatchup(players, 0, 3, 0)
        side1.update_player.assert_called_once_with([side2.rating,],
            [side2.rd,], [1,])
        side2.update_player.assert_called_once_with([side1.rating,],
            [side1.rd,], [0,])
        self.league._updateGlickoMatchup(players, 1, 2, 3)
        assert_equals(side1.update_player.call_count, 1)
        assert_equals(side2.update_player.call_count, 1)

    @patch('resources.league.Player')
    @patch('resources.league.League._getSideGlickoRating')
    def test_makeGlickoPlayersFromSides(self, getSideRtg, plyr):
        getSideRtg.return_value = (10, 42)
        assert_equals(self.league._makeGlickoPlayersFromSides([{1,2,3}, {4,5}]),
            [plyr.return_value,] * 2)

    @patch('resources.league.League._updateGlickoMatchup')
    def test_updateGlickoMatchups(self, update):
        self.league._updateGlickoMatchups([{1,2}, {3,4}, {5,6}], 'playaz', 0)
        assert_equals(update.call_count, 3)
        update.assert_called_with('playaz', 1, 2, 0)

    @patch('resources.league.League._getGlickoRating')
    @patch('resources.league.League._getSideGlickoRating')
    def test_getGlickoResultsFromPlayers(self, getSide, getRtg):
        getSide.return_value = 12, 1
        getRtg.return_value = 3, 2
        player = MagicMock()
        player.rating, player.rd = 13, 10
        players = [player,] * 3
        sides = [{1,2}, {3,4}, {5,6}]
        assert_equals(self.league._getGlickoResultsFromPlayers(sides, players),
                {1: '3/4', 2: '3/4', 3: '3/4', 4: '3/4', 5: '3/4', 6: '3/4'})

    @patch('resources.league.League._getGlickoResultsFromPlayers')
    @patch('resources.league.League._updateGlickoMatchups')
    @patch('resources.league.League._makeGlickoPlayersFromSides')
    def test_getNewGlickoRatings(self, make, update, getFrom):
        assert_equals(self.league._getNewGlickoRatings('sides', 'winningSide'),
                      getFrom.return_value)

    @patch('resources.league.League.trueSkillEnv')
    @patch('resources.league.League.getTeamRating')
    def test_getTrueSkillRating(self, getRtg, env):
        getRtg.return_value = "20/4"
        assert_equals(self.league._getTrueSkillRating(12),
                      env.create_rating.return_value)
        env.create_rating.assert_called_once_with(20, 4)

    @patch('resources.league.League._getTrueSkillRating')
    @patch('resources.league.League.trueSkillEnv')
    def test_getNewTrueSkillRatings(self, env, getRtg):
        rating = MagicMock(mu=3,sigma=5)
        env.rate.return_value = [{1: rating, 2: rating}, {3: rating}]
        assert_equals(self.league._getNewTrueSkillRatings([{1,2}, {3}], 1),
            {1: '3/5', 2: '3/5', 3: '3/5'})

    @patch('resources.league.League.getTeamRating')
    def test_getNewWinCounts(self, getRtg):
        getRtg.return_value = 3
        assert_equals(self.league._getNewWinCounts([{1, 2, 3}, {4, 5, 6}], 1),
                      {4: '4', 5: '4', 6: '4'})

    @patch('resources.league.League.getTeamRating')
    def test_getWinRate(self, getRtg):
        getRtg.return_value = "400/30"
        assert_equals(self.league._getWinRate(43), (400, 30))

    @patch('resources.league.League.getTeamRating')
    def test_getNewWinRates(self, getRtg):
        getRtg.return_value = "500/2"
        sides = [{1, 2, 3}, {4, 5}, {6, 7, 8, 9}]
        assert_equals(self.league._getNewWinRates(sides, 2),
            {1: '333/3', 2: '333/3', 3: '333/3', 4: '333/3',
             5: '333/3', 6: '667/3', 7: '667/3', 8: '667/3', 9: '667/3'})

    def test_getNewRatings(self):
        self.league.sysDict = {self.league.ratingSystem:
                               {'update': lambda x, y: 4}}
        assert_equals(self.league._getNewRatings([{1,2}, {3,4}], 0), 4)

    def test_updateEntityValue(self):
        table = MagicMock()
        self.league._updateEntityValue(table, 'Harambe', 'Name', Blue='yellow')
        table.updateMatchingEntities.assert_called_once_with({'Name':
            {'value': 'Harambe', 'type': 'positive'}}, {'Blue': 'yellow'})
        self.league._updateTeamRating(4, '4390')
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 4, 'type': 'positive'}}, {'Rating': '4390'})
        oldCount = self.teams.updateMatchingEntities.call_count
        self.league._updateRatings({4: '4390', 3: '2301', 1: '3909'})
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 4, 'type': 'positive'}}, {'Rating': '4390'})
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+3)

    @patch('resources.league.League._adjustTeamGameCount')
    def test_finishGameForTeams(self, adj):
        self.league._finishGameForTeams(({1, 2}, {3, 4, 5}, {6}))
        assert_equals(adj.call_count, 6)

    @patch('resources.league.League._finishGameForTeams')
    @patch('resources.league.League._updateRatings')
    @patch('resources.league.League._getNewRatings')
    @patch('resources.league.League._setWinners')
    def test_updateResults(self, setWin, getNew, update, finish):
        self.league._updateResults(3, [{1, 2}, {3, 4}], 0)
        setWin.assert_called_once_with(3, {1, 2}, False)
        update.assert_called_once_with(getNew.return_value)
        finish.assert_called_once_with([{1, 2}, {3, 4}])
        self.league._updateResults(12, [{1,}, {3,}], 1, False)
        setWin.assert_called_with(12, {3,}, False)
        assert_equals(update.call_count, 1)
        finish.assert_called_with([{1,}, {3,}])

    @patch('resources.league.League._updateResults')
    @patch('resources.league.League._findTeamsFromData')
    @patch('resources.league.League._getGameSidesFromData')
    @patch('resources.league.League._fetchGameData')
    def test_updateWinners(self, fetch, get, find, update):
        self._setProp(self.league.SET_REMOVE_BOOTS, False)
        get.return_value = [{1, 2, 3}, {4, 5, 6}, {7, 8}]
        find.return_value = {4, 5}
        self.league._updateWinners(1, ([43, 44], [12, 13]))
        update.assert_called_once_with(1, get.return_value, 1)
        find.return_value = {4, 5, 7}
        self._setProp(self.league.SET_REMOVE_BOOTS, True)
        self.league._updateWinners(1, ([43, 44], [12, 13]))
        update.assert_called_with(1, get.return_value, 1)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 7, 'type': 'positive'}}, {'Limit': 0})
        get.return_value = list()
        assert_raises(NameError, self.league._updateWinners, 1, ([43,44], []))

    @patch('resources.league.League.changeLimit')
    @patch('resources.league.League.updateGameVetos')
    def test_handleSpecialDeclines(self, update, change):
        self._setProp(self.league.SET_VETO_DECLINES, "FALSE")
        self._setProp(self.league.SET_REMOVE_DECLINES, "FALSE")
        self.league._handleSpecialDeclines({5, 10, 15}, 43)
        update.assert_not_called()
        change.assert_not_called()
        self._setProp(self.league.SET_VETO_DECLINES, "TRUE")
        self._setProp(self.league.SET_REMOVE_DECLINES, "TRUE")
        self.league._handleSpecialDeclines({5, 10, 15}, 20)
        update.assert_called_once_with({5, 10, 15}, 20)
        assert_equals(change.call_count, 3)
        change.assert_called_with(15, 0)

    def test_makeFakeSides(self):
        sides = [{1, 2, 3}, {4, 5}, {6, 7, 8}]
        losingTeams = {4, 6, 7}
        assert_equals(self.league.makeFakeSides(sides, losingTeams),
                      ([{4, 6, 7}, {1, 2, 3, 5, 8}], 1))
        assert_equals(self.league.makeFakeSides(sides, set(xrange(1, 9))),
                      ([set(xrange(1, 9)),], None))

    @patch('resources.league.League._getGameSidesFromData')
    @patch('resources.league.League._findTeamsFromData')
    @patch('resources.league.League._fetchGameData')
    @patch('resources.league.League._handleSpecialDeclines')
    @patch('resources.league.League.makeFakeSides')
    @patch('resources.league.League.updateVeto')
    @patch('resources.league.League._updateResults')
    def test_updateDecline(self, updateRes, veto, make, handle,
                           fetch, find, get):
        make.return_value = set(), 0
        self.league.updateDecline('ID', 'decliners')
        veto.assert_not_called()
        updateRes.assert_called_once_with('ID', set(), 0,
            adj=self.league.penalizeDeclines, declined=True)
        make.return_value = set(), None
        self.league.updateDecline('ID', 'decliners')
        veto.assert_called_once_with('ID')

    @patch('resources.league.League._finishGameForTeams')
    @patch('resources.league.League._getGameSidesFromData')
    def test_deleteGame(self, get, finish):
        self._setProp(self.league.SET_PRESERVE_RECORDS, "FALSE")
        self.league.deleteGame({'ID': 'ID'})
        self.games.removeMatchingEntities.assert_called_with({'ID':
                                                    {'value': 'ID',
                                                     'type': 'positive'}})
        get.assert_called_once_with({'ID': 'ID'})
        finish.assert_called_once_with(get.return_value)
        self._setProp(self.league.SET_PRESERVE_RECORDS, "TRUE")
        old = self.games.updateMatchingEntities.call_count
        self.league.deleteGame({'ID': 'NewID'})
        self.games.removeMatchingEntities.assert_called_with({'ID':
                                                    {'value': 'ID',
                                                     'type': 'positive'}})
        assert_equals(self.games.updateMatchingEntities.call_count, old+1)

    @patch('resources.league.League._fetchGameData')
    def test_getGameSidesFromData(self, fetch):
        gameData = {'Sides': '1,5,9/4,38,238/30,23/2,3,12,4/8'}
        expRes = [{'1', '5', '9'}, {'4', '38', '238'},
                  {'30', '23'}, {'2', '3', '12', '4'}, {'8',}]
        assert_equals(self.league._getGameSidesFromData(gameData), expRes)
        fetch.return_value = gameData
        assert_equals(self.league.getGameSides('ID'), expRes)

    def test_getTeamRating(self):
        self.teams.findEntities.return_value = [{'Rating': '43'},]
        assert_equals(self.league.getTeamRating(44), '43')
        self.league.tempTeams = {'12': '4903/4'}
        assert_equals(self.league.getTeamRating('12'), '4903/4')
        assert_equals(self.league.getTeamRating(12), '4903/4')
        assert_equals(self.league.getTeamRating(44), '43')

    def test_adjustRating(self):
        self.league.tempTeams = None
        self.teams.findEntities.return_value = [{'Rating': '33/43/490'},]
        self.league.adjustRating(43, 4)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 43, 'type': 'positive'}}, {'Rating': '37/43/490'})
        self.games.findEntities.return_value = [{'Sides': '1,2,3/4,5/6,7,8'},]
        oldCount = self.teams.updateMatchingEntities.call_count
        self._setProp(self.league.SET_VETO_PENALTY, -9)
        self.league.penalizeVeto(self.games.findEntities.return_value[0])
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount+8)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': '8', 'type': 'positive'}}, {'Rating': '42/43/490'})
        self.league.tempTeams = {'3': '43/4/3/2/1'}
        self.league.adjustRating('3', -12)
        assert_equals(self.league.tempTeams, {'3': '31/4/3/2/1'})

    def test_vetoCurrentTemplate(self):
        gameData = {'ID': '8', 'Vetoed': '12/38/349', 'Vetos': '3',
                    'Template': '420'}
        self.templates.findEntities.return_value = [{'Usage': '10'},]
        self.league.vetoCurrentTemplate(gameData)
        self.games.updateMatchingEntities.assert_called_with({'ID':
            {'value': '8', 'type': 'positive'}}, {'Vetos': 4,
            'Vetoed': '12/38/349/420', 'Template': ''})
        self.templates.updateMatchingEntities.assert_called_with({'ID':
            {'value': '420', 'type': 'positive'}}, {'Usage': '9'})

    def test_setGameTemplate(self):
        self.templates.findEntities.return_value = [{'Usage': '43'},]
        gameData = {'ID': 'gameID'}
        self.league.setGameTemplate(gameData, 'tempID')
        self.games.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'gameID', 'type': 'positive'}}, {'Template': 'tempID'})
        self.templates.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'tempID', 'type': 'positive'}}, {'Usage': '44'})
        assert_equals(gameData['Template'], 'tempID')

    def test_getTeamPlayers(self):
        self.teams.findEntities.return_value = [{'Players': '30,221,240,41'},]
        assert_equals(self.league.getTeamPlayers(12), [30,221,240,41])
        assert_equals(self.league.getSidePlayers({1,2}), [30,221,240,41,30,221,
            240,41])
        gameData = {'Sides': '1,2,3/4,5,6/7'}
        assert_equals(self.league.assembleTeams(gameData),
                      [(30,221,240,41,30,221,240,41,30,221,240,41),] * 2
                      + [(30,221,240,41)])

    def test_getTeamName(self):
        self.teams.findEntities.return_value = [{'Name': 'Bob'},]
        assert_equals(self.league.getTeamName(4), 'Bob')
        assert_equals(self.league.getNameInfo('1,2,3'),
                      ['Bob','+','Bob','+','Bob'])
        assert_equals(self.league.getNameInfo('1,2,3', 2),
                      ['..', '+', '..', '+', '..'])
        self.teams.findEntities.return_value = [{'Name': 'longnamethisoneis'},]
        assert_equals(self.league.getNameInfo('1,2,3', 10),
                      ['longnam...', '+', 'longnam...', '+', 'longnam...'])
        self.teams.findEntities.return_value = [{'Name': 'longnam...lkj'},]
        assert_equals(self.league.getNameInfo('1,2,3', 10),
                      ['longnam...', '+', 'longnam...', '+', 'longnam...'])

    @patch('resources.league.League.getTeamName')
    def test_getGameName(self, getTeamName):
        self._setProp(self.league.SET_LEAGUE_ACRONYM, "MDL")
        gameData = {'Sides': '1,2/3,4'}
        getTeamName.return_value = "Name"
        assert_equals(self.league.getGameName(gameData),
                      'MDL | Name+Name vs Name+Name')
        getTeamName.return_value = "N..."
        assert_equals(self.league.getGameName(gameData, 28),
                      'MDL | N...+N... vs N...+N...')

    def test_getPrettyRating(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        assert_equals(self.league.prettifyRating("4904"), "4904")
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_GLICKO)
        assert_equals(self.league.prettifyRating("490/4309"), "490")
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_TRUESKILL)
        assert_equals(self.league.prettifyRating("49/3"), "40")
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_WINCOUNT)
        assert_equals(self.league.prettifyRating("23"), "23")
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_WINRATE)
        assert_equals(self.league.prettifyRating("493/94"), "493")
        self.teams.findEntities.return_value = [{'Rating': '48/44'},]
        assert_equals(self.league.getPrettyRating('team'), "48")
        assert_equals(self.league.getOfficialRating('team'), 48)

    def test_getTeamRank(self):
        self.teams.findEntities.return_value = [{'Rank': '12'},]
        assert_equals(self.league.getTeamRank('team'), 12)

    def test_sideInfo(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        gameData = {'Sides': '14,43/17,81'}
        self.teams.findEntities.return_value = [{'Rating': '1399', 'Rank': '9',
            'Name': 'Test Team'},]
        assert_equals(self.league.sideInfo(gameData),
                      ("Test Team, with rank 9 and rating 1399\n" * 4)[:-1])
        self.teams.findEntities.return_value = [{'Rating': '1400', 'Rank': '',
            'Name': 'Test Team'},]
        assert_equals(self.league.sideInfo(gameData),
                      ("Test Team, not ranked with rating 1400\n" * 4)[:-1])

    def test_makeInterface(self):
        assert_equals(self.league.makeInterface(
            'https://www.warlight.net/Forum/48'),
            'https://www.warlight.net/Forum/48')
        assert_equals(self.league.makeInterface('404309'),
            'https://www.warlight.net/Forum/404309')
        assert_equals(self.league.makeInterface('interface.com'),
            'interface.com')

    def test_getTemplateName(self):
        gameData = {'Template': '43'}
        self.templates.findEntities.return_value = [{'ID': '43', 'Name': 'A'},]
        assert_equals(self.league.getTemplateName(gameData), 'A')

    @patch('resources.league.PlayerParser')
    def test_adminName(self, parser):
        parser.return_value.name = "name"
        assert_equals(self.league.adminName, "name")

    @patch('resources.league.PlayerParser')
    @patch('resources.league.League.getTemplateName')
    @patch('resources.league.League.sideInfo')
    def test_processMessage(self, sideInfo, tempName, parser):
        assert_equals(self.league.adaptMessage("MESSAGE", dict()), "MESSAGE")
        parser.return_value.name = "name"
        self._setProp(self.league.SET_SUPER_NAME, 'Cluster Name')
        self._setProp(self.league.SET_VETO_LIMIT, '9')
        self._setProp(self.league.SET_URL, 'League URL')
        self.league.name, self.league.thread = "Name", "Thread"
        sideInfo.return_value = "SIDE INFO"
        tempName.return_value = 'TEMP NAME'
        gameData = {'Vetos': 9, 'Template': '49'}
        assert_not_equal(self.league.processMessage(self.league.DEFAULT_MSG,
            gameData), self.league.DEFAULT_MSG)
        assert_not_equal(self.league.getGameMessage(gameData),
            self.league.leagueMessage)
        assert_true(len(self.league.getGameMessage(gameData)) <= 2048)
        assert_equals(self.league.processMessage("{{_TEMPLATE_NAME}}",
            gameData), "TEMP NAME")
        self._setProp(self.league.SET_EXP_THRESH, 8)
        assert_equals(self.league.processMessage("{{_ABANDON_THRESHOLD}}",
            gameData), "8")

    def test_updateHistories(self):
        gameData = {'Sides': '12,33/2390,49,448'}
        assert_equals(self.league.getAllGameTeams(gameData), ['12','33','2390',
                      '49','448'])
        assert_equals(self.league.getOtherTeams([1, 2, 3], 3), [1, 2])
        self.teams.findEntities.return_value = [{'History': '1,2,3,4'},]
        self.league.updateTeamHistory(1, ['9','8'])
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 1, 'type': 'positive'}}, {'History': '1,2,3,4,9,8'})
        self.teams.findEntities.return_value = [{'History': ''},]
        self.league.updateHistories(gameData)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': '448', 'type': 'positive'}},
            {'History': '12,33,2390,49'})

    def test_strBeginsWith(self):
        assert_true(self.league.strBeginsWith("lasdkjfvnalkjalk", "lasdkjfv"))
        assert_false(self.league.strBeginsWith("$9837vlkjas;dfkja", "$9837 "))

    def test_addTempSetting(self):
        settings = dict()
        self.league.addTempSetting(settings, "SET_A", "B")
        assert_equals(settings["A"], "B")
        self.league.addTempSetting(settings, "SET_C#D#E#F#G", "K")
        assert_equals(settings, {'A':'B','C':{'D':{'E':{'F':{'G':'K'}}}}})

    def test_addTempOverride(self):
        overrides = list()
        self.league.addTempOverride(overrides,
                                    'OVERRIDE_Random Bonus', '430904')
        assert_equals(overrides, [('Random Bonus', 430904),])

    def test_getTempSettings(self):
        self.templates.findEntities.return_value = [{'ID': 'tempID',
            'WarlightID': 4904, 'SET_A#B': '490', 'SET_SETTING': 314,
            'OVERRIDE_Bonus': 12, 'SET_DEF#GH#I': '', 'OVERRIDE_2': ''},]
        assert_equals(self.league.getTempSettings('tempID'), (4904,
            {'A': {'B': '490'}, 'SETTING': 314}, [('Bonus', 12),]))

    @patch('resources.league.datetime')
    @patch('resources.league.PlayerParser')
    def test_createGame(self, parser, datetime):
        self.games.findEntities.return_value = [{'Template': '43',
            'Sides': '1/2', 'Vetos': '8', 'ID': 'gameID'},]
        self.templates.findEntities.return_value = [{'ID': 'tempID',
            'WarlightID': 4904, 'SET_A#B': '490', 'SET_SETTING': 314,
            'OVERRIDE_Bonus': 12, 'Usage': '8', 'Name': 'TempName'},]
        self.teams.findEntities.return_value = [{'ID': '1', 'Players':
            '3022124041', 'Name': 'Team Name', 'Rating': '4034', 'Rank': '1'},]
        self.handler.createGame.return_value = "WLID"
        datetime.strftime.return_value = "strftime"
        self.league.createGame('gameID')
        self.games.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'gameID', 'type': 'positive'}}, {'WarlightID': 'WLID',
            'Created': 'strftime'})
        self.handler.createGame.side_effect = IOError
        self.league.createGame('gameID')
        failStr = "Failed to make game with 1/2 on 43 because of IOError()"
        self.parent.log.assert_called_with(failStr, self.league.name,
                                           error=True)
        self.games.removeMatchingEntities.assert_called_with({'ID':
            {'value': 'gameID', 'type': 'positive'}})

    @patch('resources.league.League.createGame')
    @patch('resources.league.League.updateHistories')
    def test_makeGame(self, update, create):
        oldCount = self.teams.updateMatchingEntities.call_count
        create.return_value = None
        self.league.makeGame('gameID')
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount)
        update.assert_not_called()
        create.return_value = {'Sides': '1,4/8,49/3/6,9'}
        self.teams.findEntities.return_value = [{'History': '',
            'Ongoing': '4', 'Finished': '400'},]
        self.league.makeGame('gameID')
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+7)
        update.assert_called_once_with(create.return_value)

    @patch('resources.league.League.updateConflicts')
    def test_getGameVetos(self, update):
        gameData = {'Vetoed': '1/5/9/390', 'Sides': '1,4,9/12,16'}
        self.teams.findEntities.return_value = [{},]
        assert_equals(self.league.getGameVetos(gameData), {1,5,9,390})
        assert_equals(update.call_count, 5)

    @patch('resources.league.League.deleteGame')
    @patch('resources.league.League.createGameFromData')
    @patch('resources.league.League.getGameVetos')
    def test_updateTemplate(self, vetos, create, delete):
        vetos.return_value = {1, 33, 2, 48}
        self.templates.findEntities.return_value = [{'ID': 1, 'Usage': 12},
            {'ID': 2, 'Usage': 23}, {'ID': 3, 'Usage': 2}, {'ID': 33,
             'Usage': 4}]
        self.league.updateTemplate({'ID': 43})
        create.assert_called_once_with({'ID': 43, 'Template': 3})
        vetos.return_value = {1, 2, 3, 33}
        self.league.updateTemplate({'ID': 43})
        delete.assert_called_once_with({'ID': 43})
        self.templates.findEntities.return_value = list()
        self.league.updateTemplate({'ID': 44})
        delete.assert_called_with({'ID': 44})

    def test_vetoDict(self):
        assert_equals(self.league.getVetoDict('4.3/389.1/39.4/8.1/9.33'),
                      {4: 3, 389: 1, 39: 4, 8: 1, 9: 33})
        self.teams.findEntities.return_value = [{'Vetos': ''},]
        assert_equals(self.league.getTeamVetoDict('teamID'), dict())
        assert_equals(self.league.packageVetoDict({5: 4, 3: 2, 1: 1}),
                      '1.1/3.2/5.4')
        assert_equals(self.league.updateVetoCt('3.2/5.4', '1', 3),
                      '1.3/3.2/5.4')
        assert_equals(self.league.updateVetoCt('1.3/3.2/5.4', '5', 5),
                      '1.3/3.2/5.9')
        self.league.updateTeamVetos('teamID', '4', 1)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Vetos': '4.1'})
        self.teams.findEntities.return_value = [{'Vetos': '1.2/3.4/4.1'},]
        self.league.updateTeamVetos('teamID', '3', 3)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Vetos': '1.2/3.7/4.1'})
        self.league.updateTeamVetos('teamID', '490', 1)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}},
            {'Vetos': '1.2/3.4/4.1/490.1'})
        self.league.updateGameVetos({1, 2, 3}, '317')
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 3, 'type': 'positive'}},
            {'Vetos': '1.2/3.4/4.1/317.1'})

    def test_getTeams(self):
        gameData = {'Sides': '67,30/105,495,384/2,5,81'}
        assert_equals(self.league.getTeams(gameData),
            {67, 30, 105, 495, 384, 2, 5, 81})

    @patch('resources.league.League.updateTemplate')
    @patch('resources.league.League.updateGameVetos')
    @patch('resources.league.League.vetoCurrentTemplate')
    @patch('resources.league.League.deleteGame')
    @patch('resources.league.League.penalizeVeto')
    def test_updateVeto(self, penalize, delete, veto, gameVetos, temp):
        gameData = {'Vetos': '9', 'Template': 3, 'Sides': '1/2'}
        self.games.findEntities.return_value = [gameData,]
        self._setProp(self.league.SET_VETO_LIMIT, 10)
        self.league.updateVeto('gameID')
        veto.assert_called_once_with(gameData)
        gameVetos.assert_called_once_with({1, 2}, 3)
        temp.assert_called_once_with(gameData)
        self._setProp(self.league.SET_VETO_LIMIT, 4)
        self.league.updateVeto('gameID')
        penalize.assert_called_once_with(gameData)
        delete.assert_called_once_with(gameData)

    def test_getOneArgFunc(self):
        func = lambda x, y, z, k: x * y * z / k
        oneArg = self.league.getOneArgFunc(func, 4, 48, 3)
        assert_equals(oneArg(3), (3 * 4 * 48 / 3))
        assert_equals(oneArg(2309505095), (2309505095 * 4 * 48 / 3))

    @patch('resources.league.League.updateVeto')
    @patch('resources.league.League.updateDecline')
    @patch('resources.league.League._updateWinners')
    @patch('resources.league.League._fetchGameStatus')
    def test_updateGame(self, fetch, win, decline, veto):
        createdTime = '2491-04-20 19:39:39'
        fetch.return_value = None
        self.league.updateGame("wlID", "gameID", createdTime)
        win.assert_not_called()
        decline.assert_not_called()
        veto.assert_not_called()
        fetch.return_value = ('FINISHED', set(), set())
        self.league.updateGame("wlID", "gameID", createdTime)
        fetch.return_value = ('DECLINED', set())
        self.league.updateGame("wlID", "gameID", createdTime)
        fetch.return_value = ('ABANDONED', None)
        self.league.updateGame("wlID", "gameID", createdTime)
        win.assert_called_once_with("gameID", (set(), set()))
        decline.assert_called_once_with("gameID", set())
        veto.assert_called_once_with("gameID")

    def test_wipeRank(self):
        self.league.wipeRank('teamID')
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Rank': ''})

    def test_rankTests(self):
        teamData = {'Finished': 43, 'Limit': 4}
        self._setProp(self.league.SET_MIN_TO_RANK, 40)
        self._setProp(self.league.SET_MIN_LIMIT_TO_RANK, 5)
        assert_false(self.league.eligibleForRank(teamData))
        self._setProp(self.league.SET_MIN_LIMIT_TO_RANK, 4)
        assert_true(self.league.eligibleForRank(teamData))
        teamData['Rank'] = ''
        assert_false(self.league.hasRank(teamData))
        teamData['Rank'] = '8'
        assert_true(self.league.hasRank(teamData))

    def test_rankUsingRatings(self):
        teamRatings = [(1, 390), (2, 904), (3, 104), (4, 569), (5, 392),
                       (6, 104)]
        oldCount = self.teams.updateMatchingEntities.call_count
        self.league.rankUsingRatings(teamRatings)
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+6)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 3, 'type': 'positive'}}, {'Rank': 5})

    def test_updateRanks(self):
        oldOfficial = self.league.getOfficialRating
        self.league.getOfficialRating = lambda ID: {'3':48,'4':55,'5':48}[ID]
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        self._setProp(self.league.SET_MIN_TO_RANK, 20)
        self._setProp(self.league.SET_MIN_LIMIT_TO_RANK, 2)
        self.teams.findEntities.return_value = [{'ID': '1', 'Rank': '',
            'Rating': '43', 'Limit': '1', 'Finished': '32'}, {'ID': '2',
            'Rank': '3', 'Rating': '49', 'Limit': '4', 'Finished': '18'},
            {'ID': '3', 'Rank': '1', 'Rating': '48', 'Limit': '2',
             'Finished': '22'}, {'ID': '4', 'Rank': '2', 'Rating': '55',
             'Limit': '3', 'Finished': '40'}, {'ID': '5', 'Rank': '3',
             'Rating': '48', 'Limit': '12', 'Finished': '35'}]
        oldCount = self.teams.updateMatchingEntities.call_count
        self.league.updateRanks()
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': '3', 'type': 'positive'}}, {'Rank': 2})
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+4) # not called for team 1
        self.league.getOfficialRating = oldOfficial

    @patch('resources.league.League.updateGame')
    def test_updateGames(self, update):
        self.games.findEntities.return_value = {1: {'ID': '1', 'Created': 'c'},
            2: {'ID': '2', 'Created': 'r'}, 4: {'ID': '3', 'Created': 'e'},
            56: {'ID': '9', 'Created': 'a'}}
        self.league.updateGames()
        assert_equals(update.call_count, 4)
        update.assert_called_with(4, '3', 'e')
        update.side_effect = sheetDB.errors.SheetError
        self.league.updateGames()
        self.parent.log.assert_called_with("Failed to update game: 4",
            league=self.league.name, error=True)

    def test_checkExcess(self):
        self._setProp(self.league.SET_MAX_TEAMS, "")
        assert_false(self.league.checkExcess(40000))
        self._setProp(self.league.SET_MAX_TEAMS, "4")
        assert_true(self.league.checkExcess(5))
        assert_false(self.league.checkExcess(4))

    @patch('resources.league.League.checkLimit')
    def test_changeLimit(self, check):
        check.return_value = 5
        self.league.changeLimit('teamID', 0)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Limit': 0})
        self.league.changeLimit('teamID', 400)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Limit': 5})

    def test_updatePlayerCounts(self):
        pc = {4: 3}
        self.league.updatePlayerCounts(pc, {1, 3, 4})
        assert_equals(pc, {1: 1, 3: 1, 4: 4})

    @patch('resources.league.datetime')
    def test_setProbation(self, dt):
        dt.strftime.return_value = 'now'
        self.league.wipeProbation('teamID')
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Probation Start': ''})
        self.league.startProbation('teamID')
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}},
            {'Probation Start': 'now'})

    def test_meetsRetention(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        self._setProp(self.league.SET_MIN_TO_CULL, 8)
        self._setProp(self.league.SET_MIN_RATING, 1500)
        self._setProp(self.league.SET_MIN_PERCENTILE, 0)
        self._setProp(self.league.SET_MAX_RANK, 25)
        teamData = {'Finished': '3', 'Rating': '1560', 'Rank': '20'}
        assert_true(self.league.meetsRetention(teamData))
        teamData['Finished'] = '12'
        assert_true(self.league.meetsRetention(teamData))
        teamData['Rating'] = '1300'
        assert_false(self.league.meetsRetention(teamData))
        teamData['Rating'], teamData['Rank'] = '1800', '28'
        assert_false(self.league.meetsRetention(teamData))
        teamData['Rank'] = '1'
        assert_true(self.league.meetsRetention(teamData))

    @patch('resources.league.League.meetsRetention')
    def test_checkTeamRating(self, meets):
        self._setProp(self.league.SET_GRACE_PERIOD, 5)
        start = datetime.strftime(datetime.now() - timedelta(3),
                                  self.league.TIMEFORMAT)
        self.teams.findEntities.return_value = [{'Probation Start':
            start},]
        meets.return_value = True
        self.league.checkTeamRating('teamID')
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 'teamID', 'type': 'positive'}}, {'Probation Start': ''})
        self.teams.findEntities.return_value[0]['Probation Start'] = ''
        oldCount = self.teams.updateMatchingEntities.call_count
        self.league.checkTeamRating('teamID')
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount)
        meets.return_value = False
        self.league.checkTeamRating('teamID')
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount+1)
        self.teams.findEntities.return_value[0]['Probation Start'] = start
        self.league.checkTeamRating('teamID')
        self._setProp(self.league.SET_GRACE_PERIOD, 2)
        assert_raises(ImproperInput, self.league.checkTeamRating, 'teamID')

    @patch('resources.league.League.changeLimit')
    @patch('resources.league.League.checkConsistentClan')
    @patch('resources.league.League.checkTeam')
    @patch('resources.league.League.checkTeamRatingUsingData')
    @patch('resources.league.League._fetchTeamData')
    def test_validateTeam(self, fetch, checkRtg, check, checkClan, change):
        assert_false(self.league.validateTeam('teamID', 'players'))
        checkRtg.assert_called_once_with('teamID', fetch.return_value)
        check.assert_called_once_with('players', 'teamID')
        checkClan.assert_called_once_with('players',
                                          self.league.maintainSameClan)
        check.side_effect = ImproperInput()
        assert_true(self.league.validateTeam('teamID', 'players'))
        self.parent.log.assert_called_with("Removing teamID because: ", 'NAME')
        change.assert_called_once_with('teamID', 0)
        fetch.return_value = {'Limit': 0}
        assert_false(self.league.validateTeam('teamID', 'players'))

    @patch('resources.league.League.changeLimit')
    @patch('resources.league.League.checkExcess')
    def test_validatePlayerGroup(self, check, change):
        check.return_value = False
        self.league.validatePlayer = self.league.validatePlayerGroup
        assert_equals(self.league.validatePlayer(dict(), set(), 'team'), False)
        assert_equals(self.league.validatePlayer({1: 3}, {3, 4, 5}, 'team'),
                      False)
        change.assert_not_called()
        assert_equals(self.league.validatePlayer({4: 3}, {3, 4, 5}, 'team'),
                      False)
        change.assert_not_called()
        check.return_value = True
        assert_equals(self.league.validatePlayer({4: 3}, {3, 4, 5}, 'team'),
                      True)
        change.assert_called_once_with('team', 0)

    def test_wasActive(self):
        assert_true(self.league.wasActive({'Ongoing': 1, 'Finished': '0'}))
        assert_true(self.league.wasActive({'Ongoing': '0', 'Finished': '8'}))
        assert_true(self.league.wasActive({'Ongoing': '4', 'Finished': 93}))
        assert_false(self.league.wasActive({'Ongoing': 0, 'Finished': 0}))

    @patch('resources.league.League.updatePlayerCounts')
    @patch('resources.league.League.validatePlayerGroup')
    @patch('resources.league.League.validateTeam')
    def test_validatePlayers(self, team, player, update):
        self.teams.findEntities.return_value = [{'Limit': '0', 'ID': '4',
            'Players': '1,2,3,4', 'Confirmations': 'TRUE,TRUE,TRUE,FALSE'},
            {'Limit': '2', 'Confirmations': 'FALSE,TRUE,TRUE,FALSE',
             'ID': '2', 'Players': '5,6,7,8'}, {'Limit': '3', 'ID': '3',
             'Players': '0,9,8,7', 'Confirmations': 'TRUE,TRUE,TRUE'}]
        team.return_value, player.return_value = False, True
        self.league.validatePlayers()
        update.assert_not_called()
        team.return_value = True
        self.league.validatePlayers()
        update.assert_not_called()
        player.return_value = False
        self.league.validatePlayers()
        update.assert_not_called()
        team.return_value = False
        self.league.validatePlayers()
        update.assert_called_once_with(dict(), ['0', '9', '8', '7'])

    def test_ratingOps(self):
        assert_equals(self.league.splitRating('1/2/3/4/5'), tuple(range(1, 6)))
        assert_equals(self.league.splitRating('128/4903409/43902/3290'),
            (128, 4903409, 43902, 3290))
        assert_equals(self.league.addRatings(['1/2/3', '2/3/5/7', '9', '43/4',
            '10/9/8/7/6/5/4/3/2/1/0/0/0']), "65/18/16/14/6/5/4/3/2/1/0/0/0")

    @patch('resources.league.League.eloEnv')
    def test_getEloPairingParity(self, eloEnv):
        self.league.getEloPairingParity('3', '8')
        eloEnv.quality_1vs1.assert_called_once_with(3, 8)

    @patch('resources.league.League.getAverageParity')
    def test_getEloParity(self, average):
        assert_equals(self.league.getEloParity(["1", "249", "4940"]),
                      average.return_value)

    def test_getAverageParity(self):
        parityFn = lambda *args: sum(args) / 1000.0
        assert_equals(self.league.getAverageParity([12, 49, 4, 40, 20, 56],
                      parityFn), 0.06)
        parityFn = lambda *args: sum(args)
        assert_equals(self.league.getAverageParity(range(100), parityFn), 1)

    def test_getGlickoParity(self):
        assert_equals(self.league.getGlickoPairingParity((49, 3), (49, 3)),
                      1.00)
        assert_almost_equal(self.league.getGlickoPairingParity((1000, 1),
                            (2000, 200)), 0.015, 3)
        assert_equals(self.league.getGlickoParity(["39/4", "49/3",
            "12/1", "49/1", "20/8", "93/4", "4/3", "-9/120"]), 0.89)
        self._setProp(self.league.SET_GLICKO_DEFAULT, 15)
        assert_almost_equal(self.league.getGlickoPairingParity((10, 0.01),
                            (20, 2)), 0.015, 3)

    @patch('resources.league.League.trueSkillEnv')
    def test_getTrueSkillParity(self, env):
        assert_equals(self.league.getTrueSkillParity(["12/3", "45/6",
                      "78/9"]), env.quality.return_value)
        assert_equals(env.create_rating.call_count, 3)
        env.quality.assert_called_once_with([(),] * 3)

    def test_getVarianceScore(self):
        assert_equals(self.league.getVarianceScore([50, 50, 50]), 1.0)
        assert_equals(self.league.getVarianceScore([94, 103930390]), 0.0)
        assert_equals(self.league.getWinCountParity(["10", "10", "50"]), 0.0)
        assert_almost_equal(self.league.getWinCountParity(["5", "6", "7",
                            "8"]), 0.656, 3)
        assert_equals(self.league._getWinRateParity(["10/9", "10/49", "50/4"]),
                      0.0)
        assert_almost_equal(self.league._getWinRateParity(["5/49", "6/32904",
                            "7/12057", "8/8"]), 0.656, 3)
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        assert_equals(self.league.getParityScore([10, 10, 10]), 1.0)
        assert_almost_equal(self.league.getParityScore([1309, 1504]), 0.49, 2)

    def test_getPlayers(self):
        assert_equals(self.league.getPlayers({'Players': '1309,320,39003'}),
                      [1309, 320, 39003])

    def test_getHistory(self):
        assert_equals(self.league.getHistory({'History': '1,2,3,4,5'}),
                      range(1, 6))

    def test_addToSetWithinDict(self):
        data = {4: {3, 2}, 5: set()}
        self.league.addToSetWithinDict(data, 4, 1)
        self.league.addToSetWithinDict(data, 5, 3)
        self.league.addToSetWithinDict(data, 6, 4)
        assert_equals(data, {4: {3, 2, 1}, 5: {3,}, 6: {4,}})

    @patch('resources.league.PlayerParser')
    def test_makePlayersDict(self, parser):
        parser.return_value.clanID = 8
        self._setProp(self.league.SET_FORBID_CLAN_MATCHUPS, "FALSE")
        teams = [{'ID': 3, 'Players': '3,6,9'}, {'ID': 2, 'Players': '2,4,6'},
                 {'ID': 6, 'Players': '6,12,18'}]
        assert_equals(self.league.makePlayersDict(teams), ({2: {2,}, 3: {3,},
                      4: {2,}, 6: {2, 3, 6}, 9: {3,}, 12: {6,}, 18: {6,}},
                      {}))
        self._setProp(self.league.SET_FORBID_CLAN_MATCHUPS, "TRUE")
        assert_equals(self.league.makePlayersDict(teams), ({2: {2,}, 3: {3,},
                      4: {2,}, 6: {2, 3, 6}, 9: {3,}, 12: {6,}, 18: {6,}},
                      {8: {2, 3, 6}}))

    def test_narrowHistory(self):
        self._setProp(self.league.SET_REMATCH_CAP, 3)
        assert_equals(self.league.narrowHistory([1,1,2,3,4,3,3,2,1,2,4,9,49]),
                      {1, 2, 3})

    @patch('resources.league.PlayerParser')
    def test_updateClanConflicts(self, parser):
        conflicts = set()
        parser.return_value.clanID = 1
        clansDict = {1: {2, 3, 4}, 2: {12, 21, 33}, None: {4, 12}}
        self._setProp(self.league.SET_FORBID_CLAN_MATCHUPS, "FALSE")
        self.league.updateClanConflicts(conflicts, 40, clansDict)
        parser.return_value.clanID = 2
        self._setProp(self.league.SET_FORBID_CLAN_MATCHUPS, "TRUE")
        self.league.updateClanConflicts(conflicts, 121, clansDict)
        assert_equals(conflicts, {12, 21, 33})
        parser.return_value.clanID = None
        self.league.updateClanConflicts(conflicts, 120, clansDict)
        parser.return_value.clanID = 8
        self.league.updateClanConflicts(conflicts, 409, clansDict)
        assert_equals(conflicts, {12, 21, 33, 4, 12})

    def test_teamsDict(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        self._setProp(self.league.SET_REMATCH_LIMIT, "ALL")
        self._setProp(self.league.SET_REMATCH_CAP, "1")
        self._setProp(self.league.SET_FORBID_CLAN_MATCHUPS, "FALSE")
        self.teams.findEntities.return_value = [{'ID': 3, 'Limit': '-3',
            'Rating': '1500', 'Confirmations': 'TRUE,TRUE,TRUE',
            'Ongoing': '1',
            'Players': '12,13,14'}, {'ID': 4, 'Limit': '2', 'Ongoing': '2',
            'Rating': '1600', 'Players': '1,23,7', 'History': '4,5,6',
            'Confirmations': 'TRUE,TRUE,FALSE'}, {'ID': 5, 'Limit': '3',
            'Ongoing': 2, 'Rating': '1950', 'Confirmations': 'TRUE,TRUE',
            'Players': '12,23,91', 'History': '12,13,9'}]
        assert_equals(self.league.teamsDict, {'5': {'rating': '1950',
            'count': 1, 'conflicts': {12, 13, 9, 4, 5}}})
        self._setProp(self.league.SET_REMATCH_LIMIT, "1")
        self._setProp(self.league.SET_GAME_SIZE, "1")
        self._setProp(self.league.SET_TEAMS_PER_SIDE, "1")
        assert_equals(self.league.teamsDict, {'5': {'rating': '1950',
            'count': 1, 'conflicts': {9, 4, 5}}})

    @patch('resources.league.League.getParityScore')
    def test_makeGrouping(self, score):
        score.return_value = 0.8
        groupingDict = {1: {'rating': 1200, 'count': 0, 'conflicts': {2}},
                        2: {'rating': 1500, 'count': 4, 'conflicts': {1}},
                        3: {'rating': 1500, 'count': 9, 'conflicts': {1}}}
        assert_equals(self.league.makeGrouping(groupingDict, 2, "/", False),
                      {'2/3'})
        assert_equals(self.league.makeGrouping(groupingDict, 3, ".", True),
                      set())
        self.league._sideSize = [2,]
        assert_equals(self.league.makeSides(groupingDict), {'2,3'})
        self.league._gameSize = [2,]
        assert_equals(self.league.makeMatchings(groupingDict), {'2/3'})

    def test_makeSidesDict(self):
        assert_equals(self.league.getSideRating('1,2,3,4,5',
                      {'1': {'rating': '43'}, '2': {'rating': '41'},
                       '3': {'rating': '18'}, '4': {'rating': '56'},
                       '5': {'rating': '12'}, '6': {'rating': '9'}}), '170')
        assert_equals(self.league.makeTeamsToSides({'1,2,3,4,5','6,7,8,9,5'}),
            {'1': {'1,2,3,4,5'}, '2': {'1,2,3,4,5'}, '3': {'1,2,3,4,5'},
             '4': {'1,2,3,4,5'}, '5': {'1,2,3,4,5', '6,7,8,9,5'},
             '6': {'6,7,8,9,5'}, '7': {'6,7,8,9,5'}, '8': {'6,7,8,9,5'},
             '9': {'6,7,8,9,5'}})
        assert_equals(self.league.getSideConflicts('1,2,3,4,5',
            {'3': {'conflicts': {'8'}}, '1': {'conflicts': set()},
             '2': {'conflicts': set()}, '4': {'conflicts': set()},
             '5': {'conflicts': set()}},
            self.league.makeTeamsToSides({'1,2,3,4,5', '5,6,7,8,9', '8,9',
                                          '55,66,77'})),
            {'1,2,3,4,5', '5,6,7,8,9', '8,9'})
        assert_equals(self.league.makeSidesDict({'1,2,3', '4,5,6'},
            {'1': {'rating': 102, 'count': 2, 'conflicts': set()},
             '2': {'rating': 490, 'count': 1, 'conflicts': {'3'}},
             '3': {'rating': 239, 'count': 8, 'conflicts': {'2'}},
             '4': {'rating': 356, 'count': 3, 'conflicts': {'1'}},
             '5': {'rating': 491, 'count': 4, 'conflicts': {'3','1','4'}},
             '6': {'rating': 236, 'count': 2, 'conflicts': {'1','5'}}}),
            {'1,2,3': {'rating': '831', 'count': 1, 'conflicts': {'1,2,3'}},
             '4,5,6': {'rating': '1083', 'count': 1, 'conflicts': {'1,2,3',
             '4,5,6'}}})

    def test_turnNoneIntoMutable(self):
        assert_equals(self.league.turnNoneIntoMutable(4, set), 4)
        assert_equals(self.league.turnNoneIntoMutable(None, set), set())

    def test_templatesDict(self):
        self.templates.findEntities.return_value = {12: {'Usage': 8},
            24: {'Usage': '9'}, 36: {'Usage': 12}, 48: {'Usage': 93}}
        assert_equals(self.league.templatesDict, {'12': {'usage': 8},
            '36': {'usage': 12}, '48': {'usage': 93}, '24': {'usage': 9}})

    def test_makeMatchingsDict(self):
        data = {1: -94, 3: 8}
        self.league.updateCountInDict(data, 1)
        self.league.updateCountInDict(data, 2)
        self.league.updateCountInDict(data, 3)
        assert_equals(data, {1: -93, 2: 1, 3: 9})
        scores = {'8': 4, '9': 1}
        self.league.updateScores({'Vetos': '49.3/3.2'}, scores)
        self.league.updateScores({'Vetos': '89.1/8.3'}, scores)
        self.league.updateScores({'Vetos': ''}, scores)
        assert_equals(scores, {'8': 7, '9': 1, '3': 2, '49': 3, '89': 1})
        conflicts = {'13', '49'}
        self.league.updateConflicts({'Drops': '13/39/239/4'}, conflicts)
        self.league.updateConflicts({'Drops': ''}, conflicts)
        assert_equals(conflicts, {'13', '49', '39', '239', '4'})
        self.templates.findEntities.return_value = {12: {'Usage': 8},
            24: {'Usage': '9'}, 36: {'Usage': 12}, 48: {'Usage': 93}}
        self.teams.findEntities.return_value = [{'Vetos': '23.1/32.1',
            'Drops': '25/65'},]
        assert_equals(self.league.makeMatchingsDict({'1,3,5/7,9,12',
            '12,24,36/48,3,1', '31,39,73/48,65,21'}),
            {'1,3,5/7,9,12': {'scores': {'23': 6, '32': 6},
             'conflicts': {'25', '65'}, 'count': 1},
             '12,24,36/48,3,1': {'scores': {'23': 6, '32': 6},
             'conflicts': {'25', '65'}, 'count': 1},
             '31,39,73/48,65,21': {'scores': {'23': 6, '32': 6},
             'conflicts': {'25', '65'}, 'count': 1}})
        self.templates.findEntities.return_value = {'25', '65'}
        assert_equals(self.league.makeMatchingsDict({'12/23', '11/47'}), {})

    @patch('resources.league.random.shuffle')
    @patch('resources.league.League.makeMatchingsDict')
    def test_makeBatch(self, matchings, shuffle):
        matchings.return_value = {'1/2': {'scores': dict(), 'conflicts': {'3'},
            'count': 1}, '3/4': {'scores': {'3': 2, '4': 1},
            'conflicts': set(), 'count': 1}}
        self.templates.findEntities.return_value = {'3': {'Usage': 1},
            '4': {'Usage': 8}, '5': {'Usage': 0}, '6': {'Usage': 2}}
        assert_equals(self.league.makeBatch({'1/2', '3/4'}),
                      [{'Sides': '1/2', 'Template': '5'},
                       {'Sides': '3/4', 'Template': '5'},])
        self.templates.findEntities.return_value = dict()
        matchings.return_value = {'1/2': {'scores': dict(),
            'conflicts': {'3', '4', '6'}, 'count': 1}, '3/4':
            {'scores': {'3': 2, '4': 1}, 'conflicts': {'3', '4', '6'},
             'count': 1}}
        assert_equals(self.league.makeBatch({'1/2', '3/4'}), list())

    @patch('resources.league.League.makeGame')
    def test_createBatch(self, make):
        batch = [{'Sides': '3/4', 'Template': '6'},
                 {'Sides': '1/2', 'Template': '4'},]
        self.games.findValue.return_value = range(33)
        self.league.createBatch(batch)
        self.games.addEntity.assert_called_with({'ID': 34, 'WarlightID': '',
            'Created': '', 'Winners': '', 'Sides': '1/2', 'Vetos': 0,
            'Vetoed': '', 'Finished': '', 'Template': '4'})
        make.assert_called_with(34)
        make.side_effect = wl_api.wl_api.APIError
        self.league.createBatch(batch)
        self.parent.log.assert_called_with("Failed to create game with ID 33",
            self.league.name, error=True)
        self.games.addEntity.side_effect = sheetDB.errors.DataError
        self.league.createBatch(batch)
        failStr = "Failed to add game to sheet due to "
        self.parent.log.assert_called_with(failStr, self.league.name,
                                           error=True)

    @patch('resources.league.League.createBatch')
    @patch('resources.league.League.makeBatch')
    @patch('resources.league.League.makeMatchings')
    @patch('resources.league.League.makeSidesDict')
    @patch('resources.league.League.makeSides')
    def test_createGames(self, make, makeDict, match, batch, create):
        self.league._sideSize = [1,]
        assert_equals(self.league.sideSize, 1)
        self.league.createGames()
        make.assert_not_called()
        makeDict.assert_called_once_with(self.league.teamsDict,
            self.league.teamsDict)
        match.assert_called_once_with(makeDict.return_value)
        batch.assert_called_once_with(match.return_value)
        create.assert_called_once_with(batch.return_value)
        self.league._sideSize = [3,]
        assert_equals(self.league.sideSize, 3)
        self.league.createGames()
        make.assert_called_once_with(self.league.teamsDict)

    def test_rescaleRatings(self):
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        self._setProp(self.league.SET_ELO_DEFAULT, "30")
        assert_equals(self.league.defaultRating, "30")
        self._setProp(self.league.SET_MAINTAIN_TOTAL, "FALSE")
        oldCount = self.teams.updateMatchingEntities.call_count
        self.teams.findEntities.return_value = [{'ID': 1, 'Limit': '-3',
            'Confirmations': 'TRUE,TRUE,TRUE', 'Ongoing': '3', 'Finished': '0',
            'Rating': '35/8'},
            {'ID': 2, 'Limit': '2', 'Confirmations': 'TRUE,TRUE,FALSE',
             'Ongoing': '0', 'Finished': '3', 'Rating': '31/5'}, {'ID': 3,
             'Limit': '3', 'Confirmations': 'TRUE,TRUE,TRUE', 'Ongoing': '1',
             'Finished': '8', 'Rating': '28/3'}, {'ID': 4, 'Limit': '3',
             'Confirmations': 'TRUE,TRUE,TRUE', 'Ongoing': '1',
             'Finished': '9', 'Rating': '28/3'}, {'ID': 5, 'Limit': '2',
             'Confirmations': 'TRUE,TRUE,FALSE', 'Ongoing': '0',
             'Finished': '0', 'Rating': '30/9'}]
        self.league.rescaleRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount)
        self._setProp(self.league.SET_MAINTAIN_TOTAL, "TRUE")
        assert_true(self.league.maintainTotal)
        self.league.rescaleRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount+4)
        self.teams.updateMatchingEntities.assert_called_with({'ID': {'type':
            'positive', 'value': 4}}, {'Rating': '30/3'})

    def test_decayTime(self):
        now = datetime.now()
        iterations = 24 / (now.hour + 1)
        assert_true(self.league.decayTime(iterations))
        assert_false(self.league.decayTime(2881))

    @patch('resources.league.League.decayTime')
    def test_decayRatings(self, decayTime):
        oldCount = self.teams.updateMatchingEntities.call_count
        self._setProp(self.league.SET_RATING_DECAY, "0")
        decayTime.return_value = False
        self.league.decayRatings()
        self._setProp(self.league.SET_RATING_DECAY, "10")
        self.league.decayRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount)
        decayTime.return_value = True
        self.teams.findEntities.return_value = [{'ID': 1, 'Rating': '33/5',
            'Ongoing': '0', 'Finished': '8', 'Limit': '0', 'Confirmations': ''},
            {'ID': 2, 'Rating': '34/8', 'Ongoing': '1', 'Finished': '0',
             'Limit': '3', 'Confirmations': 'TRUE,FALSE,FALSE'},
            {'ID': 3, 'Rating': '39/1', 'Ongoing': '2', 'Finished': '121',
             'Limit': '12', 'Confirmations': 'TRUE,TRUE,TRUE'},
            {'ID': 4, 'Rating': '12/0', 'Ongoing': '0', 'Finished': '0',
             'Limit': '0', 'Confirmations': 'FALSE,FALSE,FALSE'}]
        self.league.decayRatings()
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': 2, 'type': 'positive'}}, {'Rating': '24/8'})
        assert_equals(self.teams.updateMatchingEntities.call_count, 2)

    def test_dateUnexpired(self):
        self._setProp(self.league.SET_RETENTION_RANGE, 10)
        assert_true(self.league.dateUnexpired('2014-05-20 01:02:33',
                    datetime(year=2014, month=5, day=30)))
        assert_true(self.league.dateUnexpired('2014-05-20 01:00:00',
                    datetime(year=2014, month=5, day=20, hour=2)))
        assert_true(self.league.dateUnexpired('2014-05-20 01:00:00',
                    datetime(year=2014, month=5, day=28)))
        assert_false(self.league.dateUnexpired('2014-05-20 01:00:00',
                     datetime(year=2014, month=5, day=31)))
        assert_false(self.league.dateUnexpired('',
                     datetime(year=2016, month=1, day=1)))

    @patch('resources.league.League.dateUnexpired')
    def test_unexpiredGames(self, date):
        date.return_value = False
        self.games.findEntities.return_value = [{'ID': 0, 'Finished': '',
            'Winners': ''}, {'ID': 1, 'Finished': '', 'Winners': '1,2'},
            {'ID': 2, 'Finished': '', 'Winners': '3,4'}]
        assert_equals(self.league.unexpiredGames, list())
        date.return_value = True
        assert_equals(self.league.unexpiredGames,
            self.games.findEntities.return_value)

    @patch('resources.league.League.dateUnexpired')
    def test_calculateRatings(self, date):
        self._setProp(self.league.SET_ELO_DEFAULT, "1500")
        oldCount = self.teams.updateMatchingEntities.call_count
        date.return_value = True
        self._setProp(self.league.SET_RETENTION_RANGE, "")
        self.league.calculateRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count, oldCount)
        self._setProp(self.league.SET_RETENTION_RANGE, 3)
        self.games.findEntities.return_value = [{'ID': 0, 'Finished': '',
            'Winners': '1,2!', 'Sides': '1,2/3,4/5,6'}, {'ID': 1,
            'Finished': '', 'Winners': '2,4', 'Sides': '1,3/2,4/5,6'},
            {'ID': 2, 'Finished': '', 'Winners': '3,5,6,1!',
             'Sides': '1,2/3,4/5,6'}, {'ID': 3, 'Finished': '',
             'Winners': '', 'Sides': '3,5/1,2/4,6'}]
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_ELO)
        self.teams.findEntities.return_value = [{'ID': '1'}, {'ID': '2'},
            {'ID': '3'}, {'ID': '4'}, {'ID': '5'}, {'ID': '6'}]
        assert_equals(self.league.unexpiredGames,
                      self.games.findEntities.return_value)
        assert_equals(self.league.retentionRange, 3)
        self.league.calculateRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+6)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': '6', 'type': 'positive'}}, {'Rating': '1463'})
        self._setProp(self.league.SET_PENALIZE_DECLINES, "False")
        assert_false(self.league.penalizeDeclines)
        self.league.calculateRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+12)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': '6', 'type': 'positive'}}, {'Rating': '1471'})
        self._setProp(self.league.SET_VETO_PENALTY, "0")
        self.league.calculateRatings()
        assert_equals(self.teams.updateMatchingEntities.call_count,
                      oldCount+18)
        self.teams.updateMatchingEntities.assert_called_with({'ID':
            {'value': '6', 'type': 'positive'}}, {'Rating': '1496'})

    @patch('resources.league.League.calculateRatings')
    @patch('resources.league.League.decayRatings')
    @patch('resources.league.League.rescaleRatings')
    @patch('resources.league.League.createGames')
    @patch('resources.league.League.restoreTeams')
    @patch('resources.league.League.validatePlayers')
    @patch('resources.league.League.executeOrders')
    @patch('resources.league.League.updateGames')
    def test_run(self, update, execute, validate, restore, create,
                 rescale, decay, calculate):
        self._setProp(self.league.SET_ACTIVE, "FALSE")
        self.league.run()
        create.assert_not_called()
        for fn in {update, execute, validate, restore, rescale, decay,
                   calculate}:
            fn.assert_called_once_with()
        self._setProp(self.league.SET_ACTIVE, "TRUE")
        self.teams.findEntities.return_value = [{'Limit': '10'},] * 10
        self.templates.findEntities.return_value = xrange(5)
        assert_true(self.league.active)
        self.league.run()
        create.assert_called_once_with()

    def test_packaging(self):
        team1 = {'ID': '434', 'Name': 'Team',
                 'Players': '109,390,853', 'Confirmations': 'TRUE,TRUE,FALSE',
                 'Rating': '1920/390', 'Vetos': '12.3/49.1/39.2',
                 'Drops': '5/3/9', 'Rank': '', 'History': '11,22,390',
                 'Finished': '8', 'Limit': '4', 'Ongoing': '1'}
        team1_out = {'ID': 434, 'Name': 'Team', 'Players': {109: {'confirmed':
            True}, 390: {'confirmed': True}, 853: {'confirmed': False}},
            'Rating': (1920, 390),
            'Vetos': {12: 3, 49: 1, 39: 2}, 'Drops': {5, 3, 9},
            'Rank': '', 'History': [11, 22, 390], 'Finished': 8,
            'Limit': 4, 'Ongoing': 1}
        team2 = {'ID': '903', 'Name': 'Other Team',
                 'Players': '490,49,409', 'Confirmations': 'TRUE,TRUE,TRUE',
                 'Rating': '2393/391', 'Vetos': '',
                 'Drops': '', 'Rank': '1', 'History': '239',
                 'Finished': '1', 'Limit': '3', 'Ongoing': '0',
                 'Probation Start': '2014-03-20 04:20:00'}
        team2_out = {'ID': 903, 'Name': 'Other Team',
            'Players': {490: {'confirmed': True}, 49: {'confirmed': True},
                409: {'confirmed': True}}, 'Rating': (2393, 391),
            'Vetos': dict(), 'Drops': set(), 'Rank': 1, 'History': [239,],
            'Finished': 1, 'Limit': 3, 'Ongoing': 0,
            'Probation Start': datetime(2014, 3, 20, 4, 20)}
        self.teams.findEntities.return_value = [team1, team2]
        assert_equals(self.league.fetchTeam(434), team1_out)
        assert_equals(self.league.fetchAllTeams(), [team1_out, team2_out])
        game1 = {'ID': '10', 'WarlightID': 94043094,
            'Created': '2015-05-25 05:05:05',
            'Finished': "2015-05-30 01:02:03", 'Sides': '1,5/7,9/13,15,19',
            'Winners': '7,9', 'Vetos': '2', 'Vetoed': '12/13',
            'Template': '93'}
        game1_out = {'ID': 10, 'WarlightID': 94043094,
            'Created': datetime(2015, 5, 25, 5, 5, 5),
            'Finished': datetime(2015, 5, 30, 1, 2, 3), 'Ongoing': False,
            'Sides': [{1, 5}, {7, 9}, {13, 15, 19}], 'Winners': {7, 9},
            'Declined': False, 'EndedInVeto': False, 'Vetos': 2,
            'Vetoed': [12, 13], 'Template': 93}
        game2 = {'ID': '11', 'WarlightID': '118999',
            'Created': '2015-05-25 05:05:15',
            'Finished': "", 'Sides': '1,9/7,5/13,19',
            'Winners': '7,9!', 'Vetos': '1', 'Vetoed': '12',
            'Template': '93'}
        game2_out = {'ID': 11, 'WarlightID': 118999,
            'Created': datetime(2015, 5, 25, 5, 5, 15),
            'Finished': '', 'Ongoing': True,
            'Sides': [{1, 9}, {7, 5}, {13, 19}], 'Winners': {7, 9},
            'Declined': True, 'EndedInVeto': False, 'Vetos': 1,
            'Vetoed': [12,], 'Template': 93}
        game3 = {'ID': '12', 'WarlightID': 91197253,
            'Created': '2015-05-25 05:05:25',
            'Finished': "2015-05-31 01:09:03", 'Sides': '1,5/7,9',
            'Winners': '', 'Vetos': '2', 'Vetoed': '12/13',
            'Template': '930'}
        game3_out = {'ID': 12, 'WarlightID': 91197253,
            'Created': datetime(2015, 5, 25, 5, 5, 25),
            'Finished': datetime(2015, 5, 31, 1, 9, 3), 'Ongoing': False,
            'Sides': [{1, 5}, {7, 9}], 'Winners': set(),
            'Declined': False, 'EndedInVeto': True, 'Vetos': 2,
            'Vetoed': [12, 13], 'Template': 930}
        self.games.findEntities.return_value = [game1, game2, game3]
        assert_equals(self.league.fetchGame(10), game1_out)
        assert_equals(self.league.fetchAllGames(), [game1_out, game2_out,
                      game3_out])
        template1 = {'ID': 1290, 'Name': 'Elitist Africa',
            'WarlightID': 19304904, 'Active': 'FALSE',
            'Usage': '3'}
        template1_out = {'ID': 1290, 'Name': 'Elitist Africa',
            'WarlightID': 19304904, 'Active': False, 'Usage': 3}
        self.templates.findEntities.return_value = [template1,]
        assert_equals(self.league.fetchTemplate(1290), template1_out)
        assert_equals(self.league.fetchAllTemplates(), [template1_out,])

# run tests
if __name__ == '__main__':
    run_tests()
