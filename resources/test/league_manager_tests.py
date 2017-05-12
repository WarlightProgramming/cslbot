# league_manager_tests.py
## automated tests for the LeagueManager class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import assert_equals, assert_raises, assert_false, assert_true
from mock import patch, MagicMock
from resources.league_manager import LeagueManager, ThreadError, isInteger,\
    LeagueError

# tests
## LeagueManager class tests
class TestLeagueManager(TestCase):

    @patch('resources.league_manager.LeagueManager._getAdmin')
    @patch('resources.league_manager.LeagueManager._validateAdmin')
    def setUp(self, validateAdmin, getAdmin):
        validateAdmin.return_value = self.admin = 'ADMIN'
        self.globalManager = MagicMock()
        self.database = MagicMock()
        self.commands = MagicMock()
        self.commands.findEntities.return_value = [{LeagueManager.TITLE_ARG:
            '1v1;2v2;3v3'},]
        self.database.fetchTable.return_value = self.commands
        self.manager = LeagueManager(self.database, self.globalManager)

    def test_init(self):
        assert_equals(self.manager.database, self.database)
        assert_equals(self.manager.commands, self.commands)
        assert_equals(self.manager.logSheet,
                      self.database.fetchTable.return_value)
        assert_equals(self.manager.leagues, ['1v1', '2v2', '3v3'])
        assert_equals(self.manager.admin, self.admin)
        assert_equals(self.manager.events, {'error': False, 'events': list()})

    def test_fetchLeagueNames(self):
        self.commands.findEntities.return_value = [{LeagueManager.TITLE_ARG:
            'a;b;c;d'}, {LeagueManager.TITLE_ARG: 'de;fg'}]
        assert_equals(self.manager._fetchLeagueNames(), ['a', 'b', 'c', 'd'])
        self.commands.findEntities.return_value = list()
        assert_equals(self.manager._fetchLeagueNames(), list())

    @patch('resources.league_manager.LeagueManager.log')
    @patch('resources.league_manager.PlayerParser')
    def test_validateAdmin(self, parser, log):
        verified = self.globalManager.verifyAdmin
        verified.return_value = True
        parser.return_value.isMember = True
        assert_equals(self.manager._validateAdmin("390089"), 390089)
        parser.return_value.isMember = False
        assert_equals(self.manager._validateAdmin("1293902309"), None)
        log.assert_called_once_with("League admin is not authorized",
            error=True)
        parser.return_value.isMember = True
        verified.return_value = False
        assert_equals(self.manager._validateAdmin("390089"), None)
        log.assert_called_with("League admin is not authorized",
            error=True)

    def test_validationStr(self):
        self.database.sheet.ID = "ID"
        assert_equals(self.manager.validationStr, "!validate_league ID")

    def test_getUniqueAuthors(self):
        posts = [{'author': {'ID': '12'}}, {'author': {'ID': '13'}},
                 {'author': {'ID': '14'}}, {'author': {'ID': '15'}},
                 {'author': {'ID': '21'}}, {'author': {'ID': '13'}}]
        assert_equals(self.manager._getUniqueAuthors(posts),
                      {'12', '13', '14', '15', '21'})
        assert_equals(self.manager._getUniqueAuthors(list()), set())

    def test_validateThread(self):
        parser = MagicMock()
        self.manager.ABUSE_THRESHOLD = 5
        self.database.sheet.ID = "ID"
        parser.getPosts.return_value = [{'author': {'ID': '192'},
            'message': '',
            'title': 'Some title that does not contain [CSL] at the start'},
            {'author': {'ID': '12'}}, {'author': {'ID': '90'}},
            {'author': {'ID': '12'}}, {'author': {'ID': '3'}}]
        assert_raises(ThreadError, self.manager._validateThread, parser)
        parser.getPosts.return_value.append({'author': {'ID': '390'}})
        assert_raises(ThreadError, self.manager._validateThread, parser)
        parser.getPosts.return_value[0]['message'] = '!validate_league ID'
        assert_raises(ThreadError, self.manager._validateThread, parser)
        parser.getPosts.return_value[0]['title'] = '[CSL]Some title'
        assert_equals(self.manager._validateThread(parser), None)

    @patch('resources.league_manager.LeagueManager.log')
    def test_logThreadFailure(self, log):
        self.manager._logThreadFailure("thread")
        log.assert_called_with("Unable to scan thread thread. Quitting.",
                               error=True)

    @patch('resources.league_manager.ForumThreadParser')
    def test_makeForumThreadParser(self, parser):
        assert_false(isInteger(''))
        assert_equals(self.manager._makeForumThreadParser("10390494"),
                      parser.return_value)
        parser.assert_called_once_with(10390494)
        assert_raises(ThreadError, self.manager._makeForumThreadParser, "")
        assert_raises(ThreadError, self.manager._makeForumThreadParser,
                      "warlight.net/Forum/Forum")
        URL = "warlight.net/Forum/400283-a-b-c-d"
        assert_equals(self.manager._makeForumThreadParser(URL),
                      parser.return_value)
        parser.assert_called_with(400283)

    @patch('resources.league_manager.LeagueManager.log')
    @patch('resources.league_manager.ForumThreadParser')
    def test_fetchLeagueThread(self, parser, log):
        self.database.sheet.ID = "ID"
        self.commands.findEntities.return_value = list()
        assert_equals(self.manager._fetchLeagueThread(), None)
        self.commands.findEntities.return_value = [{'Command': 'THREAD',
            'Args': '4309340840'},]
        parser.return_value.getPosts.return_value = [{'message':
            '!validate_league ID', 'title': '[CSL] Some Thread',
            'author': {'ID': 0}}, {'author': {'ID': 1}},
            {'author': {'ID': 2}}, {'author': {'ID': 3}},
            {'author': {'ID': 2}}]
        self.manager._fetchLeagueThread()
        failStr = "Thread must have posts by at least 5 unique authors"
        log.assert_called_once_with(failStr, error=True)
        parser.return_value.getPosts.return_value.append({'author': {'ID': 4}})
        assert_equals(self.manager._fetchLeagueThread(),
                      parser.return_value)
        parser.assert_called_with(4309340840)
        self.commands.findEntities.return_value = [{'Command': 'THREAD',
            'Args': 'grepolis.net/Fora/4309340840'},]
        failStr = "Invalid forum URL"
        self.manager._fetchLeagueThread()
        log.assert_called_with(failStr, error=True)
        self.commands.findEntities.return_value = [{'Command': 'THREAD',
            'Args': 'warlight.net/Forum/430934084-some-funny-data'},]
        assert_equals(self.manager._fetchLeagueThread(),
                      parser.return_value)
        parser.assert_called_with(430934084)

    @patch('resources.league_manager.LeagueManager.log')
    def test_handleSpecifiedAdmin(self, log):
        assert_equals(self.manager._handleSpecifiedAdmin([{
            'Args': '490340'},]), '490340')
        assert_equals(self.manager._handleSpecifiedAdmin(list()), None)
        log.assert_called_once_with("Unable to find admin", error=True)

    @patch('resources.league_manager.LeagueManager.log')
    @patch('resources.league_manager.LeagueManager._fetchLeagueThread')
    def test_getAdmin(self, fetch, log):
        self.commands.findEntities.return_value = [{'Args': '2940A'},]
        fetch.return_value = None
        self.manager._getAdmin()
        log.assert_called_once_with("Unable to find admin", error=True)
        self.commands.findEntities.return_value = list()
        self.manager._getAdmin()
        log.assert_called_with("Unable to find admin", error=True)
        assert_equals(log.call_count, 2)
        parser = MagicMock()
        parser.getPosts.side_effect = IOError
        fetch.return_value = parser
        self.manager._getAdmin()
        assert_equals(log.call_count, 3)
        parser.getPosts.side_effect = None
        parser.getPosts.return_value = [{'author': {'ID': '3'}},]
        assert_equals(self.manager._getAdmin(), '3')

    def test_log(self):
        self.manager.log("description", error=False)
        assert_false(self.manager.events['error'])
        assert_equals(len(self.manager.events['events']), 1)
        self.manager.log("description", error=True)
        assert_equals(self.manager.logSheet.addEntity.call_count, 2)
        assert_true(self.manager.events['error'])
        assert_equals(len(self.manager.events['events']), 2)

    @patch('resources.league_manager.LeagueManager._fetchLeagueCommands')
    def test_getDefaultResults(self, fetch):
        assert_equals(self.manager._getDefaultResults("ALLY"),
                      fetch.return_value)
        assert_equals(self.manager._getDefaultResults("ALL"), dict())

    def test_fetchLeagueCommands(self):
        self.commands.getAllEntities.return_value = {'Cmd': [{'Args': 'Are',
            'League': ''}], 'Human': [{'Args': 'Or', 'League': 'Are'}],
            'We': [{'Args': 'Dancer', 'League': 'ALL'}], 'And': [{'Args':
            '', 'League': ''}, {'Args': 'Are;We;Human', 'League': 'ALL'}],
            'WE': [{'Args': 'Human', 'League': 'Are'}]}
        assert_equals(self.manager._fetchLeagueCommands(''),
            {'CMD': 'Are', 'WE': 'Dancer', 'AND': ''})
        assert_equals(self.manager._fetchLeagueCommands('Are'),
            {'HUMAN': 'Or', 'WE': 'Human', 'AND': 'Are;We;Human'})

    @patch('resources.league_manager.LeagueManager.log')
    @patch('resources.league_manager.LeagueManager._validateThread')
    @patch('resources.league_manager.OrderParser')
    def test_fetchThreadOrders(self, parser, validate, log):
        threadParser = MagicMock()
        threadParser.getOrders.return_value = 'orders'
        parser.return_value = threadParser
        assert_equals(self.manager._fetchThreadOrders('12049', 'offset'),
                      'orders')
        threadParser.getOrders.assert_called_once_with('offset')
        parser.assert_called_once_with(12049)
        threadParser.getOrders.side_effect = ThreadError
        assert_equals(self.manager._fetchThreadOrders('12094', '2'), set())
        validate.side_effect = ThreadError
        assert_equals(self.manager._fetchThreadOrders('1294', '2'), set())
        assert_equals(log.call_count, 2)

    def test_narrowOrders(self):
        orders = [{'type': 'add_team', 'orders': ['3v3','4']},
                  {'type': 'remove_team', 'orders': ['ALL', '9']},
                  {'type': 'confirm_team', 'orders': ['1v1', '4']},
                  {'type': 'set_limit'}]
        assert_equals(self.manager._narrowOrders(orders, '3v3'), orders[:2])

    def test_getLeagueSheets(self):
        assert_equals(self.manager._getLeagueSheets('league'),
                      tuple([self.database.fetchTable.return_value,] * 3))
        self.database.fetchTable.assert_called_with("Template Data (league)")

    def test_retrieveOffset(self):
        assert_equals(self.manager._retrieveOffset(list()), 0)
        assert_equals(self.manager._retrieveOffset([{'Command': 'OFFSET',
            'Args': '1204'},]), 1204)

    def test_handleInterfaces(self):
        self.commands.getAllEntities.return_value = list()
        assert_equals(self.manager._handleInterfaces("4v4", None),
                      "(no league interface specified)")
        assert_equals(self.manager._handleInterfaces("4v4", "C"), 'C')
        self.commands.getAllEntities.return_value = {"INTERFACE":
            [{'League': 'ALL', 'Args': 'A'}, {'League': '4v4', 'Args': 'B'}]}
        assert_equals(self.manager._handleInterfaces("4v4", None), 'B')
        assert_equals(self.manager._handleInterfaces("4v4", "C"), 'B')

    @patch('resources.league_manager.LeagueManager._handleInterfaces')
    @patch('resources.league_manager.LeagueManager._fetchLeagueCommands')
    def test_getInterfaceName(self, fetch, handle):
        assert_equals(self.manager._getInterfaceName("thread", 'league'),
                      "thread")
        assert_equals(self.manager._getInterfaceName("4290", 'league'),
            'https://www.warlight.net/Forum/4290')
        assert_equals(self.manager._getInterfaceName("", "league"),
                      handle.return_value)
        handle.assert_called_once_with('league',
                                       fetch.return_value.get.return_value)

    def test_checkLeagueExists(self):
        self.manager.leagues = ["A", "1"]
        assert_equals(self.manager._checkLeagueExists(1), None)
        assert_equals(self.manager._checkLeagueExists("A"), None)
        assert_raises(LeagueError, self.manager._checkLeagueExists, "B")

    def test_agentAuthorized(self):
        self.commands.findEntities.return_value = list()
        assert_false(self.manager._agentAuthorized("Agent Orange", "A"))
        self.commands.findEntities.return_value = [{'Args': 'K;L;M'},]
        assert_true(self.manager._agentAuthorized("K", "A"))
        assert_false(self.manager._agentAuthorized("A", "A"))
        self.commands.findEntities.return_value = [{'Args': 'K;L;M;ALL'},]
        assert_true(self.manager._agentAuthorized("A", "A"))

    @patch('resources.league_manager.League')
    @patch('resources.league_manager.LeagueManager._fetchLeagueCommands')
    @patch('resources.league_manager.LeagueManager._getLeagueSheets')
    @patch('resources.league_manager.LeagueManager._getInterfaceName')
    @patch('resources.league_manager.LeagueManager._fetchThread')
    @patch('resources.league_manager.LeagueManager._checkLeagueExists')
    def test_fetchLeague(self, check, fetch, interface, sheets, commands, lg):
        sheets.return_value = ('games', 'teams', 'templates')
        assert_equals(self.manager.fetchLeague('league'), lg.return_value)
        lg.assert_called_once_with('games', 'teams', 'templates',
            commands.return_value, list(), self.manager.admin, self.manager,
            'league', interface.return_value)
        assert_equals(self.manager.fetchLeagueOrLeagues('league', 'name',
            [{'orders': ['league',]}, {'orders': ['not league',]}]),
            [lg.return_value,])
        lg.assert_called_with('games', 'teams', 'templates',
            commands.return_value, [{'orders': ['league',]},],
            self.manager.admin, self.manager, 'league', interface.return_value)
        self.manager.leagues = ['A', 'B', 'C',]
        assert_equals(self.manager.fetchLeagueOrLeagues('ALL', 'name',
            [{'orders': ['league',]}, {'orders': ['not league',]}]),
            [lg.return_value,] * 3)

    @patch('resources.league_manager.LeagueManager._fetchLeagueCommands')
    def test_fetchCommands(self, fetch):
        fetch.side_effect = ['D', 'E', 'F', 'G']
        self.manager.leagues = ['A', 'B', 'C']
        assert_equals(self.manager.fetchCommands(), {'A': 'D', 'B': 'E',
            'C': 'F', 'ALL': 'G'})

    @patch('resources.league_manager.LeagueManager._agentAuthorized')
    def test_setCommand(self, auth):
        auth.return_value = False
        assert_raises(LeagueError, self.manager.setCommand, 'a', 'l', 'c', 'v')
        auth.return_value = True
        self.manager.setCommand('a', 'l', 'c', 'v')
        self.commands.updateMatchingEntities.assert_called_with({'Command':
            'c', 'League': 'l'}, {'Args': 'v'}, True)

    def test_fetchThread(self):
        self.commands.findEntities.return_value = list()
        assert_equals(self.manager._fetchThread(), "")
        self.commands.findEntities.return_value = [{'Args': 'A'},]
        assert_equals(self.manager._fetchThread(), "A")

    @patch('resources.league_manager.LeagueManager._runLeague')
    @patch('resources.league_manager.LeagueManager._checkAgent')
    def test_runLeague(self, check, run):
        self.manager.runLeague('agent', 'league')
        check.assert_called_once_with('agent', 'league')
        run.assert_called_once_with('league')

    @patch('resources.league_manager.datetime.datetime')
    @patch('resources.league_manager.LeagueManager._setCommand')
    @patch('resources.league_manager.LeagueManager.log')
    @patch('resources.league_manager.LeagueManager.fetchLeague')
    @patch('resources.league_manager.LeagueManager._fetchThreadOrders')
    @patch('resources.league_manager.LeagueManager._retrieveOffset')
    @patch('resources.league_manager.LeagueManager._fetchThread')
    def test_run(self, thread, offset, orders, league, log, setCom, dt):
        offset.return_value = 4903
        thread.return_value = "A"
        orders.return_value = range(30)
        self.manager.admin = None
        self.manager.run()
        thread.assert_not_called()
        self.manager.admin = 1234
        self.manager.leagues = ['A', 'B', 'C']
        self.manager.run()
        assert_equals(league.return_value.run.call_count,
                      len(self.manager.leagues))
        self.commands.updateMatchingEntities.assert_called_with({'Command':
            {'value': 'OFFSET', 'type': 'positive'}}, {'Args': '4933'}, True)
        setCom.assert_called_with('C', 'LATEST RUN',
                                  dt.strftime.return_value)
        thread.return_value = ""
        league.return_value.run.side_effect = Exception("SEGFAULT")
        self.manager.run()
        self.commands.updateMatchingEntities.assert_called_with({'Command':
            {'value': 'OFFSET', 'type': 'positive'}}, {'Args': '4903'}, True)
        log.assert_called_with("Failed to run league C: SEGFAULT",
                               error=True, league='C')
        assert_equals(self.manager.log.call_count, 3)

# run tests
if __name__ == '__main__':
    run_tests()
