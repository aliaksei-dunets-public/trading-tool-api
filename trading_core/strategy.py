import pandas as pd

from trading_core.common import StrategyParamModel

from .constants import Const
from .core import logger, config
from .common import (
    IntervalType,
    StrategyType,
    StrategyConfigModel,
    HistoryDataParamModel,
    IndicatorParamModel,
    StrategyParamModel,
    TraderSymbolIntervalLimitModel,
    HistoryDataModel,
)
from .indicator import Indicator_CCI
from .handler import buffer_runtime_handler, StrategyHandler
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
    def __init__(self, strategy):
        self.__instance = None

        strategy_config_mdl = StrategyHandler.get_strategy_config(strategy)

        if strategy in [
            StrategyType.CCI_50_TREND_0,
            StrategyType.CCI_14_TREND_100,
            StrategyType.CCI_20_TREND_100,
        ]:
            self.__instance = Strategy_CCI(strategy_config_mdl)
        elif strategy in [
            StrategyType.CCI_14_BASED_TREND_100,
            StrategyType.CCI_20_BASED_TREND_100,
        ]:
            self.__instance = StrategyDirectionBasedTrend_CCI(strategy_config_mdl)
        elif strategy == StrategyType.CCI_20_100_TREND_UP_LEVEL:
            self.__instance = Strategy_CCI_100_TrendUpLevel(strategy_config_mdl)
        else:
            raise Exception(f"STRATEGY: Strategy {strategy} isn't implemented")

    def get_strategy_data(self, param: StrategyParamModel):
        strategy_data = self.__instance.get_strategy_data(param)

        return strategy_data

    def get_strategy_data_by_history_data(self, historyt_data_mdl: HistoryDataModel):
        strategy_data = self.__instance.get_strategy_data_by_history_data(
            historyt_data_mdl
        )

        return strategy_data


class StrategyBase:
    def __init__(self, strategy_config_mdl: StrategyConfigModel):
        self._strategy_config_mdl = strategy_config_mdl
        self._min_value = self._strategy_config_mdl.miv_value
        self._max_value = self._strategy_config_mdl.max_value

    def get_strategy_config(self) -> StrategyConfigModel:
        return self._strategy_config_mdl

    def get_strategy_data(self, param: StrategyParamModel) -> pd.DataFrame:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: get_strategy_data({param.model_dump()})"
            )

    def get_strategy_data_by_history_data(
        self, historyt_data_mdl: HistoryDataModel
    ) -> pd.DataFrame:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: get_strategy_data_by_history_data(symbol={historyt_data_mdl.print_model()})"
            )


class Strategy_CCI(StrategyBase):
    def __init__(self, strategy_config_mdl: StrategyConfigModel):
        StrategyBase.__init__(self, strategy_config_mdl)
        self._cci = Indicator_CCI(self._strategy_config_mdl.length)

    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)
        default_limit = self._cci.get_length() + 2
        limit = param.limit + default_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        return self.get_strategy_data_by_history_data(history_data_mdl)

    def get_strategy_data_by_history_data(self, history_data_mdl: HistoryDataModel):
        super().get_strategy_data_by_history_data(history_data_mdl)
        cci_df = self._cci.get_indicator_by_history_data(history_data_mdl)
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

            if self._max_value and self._min_value == 0:
                if current_value > self._max_value and previous_value < self._max_value:
                    decision = Const.STRONG_BUY
                elif (
                    current_value < self._max_value and previous_value > self._max_value
                ):
                    decision = Const.STRONG_SELL
            else:
                decision = self._get_signal_decision(
                    current_value=current_value, previous_value=previous_value
                )

            signals.append(decision)

        return signals

    def _get_signal_decision(self, current_value, previous_value):
        decision = ""
        if current_value > self._max_value:
            if previous_value < self._max_value:
                decision = Const.BUY
        elif current_value < self._min_value:
            if previous_value > self._min_value:
                decision = Const.SELL
        else:
            if previous_value > self._max_value:
                decision = Const.STRONG_SELL
            elif previous_value < self._min_value:
                decision = Const.STRONG_BUY

        return decision


class Strategy_CCI_Trend_Base(Strategy_CCI):
    def get_strategy_data(self, param: StrategyParamModel):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: get_strategy_data({param.model_dump()})"
            )

    def get_strategy_data_by_history_data(self, history_data_mdl: HistoryDataModel):
        logger.error(
            f"{self.__class__.__name__}: get_strategy_data_by_history_data - Can't be used for this strategy)"
        )
        raise Exception(
            f"{self.__class__.__name__}: get_strategy_data_by_history_data - Can't be used for this strategy)"
        )

    def _get_up_trend_param(
        self, param: StrategyParamModel
    ) -> TraderSymbolIntervalLimitModel:
        interval = param.interval
        limit = param.limit
        next_interval = None
        # Detect Next Interval
        if interval == IntervalType.MIN_5:
            next_interval = IntervalType.MIN_15
            limit = limit // 3 + 1
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
            logger.error(
                f"{self.__class__.__name__}: get_strategy_data - Incorrect interval for subscription)"
            )
            raise Exception(
                f"{self.__class__.__name__}: get_strategy_data - Incorrect interval for subscription)"
            )

        if not next_interval:
            return None

        trend_param = TraderSymbolIntervalLimitModel(**param.model_dump())
        trend_param.interval = next_interval
        trend_param.limit = limit

        return trend_param


class StrategyDirectionBasedTrend_CCI(Strategy_CCI_Trend_Base):
    def get_strategy_data(self, param: StrategyParamModel):
        # Get Trend data
        trend_param = TraderSymbolIntervalLimitModel(**param.model_dump())
        trend_df = TrendCCI().calculate_trends(trend_param)

        indicator_param = IndicatorParamModel(**param.model_dump())
        cci_df = self._cci.get_indicator(indicator_param)

        cci_df = pd.merge(
            cci_df,
            trend_df[[Const.PARAM_TREND]],
            how="left",
            left_on=Const.COLUMN_DATETIME,
            right_on=Const.COLUMN_DATETIME,
        )

        # Generate Up Trend Param
        up_trend_param = self._get_up_trend_param(param)

        if not up_trend_param:
            merged_df = cci_df
        else:
            # Get Trend data for the upper timeframe
            up_trend_df = TrendCCI().calculate_trends(up_trend_param)

            # Assuming cci and trend are your DataFrames
            # Reset index to make the datetime column a regular column
            cci_df.reset_index(inplace=True)
            up_trend_df.reset_index(inplace=True)

            # Merge the DataFrames based on the datetime column
            merged_df = pd.merge_asof(
                cci_df,
                up_trend_df[[Const.COLUMN_DATETIME, Const.PARAM_TREND]],
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


class Strategy_CCI_100_TrendUpLevel(Strategy_CCI_Trend_Base):
    def get_strategy_data(self, param: StrategyParamModel):
        symbol = param.symbol
        limit = param.limit
        interval = param.interval

        indicator_param = IndicatorParamModel(**param.model_dump())
        cci_df = self._cci.get_indicator(indicator_param)

        # Generate Up Trend Param
        up_trend_param = self._get_up_trend_param(param)

        # Get Trend data for the next timeframe
        trend_df = TrendCCI().calculate_trends(up_trend_param)

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
