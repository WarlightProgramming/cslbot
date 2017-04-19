# utility_tests.py
## tests for helper functions

# imports
from resources.utility import isInteger
from nose.tools import assert_true, assert_false

def test_isInteger():
    assert_false(isInteger(""))
    assert_false(isInteger("403980.490840984"))
    assert_true(isInteger("0"))
    assert_true(isInteger("124590"))
    assert_false(isInteger("Hi I am definitely an integer"))
