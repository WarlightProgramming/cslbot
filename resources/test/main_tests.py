# main_tests.py
## automated tests for toplevel app

# imports
from werkzeug import ImmutableMultiDict
from unittest import TestCase, main as run_tests
from mock import MagicMock, patch
from nose.tools import assert_equals, assert_false, assert_true, assert_raises
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

@patch('main.globalManager')
@patch('main.LeagueManager')
@patch('main.creds')
def test_fetchCluster(credsFn, manager, globalMgr):
    assert_equals(fetchCluster('ID'), manager.return_value)
    manager.assert_called_once_with(credsFn.return_value.\
        getDatabase.return_value, globalMgr.return_value)
    credsFn.assert_called_once_with()

@patch('main.Response')
def test_packageDict(response):
    assert_equals(packageDict({'some': 'dict', 'with': {'some': 'data'}}),
        response.return_value)
    expJSON = '{"with": {"some": "data"}, "some": "dict"}'
    response.assert_called_once_with(expJSON, mimetype='application/json')
    expJSON = '{"message": "some message", "error": false}'
    assert_equals(packageMessage("some message"), response.return_value)
    response.assert_called_with(expJSON, mimetype='application/json')
    expJSON = '{"message": "some message", "error": true}'
    assert_equals(packageMessage("some message", True), response.return_value)
    response.assert_called_with(expJSON, mimetype='application/json')

def test_buildRoute():
    assert_equals(buildRoute("/prefix"), "/prefix")
    assert_equals(buildRoute("/prefix", "/some/long/winded/path"),
        "/prefix/some/long/winded/path")
    assert_equals(leaguePath(), '/<string:clusterID>/<string:leagueName>')
    assert_equals(clusterPath('/test'), '/<string:clusterID>/test')

@patch('main.globalManager')
def test_verifyAgent(globalMgr):
    mgr = MagicMock()
    mgr.verifyAgent.return_value = False
    globalMgr.return_value = mgr
    req = MagicMock()
    req.args.keys.return_value = dict()
    assert_raises(AuthError, verifyAgent, req)
    req.args.keys.return_value = {'agent': 3022124041}
    assert_raises(AuthError, verifyAgent, req)
    req.args.keys.return_value = {'agent': 3022124041, 'token': 'token'}
    assert_raises(AuthError, verifyAgent, req)
    mgr.verifyAgent.return_value = True
    assert_equals(verifyAgent(req), None)

def test_replicate():
    request = MagicMock()
    request.args = ImmutableMultiDict({'a': 'b'})
    assert_equals(replicate(request), {'a': 'b'})
    request.args = ImmutableMultiDict({'a': 'b', 'c': '{"d": ["e", "f"]}',
        'g': 'h,i,j,k'})
    assert_equals(replicate(request), {'a': 'b', 'c': '{"d": ["e", "f"]}',
        'g': 'h,i,j,k'})
    assert_equals(replicate(request, keys=['c'], lists=['g']),
        {'a': 'b', 'c': {u'd': [u'e', u'f']}, 'g': ['h', 'i', 'j', 'k']})

@patch('main.WLHandler')
def test_validateAuth(handler):
    handler.return_value.validateToken.return_value = {'clotpass': 'notpass',
        'isMember': 'False', 'name': 'bob'}
    assert_equals(validateAuth("token", "notpass"), (True, False, 'bob'))
    handler.return_value.validateToken.return_value = {'clotpass': 'hotpass',
        'isMember': 'True', 'name': 'susan'}
    assert_equals(validateAuth("token", "notpass"), (False, True, 'susan'))

@patch('main.packageDict')
@patch('main.fetchLeague')
@patch('main.fetchLeagues')
def test_fetchLeagueData(leagues, league, package):
    leagueMock = MagicMock()
    leagueMock.name, leagueMock.magic.return_value = "name", "mock"
    leagues.return_value = [leagueMock,] * 3
    assert_equals(fetchLeagueData('ID', 'name', lambda lg: lg.magic()),
        package.return_value)
    package.assert_called_once_with({'name': 'mock'})
    league.return_value = leagueMock
    leagueMock.science.return_value = {"magic": "Clarke's Third Law"}
    assert_equals(fetchLeagueDatum('ID', 'name', 'identity', lambda lg, ID:
        lg.science(ID)), package.return_value)
    package.assert_called_with({'magic': "Clarke's Third Law"})

@patch('main.packageDict')
@patch('main.fetchLeague')
@patch('main.verifyAgent')
def test_runLeagueOrder(verify, fetch, package):
    league = MagicMock()
    fetch.return_value = league
    assert_equals(runLeagueOrder('ID', 'name', 'request', 'some order',
        lambda lg, order: lg.orderFn(order)), package.return_value)
    verify.assert_called_once_with('request')
    fetch.assert_called_once_with('ID', 'name')
    league.orderFn.assert_called_once_with('some order')
    package.assert_called_once_with(league.parent.events)
    request = MagicMock()
    request.args = {'an': 'order'}
    assert_equals(runSimpleOrder('ID', 'name', request, lambda lg, order:
        lg.otherFn(order)), package.return_value)
    assert_equals(verify.call_count, 2)
    verify.assert_called_with(request)
    assert_equals(fetch.call_count, 2)
    fetch.assert_called_with('ID', 'name')
    league.otherFn.assert_called_once_with({'an': 'order'})
    package.assert_called_with(league.parent.events)
    assert_equals(package.call_count, 2)

def test_rule():
    request = MagicMock()
    request.url_rule = 'some/really/complex/url/rule'
    assert_equals(rule(request), 'rule')
    assert_equals(rule(request, 3), 'complex')

## main app
class TestMainApp(TestCase):

    def setUp(self):
        pass

# run tests
if __name__ == '__main__':
    run_tests()
