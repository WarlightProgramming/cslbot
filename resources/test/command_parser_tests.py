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
    assert_equals(parseCommandData("add_team 2v2 &quot;The Team&quot; 1 0"),
                  {'type': 'add_team',
                   'orders': ('2v2', 'The Team', '1', '0')})
    assert_equals(parseCommandData('&quot;add team&quot; 1v1 A 1'),
                  {'type': 'add team',
                   'orders': ('1v1', 'A', '1')})
    assert_equals(parseCommandData('&quot;add&quot; 1v1 A &quot;2 1&quot;'),
                  {'type': 'add',
                   'orders': ('1v1', 'A', '2 1')})
    assert_equals(parseCommandData('&quot;add a team&quot; 1v1 A'),
                  {'type': 'add a team',
                   'orders': ('1v1', 'A')})
    assert_equals(parseCommandData('add_team'), {'type': 'add_team'})
    assert_equals(parseCommandData('&quot;&quot;'), {'type': ''})
    assert_equals(parseCommandData(''), dict())
    assert_equals(parseCommandData('&quot;add a team&quot;'),
                  {'type': 'add a team'})