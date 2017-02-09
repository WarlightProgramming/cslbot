# command_parser.py
## command parser for forum threads

# imports
from wl_parsers import ForumThreadParser

# main class
class CommandParser(ForumThreadParser):
    ## class to parse commands
    ### takes a threadID (int or string)

    ## parseCommandData
    ### parses a single chunk of text
    @staticmethod
    def parseCommandData(commandText):
        quote, commandData = "&quot;", commandText.split()
        commandInfo, reserved = list(), None
        for command in commandData:
            if reserved is None:
                if (quote == command[:(len(quote))]): # at start of command
                    if (quote != command and quote == command[-(len(quote)):]): 
                        # at start and end
                        command = command.replace(quote, "")
                        commandInfo.append(command)
                    else: # only at start
                        command = command.replace(quote, "")
                        reserved = command
                else: # quote not in command
                    commandInfo.append(command)
            else: # some reserved command string
                if (quote == command[-(len(quote)):]): # at end of command
                    command = " " + command.replace(quote, "")
                    reserved += command
                    commandInfo.append(reserved)
                    reserved = None
                else:
                    command = " " + command
                    reserved += command
        command = dict()
        if (len(commandInfo) <= 0): # nothing
            return command
        command['type'] = commandInfo[0]
        if (len(commandInfo) <= 1): # just a command type
            return command
        command['orders'] = tuple(commandInfo[1:])
        return command

    ## parsePost
    ### parses an entire post
    def parsePost(self, post):
        commands, postText = list(), post['message']
        postAuthor = post['author']['ID']
        cmdMarker, cmdEnd = '<pre class="prettyprint">', '</pre>'
        ignoreCommands = False
        while (cmdEnd in postText and ignoreCommands is False):
            commandText = self.getValueFromBetween(postText,
                                cmdMarker, cmdEnd)
            if "<br>" in commandText:
                replaceText = commandText.replace("<br>",
                              (cmdEnd + cmdMarker))
            commandData = self.parseCommandData(commandText)
            if ('type' in commandData and 
                commandData['type'] == "!BOT_IGNORE"):
                ignoreCommands = True
                break
            else:
                command = dict()
                command['author'] = postAuthor
                command['command'] = commandData
                commands.append(command)
                postText = postText[(postText.find(cmdEnd) +
                                    len(cmdEnd)):]
        return commands

    ## commands
    ### parses an entire thread (starts after minOffset)
    @property
    def commands(self, minOffset):
        posts = self.getPosts(minOffset=minOffset)
        commands = list()
        for post in posts:
            commands += self.parsePost(post)
        return commands