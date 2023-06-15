from .core import Const, Symbol, TradingTimeframe
from .handler import HandlerBase, HandlerCurrencyCom


class Config:
    TA_INTERVAL_5M = "5m"
    TA_INTERVAL_15M = "15m"
    TA_INTERVAL_30M = "30m"
    TA_INTERVAL_1H = "1h"
    TA_INTERVAL_4H = "4h"
    TA_INTERVAL_1D = "1d"
    TA_INTERVAL_1WK = "1w"

    INTERVALS = [{"interval": TA_INTERVAL_5M,  "name": "5 minutes", "order": 10, "importance": Const.IMPORTANCE_LOW},
                 {"interval": TA_INTERVAL_15M, "name": "15 minutes",
                     "order": 20, "importance": Const.IMPORTANCE_LOW},
                 {"interval": TA_INTERVAL_30M, "name": "30 minutes",
                     "order": 30, "importance": Const.IMPORTANCE_MEDIUM},
                 {"interval": TA_INTERVAL_1H, "name": "1 hour",
                     "order": 40, "importance": Const.IMPORTANCE_MEDIUM},
                 {"interval": TA_INTERVAL_4H, "name": "4 hours",
                     "order": 50, "importance": Const.IMPORTANCE_HIGH},
                 {"interval": TA_INTERVAL_1D, "name": "1 day",
                     "order": 60, "importance": Const.IMPORTANCE_HIGH},
                 {"interval": TA_INTERVAL_1WK, "name": "1 week", "order": 70, "importance": Const.IMPORTANCE_HIGH}]

    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__handler = None
            class_.__tradingTimeframes = {}
        return class_._instance

    def getHandler(self) -> HandlerBase:
        if self.__handler == None:
            self.__handler = HandlerCurrencyCom()
        return self.__handler

    def getIntervals(self, importance=None):
        return [x["interval"] for x in self.getIntervalDetails(importance)]

    def getIntervalDetails(self, importance=None):
        intervals = []

        for x in self.INTERVALS:
            if importance and importance != x['importance']:
                continue
            else:
                intervals.append(x)

        return intervals

    def getIndicators(self):

        return [{"code": "CCI", "name": "Commodity Channel Index"}]

    def getStrategies(self):

        strategies = [{"code": "CCI_14_TREND_100", "name": "CCI(14): Indicator value +/- 100"},
                      {"code": "CCI_20_TREND_100",
                          "name": "CCI(20): Indicator value +/- 100"},
                      {"code": "CCI_50_TREND_0", "name": "CCI(50): Indicator value 0"}]

        return strategies

    def getStrategyConfig(self, code):
        strategies = {"CCI_14_TREND_100": {"code": "CCI_14_TREND_100", "name": "CCI(14): Indicator value +/- 100", "length": 14, "value": 100},
                      "CCI_20_TREND_100": {"code": "CCI_20_TREND_100", "name": "CCI(20): Indicator value +/- 100", "length": 20, "value": 100},
                      "CCI_50_TREND_0":   {"code": "CCI_50_TREND_0",   "name": "CCI(50): Indicator value 0",       "length": 50, "value": 0}}

        return strategies[code]

    def getStrategyCodes(self):
        return [item['code'] for item in self.getStrategies()]

    def isTradingOpen(self, tradingTime: str) -> bool:
        if not tradingTime in self.__tradingTimeframes:
            self.__tradingTimeframes[tradingTime] = TradingTimeframe(
                tradingTime)

        oTimeframe = self.__tradingTimeframes[tradingTime]

        return oTimeframe.isTradingOpen()


class SymbolList:
    def checkSymbol(self, code: str) -> bool:
        try:
            self.getSymbol(code)
            return True
        except:
            return False

    def getSymbol(self, code: str) -> Symbol:
        symbols = self.getSymbolsDictionary()
        if code not in symbols:
            raise Exception(f'Symbol with code {code} could not be found')
        symbol = symbols[code]
        return Symbol(code=symbol['code'], name=symbol['name'], status=symbol['status'], tradingTime=symbol['tradingTime'], type=symbol['type'])

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> list:
        symbols = Config().getHandler().getSymbols(
            code=code, name=name, status=status, type=type, isBuffer=isBuffer)
        return symbols

    def getSymbolsDictionary(self, isBuffer: bool = True) -> dict:
        buffer = RuntimeBuffer()
        if not buffer.buffer_symbols_dict or isBuffer == False:
            buffer.buffer_symbols_dict = Config().getHandler(
            ).getSymbolsDictionary(isBuffer=isBuffer)
        return buffer.buffer_symbols_dict

    def getSymbolCodes(self, code: str = None, name: str = None, status: str = None, type: str = None) -> list:
        return [item.code for item in self.getSymbols(code, name, status, type)]


class RuntimeBuffer:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.buffer_oSymbolList = SymbolList()
            class_.buffer_symbols_dict = {}
            class_.buffer_signals = {}
        return class_._instance

buffer = RuntimeBuffer()
config = Config()
