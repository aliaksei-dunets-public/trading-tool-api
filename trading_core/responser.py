import json
import pandas as pd

from .model import Config, Symbol, SymbolList

def decorator_json(func) -> str:
    def wrapper (*args, **kwargs):
        value = func(*args, **kwargs)

        if isinstance(value, list) and all(isinstance(item, object) for item in value):
            return json.dumps([item.__dict__ for item in value])
        elif isinstance(value, pd.DataFrame):
            return value.to_json(orient="records")
        elif isinstance(value, object):
            return json.dumps(value.__dict__)
        else:
            return json.dumps(value)
    return wrapper

def to_json(value) -> str:
    if isinstance(value, list) and all(isinstance(item, object) for item in value):
        return json.dumps([item.__dict__ for item in value])
    if isinstance(value, object):
        return json.dumps(value.__dict__)
    else:
        return json.dumps(value)


class ResponseBase:
    pass


class ResponseInterval(ResponseBase):
    def getIntervals(self) -> json:
        return json.dumps(Config().getIntervalsDetails())


class ResponseSymbol(ResponseBase):
    @decorator_json
    def getSymbol(self, code: str) -> json:
        return SymbolList().getSymbol(code)

    @decorator_json
    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None) -> list:
        return SymbolList().getSymbols(code=code, name=name, status=status, type=type)


class ResponseHistoryData(ResponseBase):
    @decorator_json
    def getData(self, symbol: str, interval: str, limit: int) -> json:
        historyData = Config().getHandler().getHistoryData(symbol=symbol, interval=interval, limit=limit)
        return historyData.getDataFrame()
