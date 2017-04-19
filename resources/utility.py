# utility.py
## helper functions

# imports
import string

# isInteger
def isInteger(num):
    """checks whether a string can be converted to an int"""
    for x in num:
        if x not in string.digits: return False
    return len(num)
