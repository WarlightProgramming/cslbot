# utility.py
## helper functions

# imports
import json
import string
from resources.constants import API_CREDS
from wl_api import APIHandler

# isInteger
def isInteger(num):
    """checks whether a string can be converted to an int"""
    for x in num:
        if x not in string.digits: return False
    return len(num)

def WLHandler():
    """creates a Warlight API handler"""
    with open(API_CREDS, 'r*') as credsFile:
        wlCreds = json.load(credsFile)
        wlHandler = APIHandler(wlCreds['E-mail'], wlCreds['APIToken'])
    return wlHandler
