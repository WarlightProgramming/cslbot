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

    ## _getValueFromBetween
    ### gets a value in a text field situated between
    ### two known markers
    ###
    ### @PARAMS
    ### 'text' (string): text to extract from
    ### 'before' (string): known marker occurring before desired text
    ### 'after' (string): known marker occurring after desired text
    @staticmethod
    def _getValueFromBetween(text, before, after):
        if before is None: before = ""
        if after is None: after = ""
        beforeLoc = text.find(before) + len(before)
        value = text[beforeLoc:]
        if (after == ""): return value
        afterLoc = value.find(after)
        value = value[:afterLoc]
        return value

    ## parsePost
    ### parses an entire post
    ### returns a list of dictionaries representing commands
    ### each dictionary contains an 'author', 'type', and
    ### (if provided) 'orders' (tuple of command args)
    def parsePost(self, post):
        commands, postText = list(), post['message']
        postAuthor = post['author']['ID']
        cmdMarker, cmdEnd = '<pre class="prettyprint">', '</pre>'
        ignoreCommands = False
        while (cmdEnd in postText and ignoreCommands is False):
            commandText = self._getValueFromBetween(postText,
                                           cmdMarker, cmdEnd)
            if "<br>" in commandText:
                replaceText = commandText.replace("<br>",
                              (cmdEnd + cmdMarker))
                postText = postText.replace(commandText,
                                            replaceText)
                commandText = commandText[:commandText.find("<br>")]
            commandData = self.parseCommandData(commandText)
            if ('type' in commandData and 
                commandData['type'] == "!BOT_IGNORE"):
                ignoreCommands = True
                break
            else:
                commandData['author'] = postAuthor
                commands.append(commandData)
                postText = postText[(postText.find(cmdEnd) +
                                    len(cmdEnd)):]
        return commands

    ## getCommands
    ### parses an entire thread (starts after minOffset)
    def getCommands(self, minOffset):
        posts = self.getPosts(minOffset=minOffset)
        commands = list()
        for post in posts:
            commands += self.parsePost(post)
        return commands