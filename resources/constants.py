# imports
from os.path import realpath, dirname, pardir, normpath, join as pathjoin

# functions
def getOwnDir():
    return dirname(realpath(__file__))

BASE_DIR = normpath(pathjoin(getOwnDir(), pardir))
API_CREDS = pathjoin(BASE_DIR, "credentials", "knyte.json")
GOOGLE_CREDS = pathjoin(BASE_DIR, "credentials", "optimus.json")
TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
DEBUG_KEY = "LhayjQvAeW8Nxs&L5s9fK%yKe+hP9zDSqkZqYbNfsufX+zcdyB!$tZMEE29v?-Px"
GLOBAL_MANAGER = "1Pi7AEy3elEeL_oHhJ92ZsOwzQl0oPcsi2sy3Y8RfgGI"
LATEST_RUN = "LATEST RUN"
OWNER_ID = 3022124041
