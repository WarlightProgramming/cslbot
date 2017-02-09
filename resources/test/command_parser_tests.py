# command_parser_tests.py
## automated tests for the CommandParser class

# imports
from nose.tools import *
from mock import patch, MagicMock
from resources.command_parser import *

# main class tests
def test_commandParser():
    cp = CommandParser("threadID")
    assert_equals(cp.ID, "threadID")
    return cp

parser = test_commandParser() # global test parser

def test_parseCommandData():
    parseCommandData = parser.parseCommandData
    assert_equals(parseCommandData("add_team 1v1 Harambes 49040590"),
                  {'type': 'add_team',
                   'orders': ('1v1', 'Harambes', '49040590')})