import json
import pandas as pd

from .model import Config, SymbolList
from .indicator import Indicator_CCI
from .strategy import StrategyFactory
from .simulator import Simulator


def decorator_json(func) -> str:
    def wrapper(*args, **kwargs):
        value = func(*args, **kwargs)

        if isinstance(value, list) and all(isinstance(item, object) for item in value):
            return json.dumps([item.__dict__ for item in value])
        elif isinstance(value, pd.DataFrame):
            return value.to_json(orient="table", index=True)
        elif isinstance(value, object):
            return json.dumps(value.__dict__)
        else:
            return json.dumps(value)
    return wrapper


def getIntervals() -> json:
    return json.dumps(Config().getIntervalDetails())


@decorator_json
def getSymbol(code: str) -> json:
    return SymbolList().getSymbol(code)


@decorator_json
def getSymbols(code: str = None, name: str = None, status: str = None, type: str = None) -> json:
    return SymbolList().getSymbols(code=code, name=name, status=status, type=type)


def getIndicators() -> json:
    return json.dumps(Config().getIndicators())


def getStrategies() -> json:
    return json.dumps(Config().getStrategies())


@decorator_json
def getHistoryData(symbol: str, interval: str, limit: int) -> json:
    historyData = Config().getHandler().getHistoryData(
        symbol=symbol, interval=interval, limit=limit)
    return historyData.getDataFrame()


@decorator_json
def getIndicatorData(code: str, length: int, symbol: str, interval: str, limit: int):
    return Indicator_CCI(length).getIndicator(symbol, interval, limit)


@decorator_json
def getStrategyData(code: str, symbol: str, interval: str, limit: int):
    return StrategyFactory(code).getStrategy(symbol, interval, limit)


def getSignals(symbols: list, intervals: list, strategyCodes: list):
    return json.dumps(Simulator().determineSignals(symbols, intervals, strategyCodes))
