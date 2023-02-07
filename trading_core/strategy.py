from .core import Const, HistoryData
from .model import Config
from .indicator import Indicator_CCI

class StrategyBase():
    def __init__(self, code):

        for strategy in Config().getStrategies():
            if strategy["code"] == code:
                self._code = strategy["code"]
                self._name = strategy["name"]

        if not self._code:
            raise Exception(f'Strategy with code {code} is missed')

    def getCode(self):
        return self._code

    def getName(self):
        return self._name

    def getStrategy(self, symbol: str, interval: str, limit: int):
        pass

    def getStrategyByHistoryData(self, historyData: HistoryData):
        pass


class StrategyFactory(StrategyBase):

    def __init__(self, code):
        StrategyBase.__init__(self, code)

        self.__instance = None

        if code == 'CCI_50_TREND_0':
            self.__instance = Strategy_CCI(code, 50, 0)
        elif code == 'CCI_14_TREND_100':
            self.__instance = Strategy_CCI(code, 14, 100)
        elif code == 'CCI_20_TREND_100':
            self.__instance = Strategy_CCI(code, 20, 100)
        else:
            raise Exception(f'Strategy with code {code} is missed')

    def getCode(self):
        return self.__instance.getCode()

    def getName(self):
        return self.__instance.getName()

    def getStrategy(self, symbol: str, interval: str, limit: int):
        return self.__instance.getStrategy(symbol, interval, limit)

    def getStrategyByHistoryData(self, historyData: HistoryData):
        return self.__instance.getStrategyByHistoryData(historyData)


class Strategy_CCI(StrategyBase):
    def __init__(self, code: str, length: int, value: float):
        StrategyBase.__init__(self, code)
        self._value = value
        self._cci = Indicator_CCI(length)

    def getStrategy(self, symbol: str, interval: str, limit: int):
        default_limit = self._cci.getLength() + 1
        limit = limit if limit > default_limit else default_limit
        historyData = Config().getHandler().getHistoryData(symbol=symbol, interval=interval, limit=limit)

        return self.getStrategyByHistoryData(historyData)

    def getStrategyByHistoryData(self, historyData: HistoryData):
        cci_df = self._cci.getIndicatorByHistoryData(historyData)
        cci_df.insert(cci_df.shape[1], Const.SIGNAL, self._determineSignal(cci_df))

        return cci_df

    def _determineSignal(self, cci_df):

        signals = []

        for i in range(len(cci_df)):

            decision = ''

            if i == 0:
                signals.append(decision)
                continue

            current_value = cci_df.iloc[i, 5]
            previous_value = cci_df.iloc[i-1, 5]
            
            if self._value == 0:
                if current_value > self._value and previous_value < self._value:
                    decision = Const.STRONG_BUY
                elif current_value < self._value and previous_value > self._value:
                    decision = Const.STRONG_SELL
            else:
                if current_value > self._value:
                    if previous_value < self._value:
                        decision = Const.BUY
                elif current_value < -self._value:
                    if previous_value > -self._value:
                        decision = Const.SELL
                else:
                    if previous_value > self._value:
                        decision = Const.STRONG_SELL
                    elif previous_value < -self._value:
                        decision = Const.STRONG_BUY

            signals.append(decision)

        return signals
