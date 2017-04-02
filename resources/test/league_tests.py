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

    def _floatPropertyTest(self, prop, label, default):
        values = {"0": 0.0, "-1": -1.0, "-1.0": -1.0, "0.0": 0.0, "210": 210.0,
                  "string": default, "None": default, "randomLOL": default,
                  "10.0": 10.0, "10": 10.0, "3334": 3334.0, "042.390": 42.390}
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

# run tests
if __name__ == '__main__':
    run_tests()
