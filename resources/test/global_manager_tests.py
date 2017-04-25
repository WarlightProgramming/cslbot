# global_manager_tests.py
## automated tests for the GlobalManager class

# imports
from unittest import TestCase, main as run_tests
from nose.tools import assert_equals, assert_raises, assert_false, assert_true
from mock import patch, MagicMock
from resources.global_manager import GlobalManager, AuthError

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

# run tests
if __name__ == '__main__':
    run_tests()
