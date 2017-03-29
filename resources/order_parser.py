# order_parser.py
## order parser for forum threads

# imports
from wl_parsers import ForumThreadParser

# main class
class OrderParser(ForumThreadParser):
    """
    class to parse orders;
    takes a threadID (int or string)
    """

    ## getOrderInfo
    @staticmethod
    def getOrderInfo(orderText):
        orderInfo, quote, space = list(), '&quot;', " "
        regions = orderText.split(quote)
        for i in xrange(len(regions)):
            region = regions[i]
            if (i % 2): # odd indices - in quotes
                orderInfo.append(region)
            else:
                orderInfo += region.split()
        return orderInfo

    ## parseOrderData
    def parseOrderData(self, orderText):
        """parses a single chunk of text"""
        orderInfo, order = self.getOrderInfo(orderText), dict()
        for i in xrange(min(len(orderInfo), 2)):
            if i == 0: order['type'] = orderInfo[i]
            else: order['orders'] = tuple(orderInfo[i:])
        return order

    ## _getValueFromBetween
    @staticmethod
    def _getValueFromBetween(text, before, after):
        """
        gets a value in a text field situated between
        two known markers

        :param text: text to extract from
        :param before: known marker occurring before desired text
        :param after:: known marker occurring after desired text
        """
        if before is None: before = ""
        if after is None: after = ""
        beforeLoc = text.find(before) + len(before)
        value = text[beforeLoc:]
        if (after == ""): return value
        afterLoc = value.find(after)
        value = value[:afterLoc]
        return value

    ## isIgnoreOrder
    @staticmethod
    def isIgnoreOrder(order):
        return ('type' in order and order['type'].lower() == '!bot_ignore')

    ## parsePost
    def parsePost(self, post):
        """
        parses an entire post
        returns a list of dictionaries representing orders
        each dictionary contains an 'author', 'type', and
        (if provided) 'orders' (tuple of order args)
        """
        orders, postText = list(), post['message']
        postAuthor = post['author']['ID']
        cmdMarker, cmdEnd = '<pre class="prettyprint">', '</pre>'
        while (cmdEnd in postText):
            orderText = self._getValueFromBetween(postText, cmdMarker, cmdEnd)
            if "<br>" in orderText:
                replaceText = orderText.replace("<br>", (cmdEnd + cmdMarker))
                postText = postText.replace(orderText, replaceText)
                orderText = orderText[:orderText.find("<br>")]
            orderData = self.parseOrderData(orderText)
            if self.isIgnoreOrder(orderData): break
            else:
                orderData['author'] = postAuthor
                orders.append(orderData)
                postText = postText[(postText.find(cmdEnd) + len(cmdEnd)):]
        return orders

    ## getorders
    def getOrders(self, minOffset):
        """
        parses an entire thread (starts after minOffset)
        """
        posts = self.getPosts(minOffset=minOffset)
        orders = list()
        for post in posts:
            orders += self.parsePost(post)
        return orders
