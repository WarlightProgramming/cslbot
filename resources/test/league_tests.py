# league_tests.py
## automated tests for the League class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import *
from mock import patch, MagicMock
from resources.league import *
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
                               'Finished': 'STRING',
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
        values = {"0": default, "": default, "none": default,
                  "2010-4-20": default,
                  "2010-04-20 10:30:50": datetime(2010, 4, 20, 10, 30, 50)}
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
        self._posPropertyTest("teamSize", self.league.SET_TEAM_SIZE, 1)

    def test_gameSize(self):
        self._setProp(self.league.SET_GAME_SIZE, "3,4,5")
        assert_true(self.league.gameSize in {3,4,5})
        oldSize = self.league.gameSize
        self._posPropertyTest("statedGameSize()", self.league.SET_GAME_SIZE, 2)
        assert_equals(self.league.gameSize, oldSize)

    def test_sideSize(self):
        self._setProp(self.league.SET_TEAMS_PER_SIDE, "1,50,100")
        assert_true(self.league.sideSize in {1,50,100})
        oldSize = self.league.sideSize
        self._posPropertyTest("statedSideSize()",
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
        assert_true(self.league.meetsVacation(player))
        self._setMaxVacation(1)
        assert_true(self.league.meetsVacation(player))
        self._setMaxVacation(0)
        assert_true(self.league.meetsVacation(player))
        self.handler.validateToken.return_value = {'onVacationUntil':
                                                   self._makeVacationDate(1)}
        assert_false(self.league.meetsVacation(player))
        self._setMaxVacation(1)
        assert_true(self.league.meetsVacation(player))
        self._setMaxVacation(2)
        assert_true(self.league.meetsVacation(player))
        self.handler.validateToken.return_value = {'onVacationUntil':
                                                   self._makeVacationDate(3)}
        assert_false(self.league.meetsVacation(player))
        self.handler.validateToken.return_value = dict()
        assert_true(self.league.meetsVacation(player))

    def test_minLimit(self):
        values = {"-3": 0, "-5": 0, "0": 0, "10": 10, "204": 204, "None": 0}
        self._propertyTest('minLimit', self.league.SET_MIN_LIMIT, 0, values)

    def test_maxLimit(self):
        self._intPropertyTest('maxLimit', self.league.SET_MAX_LIMIT, None)

    def test_constrainLimit(self):
        self._boolPropertyTest('constrainLimit',
                               self.league.SET_CONSTRAIN_LIMIT, True)

    def test_valueInRange(self):
        assert_true(self.league.valueInRange(10, None, None))
        assert_true(self.league.valueInRange(10, 10, None))
        assert_true(self.league.valueInRange(10, None, 10))
        assert_true(self.league.valueInRange(10, 10, 10))
        assert_true(self.league.valueInRange(5, 0, 30))
        assert_true(self.league.valueInRange(5, 0, None))
        assert_true(self.league.valueInRange(5, None, 30))
        assert_true(self.league.valueInRange(0, -1, 1))
        assert_false(self.league.valueInRange(0, None, -1))
        assert_false(self.league.valueInRange(0, 1, -1))
        assert_false(self.league.valueInRange(0, 1, None))
        assert_false(self.league.valueInRange(0, 1, 2))

    def _setMinLimit(self, val):
        self._setProp(self.league.SET_MIN_LIMIT, val)

    def _setMaxLimit(self, val):
        self._setProp(self.league.SET_MAX_LIMIT, val)

    def test_limitInRange(self):
        self._setMinLimit(4)
        self._setMaxLimit(20)
        assert_true(self.league.limitInRange(20))
        assert_false(self.league.limitInRange(3))
        assert_false(self.league.limitInRange(21))

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
        assert_equals(self.league.defaultWinCount, str(0))

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
        assert_true(self.league.meetsMembership(player))
        self._setMinMemberAge(1)
        assert_false(self.league.meetsMembership(player))
        self._setProp(self.league.SET_MEMBERS_ONLY, "TRUE")
        assert_false(self.league.meetsMembership(player))
        self._setMinMemberAge(0)
        assert_false(self.league.meetsMembership(player))
        player.isMember = True
        player.memberSince = date.today() - timedelta(days=3)
        self._setMinMemberAge(4)
        assert_false(self.league.meetsMembership(player))
        self._setMinMemberAge(3)
        assert_true(self.league.meetsMembership(player))
        self._setMinMemberAge(2)
        assert_true(self.league.meetsMembership(player))

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
        assert_equals(self.league.findRatingAtPercentile(0), None)
        self.teams.findValue.return_value = ["1", "2", "3", "4", "5",
                                             "6", "7", "8", "9", "10"]
        assert_equals(self.league.findRatingAtPercentile(0), None)
        assert_equals(self.league.findRatingAtPercentile(1), 2)
        assert_equals(self.league.findRatingAtPercentile(10), 2)
        assert_equals(self.league.findRatingAtPercentile(21), 4)
        assert_equals(self.league.findRatingAtPercentile(30.5), 5)
        assert_equals(self.league.findRatingAtPercentile(99.5), 10)
        assert_equals(self.league.findRatingAtPercentile(1000), 10)
        assert_equals(self.league.findRatingAtPercentile(50), 6)
        self.league.prettifyRating = oldPrettify

    @patch('resources.league.League.findRatingAtPercentile')
    def test_minPercentileRating(self, findRating):
        values = {"0": findRating.return_value, "": None, "None": None,
                  "hi": None, "10": findRating.return_value,
                  "490": findRating.return_value,
                  "43.5902": findRating.return_value}
        self._propertyTest('minPercentileRating',
                           self.league.SET_MIN_PERCENTILE, None, values)

    @patch('resources.league.League.findRatingAtPercentile')
    def test_minRating(self, findRating):
        findRating.return_value = None
        self._setProp(self.league.SET_MIN_RATING, "50")
        assert_equals(self.league.minRating, 50)
        self._setProp(self.league.SET_MIN_PERCENTILE, "30")
        findRating.return_value = 30
        assert_equals(self.league.minRating, findRating.return_value)

    def test_gracePeriod(self):
        self._intPropertyTest('gracePeriod', self.league.SET_GRACE_PERIOD, 0)

    def test_restorationPeriod(self):
        self._setProp(self.league.SET_GRACE_PERIOD, 5)
        values = {"10": 15, "": None, "None": None, " ": None, "40": 45,
                  "0": 5}
        self._propertyTest('restorationPeriod',
                           self.league.SET_RESTORATION_PERIOD, None, values)

    @patch('resources.league.League.getExtantEntities')
    def test_restoreTeams(self, getExtant):
        self._setProp(self.league.SET_RESTORATION_PERIOD, None)
        self._setProp(self.league.SET_MIN_RATING, None)
        self._setProp(self.league.SET_MIN_PERCENTILE, None)
        self.league.restoreTeams()
        getExtant.assert_not_called()
        self._setProp(self.league.SET_MIN_RATING, 50)
        self.league.restoreTeams()
        getExtant.assert_not_called()
        self._setProp(self.league.SET_GRACE_PERIOD, 5)
        self._setProp(self.league.SET_RESTORATION_PERIOD, 10)
        assert_equals(self.league.restorationPeriod, 15)
        getExtant.return_value = list()
        self.league.restoreTeams()
        assert_equals(getExtant.call_count, 1)
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
        assert_true(self.league.valueBelowCapacity(5, 6))
        assert_true(self.league.valueBelowCapacity(5, 10))
        assert_true(self.league.valueBelowCapacity(0, 1))
        assert_false(self.league.valueBelowCapacity(5, 5))
        assert_false(self.league.valueBelowCapacity(5, 4))
        assert_false(self.league.valueBelowCapacity(0, 0))
        assert_true(self.league.valueBelowCapacity(109303838, None))

    @patch('resources.league.League.valueBelowCapacity')
    def test_activeFull(self, belowCap):
        belowCap.return_value = False
        assert_true(self.league.activeFull)
        belowCap.return_value = True
        assert_false(self.league.activeFull)

    @patch('resources.league.League.valueBelowCapacity')
    def test_leagueFull(self, belowCap):
        belowCap.return_value = False
        assert_true(self.league.leagueFull)
        belowCap.return_value = True
        assert_false(self.league.leagueFull)

    def test_getDateTimeProperty(self):
        getProp = self.league.getDateTimeProperty
        assert_equals(getProp(datetime(2000, 4, 20, 10, 30, 50)),
                      datetime(2000, 4, 20, 10, 30, 50))
        assert_equals(getProp(datetime.strftime(datetime(2000, 4, 20, 10, 30,
                                                         50),
                                                self.league.TIMEFORMAT)),
                      datetime(2000, 4, 20, 10, 30, 50))

    def test_joinPeriodStart(self):
        self._dateTimePropertyTest('joinPeriodStart',
                                   self.league.SET_JOIN_PERIOD_START, None)

    def test_joinPeriodEnd(self):
        self._dateTimePropertyTest('joinPeriodEnd',
                                   self.league.SET_JOIN_PERIOD_END, None)

    def test_currentTimeWithinRange(self):
        assert_true(self.league.currentTimeWithinRange(None, None))
        start = datetime.now() - timedelta(days=1)
        end = datetime.now() + timedelta(days=1)
        assert_true(self.league.currentTimeWithinRange(start, end))
        assert_true(self.league.currentTimeWithinRange(None, end))
        assert_true(self.league.currentTimeWithinRange(start, None))
        assert_true(self.league.currentTimeWithinRange(None, None))
        assert_false(self.league.currentTimeWithinRange(None, start))
        assert_false(self.league.currentTimeWithinRange(end, None))
        assert_false(self.league.currentTimeWithinRange(end, start))

    @patch('resources.league.League.currentTimeWithinRange')
    @patch('resources.league.League.valueBelowCapacity')
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
        assert_equals(self.league.getExtantEntities(table),
                      table.findEntities.return_value)
        assert_equals(self.league.getExtantEntities(table,
                      {'Ra Ra': {'value': "Rasputin", 'type': 'positive'}}),
                      table.findEntities.return_value)
        table.findEntities.assert_called_with({'ID': {'value': '',
                                                      'type': 'negative'},
                                               'Ra Ra': {'value': 'Rasputin',
                                                         'type': 'positive'}})

    @patch('resources.league.League.getExtantEntities')
    def test_activityCounts(self, getExtant):
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

    @patch('resources.league.League.currentTimeWithinRange')
    @patch('resources.league.League.getExtantEntities')
    def test_active(self, getExtant, rangeCheck):
        getExtant.return_value = list()
        self._setProp(self.league.SET_MIN_TEMPLATES, 10)
        assert_false(self.league.active)
        getExtant.return_value = range(9)
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
            assert_true(self.league.gameCountInRange(player))
        player.currentGames = 0
        assert_false(self.league.gameCountInRange(player))
        player.currentGames = 5
        assert_false(self.league.gameCountInRange(player))
        self._setProp(self.league.SET_MIN_ONGOING_GAMES, 0)
        self._setProp(self.league.SET_MAX_ONGOING_GAMES, None)
        assert_true(self.league.gameCountInRange(player))

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
        assert_true(self.league.RTPercentInRange(player))
        self._setProp(self.league.SET_MIN_RT_PERCENT, 30)
        self._setProp(self.league.SET_MAX_RT_PERCENT, 35)
        assert_true(self.league.RTPercentInRange(player))
        player.percentRT = 35
        assert_true(self.league.RTPercentInRange(player))
        player.percentRT = 30
        assert_true(self.league.RTPercentInRange(player))
        player.percentRT = 29.9999
        assert_false(self.league.RTPercentInRange(player))
        player.percentRT = 100
        assert_false(self.league.RTPercentInRange(player))
        self._setProp(self.league.SET_MIN_RT_PERCENT, 40)
        player.percentRT = 35
        assert_false(self.league.RTPercentInRange(player))

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
        assert_false(self.league.meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_3v3_PCT, 5)
        assert_true(self.league.meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_RANKED, 500)
        assert_false(self.league.meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_RANKED, 400)
        self._setProp(self.league.SET_MIN_1v1_PCT, 50)
        assert_false(self.league.meetsMinRanked(player))
        self._setProp(self.league.SET_MIN_1v1_PCT, 30)
        self._setProp(self.league.SET_MIN_2v2_PCT, 40)
        assert_false(self.league.meetsMinRanked(player))

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
        assert_false(self.league.clanAllowed(player))
        player.clanID = 30
        self._setProp(self.league.SET_ALLOWED_CLANS, "30,40,50")
        assert_true(self.league.clanAllowed(player))
        self._setProp(self.league.SET_ALLOWED_CLANS, "ALL")
        assert_true(self.league.clanAllowed(player))
        self._setProp(self.league.SET_ALLOWED_CLANS, "")
        self._setProp(self.league.SET_BANNED_CLANS, "12,13,14")
        assert_true(self.league.clanAllowed(player))
        self._setProp(self.league.SET_BANNED_CLANS, "30,40,50")
        assert_false(self.league.clanAllowed(player))
        self._setProp(self.league.SET_BANNED_CLANS, "ALL")
        assert_false(self.league.clanAllowed(player))

    def test_processLoc(self):
        assert_equals(self.league.processLoc("    Micronesia    "),
                                             "Micronesia")
        assert_equals(self.league.processLoc(" United Haitian  Republic   \n"),
                                             "United Haitian Republic")

    def test_checkLocation(self):
        self._setProp(self.league.SET_BANNED_LOCATIONS, "")
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "")
        assert_equals(self.league.checkLocation("Texas"), None)
        self._setProp(self.league.SET_BANNED_LOCATIONS, "Texas")
        assert_false(self.league.checkLocation("Texas"))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "Texas")
        assert_true(self.league.checkLocation("Texas"))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "ALL")
        assert_false(self.league.checkLocation("California"))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "")
        assert_equals(self.league.checkLocation("California"), None)
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "ALL")
        assert_true(self.league.checkLocation("California"))

    def test_locationAllowed(self):
        player = MagicMock()
        player.location = "United States of Australia: Texas: Earth"
        self._setProp(self.league.SET_BANNED_LOCATIONS, "ALL")
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "")
        assert_false(self.league.locationAllowed(player))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "Texas")
        assert_true(self.league.locationAllowed(player))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS, "")
        self._setProp(self.league.SET_BANNED_LOCATIONS, "")
        assert_true(self.league.locationAllowed(player))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "United States")
        assert_true(self.league.locationAllowed(player))
        self._setProp(self.league.SET_BANNED_LOCATIONS, "Earth")
        assert_false(self.league.locationAllowed(player))
        self._setProp(self.league.SET_ALLOWED_LOCATIONS,
                      "United States of Australia")
        assert_true(self.league.locationAllowed(player))
        player.location = "United States of Australia"
        self._setProp(self.league.SET_BANNED_LOCATIONS, "ALL")
        assert_true(self.league.locationAllowed(player))
        player.location = ""
        assert_false(self.league.locationAllowed(player))

    def test_meetsAge(self):
        player = MagicMock()
        player.joinDate = date.today() - timedelta(30)
        self._setProp(self.league.SET_MIN_AGE, 30)
        assert_true(self.league.meetsAge(player))
        player.joinDate = date.today()
        assert_false(self.league.meetsAge(player))
        player.joinDate = date.today() - timedelta(400)
        assert_true(self.league.meetsAge(player))

    def test_meetsSpeed(self):
        player = MagicMock()
        player.playSpeed = {'Real-Time Games': 1,
                            'Multi-Day Games': 38}
        self._setProp(self.league.SET_MAX_RT_SPEED, 30)
        self._setProp(self.league.SET_MAX_MD_SPEED, 40)
        assert_false(self.league.meetsSpeed(player))
        self._setProp(self.league.SET_MAX_RT_SPEED, 60)
        assert_true(self.league.meetsSpeed(player))

    def test_meetsLastSeen(self):
        player = MagicMock()
        player.lastSeen = 30
        self._setProp(self.league.SET_MAX_LAST_SEEN, 40)
        assert_true(self.league.meetsLastSeen(player))
        player.lastSeen = 40
        assert_true(self.league.meetsLastSeen(player))
        player.lastSeen = 50
        assert_false(self.league.meetsLastSeen(player))
        self._setProp(self.league.SET_MAX_LAST_SEEN, "None")
        assert_true(self.league.meetsLastSeen(player))

    @patch('resources.league.League.meetsMinRanked')
    @patch('resources.league.League.meetsLastSeen')
    @patch('resources.league.League.RTPercentInRange')
    @patch('resources.league.League.gameCountInRange')
    @patch('resources.league.League.meetsSpeed')
    @patch('resources.league.League.meetsAge')
    @patch('resources.league.League.meetsVacation')
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
        assert_true(self.league.checkPrereqs(player))
        player.playedGames = 10
        assert_false(self.league.checkPrereqs(player))

    @patch('resources.league.League.checkPrereqs')
    def test_allowed(self, check):
        check.return_value = True
        self._setProp(self.league.SET_ALLOWED_PLAYERS, "40")
        self._setProp(self.league.SET_BANNED_PLAYERS, "40")
        assert_true(self.league.allowed(40))
        check.return_value = False
        assert_true(self.league.allowed(40))
        assert_false(self.league.allowed(43))
        check.return_value = True
        assert_true(self.league.allowed(43))
        self._setProp(self.league.SET_BANNED_PLAYERS, "40,ALL")
        assert_false(self.league.allowed(43))
        self._setProp(self.league.SET_ALLOWED_PLAYERS, "ALL,40")
        assert_true(self.league.allowed(43))

    @patch('resources.league.League.allowed')
    def test_banned(self, allowed):
        allowed.return_value = False
        assert_true(self.league.banned(40))
        allowed.return_value = True
        assert_false(self.league.banned(40))

    def test_logFailedOrder(self):
        order = {'type': 'OrderType', 'author': 3940430, 'orders': ['12','13']}
        self.league.logFailedOrder(order)
        expDesc = "Failed to process OrderType order by 3940430"
        self.parent.log.assert_called_once_with(expDesc,
                                                league=self.league.name)

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
    @patch('resources.league.League.banned')
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
                      self.league.sysDict[self.league.RATE_ELO]['default'])
        self._setProp(self.league.SET_SYSTEM, self.league.RATE_WINRATE)
        assert_equals(self.league.defaultRating,
                      self.league.sysDict[self.league.RATE_WINRATE]['default'])

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

    @patch('resources.league.League.checkTeam')
    def test_checkAuthorAndMembers(self, check):
        order = {'author': 1403, 'orders': ['1v1', 'teamName', '3', '40', '2']}
        self.league.mods = {1403,}
        assert_equals(self.league.checkAuthorAndMembers(order),
                      (check.return_value, [40, 2], [False, False]))
        self.league.mods = set()
        assert_raises(ImproperInput, self.league.checkAuthorAndMembers, order)

    def test_checkTeamDuplication(self):
        self.teams.findEntities.return_value = [
                                          {'Name': 'A', 'Players': '1,2,3'},
                                          {'Name': '402v', 'Players': '4,9'}]
        assert_equals(None, self.league.checkTeamDuplication('4,5', 'B'))
        assert_equals(None, self.league.checkTeamDuplication('6,7,8', 'D 4'))
        assert_raises(ImproperInput, self.league.checkTeamDuplication, '4,9',
                      'F')

    @patch('resources.league.League.checkLimit')
    @patch('resources.league.League.checkAuthorAndMembers')
    def test_checkEligible(self, check, limCheck):
        order = {'author': 1403, 'orders': ['1v1', 'teamName', '3', '40', '2']}
        check.return_value = [1, 2, 3]
        assert_equals(self.league.checkEligible(order),
                      (limCheck.return_value, 1, 2, 3))
        limCheck.assert_called_once_with(3)

    @patch('resources.league.League.checkTeamDuplication')
    @patch('resources.league.League.checkEligible')
    @patch('resources.league.League.checkJoins')
    def test_addTeam(self, joinCheck, eligible, checkDup):
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
                                                 'Count': 0, 'Finished': 0,
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
            fetch.return_value.get('ID')})

    @patch('resources.league.League.fetchTeamData')
    def test_checkLimitChange(self, fetch):
        assert_equals(self.league.checkLimitChange(400, -3), None)
        assert_equals(self.league.checkLimitChange(100, 0), None)
        self._setProp(self.league.SET_ACTIVE_CAPACITY, "")
        assert_equals(self.league.checkLimitChange(100, 3), None)
        self._setProp(self.league.SET_ACTIVE_CAPACITY, 2)
        self.teams.findEntities.return_value = [{'ID': 1},]
        assert_equals(self.league.checkLimitChange(42, 20), None)
        self.teams.findEntities.return_value = [{'ID': 1}, {'ID': 2}]
        fetch.return_value = {'Limit': 3}
        assert_equals(self.league.checkLimitChange(42, 20), None)
        fetch.return_value = {'Limit': 0}
        assert_raises(ImproperInput, self.league.checkLimitChange, 2, 2)
        assert_equals(self.league.checkLimitChange(42, 0), None)
        self.teams.findEntities.return_value = [{'ID': 1}, {'ID': 2},
                                                {'ID': 3}]
        assert_raises(ImproperInput, self.league.checkLimitChange, 24, 2)

    @patch('resources.league.League.changeLimit')
    @patch('resources.league.League.checkLimitChange')
    @patch('resources.league.League.fetchMatchingTeam')
    def test_setLimit(self, fetch, check, change):
        order = {'type': 'set_limit', 'author': 3022124041,
                 'orders': ['1v1', 'The Harambes', '3']}
        fetch.return_value = {'Players': '12,14,15', 'ID': 4}
        self.league.mods = set()
        assert_raises(ImproperInput, self.league.setLimit, order)
        self.league.mods = {3022124041,}
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
        self.templates.findEntities.return_value = [{'ID': 3, 'Games': 3},
                                                    {'ID': 4, 'Games': 4},
                                                    {'ID': 5, 'Games': 2},
                                                    {'ID': 1, 'Games': 0}]
        assert_equals(self.league.templateRanks, [(1,0), (5,2), (3,3), (4,4)])

    def test_findMatchingTemplate(self):
        self.templates.findValue.return_value = list()
        assert_equals(self.league.findMatchingTemplate('name'), None)
        self.templates.findValue.return_value = [1, 2, 3, 4, 5]
        assert_equals(self.league.findMatchingTemplate('name'), 1)

    @patch('resources.league.League.fetchMatchingTeam')
    def test_getExistingDrops(self, fetch):
        fetch.return_value = {'Drops': '12/13/14', 'ID': 43}
        assert_equals(self.league.getExistingDrops('order'),
                      (43, ['12','13','14']))

    @patch('resources.league.League.updateEntityValue')
    def test_updateTeamDrops(self, update):
        drops = [12, 14, 23, '12', '43', 4053]
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
        getExisting.return_value = 4032, ['12', '13', '14']
        self.templates.findEntities.return_value = xrange(200)
        self._setProp(self.league.SET_DROP_LIMIT, 3)
        assert_raises(ImproperInput, self.league.dropTemplates, order)
        self._setProp(self.league.SET_DROP_LIMIT, 4)
        assert_equals(self.league.dropLimit, 4)
        find.return_value = 3
        self.league.dropTemplates(order)
        dataStr = "Too many drops by team The Harambes, dropping only first 1"
        self.parent.log.assert_called_with(dataStr, 'NAME')
        update.assert_called_once_with(4032, ['12', '13', '14', 3])
        self._setProp(self.league.SET_DROP_LIMIT, 40)
        assert_equals(self.league.dropLimit, 40)
        oldCount = self.parent.log.call_count
        getExisting.return_value = 4033, ['12', '13', '14', '15']
        self.league.dropTemplates(order)
        assert_equals(self.parent.log.call_count, oldCount)
        update.assert_called_with(4033, ['12', '13', '14', '15', 3, 3, 3])
        find.return_value = None
        getExisting.return_value = 4033, ['12', '13', '14', '15']
        self.league.dropTemplates(order)
        update.assert_called_with(4033, ['12', '13', '14', '15'])

    @patch('resources.league.League.updateTeamDrops')
    @patch('resources.league.League.findMatchingTemplate')
    @patch('resources.league.League.getExistingDrops')
    def test_undropTemplates(self, getExisting, find, update):
        order = {'type': 'undrop_templates', 'author': 3022124041,
                 'orders': ['1v1', 'The Harambes', 'North Korea 1v1',
                           'Sanctuary 3v3', 'Cincinnati Zoo FFA']}
        getExisting.return_value = 4032, ['12', '13', '14']
        find.return_value = 12
        self.league.undropTemplates(order)
        update.assert_called_once_with(4032, ['13', '14'])
        find.return_value = None
        getExisting.return_value = 4032, ['12', '13', '14']
        self.league.undropTemplates(order)
        update.assert_called_with(4032, ['12', '13', '14'])

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

    @patch('resources.league.League.updateRanks')
    @patch('resources.league.League.logFailedOrder')
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
                           deactivateTemplate, quitLeague, logFailedOrder,
                           updateRanks):
        existingLogs = self.parent.log.call_count
        self.league.orders = [{'type': 'ADD_team'}, {'type': 'add_team'},
            {'type': 'confirm_team'}, {'type': 'CONFIRM_TEAM'},
            {'type': 'unconfirm_team'}, {'type': 'sEt_lImIt'},
            {'type': 'remove_team'}, {'type': 'drop_templates'},
            {'type': 'drop_template'}, {'type': 'undrop_template'},
            {'type': 'undrop_templates'}, {'type': 'activate_template'},
            {'type': 'deactivate_template'}, {'type': 'quit_league'},
            {'type': 'subtract_team'}]
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
        assert_true(self.league.isAbandoned(players))
        players = [{'state': 'Declined'}, {'state': 'Won'},
                   {'state': 'Declined'}, {'state': 'Wyoming'}]
        assert_false(self.league.isAbandoned(players))
        players = list()
        assert_false(self.league.isAbandoned(players))
        players = [{'state': 'Duck'}, {'state': 'Duck'},
                   {'state': 'Duck'}, {'state': 'Goose'}]
        assert_false(self.league.isAbandoned(players))

    def test_findMatchingPlayers(self):
        players = [{'id': 4, 'state': 'VotedToEnd'},
            {'id': 12, 'state': 'Velociraptor'}, {'id': 1, 'state': 'Won'},
            {'id': 39, 'state': 'Velociraptor'}, {'id': 5, 'state': 'Wyoming'},
            {'id': 40, 'state': 'Won'}, {'id': 3, 'state': 'Velociraptor'}]
        assert_equals(self.league.findMatchingPlayers(players), list())
        assert_equals(self.league.findMatchingPlayers(players, 'Won'), [1, 40])
        assert_equals(self.league.findMatchingPlayers(players, 'Velociraptor'),
                      [3, 12, 39])
        assert_equals(self.league.findMatchingPlayers(players, 'Won',
                      'Wyoming'), [1, 5, 40])
        assert_equals(self.league.findWinners(players), [1, 40])
        assert_equals(self.league.findDecliners(players), list())
        assert_equals(self.league.findWaiting(players), list())

    @patch('resources.league.League.findWinners')
    @patch('resources.league.League.isAbandoned')
    def test_handleFinished(self, abandon, find):
        abandon.return_value = True
        gameData = {'players': [{'id': 5}, {'id': 10}, {'id': 15}]}
        assert_equals(self.league.handleFinished(gameData),
                      ('ABANDONED', [5, 10, 15]))
        abandon.return_value = False
        assert_equals(self.league.handleFinished(gameData),
                      ('FINISHED', find.return_value))

    @patch('resources.league.League.findWaiting')
    @patch('resources.league.League.findDecliners')
    def test_handleWaiting(self, decliners, waiting):
        self._setProp(self.league.SET_EXP_THRESH, 3)
        assert_equals(self.league.expiryThreshold, 3)
        gameData = {'players': [1, 2, 3, 4, 5]}
        created = datetime.now() - timedelta(5)
        decliners.return_value = range(3)
        assert_equals(self.league.handleWaiting(gameData, created),
                      ('DECLINED', range(3)))
        decliners.return_value = xrange(1, 6)
        assert_equals(self.league.handleWaiting(gameData, created),
                      ('ABANDONED', None))
        waiting.return_value = xrange(3)
        decliners.return_value = list()
        assert_false(len(waiting.return_value) == len(gameData['players']))
        assert_equals(self.league.handleWaiting(gameData, created), None)
        waiting.return_value = xrange(1, 6)
        assert_equals(self.league.handleWaiting(gameData, created),
                      ('ABANDONED', None))
        created = datetime.now() - timedelta(1)
        assert_false((datetime.now() - created).days >
                     self.league.expiryThreshold)
        assert_equals(self.league.handleWaiting(gameData, created), None)

# run tests
if __name__ == '__main__':
    run_tests()
