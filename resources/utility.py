# utility.py
## utility functions

# imports
import string
from munkres import Munkres

# isInteger
def isInteger(num):
    """checks whether a string can be converted to an int"""
    for x in num:
        if x not in string.digits:
            return False
    return True

# isConflict
def isConflict(teamsDict, team1, team2):
    """determines whether a conflict exists"""
    return (team2 in teamsDict[team1]['conflicts'] or
            team1 in teamsDict[team2]['conflicts'])

# matrixReplace
def matrixReplace(matrix, replaceDict):
    """replaces values in a matrix using a dictionary"""
    results = list()
    if not isinstance(matrix[0], list):
        for val in matrix:
            if val in replaceDict:
                results.append(replaceDict[val])
            else:
                results.append(val)
        return results
    else:
        for submatrix in matrix:
            results.append(matrixReplace(submatrix, replaceDict))
        return results

# makeCostMatrix
def makeCostMatrix(teamList, teamsDict, conflictMul=100, selfMul=100,
                   costPow=1.0):
    """given a team list, makes a cost matrix"""
    results = list()
    for team1 in teamList:
        result = list()
        for team2 in teamList:
            if (team1 == team2):
                result.append('self')
            elif (isConflict(teamsDict, team1, team2)):
                result.append('conflict')
            else:
                cost = (abs(teamsDict[team1]['rating'] -
                            teamsDict[team2]['rating']))
                cost = cost ** costPow
                result.append(cost)
        results.append(result)
    maxVal = None
    for vals in results:
        for val in vals:
            if (isinstance(val, int) or isinstance(val, float) and
                (maxVal is None or val > maxVal)):
                maxVal = val
    if maxVal is None:
        # nothing but conflicts
        return None
    results = matrixReplace(results, {'conflict': conflictMul * maxVal,
                                      'self': selfMul * maxVal})
    return results

# pair
def pair(teams):
    """
    given a dictionary of team IDs, their ratings ('rating'),
    desired # of games ('count'),
    and teams they can't match up against ('conflicts'),
    returns a list of tuples of resulting matchups (using team IDs)
    """
    pairs, teamList = list(), list()
    for team in teams:
        teamList += [team,] * teams[team]['count']
    costMatrix = makeCostMatrix(teamList, teams)
    if costMatrix is None:
        return pairs
    indices, used = Munkres().compute(costMatrix), list()
    for row, col in indices:
        team1 = teamList[row]
        team2 = teamList[col]
        if (team1 == team2 or
            row in used or
            col in used):
            continue
        used += [row, col]
        pairs.append((team1, team2))
    return pairs
