import pandas_ta as ta

from .core import HistoryData
from .model import Config

class IndicatorBase():
    def __init__(self):
        self._code = ''
        self._name = ''

    def getCode(self):
        return self._code

    def getName(self):
        return self._name

    def getIndicator(self, symbol: str, interval: str, limit: int):
        return Config().getHandler().getHistoryData(symbol=symbol, interval=interval, limit=limit)

    def getIndicatorByHistoryData(self, historyData: HistoryData):
        return historyData.getDataFrame()

class Indicator_CCI(IndicatorBase):
    def __init__(self, length: int):
        IndicatorBase.__init__(self)
        self._code = 'CCI'
        self._name = 'Commodity Channel Index'

        self.__length = int(length)
    
    def getLength(self) -> int:
        return self.__length
    
    def getIndicator(self, symbol: str, interval: str, limit: int):
        limit = limit if limit > self.__length else self.__length
        historyData = super().getIndicator(symbol=symbol, interval=interval, limit=limit)

        return self.getIndicatorByHistoryData(historyData)

    def getIndicatorByHistoryData(self, historyData: HistoryData):

        historyDataFrame = super().getIndicatorByHistoryData(historyData)
        
        if historyDataFrame.shape[0] < self.__length:
            raise Exception(f'Count of history data less then indicator interval {self.__length}')

        cci_series = historyDataFrame.ta.cci(length=self.__length)

        cci_df = cci_series.to_frame(name=self._code)

        indicator_df = historyDataFrame.join(cci_df)
        indicator_df = indicator_df[indicator_df[self._code].notna()]

        return indicator_df