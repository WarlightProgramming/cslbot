# utility_tests.py
## tests for helper functions

# imports
from resources.utility import isInteger, WLHandler
from nose.tools import assert_true, assert_false, assert_equals
from mock import patch

def test_isInteger():
    assert_false(isInteger(""))
    assert_false(isInteger("403980.490840984"))
    assert_true(isInteger("0"))
    assert_true(isInteger("124590"))
    assert_false(isInteger("Hi I am definitely an integer"))

@patch('resources.utility.json.load')
@patch('resources.utility.APIHandler')
def test_WLHandler(handler, load):
    load.return_value = {'E-mail': 'e-mail', 'APIToken': 'token'}
    assert_equals(WLHandler(), handler.return_value)
    handler.assert_called_once_with('e-mail', 'token')
