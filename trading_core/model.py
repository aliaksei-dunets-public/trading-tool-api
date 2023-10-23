import copy

from .constants import Const
from .core import config, Symbol, SimulateOptions
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

    def get_interval_config(self, interval: str) -> dict:
        intervals = self.get_intervals_config()

        for row in intervals:
            if row[Const.INTERVAL] == interval:
                return row

        return None

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

    def get_symbol_list(self, code: str = None, name: str = None, status: str = None, type: str = None) -> list[Symbol]:
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

    def get_symbol_list_json(self, code: str = None, name: str = None, status: str = None, type: str = None) -> list[Symbol]:
        symbols = self.get_symbol_list(
            code=code, name=name, status=status, type=type)
        return [item.get_symbol_json() for item in symbols]

    def get_symbol_codes(self, name: str = None, status: str = None, type: str = None) -> list:
        symbols = self.get_symbol_list(name=name, status=status, type=type)
        return [item.code for item in symbols]


class ParamBase:
    @staticmethod
    def copy_instance(obj):
        return copy.deepcopy(obj)


class ParamSymbol(ParamBase):
    def __init__(self, symbol: str) -> None:

        self.__symbol_config = Symbols(from_buffer=True).get_symbol(symbol)

        if not self.__symbol_config:
            raise Exception(f"PARAM: Symbol: {symbol} doesn't exist")

        self.__symbol = symbol

    @property
    def symbol(self) -> str:
        return self.__symbol

    def get_symbol_config(self) -> Symbol:
        return self.__symbol_config


class ParamInterval(ParamBase):
    def __init__(self, interval: str) -> None:

        self.__interval_config = Model().get_interval_config(interval)

        if not self.__interval_config:
            raise Exception(f"PARAM: Interval: {interval} doesn't exist")

        self.__interval = interval

    @property
    def interval(self) -> str:
        return self.__interval

    def get_interval_config(self) -> dict:
        return self.__interval_config


class ParamStrategy(ParamBase):
    def __init__(self, strategy: str) -> None:

        self.__strategy_config = Model().get_strategy(strategy)

        if not self.__strategy_config:
            raise Exception(f"PARAM: Strategy: {strategy} doesn't exist")

        self.__strategy = strategy

    @property
    def strategy(self) -> str:
        return self.__strategy

    def get_strategy_config(self) -> dict:
        return self.__strategy_config


class ParamLimit(ParamBase):
    def __init__(self, limit: int) -> None:
        if limit < 0:
            raise Exception(f"PARAM: Limit: {limit} is incorrect value")

        self.__limit = limit

    @property
    def limit(self) -> int:
        return self.__limit


class ParamSymbolInterval(ParamSymbol, ParamInterval):
    def __init__(self, symbol: str, interval: str) -> None:
        ParamSymbol.__init__(self, symbol)
        ParamInterval.__init__(self, interval)


class ParamSymbolIntervalLimit(ParamSymbol, ParamInterval, ParamLimit):
    def __init__(self, symbol: str, interval: str, limit: int) -> None:
        ParamSymbol.__init__(self, symbol)
        ParamInterval.__init__(self, interval)
        ParamLimit.__init__(self, limit)


class ParamHistoryData(ParamSymbol, ParamInterval, ParamLimit):
    def __init__(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> None:
        ParamSymbol.__init__(self, symbol)
        ParamInterval.__init__(self, interval)
        ParamLimit.__init__(self, limit)

        self.__from_buffer = from_buffer
        self.__closed_bars = closed_bars

    @property
    def from_buffer(self):
        return self.__from_buffer

    @property
    def closed_bars(self):
        return self.__closed_bars


class ParamSymbolIntervalStrategy(ParamSymbolInterval, ParamStrategy):
    def __init__(self, symbol: str, interval: str, strategy: str) -> None:
        ParamSymbolInterval.__init__(self, symbol, interval)
        ParamStrategy.__init__(self, strategy)


class ParamSimulation(ParamSymbolIntervalStrategy):
    def __init__(self, symbol: str, interval: str, strategy: str, simulation_options: SimulateOptions) -> None:
        ParamSymbolIntervalStrategy.__init__(self, symbol, interval, strategy)

        self.__simulation_options = simulation_options

    @property
    def simulation_options(self):
        return self.__simulation_options


model = Model()
