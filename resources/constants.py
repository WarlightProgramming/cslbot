def getOwnDir():
    baseDir = __file__
    if baseDir[-3:] == "pyc":
        return baseDir[:-(len("constants.pyc"))]
    return baseDir[:-(len("constants.py"))]

BASE_DIR = (getOwnDir() + "../")
API_CREDS = (BASE_DIR + "credentials/knyte.json")
GOOGLE_CREDS = (BASE_DIR + "credentials.optimus.json")
