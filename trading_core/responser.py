import json
import pandas as pd
from datetime import datetime

from .core import log_file_name, Symbol
from .model import config, Symbols, Config
from .indicator import Indicator_CCI
from .strategy import StrategyFactory
from .simulator import Simulator


def decorator_json(func) -> str:
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)

        if isinstance(value, list):
            if all(type(item) == dict for item in value):
                return json.dumps(value)
            if all(isinstance(item, object) for item in value):
                return json.dumps([item.__dict__ for item in value])
            else:
                return json.dumps(value)
        elif isinstance(value, pd.DataFrame):
            return value.to_json(orient="table", index=True)
        elif isinstance(value, object):
            return json.dumps(value.__dict__)
        else:
            return json.dumps(value)
    return wrapper


class ResponserBase():
    def get_param_bool(self, param_value):
        return bool(param_value.lower() == 'true')

    def get_symbol(self, code: str) -> Symbol:
        return Symbols().get_symbol(code)

    def get_symbol_list(self, code: str, name: str, status: str, type: str, from_buffer: bool) -> list[Symbol]:
        return Symbols(from_buffer).get_symbol_list(code=code, name=name, status=status, type=type)

    def get_intervals(self, importances: list = None) -> list:
        return config.get_intervals_config(importances)

    def get_indicators(self) -> list:
        return config.get_indicators()

    def get_strategies(self) -> list:
        return config.get_strategies()

    def get_history_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        history_data_inst = config.get_stock_exchange_handler().getHistoryData(
            symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)
        return history_data_inst.getDataFrame()

    def get_strategy_data(self, code: str, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        strategy_inst = StrategyFactory(code)
        return strategy_inst.get_strategy_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)


class ResponserWeb(ResponserBase):
    @decorator_json
    def get_symbol(self, code: str) -> json:
        symbol = super().get_symbol(code)
        if symbol:
            return symbol
        else:
            raise Exception(f"Symbol: {code} can't be detected")

    @decorator_json
    def get_symbol_list(self, code: str, name: str, status: str, type: str, from_buffer: bool) -> json:
        return super().get_symbol_list(code=code, name=name, status=status, type=type, from_buffer=from_buffer)

    @decorator_json
    def get_intervals(self, importances: list = None) -> json:
        return super().get_intervals(importances=importances)

    @decorator_json
    def get_indicators(self) -> json:
        return super().get_indicators()

    @decorator_json
    def get_strategies(self) -> json:
        return super().get_strategies()

    @decorator_json
    def get_history_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> json:
        return super().get_history_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    @decorator_json
    def get_strategy_data(self, code: str, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> json:
        return super().get_strategy_data(code=code, symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)


@decorator_json
def getStrategyData(code: str, symbol: str, interval: str, limit: int):
    return StrategyFactory(code).get_strategy_data(symbol, interval, limit)


@decorator_json
def getSignals(symbols: list, intervals: list, strategyCodes: list, closedBar: bool):
    return Simulator().determineSignals(symbols, intervals, strategyCodes, [], closedBar)


@decorator_json
def getSimulate(symbols: list, intervals: list, strategyCodes: list):
    return Simulator().simulateTrading(symbols, intervals, strategyCodes)


@decorator_json
def getSimulations(symbols: list, intervals: list, strategyCodes: list):
    return Simulator().getSimulations(symbols, intervals, strategyCodes)


@decorator_json
def getSignalsBySimulation(symbols: list, intervals: list, strategyCodes: list):
    return Simulator().getSignalsBySimulation(symbols, intervals, strategyCodes)


def getLogs(start_date, end_date):
    # date_format = "%Y-%m-%d"
    # start_date = datetime.strptime(start_date, date_format)
    # end_date = datetime.strptime(end_date, date_format) + datetime.timedelta(days=1)
    # logs = []
    # current_date = start_date
    # while current_date < end_date:
    try:
        with open(log_file_name, "r") as log_file:
            logs = log_file.read()
    except FileNotFoundError:
        pass
        # current_date += datetime.timedelta(days=1)

    logs = logs.replace('\n', '<br>')

    return logs
