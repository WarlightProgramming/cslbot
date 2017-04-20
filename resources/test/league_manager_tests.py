# league_manager_tests.py
## automated tests for the LeagueManager class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import assert_equals, assert_raises, assert_false
from mock import patch, MagicMock
from resources.league_manager import LeagueManager, ThreadError, isInteger

# tests
## LeagueManager class tests
class TestLeagueManager(TestCase):

    @patch('resources.league_manager.LeagueManager._getAdmin')
    @patch('resources.league_manager.LeagueManager._validateAdmin')
    def setUp(self, validateAdmin, getAdmin):
        validateAdmin.return_value = self.admin = 'ADMIN'
        self.database = MagicMock()
        self.commands = MagicMock()
        self.commands.findEntities.return_value = [{LeagueManager.TITLE_ARG:
            '1v1,2v2,3v3'},]
        self.database.fetchTable.return_value = self.commands
        self.manager = LeagueManager(self.database)

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
        parser.return_value.isMember = True
        assert_equals(self.manager._validateAdmin("390089"), 390089)
        parser.return_value.isMember = False
        assert_equals(self.manager._validateAdmin("1293902309"), None)
        log.assert_called_once_with("League admin is not a Member. Quitting.",
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
        parser.getPosts.return_value = [{'author': '192', 'message': ''},
            {'author': '12'}, {'author': '90'}, {'author': '12'},
            {'author': '3'}]
        assert_raises(ThreadError, self.manager._validateThread, parser)
        parser.getPosts.return_value.append({'author': '390'})
        assert_raises(ThreadError, self.manager._validateThread, parser)
        parser.getPosts.return_value[0]['message'] = '!validate_league ID'
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
    @patch('resources.league_manager.PlayerParser')
    def test_fetchLeagueThread(self, parser, log):
        self.commands.findEntities.return_value = list()
        assert_equals(self.manager._fetchLeagueThread(), None)

# run tests
if __name__ == '__main__':
    run_tests()
