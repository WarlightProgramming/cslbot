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

def test_getValueFromBetween():
    text = "abacus"
    before = "a"
    after = "a"
    assert_equals(parser._getValueFromBetween(text, before, after),
                  "b")
    after = "cus"
    assert_equals(parser._getValueFromBetween(text, before, after),
                  "ba")
    before = ""
    assert_equals(parser._getValueFromBetween(text, before, after),
                  "aba")
    after = ""
    assert_equals(parser._getValueFromBetween(text, before, after),
                  "abacus")
    after = "aslkdjlskj"

def test_parsePost():
    parsePost = parser.parsePost
    post = {'message': ('<pre class="prettyprint">add_team 1v1 1'
                        '<br>add_team 3v3 3'
                        '<br>add_team 4v4 4</pre>'
                        '<pre class="prettyprint">command_two</pre>'
                        '<pre class="prettyprint">!BOT_IGNORE<br>'
                        'last_command</pre>'),
            'author': {'ID': 0}}
    parsed = parsePost(post)
    assert_equals(len(parsed), 4)
    assert_equals(parsed[0]['author'], 0)
    assert_equals(parsed[3]['author'], 0)
    assert_equals(parsed[2]['type'], 'add_team')
    assert_equals(parsed[2]['orders'][1], '4')
    assert_equals(parsed[3]['type'], 'command_two')
    post_2 = {'message': '', 'author': {'ID': 1}}
    assert_equals(len(parsePost(post_2)), 0)

@patch('resources.command_parser.CommandParser.parsePost')
@patch('resources.command_parser.CommandParser.getPosts')
def test_getCommnds(getPosts, parsePost):
    getPosts.return_value = [1,2,3,4,5]
    commands = parser.getCommands("minOffset")
    assert_equals(len(commands), 5)
    assert_equals(commands[2], parsePost.return_value)
    parsePost.assert_called_with(5)
    assert_equals(parsePost.call_count, 5)
    getPosts.assert_called_once_with(minOffset="minOffset")