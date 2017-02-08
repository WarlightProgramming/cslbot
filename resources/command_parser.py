# command_parser.py
## command parser for forum threads

# imports
from wl_parsers import ForumThreadParser

# main class
class CommandParser(ForumThreadParser):

    ## parseCommandData
    ### parses a single chunk of text
    @staticmethod
    def parseCommandData(commandText):
        quote, commandData, commandInfo, reserved = ("&quot;", commandText.split(), 
                                                     list(), None)
        for command in commandData:
            if reserved is None:
                if (quote == command[:(len(quote))]): # at start of command
                    if (quote != command and quote == command[-(len(quote)):]): # at start and end
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
        if (len(commandInfo) < 2):
            return command
        command["type"] = commandInfo[0]
        command["orders"] = commandInfo[1:]
        return command

    ## parsePost
    ### parses an entire post
    def parsePost(self, post):
        commands = list()
        postText = post[3]
        postAuthor = post[1][0]
        cmdMarker = '<pre class="prettyprint">'
        cmdEnd = '</pre>'
        ignoreCommands = False
        while (cmdEnd in postText and ignoreCommands == False):
            commandText = self.getValueFromBetween(postText,
                               cmdMarker, cmdEnd)
            if "<br>" in commandText:
                replaceText = commandText.replace("<br>",
                              (cmdEnd + cmdMarker))
            commandData = self.parseCommandData(commandText)
            if ('type' in commandData and commandData['type'] == "!BOT_IGNORE"):
                ignoreCommands = True
                break
            else:
                command = list()
                command.append(postAuthor)
                command.append(commandData)
                commands.append(tuple(command))
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