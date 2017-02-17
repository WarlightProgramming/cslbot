# utility.py
## utility functions

# imports
import string

def isInteger(num):
    for x in num:
        if x not in string.digits:
            return False
    return True