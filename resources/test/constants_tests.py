# constants_tests.py
## automated tests for constants

# imports
from nose.tools import *
from resources.constants import *
from resources import constants

def test_getOwnDir():
    constants.__file__ = "PATH/TO/FILE/constants.pyc"
    assert_equals(getOwnDir(), "PATH/TO/FILE/")
    constants.__file__ = "PATH/TO/FILE/constants.py"
    assert_equals(getOwnDir(), "PATH/TO/FILE/")

def test_values():
    dirName = "cslbot/"
    assert_equals(BASE_DIR[-(len(dirName)):], dirName)
