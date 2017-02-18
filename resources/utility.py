# utility.py
## utility functions

# imports
import skills
import string
from munkres import Munkres

# isInteger
## checks whether a string can be converted to an int
def isInteger(num):
    for x in num:
        if x not in string.digits:
            return False
    return True

# isConflict
## determines whether a conflict exists
def isConflict(teamsDict, team1, team2):
    return (team2 in teamsDict[team1]['conflicts'] or
            team1 in teamsDict[team2]['conflicts'])

# matrixReplace
## replaces values in a matrix using a dictionary
def matrixReplace(matrix, replaceDict):
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
## given a team list, makes a cost matrix
def makeCostMatrix(teamList, teamsDict, conflictMul=100, selfMul=100,
                   costPow=1.0):
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
## given a dictionary of team IDs, their ratings ('rating'),
## desired # of games ('count'),
## and teams they can't match up against ('conflicts'),
## returns a list of tuples of resulting matchups (using team IDs)
def pair(teams):
    pairs, teamList = list(), list()
    for team in teams:
        teamList += [team,] * teams[team]['count']
    costMatrix = makeCostMatrix(teamList, teams)
    if costMatrix is None:
        return pairs
    indices, used = Munkres().compute(costMatrix), dict()
    for row, col in indices:
        team1 = teamList[row]
        team2 = teamList[col]
        if (team1 == team2 or
            (team1, team2) in pairs or
            (team2, team1) in pairs or
            used[team1] >= teams[team1][count] or
            used[team2] >= teams[team2][count]):
            continue
        used[team1] = (1 if (team1 not in used) else (used[team1] + 1))
        used[team2] = (1 if (team2 not in used) else (used[team2] + 1))
        pairs.append((team1, team2))
    return pairs