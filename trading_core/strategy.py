import pandas as pd

from .core import logger, Const, HistoryData
from .model import config
from .indicator import Indicator_CCI


class StrategyFactory():

    def __init__(self, code):
        self.__instance = None

        strategy_config_inst = StrategyConfig(code)

        if code in [Const.TA_STRATEGY_CCI_50_TREND_0, Const.TA_STRATEGY_CCI_14_TREND_100, Const.TA_STRATEGY_CCI_20_TREND_100]:
            self.__instance = Strategy_CCI(strategy_config_inst)
        else:
            raise Exception(f'Strategy with code {code} is missed')

    def get_strategy_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool):
        logger.info(
            f'STRATEGY - {self.__instance.get_strategy_config().get_code()}: get_strategy_data(symbol={symbol}, interval={interval}, limit={limit}, from_buffer={from_buffer}, closed_bars={closed_bars})')

        return self.__instance.get_strategy_data(symbol=symbol,
                                                 interval=interval,
                                                 limit=limit,
                                                 from_buffer=from_buffer,
                                                 closed_bars=closed_bars)

    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        logger.info(
            f'STRATEGY - {self.__instance.get_strategy_config().get_code()}: get_strategy_data_by_history_data(symbol={historyData.getSymbol()}, interval={historyData.getInterval()}, limit={historyData.getLimit()}, endDatetime={historyData.getEndDateTime()})')

        return self.__instance.get_strategy_data_by_history_data(historyData)


class StrategyConfig():
    def __init__(self, code: str):
        if not code:
            raise Exception(f'Strategy code is missed')

        self._strategy_config = config.get_strategy(code)

        if not self._strategy_config:
            raise Exception(f'Strategy Config with code {code} is missed')

        self._code = self._strategy_config[Const.CODE]
        self._name = self._strategy_config[Const.NAME]
        self._length = int(self._strategy_config[Const.LENGTH])

    def get_code(self) -> str:
        return self._code

    def get_name(self) -> str:
        return self._name

    def get_length(self) -> str:
        return self._length

    def get_config(self) -> dict:
        return self._strategy_config

    def get_property(self, name: str):
        if name in self._strategy_config:
            return self._strategy_config[name]
        else:
            raise Exception(
                f'Property {name} is missed in the Strategy Config {self._code}')


class StrategyBase():
    def __init__(self, strategy_config_inst: StrategyConfig):
        self._strategy_config_inst = strategy_config_inst

    def get_strategy_config(self) -> StrategyConfig:
        return self._strategy_config_inst

    def get_strategy_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        pass

    def get_strategy_data_by_history_data(self, historyData: HistoryData) -> pd.DataFrame:
        pass


class Strategy_CCI(StrategyBase):
    def __init__(self, strategy_config_inst: StrategyConfig):
        StrategyBase.__init__(self, strategy_config_inst)
        self._value = self.get_strategy_config().get_property(Const.VALUE)
        self._cci = Indicator_CCI(self.get_strategy_config().get_length())

    def get_strategy_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool):
        default_limit = self._cci.get_length() + 2
        limit = limit if limit > default_limit else default_limit
        history_data = config.get_stock_exchange_handler().getHistoryData(symbol=symbol,
                                                                          interval=interval,
                                                                          limit=limit,
                                                                          from_buffer=from_buffer,
                                                                          closed_bars=closed_bars)

        return self.get_strategy_data_by_history_data(history_data)

    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        cci_df = self._cci.get_indicator_by_history_data(historyData)
        cci_df.insert(cci_df.shape[1], Const.SIGNAL,
                      self._determineSignal(cci_df))

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
