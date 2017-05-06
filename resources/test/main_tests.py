# main_tests.py
## automated tests for toplevel app

# imports
import main
import json
from werkzeug import ImmutableMultiDict
from unittest import TestCase, main as run_tests
from mock import MagicMock, patch
from nose.tools import assert_equals, assert_raises, assert_false
from main import AuthError, buildAuthURL, fetchLeagues,\
    fetchLeague, fetchCluster, packageDict, packageMessage, buildRoute,\
    leaguePath, clusterPath, verifyAgent, replicate, validateAuth,\
    fetchLeagueData, runLeagueOrder, runSimpleOrder, rule,\
    creds, globalManager, badRequest, fixAppengine
from resources.constants import OWNER_ID

# tests
## helper functions
@patch('__builtin__.__import__')
@patch('main.os')
def test_fixAppengine(osMod, importFn):
    osMod.environ = dict()
    fixAppengine()
    assert_false(hasattr(main, 'appengine'))
    osMod.environ['SERVER_SOFTWARE'] = 'Google App/4.2.0'
    fixAppengine()
    assert_false(hasattr(main, 'appengine'))
    osMod.environ['SERVER_SOFTWARE'] = 'Google App Engine/4.2.0'
    fixAppengine()
    assert_equals(importFn.call_count, 2)

@patch('main.Credentials')
def test_creds(gCreds):
    assert_equals(creds(), gCreds.return_value)

@patch('main.GlobalManager')
@patch('main.creds')
def test_globalManager(credsFn, managerFn):
    assert_equals(globalManager(), managerFn.return_value)
    managerFn.assert_called_once_with(
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
        main.app.testing = True
        self.app = main.app.test_client()

    @patch('main.json.load')
    def test_address(self, load):
        load.return_value = {'client_email': 'email'}
        r = self.app.get('/address')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, 'email')
        r = self.app.get('/')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, 'email')

    @patch('main.redirect')
    def test_getAgentToken(self, redir):
        redir.return_value = "redir"
        r = self.app.get('/agentToken')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, redir.return_value)
        exp = ("https://www.warlight.net/CLOT/Auth?p=" + str(OWNER_ID) +
               "&state=REGISTER")
        redir.assert_called_once_with(exp)

    @patch('main.packageDict')
    def test_success(self, package):
        package.return_value = "retval"
        r = self.app.get('/agentSuccess/token')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, package.return_value)
        package.assert_called_once_with({'error': False, 'token': 'token'})
        r = self.app.get('/adminSuccess/name')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, package.return_value)
        package.assert_called_with({'error': False, 'message':
            'Successful authorization by name'})

    @patch('main.validateAuth')
    @patch('main.globalManager')
    def test_login(self, manager, validate):
        manager.return_value.updateAgentToken.return_value = 'token'
        validate.return_value = (False, False, 'Bob')
        assert_raises(AuthError, self.app.post, '/login',
            query_string={'token': '1234', 'clotpass': '5678',
                          'state': 'REGISTER'})
        validate.return_value = (True, False, 'Bob')
        assert_raises(AuthError, self.app.post, '/login',
            query_string={'token': '1234', 'clotpass': '7890',
                          'state': 'MINNESOTA'})
        validate.return_value = (True, True, 'Bob')
        r = self.app.get('/login?state=REGISTER&token=1234&clotpass=7890')
        assert_equals(r.status_code, 302)
        r = self.app.get('/login?state=MINNESOTA&token=1234&clotpass=7890')
        assert_equals(r.status_code, 302)

    @patch('main.creds')
    @patch('main.globalManager')
    @patch('main.LeagueManager')
    def test_run(self, lgMan, glMan, credsFn):
        creds = MagicMock()
        cluster1, cluster2, cluster3 = MagicMock(), MagicMock(), MagicMock()
        cluster1.sheet.ID = 3
        cluster2.sheet.ID = 4
        cluster3.sheet.ID = 7
        creds.getAllDatabases.return_value = [cluster1, cluster2, cluster3]
        credsFn.return_value = creds
        lgMan.return_value.events = {'events': [1, 2, 3]}
        glMan.return_value.database.sheet.ID = 4
        r = self.app.get('/run')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'events': [1, 2, 3, 1, 2, 3],
            'error': False}))

    @patch('main.fetchCluster')
    def test_clusterCommands(self, fetchFn):
        fetchFn.return_value.fetchCommands.return_value = {"commands": "data"}
        r = self.app.get('/clusterID/commands')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'commands': 'data'}))
        fetchFn.assert_called_once_with('clusterID')

    def test_authorize(self):
        r = self.app.get('/someOtherClusterID/authorize')
        assert_equals(r.status_code, 302)

    @patch('main.fetchCluster')
    @patch('main.verifyAgent')
    def test_runCluster(self, verify, fetch):
        fetch.return_value.events = {'error': False, 'events': ['a', 'bcd']}
        r = self.app.post('/yetAnotherClusterID/run', query_string={'agent':
            'agent', 'token': 'token'})
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'error': False,
            'events': ['a', 'bcd']}))
        fetch.assert_called_once_with('yetAnotherClusterID')
        assert_equals(verify.call_count, 1)

    @patch('main.fetchLeague')
    def test_showLeague(self, fetchFn):
        league = MagicMock()
        league.fetchAllTeams.return_value = ['t', 'ea', 'ms']
        league.fetchAllGames.return_value = ['g', 'a', 'm', 'e', 's']
        league.fetchAllTemplates.return_value = ['t', 'e', 'mp', 's']
        fetchFn.return_value = league
        r = self.app.get('/clusterID/leagueName')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'teams': ['t', 'ea', 'ms'],
            'games': ['g', 'a', 'm', 'e', 's'], 'templates':
            ['t', 'e', 'mp', 's']}))

    @patch('main.fetchCluster')
    def test_leagueCommands(self, fetchFn):
        fetchFn.return_value.fetchCommands.return_value = {"lg": {"cmd": "v"}}
        r = self.app.get('/clusterID/lg/commands')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'cmd': 'v'}))
        r = self.app.get('/clusterID/league/commands')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({}))

    @patch('main.fetchLeagues')
    def test_fetchGroup(self, fetchFn):
        league1, league2, league3 = MagicMock(), MagicMock(), MagicMock()
        league1.name, league2.name, league3.name = "one", "two", "three"
        league1.fetchAllTeams.return_value = "all one teams"
        league1.fetchAllGames.return_value = "all one games"
        league1.fetchAllTemplates.return_value = "all one templates"
        league2.fetchAllTeams.return_value = "all two teams"
        league2.fetchAllGames.return_value = "all two games"
        league2.fetchAllTemplates.return_value = "all two templates"
        league3.fetchAllTeams.return_value = "all three teams"
        league3.fetchAllGames.return_value = "all three games"
        league3.fetchAllTemplates.return_value = "all three templates"
        fetchFn.return_value = [league1, league2, league3]
        r = self.app.get('/clusterID/ALL/games')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'one': 'all one games',
            'two': 'all two games', 'three': 'all three games'}))
        r = self.app.get('/clusterID/ALL/allTemplates')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'one': 'all one templates',
            'two': 'all two templates', 'three': 'all three templates'}))
        fetchFn.return_value = [league1]
        r = self.app.get('/clusterID/one/teams')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'one': 'all one teams'}))

    @patch('main.fetchLeague')
    def test_fetchEntity(self, fetchFn):
        league = MagicMock()
        league.fetchTeam.return_value = {'team': 'one'}
        league.fetchGame.return_value = {'game': 'one'}
        league.fetchTemplate.return_value = {'template': 'one'}
        fetchFn.return_value = league
        r = self.app.get('/clusterID/leagueID/team/43')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'team': 'one'}))
        r = self.app.get('/clusterID/leagueID/template/48')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'template': 'one'}))
        r = self.app.get('/clusterID/leagueID/game/434903')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps({'game': 'one'}))

    @patch('main.verifyAgent')
    @patch('main.fetchLeague')
    def test_orders(self, fetchFn, verifyAgent):
        league = MagicMock()
        league.parent.events = {'error': False, 'events': 'data'}
        fetchFn.return_value = league
        r = self.app.get('/clusterID/leagueName/addTeam?players=1,2,3')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        league.addTeam.assert_called_once_with({'players': ['1','2','3']})
        r = self.app.get('/clusterID/leagueName/confirmTeam?players=1,2,3')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        league.confirmTeam.assert_called_once_with({'players': ['1','2','3']})
        r = self.app.get('/clusterID/leagueName/unconfirmTeam?players=1,3')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        league.unconfirmTeam.assert_called_once_with({'players': ['1','3']})
        r = self.app.get('/clusterID/leagueName/setLimit')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        league.setLimit.assert_called_once_with(dict())
        r = self.app.get('/clusterID/leagueName/renameTeam')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.renameTeam.call_count, 1)
        r = self.app.get('/clusterID/leagueName/removeTeam')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.removeTeam.call_count, 1)
        r = self.app.get('/clusterID/leagueName/addTemplate')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.addTemplate.call_count, 1)
        r = self.app.get('/clusterID/leagueName/activateTemplate')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.activateTemplate.call_count, 1)
        r = self.app.get('/clusterID/leagueName/deactivateTemplate')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.deactivateTemplate.call_count, 1)
        r = self.app.get('/clusterID/leagueName/quitLeague')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.quitLeague.call_count, 1)
        r = self.app.get('/clusterID/leagueName/undropTemplates')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        assert_equals(league.undropTemplates.call_count, 1)
        r = self.app.post('/clusterID/leagueName/dropTemplates',
            query_string={'templates': '1,3,5', 'data': 'value'})
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(league.parent.events))
        league.dropTemplates.assert_called_once_with({'templates': [u'1', u'3',
            u'5'], 'data': u'value'})

    @patch('main.fetchLeague')
    @patch('main.verifyAgent')
    def test_executeOrders(self, verify, fetch):
        fetch.return_value.parent.events = dict()
        r = self.app.get('/clusterID/lg/executeOrders',
            query_string={'agent': 'token', 'order0': '{"this": "is"}',
            'order1': '{"a": []}', 'order2': '{"of": "orders"}'})
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(dict()))
        fetch.return_value.executeOrders.assert_called_once_with('token',
            [{u'this': u'is'}, {u'a': list()}, {u'of': u'orders'}])

    @patch('main.fetchCluster')
    @patch('main.verifyAgent')
    def test_runLeague(self, verify, fetch):
        fetch.return_value.events = {'error': True, 'events': [dict(), {1: 2}]}
        r = self.app.get('/clusterID/leagueIDofsomesort/run?agent=4903')
        assert_equals(r.status_code, 200)
        assert_equals(r.data, json.dumps(fetch.return_value.events))
        fetch.assert_called_once_with('clusterID')
        fetch.return_value.runLeague.assert_called_once_with('4903',
            'leagueIDofsomesort')

    def test_errors(self):
        exp = "Error: Your request had flawed or missing parameters"
        assert_equals(badRequest().data, json.dumps({'message': exp,
            'error': True}))

# run tests
if __name__ == '__main__':
    run_tests()
