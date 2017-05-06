######################
# main.py
# toplevel application
######################

# imports
import os
import json
from flask import Flask, Response, redirect, request
from sheetDB import Credentials
from resources.constants import GOOGLE_CREDS, GLOBAL_MANAGER, OWNER_ID
from resources.league_manager import LeagueManager
from resources.global_manager import GlobalManager
from resources.utility import WLHandler

# google app engine fixes
def fixAppengine():
    software = os.environ.get('SERVER_SOFTWARE')
    if (isinstance(software, str) and (software.startswith('Development')
        or software.startswith('Google App Engine'))):
        from requests_toolbelt.adapters import appengine
        from google.appengine.api import urlfetch
        appengine.monkeypatch()
        urlfetch.set_default_fetch_limit(600)

fixAppengine()

# global variables
app = Flask(__name__)

LEAGUE_PREFIX = '/<string:clusterID>/<string:leagueName>'
CLUSTER_PREFIX = '/<string:clusterID>'
KW_REGISTER = "REGISTER"

# errors
class AuthError(Exception):
    """raised for auth issues"""
    pass

# helper functions
def creds():
    return Credentials(GOOGLE_CREDS)

def globalManager():
    return GlobalManager(creds().getDatabase(GLOBAL_MANAGER,
                                             checkFormat=False))

def buildAuthURL(state=None):
    authURL = "https://www.warlight.net/CLOT/Auth"
    data = [authURL, "?p=", str(OWNER_ID)]
    if state is not None: data += ["&state=", str(state)]
    return ''.join(data)

def fetchLeagues(clusterID, leagueName):
    cluster = fetchCluster(clusterID)
    return cluster.fetchLeagueOrLeagues(leagueName)

def fetchLeague(clusterID, leagueName):
    cluster = fetchCluster(clusterID)
    return cluster.fetchLeague(leagueName)

def fetchCluster(clusterID):
    cluster = creds().getDatabase(clusterID, checkFormat=False)
    return LeagueManager(cluster, globalManager())

def packageDict(data):
    return Response(json.dumps(data), mimetype='application/json')

def packageMessage(message, error=False):
    return packageDict({'error': error, 'message': message})

def buildRoute(prefix, path=""):
    return prefix + path

def leaguePath(path=""):
    return LEAGUE_PREFIX + path

def clusterPath(path=""):
    return CLUSTER_PREFIX + path

def _runVerification(agent, token):
    if not globalManager().verifyAgent(agent, token):
        raise AuthError("Unregistered or banned agent")

def verifyAgent(req):
    keys = req.args.keys()
    if ('agent' not in keys): raise AuthError("Missing agent ID")
    if ('token' not in keys): raise AuthError("Missing agent token")
    _runVerification(req.args['agent'], req.args['token'])

def _noneList(obj):
    return list() if obj is None else obj

def replicate(req, keys=None, lists=None):
    result, keys, lists = dict(), _noneList(keys), _noneList(lists)
    for key in req.args:
        if key in keys: result[key] = json.loads(req.args[key])
        elif key in lists: result[key] = req.args[key].split(',')
        else: result[key] = req.args[key]
    return result

def validateAuth(token, clotpass):
    data = WLHandler().validateToken(token, clotpass)
    return ((data['clotpass'] == clotpass),
            (data['isMember'].lower() == 'true'),
            data['name'].encode('ascii', 'replace'))

def fetchLeagueData(clusterID, leagueName, fetchFn):
    result, leagues = dict(), fetchLeagues(clusterID, leagueName)
    for league in leagues: result[league.name] = fetchFn(league)
    return packageDict(result)

def runLeagueOrder(clusterID, leagueName, req, order, orderFn):
    verifyAgent(req)
    league = fetchLeague(clusterID, leagueName)
    orderFn(league, order)
    return packageDict(league.parent.events)

def runSimpleOrder(clusterID, leagueName, req, orderFn):
    return runLeagueOrder(clusterID, leagueName, req, replicate(req),
        orderFn)

def rule(req, backoff=1):
    return str(req.url_rule).split('/')[-backoff]

def _clusterCommands(clusterID):
    """helper for clusterCommands"""
    return fetchCluster(clusterID).fetchCommands()

def _orderLabel(index):
    """appends index to the string 'order'"""
    return "order" + str(index)

def _getOrderList(req):
    """fetches orders from req"""
    results, index = list(), 0
    while (_orderLabel(index)) in req.args:
        results.append(json.loads(req.args.get(_orderLabel(index))))
        index += 1
    return results

# [START app]
## toplevel
@app.route('/')
@app.route('/address')
def address():
    """fetches the service e-mail associated with the cslbot instance"""
    with open(GOOGLE_CREDS, 'r*') as googleCreds: data = json.load(googleCreds)
    return data['client_email']

@app.route('/agentToken')
def getAgentToken():
    """lets agents/interfaces get their tokens"""
    return redirect(buildAuthURL(KW_REGISTER))

@app.route('/agentSuccess/<string:token>')
def agentSuccess(token):
    return packageDict({'error': False, 'token': token})

@app.route('/adminSuccess/<string:name>')
def adminSuccess(name):
    msg = 'Successful authorization by %s' % (name)
    return packageMessage(msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """handles login from Warlight"""
    args = request.args
    token, clotpass = args.get('token'), args.get('clotpass')
    valid, isMember, name = validateAuth(token, clotpass)
    if not valid: raise AuthError("Invalid clotpass for %s" % (name))
    state = args.get('state')
    if state == KW_REGISTER:
        token = globalManager().updateAgentToken(token)
        return redirect('/agentSuccess/' + token)
    if not isMember:
        failStr = "%s is not a Warlight member" % (name)
        raise AuthError(failStr)
    globalManager().updateAdmin(token, state)
    return redirect('/adminSuccess/' + name)

@app.route('/run')
def run():
    """runs all clusters linked to the cslbot instance"""
    events, clusters = list(), creds().getAllDatabases(checkFormat=False)
    globalMgr = globalManager()
    for cluster in clusters:
        if cluster.sheet.ID == globalMgr.database.sheet.ID: continue
        manager = LeagueManager(cluster, globalMgr)
        manager.run()
        events += manager.events['events']
    return packageDict({'events': events, 'error': False})

## cluster operations
@app.route(clusterPath())
@app.route(clusterPath('/commands'))
def clusterCommands(clusterID):
    """fetches commands for all leagues in the cluster"""
    return packageDict(_clusterCommands(clusterID))

@app.route(clusterPath('/authorize'))
def authorize(clusterID):
    """authorizes a cluster-admin relationship"""
    return redirect(buildAuthURL(clusterID))

@app.route(clusterPath('/run'), methods=['GET', 'POST'])
def runCluster(clusterID):
    """runs all leagues in the cluster"""
    verifyAgent(request)
    cluster = fetchCluster(clusterID)
    cluster.run()
    return packageDict(cluster.events)

## league operations
@app.route(leaguePath())
def showLeague(clusterID, leagueName):
    league = fetchLeague(clusterID, leagueName)
    teams = league.fetchAllTeams()
    games = league.fetchAllGames()
    templates = league.fetchAllTemplates()
    return packageDict({'teams': teams, 'games': games,
        'templates': templates})

@app.route(leaguePath('/commands'))
def leagueCommands(clusterID, leagueName):
    return packageDict(_clusterCommands(clusterID).get(leagueName, dict()))

@app.route(leaguePath('/teams'))
@app.route(leaguePath('/games'))
@app.route(leaguePath('/templates'))
@app.route(leaguePath('/allTeams'))
@app.route(leaguePath('/allGames'))
@app.route(leaguePath('/allTemplates'))
def fetchGroup(clusterID, leagueName):
    urlRule = rule(request).replace('all', '').lower()
    fetchFn = {'teams': lambda lg: lg.fetchAllTeams(),
        'games': lambda lg: lg.fetchAllGames(),
        'templates': lambda lg: lg.fetchAllTemplates()}[urlRule]
    return fetchLeagueData(clusterID, leagueName, fetchFn)

@app.route(leaguePath('/team/<int:ID>'))
@app.route(leaguePath('/game/<int:ID>'))
@app.route(leaguePath('/template/<int:ID>'))
def fetchEntity(clusterID, leagueName, ID):
    league = fetchLeague(clusterID, leagueName)
    value =  {'team': league.fetchTeam, 'game': league.fetchGame,
        'template': league.fetchTemplate}[rule(request, 2)](ID)
    return packageDict(value)

@app.route(leaguePath('/addTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/confirmTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/unconfirmTeam'), methods=['GET', 'POST'])
def runTeamOrder(clusterID, leagueName):
    urlRule = rule(request)
    fetchFn = {'addTeam': lambda lg, order: lg.addTeam(order),
        'confirmTeam': lambda lg, order: lg.confirmTeam(order),
        'unconfirmTeam': lambda lg, order: lg.unconfirmTeam(order)}[urlRule]
    return runLeagueOrder(clusterID, leagueName, request, replicate(request,
        lists=['players']), fetchFn)

@app.route(leaguePath('/setLimit'), methods=['GET', 'POST'])
@app.route(leaguePath('/renameTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/removeTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/quitLeague'), methods=['GET', 'POST'])
@app.route(leaguePath('/addTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/activateTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/deactivateTemplate'), methods=['GET', 'POST'])
def handleSimpleOrder(clusterID, leagueName):
    fetchFn = {'setLimit': lambda lg, o: lg.setLimit(o),
        'renameTeam': lambda lg, o: lg.renameTeam(o),
        'removeTeam': lambda lg, o: lg.removeTeam(o),
        'addTemplate': lambda lg, o: lg.addTemplate(o),
        'activateTemplate': lambda lg, o: lg.activateTemplate(o),
        'deactivateTemplate': lambda lg, o: lg.deactivateTemplate(o),
        'quitLeague': lambda lg, o: lg.quitLeague(o)}[rule(request)]
    return runSimpleOrder(clusterID, leagueName, request, fetchFn)

@app.route(leaguePath('/dropTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/dropTemplates'), methods=['GET', 'POST'])
@app.route(leaguePath('/undropTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/undropTemplates'), methods=['GET', 'POST'])
def dropOrUndrop(clusterID, leagueName):
    if 'undrop' in rule(request):
        fetchFn = lambda lg, order: lg.undropTemplates(order)
    else: fetchFn = lambda lg, order: lg.dropTemplates(order)
    return runLeagueOrder(clusterID, leagueName, request, replicate(request,
        lists=['templates']), fetchFn)

@app.route(leaguePath('/executeOrders'), methods=['GET', 'POST'])
def executeOrders(clusterID, leagueName):
    verifyAgent(request)
    league = fetchLeague(clusterID, leagueName)
    orderList = _getOrderList(request)
    league.executeOrders(request.args.get('agent'), orderList)
    return packageDict(league.parent.events)

@app.route(leaguePath('/run'), methods=['GET', 'POST'])
def runLeague(clusterID, leagueName):
    verifyAgent(request)
    agent = request.args.get('agent')
    cluster = fetchCluster(clusterID)
    cluster.runLeague(agent, leagueName)
    return packageDict(cluster.events)

## error handling
@app.errorhandler(400)
def badRequest():
    return error("Your request had flawed or missing parameters")

@app.errorhandler(500)
def error(e):
    msg = "Error: " + str(e)
    return packageMessage(msg, error=True)
# [END app]
