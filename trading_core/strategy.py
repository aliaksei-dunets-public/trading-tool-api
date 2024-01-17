import pandas_ta as ta
import pandas as pd

from trading_core.common import StrategyParamModel

from .constants import Const
from .core import logger, config
from .common import (
    IntervalType,
    StrategyType,
    SignalType,
    TrendDirectionType,
    IndicatorType,
    StrategyConfigModel,
    SignalModel,
    HistoryDataParamModel,
    IndicatorParamModel,
    StrategyParamModel,
    SignalParamModel,
    TraderSymbolIntervalLimitModel,
)
from .handler import buffer_runtime_handler, ExchangeHandler
from .indicator import Indicator_CCI, Indicator_ATR, Indicator_CCI_ATR
from .trend import TrendCCI


class SignalFactory:
    def __init__(self) -> None:
        self.__buffer_inst = buffer_runtime_handler.get_signal_handler()

    def get_signal(self, param: SignalParamModel) -> SignalModel:
        signal_mdl = self._get_signal(param)
        if signal_mdl and signal_mdl.is_compatible(signal_types=param.types):
            return signal_mdl
        else:
            return None

    def get_signals(self, params: list[SignalParamModel]) -> list[SignalModel]:
        signal_mdls = []

        for signal_param in params:
            signal_mdl = self.get_signal(param=signal_param)
            if signal_mdl:
                signal_mdls.append(signal_mdl)

        return signal_mdls

    def get_signals_by_list(
        self,
        trader_id: str,
        symbols: list,
        intervals: list,
        strategies: list,
        signal_types: list,
        closed_bars: bool,
    ) -> list[SignalModel]:
        signal_params = []
        for symbol in symbols:
            for interval in intervals:
                for strategy in strategies:
                    signal_param = SignalParamModel(
                        trader_id=trader_id,
                        symbol=symbol,
                        interval=interval,
                        strategy=strategy,
                        from_buffer=True,
                        closed_bars=closed_bars,
                        types=signal_types,
                    )

                    signal_params.append(signal_param)

        return self.get_signals(params=signal_params)

    def _get_signal(self, param: SignalParamModel) -> SignalModel:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"{self.__class__.__name__}: get_signal({param.model_dump()})")

        signal_mdl: SignalModel = None

        # Take signal from buffer
        buffer_key = self._get_buffer_key(
            trader_id=param.trader_id,
            symbol=param.symbol,
            interval=param.interval.value,
            strategy=param.strategy.value,
        )

        if self.__buffer_inst.is_data_in_buffer(key=buffer_key):
            signal_mdl = self.__buffer_inst.get_buffer(key=buffer_key)

            end_date_time = ExchangeHandler.get_handler(
                trader_id=param.trader_id
            ).get_end_datetime(interval=param.interval, closed_bars=param.closed_bars)

            if end_date_time == signal_mdl.date_time:
                return signal_mdl

        # Calculate Signal
        strategy_df = StrategyFactory.get_strategy_data(param).tail(1)

        # Init signal model
        for index, strategy_row in strategy_df.iterrows():
            signal_mdl = SignalModel(
                trader_id=param.trader_id,
                symbol=param.symbol,
                interval=param.interval,
                strategy=param.strategy,
                limit=param.limit,
                from_buffer=param.from_buffer,
                closed_bars=param.closed_bars,
                date_time=index,
                open=strategy_row["Open"],
                high=strategy_row["High"],
                low=strategy_row["Low"],
                close=strategy_row["Close"],
                volume=strategy_row["Volume"],
                atr=strategy_row[IndicatorType.ATR.value],
                signal=strategy_row[Const.PARAM_SIGNAL],
            )
            break

        if signal_mdl:
            self.__buffer_inst.set_buffer(key=buffer_key, data=signal_mdl)

            return signal_mdl
        else:
            logger.error(
                f"{self.__class__.__name__}: Error during get_signal({param.model_dump()})"
            )
            raise Exception(
                f"{self.__class__.__name__}: Error during get_signal({param.model_dump()})"
            )

    def _get_buffer_key(
        self, trader_id: str, symbol: str, interval: str, strategy: str
    ) -> tuple:
        if not symbol or not interval or not strategy:
            Exception(
                f"{self.__class__.__name__} Buffer key is invalid: symbol: {symbol}, interval: {interval}, strategy: {strategy}"
            )
        buffer_key = (trader_id, symbol, interval, strategy)

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"{self.__class__.__name__} Signal buffer key - {buffer_key}")

        return buffer_key


class StrategyFactory:
    @staticmethod
    def get_strategy_data(param: StrategyParamModel):
        strategy = param.strategy
        strategy_instance = None

        strategy_config_mdl = StrategyFactory.get_strategy_config(strategy)

        if strategy in [
            StrategyType.CCI_50_TREND_0,
            StrategyType.CCI_14_TREND_100,
            StrategyType.CCI_20_TREND_100,
        ]:
            strategy_instance = Strategy_CCI(strategy_config_mdl)
        elif strategy in [
            StrategyType.CCI_14_BASED_TREND_100,
            StrategyType.CCI_20_BASED_TREND_100,
        ]:
            strategy_instance = StrategyDirectionBasedTrend_CCI(strategy_config_mdl)
        elif strategy in [
            StrategyType.CCI_20_100_TREND_UP_LEVEL,
            StrategyType.CCI_14_100_TREND_UP_LEVEL,
        ]:
            strategy_instance = Strategy_CCI_100_TrendUpLevel(strategy_config_mdl)
        elif strategy in [
            StrategyType.CCI_14_100_TRENDS_DIRECTION,
        ]:
            strategy_instance = Strategy_CCI_100_TRENDS_QUICK_POSITIONS(
                strategy_config_mdl
            )
        elif strategy in [
            StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14,
        ]:
            strategy_instance = Strategy_EMA_8_CROSS_EMA_30_FILTER_CCI_14(
                strategy_config_mdl
            )
        elif strategy in [
            StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_20,
        ]:
            strategy_instance = EMA_8_CROSS_EMA_30_FILTER_CCI_20(strategy_config_mdl)
        else:
            raise Exception(
                f"{StrategyFactory.__name__}: Strategy {strategy} isn't implemented"
            )

        strategy_data = strategy_instance.get_strategy_data(param)
        return strategy_data

    @staticmethod
    def get_strategy_config_dict_vh() -> dict:
        return {
            StrategyType.CCI_14_TREND_100: StrategyConfigModel(
                strategy=StrategyType.CCI_14_TREND_100,
                name="CCI(14) cross +/- 100",
                length=14,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.CCI_20_TREND_100: StrategyConfigModel(
                strategy=StrategyType.CCI_20_TREND_100,
                name="CCI(20) cross +/- 100",
                length=20,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.CCI_14_BASED_TREND_100: StrategyConfigModel(
                strategy=StrategyType.CCI_14_BASED_TREND_100,
                name="Check Trends and CCI(14) cross +/- 100",
                length=14,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.CCI_20_100_TREND_UP_LEVEL: StrategyConfigModel(
                strategy=StrategyType.CCI_20_100_TREND_UP_LEVEL,
                name="Check Trend Up Level and CCI(20) +/- 100",
                length=20,
                miv_value=-100,
                max_value=100,
            ),
            # StrategyType.CCI_14_100_TREND_UP_LEVEL: StrategyConfigModel(
            #     strategy=StrategyType.CCI_14_100_TREND_UP_LEVEL,
            #     name="Check Trend Up Level and CCI(14) +/- 100",
            #     length=14,
            #     miv_value=-100,
            #     max_value=100,
            # ),
            StrategyType.CCI_14_100_TRENDS_DIRECTION: StrategyConfigModel(
                strategy=StrategyType.CCI_14_100_TRENDS_DIRECTION,
                name="Quick positions for Trends and CCI(14) +/- 100",
                length=14,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14: StrategyConfigModel(
                strategy=StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14,
                name="EMA 8 crosses EMA 30 with filter CCI(14) +/- 100",
                length=14,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_20: StrategyConfigModel(
                strategy=StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_20,
                name="EMA 8 crosses EMA 30 with filter EMA 100 and CCI(20) +/- 100",
                length=20,
                miv_value=-100,
                max_value=100,
            ),
        }

    @staticmethod
    def get_strategy_config_list_vh() -> list[StrategyConfigModel]:
        return [
            strategy_mdl
            for strategy_mdl in StrategyFactory.get_strategy_config_dict_vh().values()
        ]

    @staticmethod
    def get_strategy_config(strategy: StrategyType) -> StrategyConfigModel:
        strategy_configs = StrategyFactory.get_strategy_config_dict_vh()
        if not strategy in strategy_configs:
            raise Exception(f"Strategy {strategy} doesn't exist")

        return strategy_configs[strategy]

    @staticmethod
    def get_strategies():
        return [item for item in StrategyFactory.get_strategy_config_dict_vh().keys()]

    @staticmethod
    def get_sorted_strategies(
        strategies: list = None, sort_by_desc: bool = True
    ) -> list[StrategyConfigModel]:
        strategy_configs = []

        if not strategies:
            strategy_configs = StrategyFactory.get_strategy_config_list_vh()
        else:
            for strategy in strategies:
                strategy_configs.append(StrategyFactory.get_strategy_config(strategy))

        if sort_by_desc:
            sorted_strategies = sorted(strategy_configs, key=lambda x: -x.length)
        else:
            sorted_strategies = sorted(strategy_configs, key=lambda x: x.length)

        return [item.strategy for item in sorted_strategies]


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


class Strategy_CCI(StrategyBase):
    def __init__(self, strategy_config_mdl: StrategyConfigModel):
        StrategyBase.__init__(self, strategy_config_mdl)
        self._cci = Indicator_CCI_ATR(self._strategy_config_mdl.length)

    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)
        default_limit = self._cci.get_length() + 2
        limit = param.limit + default_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

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

            decision = self._get_signal_decision(
                current_value=current_value, previous_value=previous_value
            )

            signals.append(decision)

        return signals

    def _get_signal_decision(self, current_value, previous_value):
        decision = ""
        if self._max_value == 0 and self._min_value == 0:
            if current_value > self._max_value and previous_value < self._max_value:
                decision = Const.STRONG_BUY
            elif current_value < self._max_value and previous_value > self._max_value:
                decision = Const.STRONG_SELL
        else:
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

    def _get_up_trend_param(
        self, param: StrategyParamModel
    ) -> TraderSymbolIntervalLimitModel:
        interval = param.interval
        limit = param.limit
        next_interval = None
        # Detect Next Interval
        if interval == IntervalType.MIN_1:
            next_interval = IntervalType.MIN_5
            limit = limit // 5 + 1
        elif interval == IntervalType.MIN_5:
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

    def _get_decision_base_trend(self, trend, cci_decision) -> str:
        if trend == Const.STRONG_TREND_UP:
            if cci_decision == Const.STRONG_SELL:
                cci_decision = Const.SELL
            elif cci_decision == Const.BUY:
                cci_decision = ""
        elif trend == Const.STRONG_TREND_DOWN:
            if cci_decision == Const.STRONG_BUY:
                cci_decision = Const.BUY
            elif cci_decision == Const.SELL:
                cci_decision = ""
        else:
            if cci_decision == Const.STRONG_BUY:
                cci_decision = Const.BUY
            elif cci_decision == Const.STRONG_SELL:
                cci_decision = Const.SELL

        return cci_decision


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
                suffixes=("", "_up_level"),
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

            trend = cci_df.iloc[i, 7]
            trend_previous = cci_df.iloc[i - 1, 7]

            if len(cci_df.columns) >= 9:
                trend_up_level = cci_df.iloc[i, 8]
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

            elif trend == Const.STRONG_TREND_UP:
                if trend_up_level in [Const.STRONG_TREND_UP, Const.TREND_UP]:
                    decision = self._get_signal_decision(current_value, previous_value)
                    if decision in [Const.SELL, Const.STRONG_SELL]:
                        decision = ""
                    elif decision == Const.BUY:
                        decision = Const.STRONG_BUY

            elif trend == Const.STRONG_TREND_DOWN:
                if trend_up_level in [Const.STRONG_TREND_DOWN, Const.TREND_DOWN]:
                    decision = self._get_signal_decision(current_value, previous_value)
                    if decision in [Const.BUY, Const.STRONG_BUY]:
                        decision = ""
                    elif decision == Const.SELL:
                        decision = Const.STRONG_SELL

            signals.append(decision)

        return signals

    def _get_decision_base_trend(self, trend, cci_decision) -> str:
        if trend in [Const.STRONG_TREND_UP, Const.TREND_UP]:
            if cci_decision == Const.STRONG_SELL:
                cci_decision = Const.SELL
            elif cci_decision == Const.BUY:
                cci_decision = ""
        elif trend in [Const.STRONG_TREND_DOWN, Const.TREND_DOWN]:
            if cci_decision == Const.STRONG_BUY:
                cci_decision = Const.BUY
            elif cci_decision == Const.SELL:
                cci_decision = ""

        return cci_decision


class Strategy_CCI_100_TrendUpLevel(Strategy_CCI_Trend_Base):
    def get_strategy_data(self, param: StrategyParamModel):
        indicator_param = IndicatorParamModel(**param.model_dump())
        cci_df = self._cci.get_indicator(indicator_param)

        # Generate Up Trend Param
        up_trend_param = self._get_up_trend_param(param)

        if up_trend_param:
            # Get Trend data for the next timeframe
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
            )

            merged_df = merged_df.rename(
                columns={Const.PARAM_TREND: f"{Const.PARAM_TREND}_up_level"}
            )

            # Set the datetime column as the index again
            merged_df.set_index(Const.COLUMN_DATETIME, inplace=True)

        else:
            merged_df = cci_df

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

            if len(cci_df.columns) >= 8:
                trend = cci_df.iloc[i, 7]

            if not trend:
                decision = ""
            else:
                decision = self._get_decision_base_trend(
                    trend=trend,
                    cci_decision=self._get_signal_decision(
                        current_value, previous_value
                    ),
                )

            signals.append(decision)

        return signals


class Strategy_CCI_100_TRENDS_QUICK_POSITIONS(Strategy_CCI_Trend_Base):
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
                suffixes=("", "_up_level"),
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
        trend_up_level = None

        for i in range(len(cci_df)):
            decision = ""

            if i == 0:
                signals.append(decision)
                continue

            current_value = cci_df.iloc[i, 5]
            previous_value = cci_df.iloc[i - 1, 5]

            trend = cci_df.iloc[i, 7]
            trend_previous = cci_df.iloc[i - 1, 7]

            if len(cci_df.columns) >= 9:
                trend_up_level = cci_df.iloc[i, 8]

            decision = self._get_signal_decision(current_value, previous_value)

            # if trend == Const.STRONG_TREND_UP:
            #     if decision != Const.STRONG_BUY:
            #         decision = ""
            # elif trend == Const.STRONG_TREND_DOWN:
            #     if decision != Const.STRONG_SELL:
            #         decision = ""

            if trend_up_level in [Const.STRONG_TREND_UP, Const.STRONG_TREND_DOWN]:
                decision = self._get_decision_base_trend(
                    trend=trend_up_level, cci_decision=decision
                )

            signals.append(decision)

        return signals


class Strategy_EMA_8_CROSS_EMA_30_FILTER_CCI_14(StrategyBase):
    CCI_COLUMN_NAME = "CCI"
    ATR_COLUMN_NAME = "ATR"
    EMA_8_COLUMN_NAME = "EMA_8"
    EMA_30_COLUMN_NAME = "EMA_30"

    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)
        default_limit = 32
        limit = param.limit + default_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        # Create your own Custom Strategy
        CustomStrategy = ta.Strategy(
            name="EMA_8_CROSS_EMA_30_FILTER_CCI_14",
            description="EMA 8 crosses EMA 30 with filter CCI(14) +/- 100",
            ta=[
                {
                    "kind": "cci",
                    "length": 14,
                    "col_names": (self.CCI_COLUMN_NAME, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "atr",
                    "length": 14,
                    "col_names": (self.ATR_COLUMN_NAME),
                },
                {
                    "kind": "ema",
                    "length": 8,
                    "col_names": (self.EMA_8_COLUMN_NAME),
                },
                {
                    "kind": "ema",
                    "length": 30,
                    "col_names": (self.EMA_30_COLUMN_NAME),
                },
                # {
                #     "kind": "macd",
                #     "fast": 8,
                #     "slow": 21,
                #     "col_names": ("MACD", "MACD_H", "MACD_S"),
                # },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        df = df.dropna(
            subset=[
                self.CCI_COLUMN_NAME,
                self.CCI_COLUMN_NAME,
                self.EMA_8_COLUMN_NAME,
                self.EMA_30_COLUMN_NAME,
            ]
        )

        df.insert(df.shape[1], Const.PARAM_SIGNAL, self._determineSignal(df))

        return df

    def _determineSignal(self, df):
        signals = []

        for i in range(len(df)):
            decision = ""

            if i < 2:
                signals.append(decision)
                continue

            current_bar = df.iloc[i]
            current_cci = current_bar[self.CCI_COLUMN_NAME]

            previous_bar = df.iloc[i - 1]
            second_previous_bar = df.iloc[i - 2]

            decision = self._get_ema_cross_signal(
                target_series=previous_bar, previous_series=second_previous_bar
            )

            if decision == SignalType.STRONG_BUY:
                if current_cci <= self._strategy_config_mdl.max_value:
                    decision = SignalType.NONE
            elif decision == SignalType.STRONG_SELL:
                if current_cci >= self._strategy_config_mdl.miv_value:
                    decision = SignalType.NONE

            # current_cci = df.iloc[i, 5]
            # previous_cci = df.iloc[i - 1, 5]

            # current_ema_8 = df.iloc[i, 7]
            # previous_ema_8 = df.iloc[i - 1, 7]

            # current_ema_30 = df.iloc[i, 8]
            # previous_ema_30 = df.iloc[i - 1, 8]

            # current_delta = current_ema_8 - current_ema_30
            # previous_delta = previous_ema_8 - previous_ema_30

            # if current_delta >= 0:
            #     # Current - LONG
            #     if previous_delta >= 0:
            #         # Previous - LONG
            #         pass
            #     else:
            #         # Previous - SHORT
            #         decision = Const.STRONG_BUY
            # else:
            #     # SHORT
            #     if previous_delta >= 0:
            #         # Previous - LONG
            #         decision = Const.STRONG_SELL
            #     else:
            #         # Previous - SHORT
            #         pass

            signals.append(decision)

        return signals

    def _get_ema_cross_signal(self, target_series, previous_series) -> SignalType:
        target_ema_8 = target_series[self.EMA_8_COLUMN_NAME]
        target_ema_30 = target_series[self.EMA_30_COLUMN_NAME]

        previous_ema_8 = previous_series[self.EMA_8_COLUMN_NAME]
        previous_ema_30 = previous_series[self.EMA_30_COLUMN_NAME]

        target_delta = target_ema_8 - target_ema_30
        previous_delta = previous_ema_8 - previous_ema_30

        if target_delta >= 0:
            # Current - LONG
            if previous_delta >= 0:
                # Previous - LONG
                decision = SignalType.NONE
            else:
                # Previous - SHORT
                decision = SignalType.STRONG_BUY
        else:
            # SHORT
            if previous_delta >= 0:
                # Previous - LONG
                decision = SignalType.STRONG_SELL
            else:
                # Previous - SHORT
                decision = SignalType.NONE

        return decision

    def _get_signal_decision(self, current_value, previous_value):
        decision = ""
        if self._max_value == 0 and self._min_value == 0:
            if current_value > self._max_value and previous_value < self._max_value:
                decision = Const.STRONG_BUY
            elif current_value < self._max_value and previous_value > self._max_value:
                decision = Const.STRONG_SELL
        else:
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


class EMA_8_CROSS_EMA_30_FILTER_CCI_20(StrategyBase):
    CCI_COLUMN_NAME = "CCI"
    ATR_COLUMN_NAME = "ATR"
    EMA_8_COLUMN_NAME = "EMA_8"
    EMA_30_COLUMN_NAME = "EMA_30"
    EMA_100_COLUMN_NAME = "EMA_100"

    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)
        default_limit = 102
        limit = param.limit + default_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        # Create your own Custom Strategy
        CustomStrategy = ta.Strategy(
            name="EMA_8_CROSS_EMA_30_FILTER_CCI_14",
            description="EMA 8 crosses EMA 30 with filter CCI(14) +/- 100",
            ta=[
                {
                    "kind": "cci",
                    "length": 14,
                    "col_names": (self.CCI_COLUMN_NAME, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "atr",
                    "length": 14,
                    "col_names": (self.ATR_COLUMN_NAME),
                },
                {
                    "kind": "ema",
                    "length": 8,
                    "col_names": (self.EMA_8_COLUMN_NAME),
                },
                {
                    "kind": "ema",
                    "length": 30,
                    "col_names": (self.EMA_30_COLUMN_NAME),
                },
                {
                    "kind": "ema",
                    "length": 100,
                    "col_names": (self.EMA_100_COLUMN_NAME),
                },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        df = df.dropna(
            subset=[
                self.CCI_COLUMN_NAME,
                self.CCI_COLUMN_NAME,
                self.EMA_8_COLUMN_NAME,
                self.EMA_30_COLUMN_NAME,
                self.EMA_100_COLUMN_NAME,
            ]
        )

        df.insert(df.shape[1], Const.PARAM_SIGNAL, self._determineSignal(df))

        return df

    def _determineSignal(self, df):
        signals = []

        for i in range(len(df)):
            decision = ""

            if i < 2:
                signals.append(decision)
                continue

            current_bar = df.iloc[i]
            current_cci = current_bar[self.CCI_COLUMN_NAME]

            previous_bar = df.iloc[i - 1]
            previous_cci = previous_bar[self.CCI_COLUMN_NAME]

            ema_decision = self._get_ema_signal(
                target_series=current_bar, previous_series=previous_bar
            )

            decision = self._get_cci_signal(
                current_value=current_cci, previous_value=previous_cci
            )

            if ema_decision in [SignalType.STRONG_BUY, SignalType.STRONG_SELL]:
                # Take signal based on EMA cross
                decision = ema_decision
            elif ema_decision == SignalType.BUY:
                # In this case decision take into account CCI_20 strategy with UP trend direction: sell for STRONG_BUY and BUY signals
                if decision == SignalType.BUY:
                    decision = SignalType.STRONG_BUY
                elif decision in [SignalType.STRONG_SELL, SignalType.SELL]:
                    decision = SignalType.NONE
            elif ema_decision == SignalType.SELL:
                # In this case decision take into account CCI_20 strategy with Down trend direction: sell for STRONG_SELL and SELL signals
                if decision == SignalType.SELL:
                    decision = SignalType.STRONG_SELL
                elif decision in [SignalType.STRONG_BUY, SignalType.BUY]:
                    decision = SignalType.NONE
            else:
                decision = SignalType.NONE

            signals.append(decision)

        return signals

    def _get_trend_direction(self, ema_short, ema_long) -> TrendDirectionType:
        delta = ema_short - ema_long
        return (
            TrendDirectionType.TREND_UP if delta > 0 else TrendDirectionType.TREND_DOWN
        )

    def _get_ema_signal(self, target_series, previous_series) -> SignalType:
        decision = SignalType.NONE

        target_ema_8 = target_series[self.EMA_8_COLUMN_NAME]
        target_ema_30 = target_series[self.EMA_30_COLUMN_NAME]
        target_ema_100 = target_series[self.EMA_100_COLUMN_NAME]

        previous_ema_8 = previous_series[self.EMA_8_COLUMN_NAME]
        previous_ema_30 = previous_series[self.EMA_30_COLUMN_NAME]

        target_ema_8_30_trend = self._get_trend_direction(
            ema_short=target_ema_8, ema_long=target_ema_30
        )
        target_ema_8_100_trend = self._get_trend_direction(
            ema_short=target_ema_8, ema_long=target_ema_100
        )
        target_ema_30_100_trend = self._get_trend_direction(
            ema_short=target_ema_30, ema_long=target_ema_100
        )

        previous_ema_8_30_trend = self._get_trend_direction(
            ema_short=previous_ema_8, ema_long=previous_ema_30
        )

        if target_ema_8_30_trend == TrendDirectionType.TREND_UP:
            # Current - LONG
            if previous_ema_8_30_trend == TrendDirectionType.TREND_DOWN:
                # Previous - SHORT
                decision = SignalType.STRONG_BUY
            elif (
                target_ema_8_100_trend == TrendDirectionType.TREND_UP
                and target_ema_30_100_trend == TrendDirectionType.TREND_UP
            ):
                # Current - LONG
                decision = SignalType.BUY
            else:
                decision = SignalType.NONE

        else:
            # Current - SHORT
            if previous_ema_8_30_trend == TrendDirectionType.TREND_UP:
                # Previous - LONG
                decision = SignalType.STRONG_SELL
            elif (
                target_ema_8_100_trend == TrendDirectionType.TREND_DOWN
                and target_ema_30_100_trend == TrendDirectionType.TREND_DOWN
            ):
                # Current - SHORT
                decision = SignalType.SELL
            else:
                decision = SignalType.NONE

        return decision

    def _get_cci_signal(self, current_value, previous_value) -> SignalType:
        decision = ""
        if current_value > self._max_value:
            if previous_value < self._max_value:
                decision = SignalType.STRONG_BUY
        elif current_value < self._min_value:
            if previous_value > self._min_value:
                decision = SignalType.STRONG_SELL
        else:
            if previous_value > self._max_value:
                decision = SignalType.STRONG_SELL
            elif previous_value < self._min_value:
                decision = SignalType.STRONG_BUY

        return decision
