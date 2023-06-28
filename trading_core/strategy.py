import pandas as pd

from .core import logger, config, runtime_buffer, Const, HistoryData, Signal
from .model import model
from .indicator import Indicator_CCI


class SignalFactory():
    def get_signal(self, symbol: str, interval: str, strategy: str, signals_config: list, closed_bars: bool) -> Signal:

        # Get DateTime of the Strategy
        end_date_time = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=closed_bars)

        # Get signal from the buffer
        signal_inst = runtime_buffer.get_signal_from_buffer(
            symbol=symbol, interval=interval, strategy=strategy, date_time=end_date_time)

        # Check if buffer contains corresponding signal
        if signal_inst:
            if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                logger.info(
                    f'BUFFER: get_signal(symbol={symbol}, interval={interval}, strategy={strategy}, signals_config={signals_config}, closed_bars={closed_bars})')
        else:

            # Calculate signal from the API
            # Get the latest bar from the Strategy Factory
            strategy_df = StrategyFactory(strategy).get_strategy_data(
                symbol=symbol, interval=interval, closed_bars=closed_bars).tail(1)

            # Init signal instance
            for index, strategy_row in strategy_df.iterrows():
                signal_inst = Signal(date_time=index, symbol=symbol, interval=interval,
                                     strategy=strategy, signal=strategy_row[Const.SIGNAL])

            # Add signal to the buffer
            runtime_buffer.set_signal_to_buffer(signal_inst)

            if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                logger.info(
                    f'SIGNAL: get_signal(symbol={symbol}, interval={interval}, strategy={strategy}, signals_config={signals_config}, closed_bars={closed_bars})')

        # Return signal data if signal is compatible with signal config, else return None
        if signal_inst.is_compatible(signals_config):
            return signal_inst
        else:
            return None

    def get_signals(self, symbols: list, intervals: list = None, strategies: list = None, signals_config: list = None, closed_bars: bool = True) -> list[Signal]:
        signals = []

        if not symbols:
            raise Exception(f'Symbol is missed')

        if not intervals:
            intervals = model.get_intervals()

        sorted_strategies = model.get_sorted_strategy_codes(strategies)

        for symbol in symbols:
            for interval in intervals:
                for strategy in sorted_strategies:
                    try:
                        signal = self.get_signal(
                            symbol=symbol, interval=interval, strategy=strategy, signals_config=signals_config, closed_bars=closed_bars)
                        if signal:
                            signals.append(signal)
                        else:
                            continue
                    except Exception as error:
                        logger.error(
                            f'For symbol={symbol}, interval={interval}, strategy={strategy} - {error}')
                        continue

        return signals


class StrategyFactory():

    def __init__(self, code):
        self.__instance = None

        strategy_config_inst = StrategyConfig(code)

        if code in [Const.TA_STRATEGY_CCI_50_TREND_0, Const.TA_STRATEGY_CCI_14_TREND_100, Const.TA_STRATEGY_CCI_20_TREND_100]:
            self.__instance = Strategy_CCI(strategy_config_inst)
        else:
            raise Exception(f'Strategy with code {code} is missed')

    def get_strategy_data(self, symbol: str, interval: str, limit: int = 0, from_buffer: bool = True, closed_bars: bool = True):
        strategy_data = self.__instance.get_strategy_data(symbol=symbol,
                                                          interval=interval,
                                                          limit=limit,
                                                          from_buffer=from_buffer,
                                                          closed_bars=closed_bars)

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f'STRATEGY - {self.__instance.get_strategy_config().get_code()}: get_strategy_data(symbol={symbol}, interval={interval}, limit={limit}, from_buffer={from_buffer}, closed_bars={closed_bars})')

        return strategy_data

    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        strategy_data = self.__instance.get_strategy_data_by_history_data(
            historyData)

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f'STRATEGY - {self.__instance.get_strategy_config().get_code()}: get_strategy_data_by_history_data(symbol={historyData.getSymbol()}, interval={historyData.getInterval()}, limit={historyData.getLimit()}, endDatetime={historyData.getEndDateTime()})')

        return strategy_data


class StrategyConfig():
    def __init__(self, code: str):
        if not code:
            raise Exception(f'Strategy code is missed')

        self._strategy_config = model.get_strategy(code)

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
        history_data = model.get_handler().getHistoryData(symbol=symbol,
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
