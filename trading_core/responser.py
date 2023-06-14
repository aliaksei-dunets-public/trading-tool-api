import json
import pandas as pd
from datetime import datetime 

from .core import log_file_name
from .model import Config, SymbolList
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


def getIntervals(importance: str) -> json:
    return json.dumps(Config().getIntervalDetails(importance))


@decorator_json
def getSymbol(code: str) -> json:
    return SymbolList().getSymbol(code)


@decorator_json
def getSymbols(code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> json:
    return SymbolList().getSymbols(code=code, name=name, status=status, type=type, isBuffer=isBuffer)


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
