from .core import Symbol
from .handler import HandlerBase, HandlerCurrencyCom


class Config:
    TA_INTERVAL_5M = "5m"
    TA_INTERVAL_15M = "15m"
    TA_INTERVAL_30M = "30m"
    TA_INTERVAL_1H = "1h"
    TA_INTERVAL_4H = "4h"
    TA_INTERVAL_1D = "1d"
    TA_INTERVAL_1WK = "1w"

    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__handler = None
        return class_._instance

    def getHandler(self) -> HandlerBase:
        if self.__handler == None:
            self.__handler = HandlerCurrencyCom()
        return self.__handler

    def getIntervals(self):
        return [self.TA_INTERVAL_5M, self.TA_INTERVAL_15M, self.TA_INTERVAL_30M,
                self.TA_INTERVAL_1H, self.TA_INTERVAL_4H, self.TA_INTERVAL_1D, self.TA_INTERVAL_1WK]

    def getIntervalsDetails(self):

        details = [{"interval": self.TA_INTERVAL_5M,  "name": "5 minutes", "order": 10},
                   {"interval": self.TA_INTERVAL_15M,
                       "name": "15 minutes", "order": 20},
                   {"interval": self.TA_INTERVAL_30M,
                       "name": "30 minutes", "order": 30},
                   {"interval": self.TA_INTERVAL_1H,
                       "name": "1 hour", "order": 40},
                   {"interval": self.TA_INTERVAL_4H,
                       "name": "4 hours", "order": 50},
                   {"interval": self.TA_INTERVAL_1D,
                       "name": "1 day", "order": 60},
                   {"interval": self.TA_INTERVAL_1WK, "name": "1 week", "order": 70}]

        return details


class SymbolList:
    def checkSymbol(self, code: str) -> bool:
        try:
            self.getSymbol(code)
            return True
        except:
            return False

    def getSymbol(self, code: str) -> Symbol:
        symbols = self.getSymbols(code=code)
        if len(symbols) == 0:
            raise Exception('Symbol with code {code} could not be found')
        return symbols[0]

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None) -> list:
        symbols = Config().getHandler().getSymbols(code=code, name=name, status=status, type=type)
        return symbols

    # def getSymbol(self, code):
    #     symbols = self.getSymbols(code=code)

    #     if len(symbols) == 0:
    #         raise Exception(f'Symbol with code {code} can not be found')

    #     return symbols[0]

    # def getSymbols(self, code=None, name=None, status=None, type=None, isBuffer=True) -> list:
    #     return self.getHandler().getExchangeInfo(code, name, status, type, isBuffer)

# class Symbol:
#     def __init__(self, code, name, status, tradingTime, type):
#         self.code = code
#         self.name = name
#         self.status = status
#         self.tradingTime = tradingTime
#         self.type = type

#     def getTradingTime(self):
#         pass

# class Symbols:
#     pass

# class Asset:
#     def __init__(self, symbol):
#         self.__symbol = symbol
#         self.__handler = config.Configuration().getHandler()
#         self.__name = symbol

#     def getSymbol(self):
#         return self.__symbol

#     def getName(self):
#         return config.Configuration().getSymbol(code=self.__symbol).name

#     def getHistoryDataFrame(self, interval, limit):
#         return self.__handler.getHistoryDataFrame(self.__symbol, interval, limit)
