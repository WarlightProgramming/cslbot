######################
# cslbot.py
# toplevel application
######################

# imports
import os
import json
from flask import Flask, Response, redirect, request
from sheetDB import Credentials
from resources.constants import GOOGLE_CREDS, GLOBAL_MANAGER
from resources.league_manager import LeagueManager

# global variables
app = Flask(__name__)
creds = Credentials(GOOGLE_CREDS)
globalManager = creds.getDatabase(GLOBAL_MANAGER, checkFormat=False)

# helper functions
def _fetchLeagues(clusterID, leagueName):
    cluster = _fetchCluster(clusterID)
    return cluster.fetchLeagueOrLeagues(leagueName)

def _fetchCluster(clusterID):
    cluster = creds.getDatabase(clusterID, checkFormat=False)
    return LeagueManager(cluster)

def _packageDict(data):
    return Response(json.dumps(data), mimetype='application/json')

def _packageMessage(message, error=False):
    return _packageDict({'error': error, 'message': message})

# [START app]
@app.route('/address')
def address():
    return creds.client.auth._service_account_email

@app.route('/run')
def run():
    events, clusters = list(), creds.getAllDatabases(checkFormat=False)
    for cluster in clusters:
        if cluster.sheet.ID == globalManager.sheet.ID: continue
        manager = LeagueManager(cluster)
        manager.run()
        events += manager.events['events']
    return _packageDict({'events': events, 'error': False})

@app.errorhandler(500):
def error(e):
    msg = "Error: " + str(e)
    return _packageMessage(msg, error=True)
# [END app]
