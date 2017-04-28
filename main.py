######################
# main.py
# toplevel application
######################

# imports
import json
from wl_api import validateToken
from flask import Flask, Response, redirect, request
from sheetDB import Credentials
from resources.constants import GOOGLE_CREDS, GLOBAL_MANAGER, OWNER_ID
from resources.league_manager import LeagueManager

# global variables
app = Flask(__name__)
creds = Credentials(GOOGLE_CREDS)
globalManager = creds.getDatabase(GLOBAL_MANAGER, checkFormat=False)
LEAGUE_PREFIX = '/<string:clusterID>/<string:leagueName>'
CLUSTER_PREFIX = '/<string:clusterID>'

# errors
class AuthError(Exception):
    """raised for auth issues"""
    pass

# helper functions
def buildAuthURL(state=None):
    authURL = "https://www.WarLight.net/CLOT/Auth"
    data = [authURL, "?p=", str(OWNER_ID)]
    if state is not None: data += ["&state=", str(state)]
    return ''.join(data)

def fetchLeagues(clusterID, leagueName):
    cluster = fetchCluster(clusterID)
    return cluster.fetchLeagueOrLeagues(leagueName)

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

def replicate(request, *keys):
    result = dict()
    for key in request.args:
        if key in keys: result[key] = json.loads(request.args[key])
        else: result[key] = request.args[key]
    return result

# [START app]
## toplevel
@app.route('/address')
def address():
    """fetches the service e-mail associated with the cslbot instance"""
    return creds.client.auth._service_account_email

@app.route('/agentToken')
def getAgentToken():
    """lets agents/interfaces get their tokens"""
    pass

@app.route('/login')
def login():
    """handles login from Warlight"""
    pass

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

@app.route(clusterPath('/run'), methods=['GET', 'POST'])
def runCluster(clusterID):
    """runs all leagues in the cluster"""
    verifyAgent(request)
    with fetchCluster(clusterID) as cluster:
        cluster.run()
        return packageDict(cluster.events)

## league operations
@app.route(leaguePath())
def showLeague(clusterID, leagueName):
    pass

@app.route(leaguePath('/commands'))
def leagueCommands(clusterID, leagueName):
    return packageDict(clusterCommands(clusterID).get(leagueName, dict()))

@app.route(leaguePath('/teams'))
def fetchTeams(clusterID, leagueName):
    pass

@app.route(leaguePath('/games'))
def fetchGames(clusterID, leagueName):
    pass

@app.route(leaguePath('/templates'))
def fetchTemplates(clusterID, leagueName):
    pass

@app.route(leaguePath('/team/<int:teamID>'))
def fetchTeam(clusterID, leagueName, teamID):
    pass

@app.route(leaguePath('/team/<int:gameID>'))
def fetchGame(clusterID, leagueName, gameID):
    pass

@app.route(leaguePath('/team/<int:templateID>'))
def fetchTemplate(clusterID, leagueName, templateID):
    pass

@app.route(leaguePath('/addTeam'))
def addTeam(clusterID, leagueName):
    pass

@app.route(leaguePath('/confirmTeam'))
def confirmTeam(clusterID, leagueName):
    pass

@app.route(leaguePath('/renameTeam'))
def renameTeam(clusterID, leagueName):
    pass

@app.route(leaguePath('/removeTeam'))
def removeTeam(clusterID, leagueName):
    pass

@app.route(leaguePath('/quitLeague'))
def quitLeague(clusterID, leagueName):
    pass

@app.route(leaguePath('/setLimit'))
def setLimit(clusterID, leagueName):
    pass

@app.route(leaguePath('/dropTemplate'))
@app.route(leaguePath('/dropTemplates'))
def dropTemplates(clusterID, leagueName):
    pass

@app.route(leaguePath('/undropTemplate'))
@app.route(leaguePath('/undropTemplates'))
def undropTemplates(clusterID, leagueName):
    pass

@app.route(leaguePath('/addTemplate'))
def addTemplate(clusterID, leagueName):
    pass

@app.route(leaguePath('/activateTemplate'))
def activateTemplate(clusterID, leagueName):
    pass

@app.route(leaguePath('/deactivateTemplate'))
def deactivateTemplate(clusterID, leagueName):
    pass

@app.route(leaguePath('/executeOrders'))
def executeOrders(clusterID, leagueName):
    pass

@app.route(leaguePath('/run'), methods=['GET', 'POST'])
def runLeague(clusterID, leagueName):
    verifyAgent(request)
    agent = request.args.get('agent')
    with fetchCluster(clusterID) as cluster:
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
