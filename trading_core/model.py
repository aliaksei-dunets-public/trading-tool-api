from .constants import Const
from .core import config, Symbol
from .handler import StockExchangeHandler


class Model:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__handler = None
        return class_._instance

    def get_handler(self) -> StockExchangeHandler:
        if self.__handler == None:
            self.__handler = StockExchangeHandler()
        return self.__handler

    def get_intervals(self, importances: list = None) -> list:
        return [x[Const.INTERVAL] for x in self.get_intervals_config(importances)]

    def get_intervals_config(self, importances: list = None) -> list:
        intervals = []
        interval_details = self.get_handler().get_intervals()

        for item in interval_details:
            if importances and item[Const.IMPORTANCE] not in importances:
                continue
            else:
                intervals.append(item)

        return intervals

    def get_indicators_config(self) -> list:
        return config.get_indicators_config()

    def get_strategies_config(self):
        return config.get_strategies_config()

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

    def get_sorted_strategy_codes(self, strategies: list = None, desc: bool = True) -> list:
        strategies_config = []

        if not strategies:
            for strategy in self.get_strategies_config().values():
                strategies_config.append(strategy)
        else:
            for code in strategies:
                strategies_config.append(self.get_strategy(code))

        if desc:
            sorted_strategies = sorted(
                strategies_config, key=lambda x: -x[Const.LENGTH])
        else:
            sorted_strategies = sorted(
                strategies_config, key=lambda x: x[Const.LENGTH])

        return [item[Const.CODE] for item in sorted_strategies]


class Symbols:
    def __init__(self, from_buffer: bool = False):
        self.__from_buffer = from_buffer
        self.__symbols = {}

    def __get_symbols(self):
        if not self.__symbols:
            self.__symbols = model.get_handler().getSymbols(self.__from_buffer)

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


model = Model()
