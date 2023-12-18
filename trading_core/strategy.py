import pandas as pd

from .constants import Const
from .core import logger, config, runtime_buffer, HistoryData, Signal
from .model import model, Symbols
from .common import IntervalType, SymbolIntervalLimitModel
from .indicator import Indicator_CCI
from .handler import buffer_runtime_handler
from .trend import TrendCCI


class SignalFactory:
    def get_signal(
        self,
        symbol: str,
        interval: str,
        strategy: str,
        signals_config: list,
        closed_bars: bool,
    ) -> Signal:
        # Check if trading is not available for symbol -> skip processing
        if not buffer_runtime_handler.get_symbol_handler().is_trading_available(
            interval=interval, symbol=symbol
        ):
            return None

        # Get DateTime of the Strategy
        end_date_time = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=closed_bars
        )

        # Get signal from the buffer
        signal_inst = runtime_buffer.get_signal_from_buffer(
            symbol=symbol, interval=interval, strategy=strategy, date_time=end_date_time
        )

        # Check if buffer contains corresponding signal
        if not signal_inst:
            # Calculate signal from the API
            # Get the latest bar from the Strategy Factory
            strategy_df = (
                StrategyFactory(strategy)
                .get_strategy_data(
                    symbol=symbol, interval=interval, closed_bars=closed_bars
                )
                .tail(1)
            )

            # Init signal instance
            for index, strategy_row in strategy_df.iterrows():
                signal_inst = Signal(
                    date_time=index,
                    symbol=symbol,
                    interval=interval,
                    strategy=strategy,
                    signal=strategy_row[Const.PARAM_SIGNAL],
                )

            # Add signal to the buffer
            runtime_buffer.set_signal_to_buffer(signal_inst)

            if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                logger.info(
                    f"SIGNAL: get_signal(symbol={symbol}, interval={interval}, strategy={strategy}, signals_config={signals_config}, closed_bars={closed_bars})"
                )

        # Return signal data if signal is compatible with signal config, else return None
        if signal_inst.is_compatible(signals_config):
            return signal_inst
        else:
            return None

    def get_signals(
        self,
        symbols: list,
        intervals: list = None,
        strategies: list = None,
        signals_config: list = None,
        closed_bars: bool = True,
    ) -> list[Signal]:
        signals = []

        if not symbols:
            symbols = Symbols(from_buffer=False).get_symbol_codes(
                status=Const.STATUS_OPEN
            )

        if not intervals:
            intervals = buffer_runtime_handler.get_interval_handler().get_intervals()

        sorted_strategies = model.get_sorted_strategy_codes(strategies)

        for symbol in symbols:
            for interval in intervals:
                for strategy in sorted_strategies:
                    try:
                        signal = self.get_signal(
                            symbol=symbol,
                            interval=interval,
                            strategy=strategy,
                            signals_config=signals_config,
                            closed_bars=closed_bars,
                        )
                        if signal:
                            signals.append(signal)
                        else:
                            continue
                    except Exception as error:
                        logger.error(
                            f"SIGNAL: For symbol={symbol}, interval={interval}, strategy={strategy} - {error}"
                        )
                        continue

        return signals


class StrategyFactory:
    def __init__(self, code):
        self.__instance = None

        strategy_config_inst = StrategyConfig(code)

        if code in [
            Const.TA_STRATEGY_CCI_50_TREND_0,
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_20_TREND_100,
        ]:
            self.__instance = Strategy_CCI(strategy_config_inst)
        elif code in [
            Const.TA_STRATEGY_CCI_14_BASED_TREND_100,
            Const.TA_STRATEGY_CCI_20_BASED_TREND_100,
        ]:
            self.__instance = StrategyDirectionBasedTrend_CCI(strategy_config_inst)
        elif code == Const.TA_STRATEGY_CCI_20_100_TREND_UP_LEVEL:
            self.__instance = Strategy_CCI_100_TrendUpLevel(strategy_config_inst)
        else:
            raise Exception(f"STARTEGY: Strategy with code {code} is missed")

    def get_strategy_data(
        self,
        symbol: str,
        interval: str,
        limit: int = 0,
        from_buffer: bool = True,
        closed_bars: bool = True,
    ):
        strategy_data = self.__instance.get_strategy_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"STRATEGY: {self.__instance.get_strategy_config().get_code()} - get_strategy_data(symbol={symbol}, interval={interval}, limit={limit}, from_buffer={from_buffer}, closed_bars={closed_bars})"
            )

        return strategy_data

    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        strategy_data = self.__instance.get_strategy_data_by_history_data(historyData)

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"STRATEGY: {self.__instance.get_strategy_config().get_code()} - get_strategy_data_by_history_data(symbol={historyData.getSymbol()}, interval={historyData.getInterval()}, limit={historyData.getLimit()}, endDatetime={historyData.getEndDateTime()})"
            )

        return strategy_data


class StrategyConfig:
    def __init__(self, code: str):
        if not code:
            raise Exception(f"Strategy code is missed")

        self._strategy_config = model.get_strategy(code)

        if not self._strategy_config:
            raise Exception(f"Strategy Config with code {code} is missed")

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
                f"Property {name} is missed in the Strategy Config {self._code}"
            )


class StrategyBase:
    def __init__(self, strategy_config_inst: StrategyConfig):
        self._strategy_config_inst = strategy_config_inst

    def get_strategy_config(self) -> StrategyConfig:
        return self._strategy_config_inst

    def get_strategy_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool,
        closed_bars: bool,
    ) -> pd.DataFrame:
        pass

    def get_strategy_data_by_history_data(
        self, historyData: HistoryData
    ) -> pd.DataFrame:
        pass


class Strategy_CCI(StrategyBase):
    def __init__(self, strategy_config_inst: StrategyConfig):
        StrategyBase.__init__(self, strategy_config_inst)
        self._value = self.get_strategy_config().get_property(Const.VALUE)
        self._cci = Indicator_CCI(self.get_strategy_config().get_length())

    def get_strategy_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool,
        closed_bars: bool,
    ):
        default_limit = self._cci.get_length() + 2
        limit = limit + default_limit
        history_data = model.get_handler().getHistoryData(
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )

        return self.get_strategy_data_by_history_data(history_data)

    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        cci_df = self._cci.get_indicator_by_history_data(historyData)
        cci_df.insert(
            cci_df.shape[1], Const.PARAM_SIGNAL, self._determineSignal(cci_df)
        )

        return cci_df

    def _determineSignal(self, cci_df):
        signals = []

        for i in range(len(cci_df)):
            decision = ""

            if i == 0:
                signals.append(decision)
                continue

            current_value = cci_df.iloc[i, 5]
            previous_value = cci_df.iloc[i - 1, 5]

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

    def _get_signal_decision(self, current_value, previous_value):
        decision = ""
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

        return decision


class StrategyDirectionBasedTrend_CCI(Strategy_CCI):
    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        symbol = historyData.getSymbol()
        limit = historyData.getLimit()
        interval = historyData.getInterval()
        next_interval = None

        cci_df = self._cci.get_indicator_by_history_data(historyData)

        param = SymbolIntervalLimitModel(
            symbol=symbol, interval=interval, limit=limit, consistency_check=False
        )

        trend_df = TrendCCI().calculate_trends(param)

        cci_df = pd.merge(
            cci_df,
            trend_df[[Const.PARAM_TREND]],
            how="left",
            left_on=Const.COLUMN_DATETIME,
            right_on=Const.COLUMN_DATETIME,
        )

        # Detect Next Interval
        if interval == IntervalType.MIN_5:
            next_interval = IntervalType.MIN_30
            limit = limit // 6 + 1
        elif interval == IntervalType.MIN_15:
            next_interval = IntervalType.HOUR_1
            limit = limit // 4 + 1
        elif interval == IntervalType.MIN_30:
            next_interval = IntervalType.HOUR_4
            limit = limit // 8 + 1
        elif interval == IntervalType.HOUR_1:
            next_interval = IntervalType.HOUR_4
            limit = limit // 4 + 1
        elif interval == IntervalType.HOUR_4:
            next_interval = IntervalType.DAY_1
            limit = limit // 6 + 1
        elif interval == IntervalType.DAY_1:
            next_interval = IntervalType.WEEK_1
            limit = limit // 7 + 1
        elif interval == IntervalType.WEEK_1:
            pass
        else:
            raise Exception("Incorrect interval for subscription")

        if not next_interval:
            merged_df = cci_df
        else:
            param = SymbolIntervalLimitModel(
                symbol=symbol,
                interval=next_interval,
                limit=limit,
            )

            trend_df = TrendCCI().calculate_trends(param)

            # Assuming cci and trend are your DataFrames
            # Reset index to make the datetime column a regular column
            cci_df.reset_index(inplace=True)
            trend_df.reset_index(inplace=True)

            # Merge the DataFrames based on the datetime column
            merged_df = pd.merge_asof(
                cci_df,
                trend_df[[Const.COLUMN_DATETIME, Const.PARAM_TREND]],
                left_on=Const.COLUMN_DATETIME,
                right_on=Const.COLUMN_DATETIME,
                direction="backward",
                suffixes=("", "_UpLevel"),
            )

            # Set the datetime column as the index again
            merged_df.set_index(Const.COLUMN_DATETIME, inplace=True)

        merged_df.insert(
            cci_df.shape[1],
            Const.PARAM_SIGNAL,
            self._determineSignal(merged_df),
        )

        return merged_df

    def _determineSignal(self, cci_df):
        signals = []

        for i in range(len(cci_df)):
            decision = ""

            if i == 0:
                signals.append(decision)
                continue

            current_value = cci_df.iloc[i, 5]
            previous_value = cci_df.iloc[i - 1, 5]

            trend = cci_df.iloc[i, 6]
            trend_previous = cci_df.iloc[i - 1, 6]

            if len(cci_df.columns) >= 8:
                trend_up_level = cci_df.iloc[i, 7]
            else:
                trend_up_level = None

            if not trend_up_level:
                if trend == Const.STRONG_TREND_UP:
                    decision = self._get_signal_decision(current_value, previous_value)
                    if decision in [Const.SELL, Const.STRONG_SELL]:
                        decision = ""
                    elif decision == Const.BUY:
                        decision = Const.STRONG_BUY
                elif trend == Const.STRONG_TREND_DOWN:
                    decision = self._get_signal_decision(current_value, previous_value)
                    if decision in [Const.BUY, Const.STRONG_BUY]:
                        decision = ""
                    elif decision == Const.SELL:
                        decision = Const.STRONG_SELL
                # Remove signal for close position - use stop loss and take profit
                # else:
                #     if trend_previous == Const.STRONG_TREND_DOWN:
                #         decision = Const.BUY
                #     elif trend_previous == Const.STRONG_TREND_UP:
                #         decision = Const.SELL

            elif trend == Const.STRONG_TREND_UP:
                if trend_up_level in [Const.STRONG_TREND_UP, Const.TREND_UP]:
                    decision = self._get_signal_decision(current_value, previous_value)
                    if decision in [Const.SELL, Const.STRONG_SELL]:
                        decision = ""
                    elif decision == Const.BUY:
                        decision = Const.STRONG_BUY

            # Remove signal for close position - use stop loss and take profit
            # elif trend == Const.TREND_UP:
            #     if trend_previous in [Const.STRONG_TREND_DOWN, Const.TREND_DOWN]:
            #         decision = Const.BUY

            elif trend == Const.STRONG_TREND_DOWN:
                if trend_up_level in [Const.STRONG_TREND_DOWN, Const.TREND_DOWN]:
                    decision = self._get_signal_decision(current_value, previous_value)
                    if decision in [Const.BUY, Const.STRONG_BUY]:
                        decision = ""
                    elif decision == Const.SELL:
                        decision = Const.STRONG_SELL

            # Remove signal for close position - use stop loss and take profit
            # elif trend == Const.TREND_DOWN:
            #     if trend_previous in [Const.STRONG_TREND_UP, Const.TREND_UP]:
            #         decision = Const.SELL

            signals.append(decision)

        return signals


class Strategy_CCI_100_TrendUpLevel(Strategy_CCI):
    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        symbol = historyData.getSymbol()
        limit = historyData.getLimit()
        interval = historyData.getInterval()
        next_interval = None

        # Detect Next Interval
        if interval == IntervalType.MIN_5:
            next_interval = IntervalType.MIN_30
            limit = limit // 6 + 1
        elif interval == IntervalType.MIN_15:
            next_interval = IntervalType.HOUR_1
            limit = limit // 4 + 1
        elif interval == IntervalType.MIN_30:
            next_interval = IntervalType.HOUR_4
            limit = limit // 8 + 1
        elif interval == IntervalType.HOUR_1:
            next_interval = IntervalType.HOUR_4
            limit = limit // 4 + 1
        elif interval == IntervalType.HOUR_4:
            next_interval = IntervalType.DAY_1
            limit = limit // 6 + 1
        elif interval == IntervalType.DAY_1:
            next_interval = IntervalType.WEEK_1
            limit = limit // 7 + 1
        elif interval == IntervalType.WEEK_1:
            next_interval = IntervalType.WEEK_1
        else:
            raise Exception("Incorrect interval for subscription")

        cci_df = self._cci.get_indicator_by_history_data(historyData)

        param = SymbolIntervalLimitModel(
            symbol=symbol,
            interval=next_interval,
            limit=limit,
        )

        trend_df = TrendCCI().calculate_trends(param)

        # Assuming cci and trend are your DataFrames
        # Reset index to make the datetime column a regular column
        cci_df.reset_index(inplace=True)
        trend_df.reset_index(inplace=True)

        # Merge the DataFrames based on the datetime column
        merged_df = pd.merge_asof(
            cci_df,
            trend_df[[Const.COLUMN_DATETIME, Const.PARAM_TREND]],
            left_on=Const.COLUMN_DATETIME,
            right_on=Const.COLUMN_DATETIME,
            direction="backward",
        )

        # Set the datetime column as the index again
        merged_df.set_index(Const.COLUMN_DATETIME, inplace=True)

        merged_df.insert(
            cci_df.shape[1],
            Const.PARAM_SIGNAL,
            self._determineSignal(merged_df),
        )

        return merged_df

    def _determineSignal(self, cci_df):
        signals = []

        for i in range(len(cci_df)):
            decision = ""

            if i == 0:
                signals.append(decision)
                continue

            current_value = cci_df.iloc[i, 5]
            previous_value = cci_df.iloc[i - 1, 5]

            trend = cci_df.iloc[i, 6]
            # trend_previous = cci_df.iloc[i - 1, 6]

            decision = self._get_signal_decision(current_value, previous_value)

            if trend in [Const.STRONG_TREND_UP, Const.TREND_UP]:
                if decision in [Const.STRONG_SELL, Const.SELL]:
                    decision = ""
                elif decision == Const.BUY:
                    decision = Const.STRONG_BUY
            elif trend in [Const.STRONG_TREND_DOWN, Const.TREND_DOWN]:
                if decision in [Const.STRONG_BUY, Const.BUY]:
                    decision = ""
                elif decision == Const.SELL:
                    decision = Const.STRONG_SELL

            signals.append(decision)

        return signals


class StrategyDirectionBasedTrend(Strategy_CCI):
    def get_strategy_data_by_history_data(self, historyData: HistoryData):
        symbol = historyData.getSymbol()
        limit = historyData.getLimit()
        interval = historyData.getInterval()

        cci_df = self._cci.get_indicator_by_history_data(historyData)

        param = SymbolIntervalLimitModel(symbol=symbol, interval=interval, limit=limit)

        trend_df = TrendCCI().calculate_trends(param)

        cci_df = pd.merge(
            cci_df,
            trend_df[[Const.PARAM_TREND]],
            how="left",
            left_on=Const.COLUMN_DATETIME,
            right_on=Const.COLUMN_DATETIME,
        )

        cci_df = pd.merge(
            cci_df,
            trend_df[[Const.PARAM_SIGNAL]],
            how="left",
            left_on=Const.COLUMN_DATETIME,
            right_on=Const.COLUMN_DATETIME,
        )

        cci_df[Const.PARAM_SIGNAL] = cci_df[Const.PARAM_SIGNAL].fillna("")

        return cci_df
