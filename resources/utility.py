# utility.py
## utility functions

# imports
import string
import random
import copy
import skills

# isInteger
## checks whether a string can be converted to an int
def isInteger(num):
    for x in num:
        if x not in string.digits:
            return False
    return True

# isOdd
## given an integer, returns True if it's odd
def isOdd(num):
    return bool(num % 2) # 1 if odd -> True

# declareConflict
## adds a conflict to teams dict
def declareConflict(teamsDict, team, conflict):
    teamsDict[team]['conflicts'].append(conflict)
    if team != conflict: # symmtery
        teamsDict[conflict]['conflicts'].append(team)

# isConflict
## determines whether a conflict exists
def isConflict(teamsDict, team1, team2):
    return (team2 in teamsDict[team1]['conflicts'] or
            team1 in teamsDict[team2]['conflicts'])

# getNeighbor
## finds nearest non-conflict neighbor
def getNeighbor(team, teamsList, teamsDict):
    for neighbor in teamsList:
        if (neighbor is not team and 
            not isConflict(teamsDict, team, neighbor)):
            return neighbor
    return None

# pair
## given a dictionary of team IDs, their ratings ('rating'), 
## desired # of games ('count'), 
## and teams they can't match up against ('conflicts'),
## returns a list of tuples of resulting matchups (using team IDs)
def pair(teams):
    teams = copy.deepcopy(teams) # will be modified
    pairs, teamList = list(), list()
    for team in teams:
        for x in xrange(teams[team]['count']): teamList.append(team)
    teamList.sort(key = lambda team: teams[team]['count'], reverse=True)
    if isOdd(len(teamList)):
        teamList.remove(teamList[0]) # drop highest count team
    teamList.sort(key = lambda team: teams[team]['rating'], reverse=True)
    for i in xrange(len(teamList)): # exactly len(teamList) attempts
        if len(teamList) == 0: break # exits loop
        team = teamList[0]
        neighbor = getNeighbor(team, teamList, teams)
        if neighbor is not None:
            declareConflict(teams, team, neighbor)
            pairs.append((team, neighbor))
            teamList.remove(neighbor)
        teamList.remove(team)
    return pairs