class TradingTime:
    pass


class Symbol:
    def __init__(self, code: str, name: str, status: str, type: str, tradingTime: TradingTime):
        self.code = code
        self.name = name
        self.status = status
        self.tradingTime = tradingTime
        self.type = type


class HistoryData:
    def __init__(self, symbol: str, interval: str, limit: int, dataFrame):
        self.__symbol = symbol
        self.__interval = interval
        self.__limit = limit
        self.__dataFrame = dataFrame

    def getSymbol(self):
        return self.__symbol
    
    def getInterval(self):
        return self.__interval
    
    def getLimit(self):
        return self.__limit

    def getDataFrame(self):
        return self.__dataFrame



class ExhangeInfo:
    pass
