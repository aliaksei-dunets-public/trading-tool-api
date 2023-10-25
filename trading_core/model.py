import copy

from .constants import Const
from .core import config, logger, Symbol, SimulateOptions
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
    def __init__(self, symbol: str, consistency_check: bool = True) -> None:
        self.__symbol = symbol
        self.__symbol_config = None

        # If consistency check is True -> get config and validate the symbol
        if consistency_check:
            self.get_symbol_config()

    @property
    def symbol(self) -> str:
        return self.__symbol

    def get_symbol_config(self) -> Symbol:
        if not self.__symbol_config:
            self.__symbol_config = Symbols(
                from_buffer=True).get_symbol(self.__symbol)

            if not self.__symbol_config:
                raise Exception(
                    f"PARAM: Symbol: {self.__symbol} doesn't exist")

        return self.__symbol_config


class ParamInterval(ParamBase):
    def __init__(self, interval: str, consistency_check: bool = True) -> None:
        self.__interval = interval
        self.__interval_config = None

        # If consistency check is True -> get config and validate the symbol
        if consistency_check:
            self.get_interval_config()

    @property
    def interval(self) -> str:
        return self.__interval

    def get_interval_config(self) -> dict:
        if not self.__interval_config:
            self.__interval_config = Model().get_interval_config(self.__interval)

            if not self.__interval_config:
                raise Exception(
                    f"PARAM: Interval: {self.__interval} doesn't exist")

        return self.__interval_config


class ParamStrategy(ParamBase):
    def __init__(self, strategy: str, consistency_check: bool = True) -> None:
        self.__strategy = strategy
        self.__strategy_config = None

        # If consistency check is True -> get config and validate the symbol
        if consistency_check:
            self.get_strategy_config()

    @property
    def strategy(self) -> str:
        return self.__strategy

    def get_strategy_config(self) -> dict:
        if not self.__strategy_config:
            self.__strategy_config = Model().get_strategy(self.__strategy)

            if not self.__strategy_config:
                raise Exception(
                    f"PARAM: Strategy: {self.__strategy} doesn't exist")

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
    def __init__(self, symbol: str, interval: str, consistency_check: bool = True) -> None:
        ParamSymbol.__init__(self, symbol, consistency_check)
        ParamInterval.__init__(self, interval, consistency_check)


class ParamSymbolIntervalLimit(ParamSymbol, ParamInterval, ParamLimit):
    def __init__(self, symbol: str, interval: str, limit: int, consistency_check: bool = True) -> None:
        ParamSymbol.__init__(self, symbol, consistency_check)
        ParamInterval.__init__(self, interval, consistency_check)
        ParamLimit.__init__(self, limit)


class ParamHistoryData(ParamSymbol, ParamInterval, ParamLimit):
    def __init__(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool, consistency_check: bool = True) -> None:
        ParamSymbol.__init__(self, symbol, consistency_check)
        ParamInterval.__init__(self, interval, consistency_check)
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
    def __init__(self, symbol: str, interval: str, strategy: str, consistency_check: bool = True) -> None:
        ParamSymbolInterval.__init__(self, symbol, interval, consistency_check)
        ParamStrategy.__init__(self, strategy, consistency_check)


class ParamSimulation(ParamSymbolIntervalStrategy):
    def __init__(self, symbol: str, interval: str, strategy: str, simulation_options: SimulateOptions, consistency_check) -> None:
        ParamSymbolIntervalStrategy.__init__(
            self, symbol, interval, strategy, consistency_check)

        self.__simulation_options = simulation_options

    @property
    def simulation_options(self):
        return self.__simulation_options


class ParamSymbolList(ParamBase):
    def __init__(self, symbols: list = None) -> None:

        self.__symbols = []
        consistency_check = True

        if not symbols:
            symbols = Symbols(from_buffer=True).get_symbol_codes()
            consistency_check = False

        for symbol in symbols:
            try:
                self.__symbols.append(ParamSymbol(symbol, consistency_check))
            except Exception as error:
                logger.error(f'PARAM: For symbol={symbol} - {error}')
                continue

    @property
    def symbols(self) -> list[ParamSymbol]:
        return self.__symbols


class ParamIntervalList(ParamBase):
    def __init__(self, intervals: list = None) -> None:

        self.__intervals = []
        consistency_check = True

        if not intervals:
            intervals = model.get_intervals()
            consistency_check = False

        for interval in intervals:
            try:
                self.__intervals.append(
                    ParamInterval(interval, consistency_check))
            except Exception as error:
                logger.error(f'PARAM: For interval={interval} - {error}')
                continue

    @property
    def intervals(self) -> list[ParamInterval]:
        return self.__intervals


class ParamStrategyList(ParamBase):
    def __init__(self, strategies: list = None) -> None:

        self.__strategies = []
        consistency_check = True

        if not strategies:
            strategies = model.get_sorted_strategy_codes()
            consistency_check = False

        for strategy in strategies:
            try:
                self.__strategies.append(
                    ParamStrategy(strategy, consistency_check))
            except Exception as error:
                logger.error(f'PARAM: For strategy={strategy} - {error}')
                continue

    @property
    def strategies(self) -> list[ParamStrategy]:
        return self.__strategies


class ParamSymbolIntervalList(ParamSymbolList, ParamIntervalList):
    def __init__(self, symbols: list = None, intervals: list = None) -> None:
        ParamSymbolList.__init__(self, symbols)
        ParamIntervalList.__init__(self, intervals)

    def get_param_symbol_interval_list(self) -> list[ParamSymbolInterval]:
        params = []

        for symbol in self.symbols:
            for interval in self.intervals:
                params.append(ParamSymbolInterval(symbol=symbol.symbol,
                                                  interval=interval.interval,
                                                  consistency_check=False))

        return params


class ParamSymbolIntervalStrategyList(ParamSymbolIntervalList, ParamStrategyList):
    def __init__(self, symbols: list = None, intervals: list = None, strategies: list = None) -> None:
        ParamSymbolIntervalList.__init__(self, symbols, intervals)
        ParamStrategyList.__init__(self, strategies)

    def get_param_symbol_interval_strategy_list(self) -> list[ParamSymbolIntervalStrategy]:
        params = []

        for symbol in self.symbols:
            for interval in self.intervals:
                for strategy in self.strategies:
                    params.append(ParamSymbolIntervalStrategy(symbol=symbol.symbol,
                                                              interval=interval.interval,
                                                              strategy=strategy.strategy,
                                                              consistency_check=False))

        return params


class ParamSimulationList(ParamSymbolIntervalStrategyList):
    def __init__(self, symbols: list = None, intervals: list = None, strategies: list = None, simulation_options_list: list[SimulateOptions] = None) -> None:
        ParamSymbolIntervalStrategyList.__init__(
            self, symbols, intervals, strategies)

        if not simulation_options_list:
            for item in self.intervals:
                simulation_options_list = config.get_default_simulation_options(
                    item.interval)

        self.__simulation_options_list = simulation_options_list

    @property
    def simulation_options_list(self):
        return self.__simulation_options_list

    def get_param_simulation_list(self) -> list[ParamSimulation]:
        params = []

        for symbol in self.symbols:
            for interval in self.intervals:
                for strategy in self.strategies:
                    for option in self.simulation_options_list:
                        params.append(ParamSimulation(symbol=symbol.symbol,
                                                      interval=interval.interval,
                                                      strategy=strategy.strategy,
                                                      simulation_options=copy.deepcopy(option),
                                                      consistency_check=False))

        return params


model = Model()
