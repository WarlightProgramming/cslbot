# global_manager_tests.py
## automated tests for the GlobalManager class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import assert_equals, assert_false, assert_true
from resources.global_manager import GlobalManager
from mock import MagicMock, patch
from passlib.hash import pbkdf2_sha256 as token_hash

# tests
## GlobalManager class tests
class TestGlobalManager(TestCase):

    def setUp(self):
        self.database = MagicMock()
        self.manager = GlobalManager(self.database)

    def test_init(self):
        assert_equals(self.manager.database, self.database)
        assert_equals(self.manager.admins,
                      self.database.fetchTable.return_value)
        assert_equals(self.manager.agents,
                      self.database.fetchTable.return_value)

    def test_randStr(self):
        assert_equals(len(self.manager._randStr(490)), 490)

    @patch('resources.global_manager.token_hash.hash')
    @patch('resources.global_manager.GlobalManager._randStr')
    def test_updateAgentToken(self, rand, hashFn):
        hashFn.return_value = "hash"
        rand.return_value = "token"
        assert_equals(self.manager.updateAgentToken(43904309), "token")
        self.manager.agents.updateMatchingEntities.assert_called_with({'ID':
            43904309}, {'TOKEN HASH': 'hash'}, True)

    def test_verifyAgent(self):
        self.manager.agents.findEntities.return_value = list()
        assert_false(self.manager.verifyAgent(1234, "token"))
        self.manager.agents.findEntities.return_value = [{'BANNED': True},]
        assert_false(self.manager.verifyAgent(1234, "token"))
        expHash = token_hash.hash('token')
        self.manager.agents.findEntities.return_value = [{'BANNED': "",
            'ID': 1234, 'TOKEN HASH': expHash},]
        assert_true(self.manager.verifyAgent(1234, "token"))

    def test_updateAdmin(self):
        self.manager.admins.findEntities.return_value = list()
        self.manager.updateAdmin(1234, 5678)
        self.manager.admins.addEntity.assert_called_with({'ID': 1234,
            'AUTHORIZED': '5678'})
        self.manager.admins.findEntities.return_value = [{'ID': 1234,
            'AUTHORIZED': ''},]
        self.manager.updateAdmin(1234, 91011)
        self.manager.admins.updateMatchingEntities.assert_called_with({'ID':
            1234}, {'AUTHORIZED': '91011'})
        self.manager.admins.findEntities.return_value = [{'ID': 1234,
            'AUTHORIZED': '1;2;3;4'},]
        self.manager.updateAdmin(1234, 91011)
        self.manager.admins.updateMatchingEntities.assert_called_with({'ID':
            1234}, {'AUTHORIZED': '1;2;3;4;91011'})

    def test_verifyAdmin(self):
        self.manager.admins.findEntities.return_value = list()
        assert_false(self.manager.verifyAdmin(1234, 5678))
        self.manager.admins.findEntities.return_value = [{'AUTHORIZED':
            '12;23;48'},]
        assert_false(self.manager.verifyAdmin(1234, 5678))
        assert_true(self.manager.verifyAdmin(1234, 12))

# run tests
if __name__ == '__main__':
    run_tests()
