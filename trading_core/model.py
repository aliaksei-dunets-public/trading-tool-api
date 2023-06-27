from .core import Const, Symbol
from .handler import HandlerBase, HandlerCurrencyCom, StockExchangeHandler


class Config:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__handler = None
            class_.__stock_exchange_handler = None
        return class_._instance

    def get_stock_exchange_id(self) -> str:
        return Const.STOCK_EXCH_CURRENCY_COM

    def get_stock_exchange_handler(self) -> StockExchangeHandler:
        if self.__stock_exchange_handler == None:
            self.__stock_exchange_handler = StockExchangeHandler(
                self.get_stock_exchange_id())
        return self.__stock_exchange_handler

    def is_trading_open(self, interval: str, trading_time: str) -> bool:
        return self.__stock_exchange_handler.is_trading_open(interval, trading_time)

    def get_intervals(self, importances: list = None) -> list:
        return [x[Const.INTERVAL] for x in self.get_intervals_config(importances)]

    def get_intervals_config(self, importances: list = None) -> list:
        intervals = []
        interval_details = self.get_stock_exchange_handler().get_intervals()

        for item in interval_details:
            if importances and item[Const.IMPORTANCE] not in importances:
                continue
            else:
                intervals.append(item)

        return intervals

    def get_indicators(self) -> list:
        return [{Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]

    def get_strategies_config(self):
        strategies = {Const.TA_STRATEGY_CCI_14_TREND_100: {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                                                           Const.NAME: "CCI(14): Indicator value +/- 100",
                                                           Const.LENGTH: 14,
                                                           Const.VALUE: 100},
                      Const.TA_STRATEGY_CCI_20_TREND_100: {Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                                                           Const.NAME: "CCI(20): Indicator value +/- 100",
                                                           Const.LENGTH: 20,
                                                           Const.VALUE: 100},
                      Const.TA_STRATEGY_CCI_50_TREND_0: {Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                                                         Const.NAME: "CCI(50): Indicator value 0",
                                                         Const.LENGTH: 50,
                                                         Const.VALUE: 0}}

        return strategies

    def get_strategy(self, code: str) -> dict:
        strategies = self.get_strategies_config()
        if code in strategies:
            return strategies[code]
        else:
            None

    def get_strategies(self):
        return [{Const.CODE: item[Const.CODE], Const.NAME: item[Const.NAME]} for item in self.get_strategies_config().values()]

    def get_strategy_codes(self):
        return [item for item in self.get_strategies_config().keys()]

    def getHandler(self) -> HandlerBase:
        if self.__handler == None:
            self.__handler = HandlerCurrencyCom()
        return self.__handler


class Symbols:
    def __init__(self, from_buffer: bool = False):
        self.__from_buffer = from_buffer
        self.__symbols = {}

    def __get_symbols(self):
        if not self.__symbols:
            self.__symbols = config.get_stock_exchange_handler().getSymbols(self.__from_buffer)

        return self.__symbols

    def check_symbol(self, code: str) -> bool:
        return code in self.__get_symbols()

    def get_symbol(self, code: str) -> Symbol:
        if self.check_symbol(code):
            return self.__get_symbols()[code]
        else:
            return None

    def get_symbols(self):
        return self.__get_symbols()

    def get_symbol_list(self, code: str, name: str, status: str, type: str) -> list[Symbol]:
        symbols_list = []
        symbols_dict = self.__get_symbols()

        for symbol in symbols_dict.values():
            if code and symbol.code != code:
                continue
            elif name and name.lower() not in symbol.name.lower():
                continue
            elif status and symbol.status != status:
                continue
            elif type and symbol.type != type:
                continue
            else:
                symbols_list.append(symbol)

        return symbols_list


class RuntimeBuffer:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.buffer_symbols_dict = {}
            class_.buffer_signals = {}
        return class_._instance


buffer = RuntimeBuffer()


config = Config()
