from trading_core.handler import HandlerBase, HandlerCurrencyCom


class Configuration:
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

    def setHandler(self, handler):
        self.__handler = handler

    def getIntervals(self):
        return [self.TA_INTERVAL_5M, self.TA_INTERVAL_15M, self.TA_INTERVAL_30M,
                self.TA_INTERVAL_1H, self.TA_INTERVAL_4H, self.TA_INTERVAL_1D, self.TA_INTERVAL_1WK]

    def getSymbol(self, code):
        symbols = self.getSymbols(code=code)

        if len(symbols) == 0:
            raise Exception(f'Symbol with code {code} can not be found')

        return symbols[0]

    def getSymbols(self, code=None, name=None, status=None, type=None, isBuffer=True) -> list:
        return self.getHandler().getExchangeInfo(code, name, status, type, isBuffer)
