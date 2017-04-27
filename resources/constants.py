# imports
from os.path import realpath, dirname, pardir, normpath, join as pathjoin

# functions
def getOwnDir():
    return dirname(realpath(__file__))

BASE_DIR = normpath(pathjoin(getOwnDir(), pardir))
API_CREDS = pathjoin(BASE_DIR, "resources", "fake-credentials", "wl_api.json")
GOOGLE_CREDS = pathjoin(BASE_DIR, "resources", "fake-credentials", "google_creds.json")
TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
DEBUG_KEY = "DEBUG MODE"
GLOBAL_MANAGER = ""
LATEST_RUN = "LATEST RUN"
OWNER_ID = 0
