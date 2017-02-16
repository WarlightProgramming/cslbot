# order_parser.py
## order parser for forum threads

# imports
from wl_parsers import ForumThreadParser

# main class
class OrderParser(ForumThreadParser):
    ## class to parse orders
    ### takes a threadID (int or string)

    ## parseOrderData
    ### parses a single chunk of text
    @staticmethod
    def parseOrderData(orderText):
        quote, orderData = "&quot;", orderText.split()
        orderInfo, reserved = list(), None
        for order in orderData:
            if reserved is None:
                if (quote == order[:(len(quote))]): # at start of order
                    if (quote != order and quote == order[-(len(quote)):]): 
                        # at start and end
                        order = order.replace(quote, "")
                        orderInfo.append(order)
                    else: # only at start
                        order = order.replace(quote, "")
                        reserved = order
                else: # quote not in order
                    orderInfo.append(order)
            else: # some reserved order string
                if (quote == order[-(len(quote)):]): # at end of order
                    order = " " + order.replace(quote, "")
                    reserved += order
                    orderInfo.append(reserved)
                    reserved = None
                else:
                    order = " " + order
                    reserved += order
        order = dict()
        if (len(orderInfo) <= 0): # nothing
            return order
        order['type'] = orderInfo[0]
        if (len(orderInfo) <= 1): # just a order type
            return order
        order['orders'] = tuple(orderInfo[1:])
        return order

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
    ### returns a list of dictionaries representing orders
    ### each dictionary contains an 'author', 'type', and
    ### (if provided) 'orders' (tuple of order args)
    def parsePost(self, post):
        orders, postText = list(), post['message']
        postAuthor = post['author']['ID']
        cmdMarker, cmdEnd = '<pre class="prettyprint">', '</pre>'
        ignoreOrders = False
        while (cmdEnd in postText and ignoreOrders is False):
            orderText = self._getValueFromBetween(postText,
                                           cmdMarker, cmdEnd)
            if "<br>" in orderText:
                replaceText = orderText.replace("<br>",
                              (cmdEnd + cmdMarker))
                postText = postText.replace(orderText,
                                            replaceText)
                orderText = orderText[:orderText.find("<br>")]
            orderData = self.parseOrderData(orderText)
            if ('type' in orderData and 
                orderData['type'] == "!BOT_IGNORE"):
                ignoreOrders = True
                break
            else:
                orderData['author'] = postAuthor
                orders.append(orderData)
                postText = postText[(postText.find(cmdEnd) +
                                    len(cmdEnd)):]
        return orders

    ## getorders
    ### parses an entire thread (starts after minOffset)
    def getOrders(self, minOffset):
        posts = self.getPosts(minOffset=minOffset)
        orders = list()
        for post in posts:
            orders += self.parsePost(post)
        return orders