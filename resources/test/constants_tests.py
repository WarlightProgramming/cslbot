# constants_tests.py
## automated tests for constants

# imports
from nose.tools import assert_equals
from resources.constants import getOwnDir, BASE_DIR
from resources import constants

def test_getOwnDir():
    expected = 'PATH/TO/FILE'
    constants.__file__ = "PATH/TO/FILE/constants.pyc"
    assert_equals(getOwnDir()[-len(expected):], expected)
    constants.__file__ = "PATH/TO/FILE/constants.py"
    assert_equals(getOwnDir()[-len(expected):], expected)

def test_values():
    constants.__file__ = "constants.pyc"
    dirName = getOwnDir()
    assert_equals(BASE_DIR[-(len(dirName)):], dirName)
