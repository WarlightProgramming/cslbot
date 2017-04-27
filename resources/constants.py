# imports
from os.path import normpath

# functions
def getOwnDir():
    baseDir = __file__
    if baseDir[-3:] == "pyc":
         return baseDir[:-(len("constants.pyc"))]
    return baseDir[:-(len("constants.py"))]

BASE_DIR = normpath(getOwnDir() + "..") + "/"
API_CREDS = (BASE_DIR + "resources/fake-credentials/wl_api.json")
GOOGLE_CREDS = (BASE_DIR + "resources/fake-credentials/google_creds.json")
TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
DEBUG_KEY = "DEBUG MODE"
GLOBAL_MANAGER = ""
LATEST_RUN = "LATEST RUN"
