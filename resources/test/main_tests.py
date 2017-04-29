# main_tests.py
## automated tests for toplevel app

# imports
from unittest import TestCase, main as run_tests
from mock import MagicMock, patch
from nose.tools import assert_equals, assert_false, assert_true
from main import AuthError, WLHandler, buildAuthURL, fetchLeagues,\
    fetchLeague, fetchCluster, packageDict, packageMessage, buildRoute,\
    leaguePath, clusterPath, verifyAgent, replicate, validateAuth,\
    fetchLeagueData, fetchLeagueDatum, runLeagueOrder, runSimpleOrder, rule,\
    creds, globalManager
from resources.constants import OWNER_ID

# tests
## helper functions
@patch('main.Credentials')
def test_creds(gCreds):
    assert_equals(creds(), gCreds.return_value)

@patch('main.creds')
def test_globalManager(credsFn):
    assert_equals(globalManager(),
        credsFn.return_value.getDatabase.return_value)

def test_buildAuthURL():
    expStr = "https://www.warlight.net/CLOT/Auth?p=" + str(OWNER_ID)
    assert_equals(buildAuthURL(), expStr)
    expStr = expStr + "&state=STATE"
    assert_equals(buildAuthURL("STATE"), expStr)

@patch('main.fetchCluster')
def test_fetchLeagues(cluster):
    fakeCluster = MagicMock()
    cluster.return_value = fakeCluster
    fakeCluster.fetchLeagueOrLeagues.return_value = ['A', 'B', 'C']
    assert_equals(fetchLeagues('clusterID', 'ALL'), ['A', 'B', 'C'])
    fakeCluster.fetchLeagueOrLeagues.return_value = ['A']
    assert_equals(fetchLeagues('clusterID', 'A'), ['A'])

@patch('main.fetchCluster')
def test_fetchLeague(cluster):
    assert_equals(fetchLeague('clusterID', 'leagueName'),
        cluster.return_value.fetchLeague.return_value)
    cluster.return_value.fetchLeague.assert_called_once_with('leagueName')

## main app
class TestMainApp(TestCase):

    def setUp(self):
        pass

# run tests
if __name__ == '__main__':
    run_tests()
