######################
# main.py
# toplevel application
######################

# imports
import json
from wl_api import APIHandler
from flask import Flask, Response, redirect, request
from sheetDB import Credentials
from resources.constants import GOOGLE_CREDS, GLOBAL_MANAGER, OWNER_ID,\
    API_CREDS
from resources.league_manager import LeagueManager

# global variables
app = Flask(__name__)
creds = Credentials(GOOGLE_CREDS)
globalManager = creds.getDatabase(GLOBAL_MANAGER, checkFormat=False)

LEAGUE_PREFIX = '/<string:clusterID>/<string:leagueName>'
CLUSTER_PREFIX = '/<string:clusterID>'
KW_REGISTER = "REGISTER"

# errors
class AuthError(Exception):
    """raised for auth issues"""
    pass

# helper functions
def WLHandler():
    with open(API_CREDS) as credsFile:
        wlCreds = json.load(credsFile)
        wlHandler = APIHandler(wlCreds['E-mail'], wlCreds['APIToken'])
    return wlHandler

def buildAuthURL(state=None):
    authURL = "https://www.WarLight.net/CLOT/Auth"
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
    cluster = creds.getDatabase(clusterID, checkFormat=False)
    return LeagueManager(cluster, globalManager)

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
    if not globalManager.verifyAgent(agent, token):
        raise AuthError("Unregistered or banned agent")

def verifyAgent(request):
    keys = request.args.keys()
    if ('agent' not in keys): raise AuthError("Missing agent ID")
    if ('token' not in keys): raise AuthError("Missing agent token")
    _runVerification(request.args['agent'], request.args['token'])

def _noneList(obj):
    return list() if obj is None else obj

def replicate(request, keys=None, lists=None):
    result, keys, lists = dict(), _noneList(keys), _noneList(lists)
    for key in request.args:
        if key in keys: result[key] = json.loads(request.args[key])
        elif key in lists: request[key] = request.args.getlist(key)
        else: result[key] = request.args[key]
    return result

def validateAuth(token, clotpass):
    data = WLHandler().validateToken(token, clotpass)
    return ((data['clotpass'] == clotpass),
            (data['isMember'].lower() == 'true'),
            data['name'])

def fetchLeagueData(clusterID, leagueName, fetchFn):
    result, leagues = dict(), fetchLeagues(clusterID, leagueName)
    for league in leagues: result[league.name] = fetchFn(league)
    return packageDict(result)

def runLeagueOrder(clusterID, leagueName, order, orderFn):
    verifyAgent(request)
    league = fetchLeague(clusterID, leagueName)
    orderFn(league, order)
    return packageDict(league.parent.events)

def runSimpleOrder(clusterID, leagueName, request, orderFn):
    return runLeagueOrder(clusterID, leagueName, replicate(request),
        orderFn)

# [START app]
## toplevel
@app.route('/address')
def address():
    """fetches the service e-mail associated with the cslbot instance"""
    return creds.client.auth._service_account_email

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
    if not valid: raise AuthError("Invalid clotpass")
    state = args.get('state')
    if state == KW_REGISTER:
        token = globalManager.updateAgentToken(token)
        return redirect('/agentSuccess/' + token)
    if not isMember:
        failStr = "%s is not a Warlight member" % (name)
        raise AuthError(failStr)
    globalManager.updateAdmin(token, state)
    return redirect('/adminSuccess/' + name)

@app.route('/run')
def run():
    """runs all clusters linked to the cslbot instance"""
    events, clusters = list(), creds.getAllDatabases(checkFormat=False)
    for cluster in clusters:
        if cluster.sheet.ID == globalManager.sheet.ID: continue
        manager = LeagueManager(cluster, globalManager)
        manager.run()
        events += manager.events['events']
    return packageDict({'events': events, 'error': False})

## cluster operations
@app.route(clusterPath())
@app.route(clusterPath('/commands'))
def clusterCommands(clusterID):
    """fetches commands for all leagues in the cluster"""
    return packageDict(fetchCluster(clusterID).fetchCommands())

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
    teams = fetchTeams(clusterID, leagueName)
    games = fetchGames(clusterID, leagueName)
    templates = fetchTemplates(clusterID, leagueName)
    return packageDict({'teams': teams, 'games': games,
        'templates': templates})

@app.route(leaguePath('/commands'))
def leagueCommands(clusterID, leagueName):
    return packageDict(clusterCommands(clusterID).get(leagueName, dict()))

@app.route(leaguePath('/teams'))
def fetchTeams(clusterID, leagueName):
    return fetchLeagueData(clusterID, leagueName,
        fetchFn=lambda lg: lg.fetchAllTeams())

@app.route(leaguePath('/games'))
def fetchGames(clusterID, leagueName):
    return fetchLeagueData(clusterID, leagueName,
        fetchFn=lambda lg: lg.fetchAllGames())

@app.route(leaguePath('/templates'))
def fetchTemplates(clusterID, leagueName):
    return fetchLeagueData(clusterID, leagueName,
        fetchFn=lambda lg: lg.fetchAllTemplates())

@app.route(leaguePath('/team/<int:teamID>'))
def fetchTeam(clusterID, leagueName, teamID):
    return packageDict(fetchLeague(clusterID, leagueName).fetchTeam(teamID))

@app.route(leaguePath('/team/<int:gameID>'))
def fetchGame(clusterID, leagueName, gameID):
    return packageDict(fetchLeague(clusterID, leagueName).fetchGame(gameID))

@app.route(leaguePath('/team/<int:templateID>'))
def fetchTemplate(clusterID, leagueName, templateID):
    return packageDict(fetchLeague(clusterID,
        leagueName).fetchTemplate(templateID))

@app.route(leaguePath('/addTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/confirmTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/unconfirmTeam'), methods=['GET', 'POST'])
def runTeamOrder(clusterID, leagueName):
    rule = request.url_rule
    fetchFn = {'/addTeam': lambda lg, order: lg.addteam(order),
        '/confirmTeam': lambda lg, order: lg.confirmTeam(order),
        '/unconfirmTeam': lambda lg, order: lg.unconfirmTeam(order)}[rule]
    return runLeagueOrder(clusterID, leagueName, replicate(request,
        lists=['players']), fetchFn)

@app.route(leaguePath('/setLimit'), methods=['GET', 'POST'])
@app.route(leaguePath('/renameTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/removeTeam'), methods=['GET', 'POST'])
@app.route(leaguePath('/quitLeague'), methods=['GET', 'POST'])
@app.route(leaguePath('/addTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/activateTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/deactivateTemplate'), methods=['GET', 'POST'])
def handleSimpleOrder(clusterID, leagueName):
    fetchFn = {'/setLimit': lambda lg, o: lg.setLimit(o),
        '/renameTeam': lambda lg, o: lg.renameTeam(o),
        '/removeTeam': lambda lg, o: lg.removeTeam(o),
        '/addTemplate': lambda lg, o: lg.addTemplate(o),
        '/activateTemplate': lambda lg, o: lg.activateTemplate(o),
        '/deactivateTemplate': lambda lg, o: lg.deactivateTemplate(o),
        '/quitLeague': lambda lg, o: lg.quitLeague(o)}[request.url_rule]
    return runSimpleOrder(clusterID, leagueName, request, fetchFn)

@app.route(leaguePath('/dropTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/dropTemplates'), methods=['GET', 'POST'])
@app.route(leaguePath('/undropTemplate'), methods=['GET', 'POST'])
@app.route(leaguePath('/undropTemplates'), methods=['GET', 'POST'])
def dropOrUndrop(clusterID, leagueName):
    if 'undrop' in request.url_rule:
        fetchFn = lambda lg, order: lg.undropTemplates(order)
    else: fetchFn = lambda lg, order: lg.dropTemplates(order)
    return runLeagueOrder(clusterID, leagueName, replicate(request,
        lists=['templates']), fetchFn)

@app.route(leaguePath('/executeOrders'), methods=['GET', 'POST'])
def executeOrders(clusterID, leagueName):
    verifyAgent(request)
    league = fetchLeague(clusterID, leagueName)
    orderList = [json.loads(order) for order in request.args.getlist('orders')]
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
