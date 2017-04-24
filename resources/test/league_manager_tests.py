# league_manager_tests.py
## automated tests for the LeagueManager class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import assert_equals, assert_raises, assert_false, assert_true
from mock import patch, MagicMock
from resources.league_manager import LeagueManager, ThreadError, isInteger

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
            '1v1,2v2,3v3'},]
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
            'a,b,c,d'}, {LeagueManager.TITLE_ARG: 'de,fg'}]
        assert_equals(self.manager._fetchLeagueNames(), ['a', 'b', 'c', 'd'])
        self.commands.findEntities.return_value = list()
        assert_equals(self.manager._fetchLeagueNames(), list())

    @patch('resources.league_manager.LeagueManager.log')
    @patch('resources.league_manager.PlayerParser')
    def test_validateAdmin(self, parser, log):
        verified = self.globalManager.adminVerified
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
        posts = [{'author': '12'}, {'author': '13'}, {'author': '14'},
                 {'author': '15'}, {'author': '21'}, {'author': '13'}]
        assert_equals(self.manager._getUniqueAuthors(posts),
                      {'12', '13', '14', '15', '21'})
        assert_equals(self.manager._getUniqueAuthors(list()), set())

    def test_validateThread(self):
        parser = MagicMock()
        self.manager.ABUSE_THRESHOLD = 5
        self.database.sheet.ID = "ID"
        parser.getPosts.return_value = [{'author': '192', 'message': '',
            'title': 'Some title that does not contain [CSL] at the start'},
            {'author': '12'}, {'author': '90'}, {'author': '12'},
            {'author': '3'}]
        assert_raises(ThreadError, self.manager._validateThread, parser)
        parser.getPosts.return_value.append({'author': '390'})
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
            '!validate_league ID', 'title': '[CSL] Some Thread', 'author': 0},
            {'author': 1}, {'author': 2}, {'author': 3}, {'author': 2}]
        self.manager._fetchLeagueThread()
        failStr = "Thread must have posts by at least 5 unique authors"
        log.assert_called_once_with(failStr, error=True)
        parser.return_value.getPosts.return_value.append({'author': 4})
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
            'League': 'We'}], 'Human': [{'Args': 'Or', 'League': 'Are'}],
            'We': [{'Args': 'Dancer', 'League': 'ALL'}], 'And': [{'Args':
            '', 'League': 'We'}, {'Args': 'Are,We,Human', 'League': 'ALL'}],
            'WE': [{'Args': 'Human', 'League': 'Are'}]}
        assert_equals(self.manager._fetchLeagueCommands('We'),
            {'CMD': 'ARE', 'WE': 'DANCER', 'AND': ''})
        assert_equals(self.manager._fetchLeagueCommands('Are'),
            {'HUMAN': 'OR', 'WE': 'HUMAN', 'AND': ['ARE','WE','HUMAN']})

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

# run tests
if __name__ == '__main__':
    run_tests()
