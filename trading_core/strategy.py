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
    StrategyModel,
    StrategyConfigModel,
    SignalModel,
    HistoryDataParamModel,
    StrategyParamModel,
    SignalParamModel,
    RiskType,
)
from .handler import buffer_runtime_handler, ExchangeHandler
from .indicator import Indicator_CCI_ATR
from .trend import TrendCCI


class SignalFactory:
    def get_signal(self, param: SignalParamModel) -> SignalModel:
        signal_mdl = self._get_signal(param)
        if signal_mdl and signal_mdl.is_compatible(signal_types=param.types):
            if config.get_config_value(Const.CONF_PROPERTY_CORE_LOG):
                logger.info(
                    f"{self.__class__.__name__}: Signal will be used - {signal_mdl.model_dump()}"
                )

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
        if config.get_config_value(Const.CONF_PROPERTY_CORE_LOG):
            logger.info(f"{self.__class__.__name__}: get_signal({param.model_dump()})")

        signal_mdl: SignalModel = None

        # Check traiding time and skip closed symbols
        if not buffer_runtime_handler.get_symbol_handler(
            trader_id=param.trader_id
        ).is_trading_available(interval=param.interval, symbol=param.symbol):
            return None

        # Take signal from buffer
        if param.from_buffer:
            buffer_handler = buffer_runtime_handler.get_signal_handler()

            buffer_key = self._get_buffer_key(
                trader_id=param.trader_id,
                symbol=param.symbol,
                interval=param.interval.value,
                strategy=param.strategy.value,
            )

            if buffer_handler.is_data_in_buffer(key=buffer_key):
                signal_mdl = buffer_handler.get_buffer(key=buffer_key)

                if config.get_config_value(Const.CONF_PROPERTY_CORE_LOG):
                    logger.info(
                        f"{self.__class__.__name__}: Check Signal from Buffer - {signal_mdl.model_dump()}"
                    )

                end_date_time = ExchangeHandler.get_handler(
                    trader_id=param.trader_id
                ).get_end_datetime(
                    interval=param.interval, closed_bars=param.closed_bars
                )

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
                stop_loss_value=strategy_row[Const.FLD_STOP_LOSS_VALUE],
                take_profit_value=strategy_row[Const.FLD_TAKE_PROFIT_VALUE],
                signal=strategy_row[Const.PARAM_SIGNAL],
            )
            break

        if signal_mdl:
            if param.from_buffer:
                buffer_handler.set_buffer(key=buffer_key, data=signal_mdl)

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
                f"{self.__class__.__name__}: Buffer key is invalid: symbol: {symbol}, interval: {interval}, strategy: {strategy}"
            )
        buffer_key = (trader_id, symbol, interval, strategy)

        if config.get_config_value(Const.CONF_PROPERTY_CORE_LOG):
            logger.info(f"{self.__class__.__name__}: Get Buffer key - {buffer_key}")

        return buffer_key


class StrategyFactory:
    @staticmethod
    def get_strategy_data(param: StrategyParamModel):
        strategy = param.strategy
        strategy_instance = None

        strategy_config_mdl = StrategyFactory.get_strategy_config(strategy)

        if strategy in [
            StrategyType.CCI_50_CROSS_0,
            StrategyType.CCI_14_CROSS_100,
            StrategyType.CCI_20_CROSS_100,
        ]:
            strategy_instance = Strategy_CCI(strategy_config_mdl)

        elif strategy == StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14:
            strategy_instance = Strategy_EMA_8_CROSS_EMA_30_FILTER_CCI_14(
                strategy_config_mdl
            )

        elif strategy == StrategyType.EMA_30_CROSS_EMA_100:
            strategy_instance = EMA_30_CROSS_EMA_100(strategy_config_mdl)

        elif strategy == StrategyType.EMA_30_CROSS_EMA_100_FILTER_CCI_50:
            strategy_instance = EMA_30_CROSS_EMA_100_FILTER_CCI_50(strategy_config_mdl)

        elif strategy == StrategyType.EMA_8_CROSS_EMA_30_FILTER_EMA_100:
            strategy_instance = EMA_8_CROSS_EMA_30_FILTER_EMA_100(strategy_config_mdl)

        elif strategy in [StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND]:
            strategy_instance = EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND(
                strategy_config_mdl
            )

        elif strategy in [
            StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP,
        ]:
            strategy_instance = EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP(
                strategy_config_mdl
            )

        else:
            raise Exception(
                f"{StrategyFactory.__name__}: Strategy {strategy} isn't implemented"
            )

        strategy_data = strategy_instance.get_strategy_data(param)
        return strategy_data

    @staticmethod
    def get_strategy_config_dict_vh() -> dict:
        return {
            StrategyType.CCI_14_CROSS_100: StrategyConfigModel(
                strategy=StrategyType.CCI_14_CROSS_100,
                name="1. CCI(14) cross +/- 100",
                history_limit=16,
                length=14,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.CCI_20_CROSS_100: StrategyConfigModel(
                strategy=StrategyType.CCI_20_CROSS_100,
                name="2. CCI(20) cross +/- 100",
                is_close_by_signal=True,
                risk_type=RiskType.DEFAULT,
                tp_move_limit=0.7,
                tp_move_step=0.25,
                tp_increment_limit=0,
                history_limit=22,
                length=20,
                miv_value=-100,
                max_value=100,
            ),
            StrategyType.CCI_50_CROSS_0: StrategyConfigModel(
                strategy=StrategyType.CCI_50_CROSS_0,
                name="3. CCI(50) cross 0",
                history_limit=52,
                length=50,
                miv_value=0,
                max_value=0,
            ),
            StrategyType.EMA_30_CROSS_EMA_100: StrategyConfigModel(
                strategy=StrategyType.EMA_30_CROSS_EMA_100,
                name="4. EMA(30) cross EMA(100)",
                history_limit=300,
                ema_short=30,
                ema_long=100,
            ),
            StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14: StrategyConfigModel(
                strategy=StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14,
                name="5. EMA(8) cross EMA(30) Filter CCI(14) +/- 100",
                is_close_by_signal=False,
                history_limit=100,
                length=14,
                miv_value=-100,
                max_value=100,
                ema_short=8,
                ema_long=30,
            ),
            StrategyType.EMA_30_CROSS_EMA_100_FILTER_CCI_50: StrategyConfigModel(
                strategy=StrategyType.EMA_30_CROSS_EMA_100_FILTER_CCI_50,
                name="6. EMA(30) cross EMA(100) Filter CCI(50)",
                history_limit=300,
                ema_short=30,
                ema_long=100,
            ),
            StrategyType.EMA_8_CROSS_EMA_30_FILTER_EMA_100: StrategyConfigModel(
                strategy=StrategyType.EMA_8_CROSS_EMA_30_FILTER_EMA_100,
                name="7. EMA(8) cross EMA(30) Filter EMA(100)",
                history_limit=300,
                ema_short=8,
                ema_medium=30,
                ema_long=100,
            ),
            StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND: StrategyConfigModel(
                strategy=StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND,
                name="8. EMA(50) cross EMA(100) Filter Up Level Trend",
                history_limit=300,
                ema_short=50,
                ema_long=100,
            ),
            StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP: StrategyConfigModel(
                strategy=StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP,
                name="9. SL bound to TP - EMA(50) cross EMA(100) Filter Up Level Trend",
                risk_type=RiskType.SL_BOUND_TO_TP,
                tp_move_limit=0.7,
                tp_move_step=0.25,
                tp_increment_limit=2,
                history_limit=300,
                ema_short=50,
                ema_long=100,
            ),
        }

    @staticmethod
    def get_strategy_config_list_vh() -> list[StrategyConfigModel]:
        return [
            strategy_mdl
            for strategy_mdl in StrategyFactory.get_strategy_config_dict_vh().values()
        ]

    @staticmethod
    def get_strategy_model(strategy: StrategyType) -> StrategyModel:
        strategy_config = StrategyFactory.get_strategy_config(strategy)

        return StrategyModel(**strategy_config.model_dump())

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
        if config.get_config_value(Const.CONF_PROPERTY_CORE_LOG):
            logger.info(
                f"{self.__class__.__name__}: get_strategy_data({param.model_dump()})"
            )

    def _determine_signal(self, df: pd.DataFrame) -> SignalType:
        pass

    def _determine_stop_loss_value(self, df: pd.DataFrame) -> float:
        pass

    def _determine_take_profit_value(self, df: pd.DataFrame) -> float:
        pass


class Strategy_EMA_Base(StrategyBase):
    def _get_ema_delta(self, short_ema: float, long_ema: float) -> float:
        return short_ema - long_ema

    def _get_ema_cross_signal(
        self, delta_target_emas: float, delta_previous_emas: float
    ) -> SignalType:
        signal = SignalType.NONE

        if delta_target_emas > 0:
            # Current - LONG
            if delta_previous_emas <= 0:
                # Previous - SHORT
                signal = SignalType.STRONG_BUY
        else:
            # Current - SHORT
            if delta_previous_emas >= 0:
                # Previous - LONG
                signal = SignalType.STRONG_SELL

        return signal

    def _get_2_emas_trend(
        self, short_ema: float, long_ema: float
    ) -> TrendDirectionType:
        if short_ema > long_ema:
            # LONG
            return TrendDirectionType.TREND_UP
        elif short_ema <= long_ema:
            # SHORT
            return TrendDirectionType.TREND_DOWN

    def _get_3_emas_trend(
        self, short_ema: float, medium_ema: float, long_ema: float
    ) -> TrendDirectionType:
        # For ex. EMAs: 8, 30, 100
        short_medium_trend = self._get_2_emas_trend(
            short_ema=short_ema, long_ema=medium_ema
        )
        short_long_trend = self._get_2_emas_trend(
            short_ema=short_ema, long_ema=long_ema
        )
        medium_long_trend = self._get_2_emas_trend(
            short_ema=medium_ema, long_ema=long_ema
        )

        if medium_long_trend == TrendDirectionType.TREND_UP:
            # LONG:
            # 30 upper 100
            if short_medium_trend == TrendDirectionType.TREND_UP:
                # 8 upper 30 - this scenario is for open LONG position, when previous bar has TREND_UP
                return TrendDirectionType.STRONG_TREND_UP
            else:
                # 8 lower 30
                if short_long_trend == TrendDirectionType.TREND_UP:
                    # 8 upper 100 - this scenario detects corrections
                    return TrendDirectionType.TREND_UP
                else:
                    # 8 lower 100 - this scenario is for close LONG position, when previous bar has TREND_UP or STRONG_TREND_UP
                    return TrendDirectionType.TREND_DOWN
        else:
            # SHORT
            # 30 lower 100
            if short_medium_trend == TrendDirectionType.TREND_DOWN:
                # 8 lower 30 - this scenario is for open SHORT position, when previous bar has TREND_DOWN
                return TrendDirectionType.STRONG_TREND_DOWN
            else:
                # 8 upper 30
                if short_long_trend == TrendDirectionType.TREND_DOWN:
                    # 8 lower 100 - this scenario detects corrections
                    return TrendDirectionType.TREND_DOWN
                else:
                    # 8 upper 100 - this scenario is for close SHORT position, when previous bar has TREND_DOWN or STRONG_TREND_DOWN
                    return TrendDirectionType.TREND_UP

    def _get_up_level_param(self, param: StrategyParamModel) -> StrategyParamModel:
        interval = param.interval
        limit = param.limit
        next_interval = None
        # Detect Next Interval
        if interval == IntervalType.MIN_1:
            next_interval = IntervalType.MIN_15
            limit = limit // 15 + 1
        elif interval == IntervalType.MIN_5:
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
            logger.error(
                f"{self.__class__.__name__}: get_strategy_data - Incorrect interval for subscription)"
            )
            raise Exception(
                f"{self.__class__.__name__}: get_strategy_data - Incorrect interval for subscription)"
            )

        if not next_interval:
            return None

        up_level_param = StrategyParamModel(**param.model_dump())
        up_level_param.interval = next_interval
        up_level_param.limit = limit

        return up_level_param

    def _determine_trend(self, df):
        ema_short = None
        ema_medium = None
        ema_long = None
        trends = []

        for i in range(len(df)):
            bar = df.iloc[i]

            if self._strategy_config_mdl.ema_short != 0:
                ema_short = bar[Const.FLD_EMA_SHORT]

            if self._strategy_config_mdl.ema_medium != 0:
                ema_medium = bar[Const.FLD_EMA_MEDIUM]

            if self._strategy_config_mdl.ema_long != 0:
                ema_long = bar[Const.FLD_EMA_LONG]

            if ema_short and ema_long:
                if ema_medium:
                    trend = self._get_3_emas_trend(
                        short_ema=ema_short,
                        medium_ema=ema_medium,
                        long_ema=ema_long,
                    )
                else:
                    trend = self._get_2_emas_trend(
                        short_ema=ema_short, long_ema=ema_long
                    )

                trends.append(trend)

        return trends


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
            cci_df.shape[1], Const.PARAM_SIGNAL, self._determine_signal(cci_df)
        )

        # Determive Stop Loss Value = 2 * ATR
        cci_df.insert(
            cci_df.shape[1],
            Const.FLD_STOP_LOSS_VALUE,
            self._determine_stop_loss_value(cci_df),
        )

        # Determive Take Profit Value = 3 * ATR
        cci_df.insert(
            cci_df.shape[1],
            Const.FLD_TAKE_PROFIT_VALUE,
            self._determine_take_profit_value(cci_df),
        )

        return cci_df

    def _determine_signal(self, cci_df):
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

    def _determine_stop_loss_value(self, df: pd.DataFrame):
        values = []

        for i in range(len(df)):
            value = 2 * df.iloc[i][Const.FLD_ATR]
            values.append(value)

        return values

    def _determine_take_profit_value(self, df: pd.DataFrame):
        values = []

        for i in range(len(df)):
            value = 3 * df.iloc[i][Const.FLD_ATR]
            values.append(value)

        return values

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


class Strategy_EMA_8_CROSS_EMA_30_FILTER_CCI_14(StrategyBase):
    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)
        limit = param.limit + self._strategy_config_mdl.display_rows
        history_limit = param.limit + self._strategy_config_mdl.history_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = history_limit

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
                    "col_names": (Const.FLD_CCI, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "atr",
                    "length": 14,
                    "col_names": (Const.FLD_ATR),
                },
                {
                    "kind": "ema",
                    "length": 8,
                    "col_names": (Const.FLD_EMA_8),
                },
                {
                    "kind": "ema",
                    "length": 30,
                    "col_names": (Const.FLD_EMA_30),
                },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        df = df.dropna(
            subset=[
                Const.FLD_CCI,
                Const.FLD_ATR,
                Const.FLD_EMA_8,
                Const.FLD_EMA_30,
            ]
        )

        df = df.tail(limit)

        df.insert(df.shape[1], Const.PARAM_SIGNAL, self._determine_signal(df))

        # Determive Stop Loss Value = 2 * ATR
        df.insert(
            df.shape[1],
            Const.FLD_STOP_LOSS_VALUE,
            self._determine_stop_loss_value(df),
        )

        # Determive Take Profit Value = 3 * ATR
        df.insert(
            df.shape[1],
            Const.FLD_TAKE_PROFIT_VALUE,
            self._determine_take_profit_value(df),
        )

        return df

    def _determine_signal(self, df):
        signals = []

        for i in range(len(df)):
            decision = ""

            if i < 2:
                signals.append(decision)
                continue

            current_bar = df.iloc[i]
            current_cci = current_bar[Const.FLD_CCI]

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

            signals.append(decision)

        return signals

    def _determine_stop_loss_value(self, df: pd.DataFrame):
        values = []

        for i in range(len(df)):
            value = 2 * df.iloc[i][Const.FLD_ATR]
            values.append(value)

        return values

    def _determine_take_profit_value(self, df: pd.DataFrame):
        values = []

        for i in range(len(df)):
            value = 3 * df.iloc[i][Const.FLD_ATR]
            values.append(value)

        return values

    def _get_ema_cross_signal(self, target_series, previous_series) -> SignalType:
        target_ema_8 = target_series[Const.FLD_EMA_8]
        target_ema_30 = target_series[Const.FLD_EMA_30]

        previous_ema_8 = previous_series[Const.FLD_EMA_8]
        previous_ema_30 = previous_series[Const.FLD_EMA_30]

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


class EMA_30_CROSS_EMA_100(Strategy_EMA_Base):
    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)

        limit = param.limit + self._strategy_config_mdl.display_rows
        history_limit = param.limit + self._strategy_config_mdl.history_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = history_limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        # Create your own Custom Strategy
        CustomStrategy = ta.Strategy(
            name="EMA_30_CROSS_EMA_100",
            description="EMA 30 crosses EMA 100",
            ta=[
                {
                    "kind": "ema",
                    "length": 30,
                    "col_names": (Const.FLD_EMA_30, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "ema",
                    "length": 100,
                    "col_names": (Const.FLD_EMA_100),
                },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        # Remove initial values from DF
        df = df.dropna(
            subset=[
                Const.FLD_EMA_30,
                Const.FLD_EMA_100,
            ]
        )

        # Calculate Strategy data only for requested limit + 3
        df = df.tail(limit)

        df.insert(df.shape[1], Const.FLD_SIGNAL, self._determine_signal(df))

        # Determive Stop Loss Value
        df.insert(
            df.shape[1], Const.FLD_STOP_LOSS_VALUE, self._determine_stop_loss_value(df)
        )

        # Determive Take Profit Value
        df.insert(
            df.shape[1],
            Const.FLD_TAKE_PROFIT_VALUE,
            self._determine_take_profit_value(df),
        )

        return df

    def _determine_stop_loss_value(self, df):
        values = []
        lv_ema_100_shift = 0.002

        for i in range(len(df)):
            stop_loss_value = 0

            current_bar = df.iloc[i]
            current_close = current_bar[Const.FLD_CLOSE]
            current_ema_30 = current_bar[Const.FLD_EMA_30]
            current_ema_100 = current_bar[Const.FLD_EMA_100]

            # Stop Loss calculation
            if current_ema_100 > current_ema_30:
                # SHORT
                # SL Price = EMA 100 + 0.5%
                stop_loss_price = (1 + lv_ema_100_shift) * current_ema_100
                if stop_loss_price > current_close:
                    stop_loss_value = stop_loss_price - current_close
                else:
                    stop_loss_value = lv_ema_100_shift * current_ema_100
            else:
                # LONG
                # SL Price = EMA 100 - 0.5%
                stop_loss_price = (1 - lv_ema_100_shift) * current_ema_100
                if stop_loss_price < current_close:
                    stop_loss_value = current_close - stop_loss_price
                else:
                    stop_loss_value = lv_ema_100_shift * current_ema_100

            values.append(stop_loss_value)

        return values

    def _determine_take_profit_value(self, df):
        values = []

        for i in range(len(df)):
            take_profit_value = 0

            current_bar = df.iloc[i]
            stop_loss_value = current_bar[Const.FLD_STOP_LOSS_VALUE]

            take_profit_value = 2 * stop_loss_value

            values.append(take_profit_value)

        return values

    def _determine_signal(self, df):
        signals = []

        for i in range(len(df)):
            decision = SignalType.NONE

            if i < 1:
                signals.append(decision)
                continue

            current_bar = df.iloc[i]
            previous_bar = df.iloc[i - 1]

            decision = self._get_ema_signal(
                target_series=current_bar, previous_series=previous_bar
            )

            signals.append(decision)

        return signals

    def _get_ema_signal(self, target_series, previous_series) -> SignalType:
        signal = SignalType.NONE

        target_ema_30 = target_series[Const.FLD_EMA_30]
        target_ema_100 = target_series[Const.FLD_EMA_100]

        previous_ema_30 = previous_series[Const.FLD_EMA_30]
        previous_ema_100 = previous_series[Const.FLD_EMA_100]

        delta_target_ema_30_100 = self._get_ema_delta(
            short_ema=target_ema_30, long_ema=target_ema_100
        )
        delta_previous_ema_30_100 = self._get_ema_delta(
            short_ema=previous_ema_30, long_ema=previous_ema_100
        )

        if delta_target_ema_30_100 > 0:
            # Current - LONG
            if delta_previous_ema_30_100 <= 0:
                # Previous - SHORT
                signal = SignalType.STRONG_BUY
        else:
            # Current - SHORT
            if delta_previous_ema_30_100 >= 0:
                # Previous - LONG
                signal = SignalType.STRONG_SELL

        return signal


class EMA_30_CROSS_EMA_100_FILTER_CCI_50(Strategy_EMA_Base):
    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)

        limit = param.limit + self._strategy_config_mdl.display_rows
        history_limit = param.limit + self._strategy_config_mdl.history_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = history_limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        # Create your own Custom Strategy
        CustomStrategy = ta.Strategy(
            name="EMA_30_CROSS_EMA_100_FILTER_CCI_50",
            description="EMA 30 cross EMA 100 with filter CCI(20) +/- 100 and Trend CCi(50)",
            ta=[
                {
                    "kind": "cci",
                    "length": 50,
                    "col_names": (Const.FLD_CCI, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "ema",
                    "length": 30,
                    "col_names": (Const.FLD_EMA_30),
                },
                {
                    "kind": "ema",
                    "length": 100,
                    "col_names": (Const.FLD_EMA_100),
                },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        # Remove initial values from DF
        df = df.dropna(
            subset=[
                Const.FLD_CCI,
                Const.FLD_EMA_30,
                Const.FLD_EMA_100,
            ]
        )

        # Exclude rest data from calculation
        df = df.tail(limit + 10)

        df.insert(df.shape[1], Const.FLD_SIGNAL, self._determine_signal(df))

        # Determive Stop Loss Value
        df.insert(
            df.shape[1], Const.FLD_STOP_LOSS_VALUE, self._determine_stop_loss_value(df)
        )

        # Determive Take Profit Value
        df.insert(
            df.shape[1],
            Const.FLD_TAKE_PROFIT_VALUE,
            self._determine_take_profit_value(df),
        )

        # Calculate Strategy data only for requested limit + 3
        df = df.tail(limit)

        return df

    def _determine_stop_loss_value(self, df):
        values = []
        lv_ema_100_shift = 0.01

        for i in range(len(df)):
            stop_loss_value = 0

            current_bar = df.iloc[i]
            current_close = current_bar[Const.FLD_CLOSE]
            current_ema_30 = current_bar[Const.FLD_EMA_30]
            current_ema_100 = current_bar[Const.FLD_EMA_100]

            # Stop Loss calculation
            if current_ema_100 > current_ema_30:
                # SHORT
                # SL Price = EMA 100 + 0.5%
                stop_loss_price = (1 + lv_ema_100_shift) * current_ema_100
                if stop_loss_price > current_close:
                    stop_loss_value = stop_loss_price - current_close
                else:
                    stop_loss_value = lv_ema_100_shift * current_ema_100
            else:
                # LONG
                # SL Price = EMA 100 - 0.5%
                stop_loss_price = (1 - lv_ema_100_shift) * current_ema_100
                if stop_loss_price < current_close:
                    stop_loss_value = current_close - stop_loss_price
                else:
                    stop_loss_value = lv_ema_100_shift * current_ema_100

            values.append(stop_loss_value)

        return values

    def _determine_take_profit_value(self, df):
        values = []

        for i in range(len(df)):
            take_profit_value = 0

            current_bar = df.iloc[i]
            stop_loss_value = current_bar[Const.FLD_STOP_LOSS_VALUE]

            take_profit_value = stop_loss_value

            values.append(take_profit_value)

        return values

    def _determine_signal(self, df):
        signals = []

        LIMIT = 10
        trend_up_counter = 0
        trend_down_counter = 0

        for i in range(len(df)):
            decision = SignalType.NONE

            current_bar = df.iloc[i]
            current_cci = current_bar[Const.FLD_CCI]

            # Calculate counter of trend bars
            if current_cci > 0:
                trend_up_counter += 1
                trend_down_counter = 0
            else:
                trend_down_counter += 1
                trend_up_counter = 0

            if i < 10:
                signals.append(decision)
                continue

            previous_bar = df.iloc[i - 1]

            decision = self._get_ema_signal(
                target_series=current_bar, previous_series=previous_bar
            )

            if decision == SignalType.STRONG_BUY:
                if trend_up_counter >= LIMIT:
                    pass
                else:
                    decision = SignalType.BUY
            elif decision == SignalType.STRONG_SELL:
                if trend_down_counter >= LIMIT:
                    pass
                else:
                    decision = SignalType.SELL
            else:
                decision = SignalType.NONE

            signals.append(decision)

        return signals

    def _get_ema_signal(self, target_series, previous_series) -> SignalType:
        signal = SignalType.NONE

        target_ema_30 = target_series[Const.FLD_EMA_30]
        target_ema_100 = target_series[Const.FLD_EMA_100]

        previous_ema_30 = previous_series[Const.FLD_EMA_30]
        previous_ema_100 = previous_series[Const.FLD_EMA_100]

        delta_target_ema_30_100 = self._get_ema_delta(
            short_ema=target_ema_30, long_ema=target_ema_100
        )
        delta_previous_ema_30_100 = self._get_ema_delta(
            short_ema=previous_ema_30, long_ema=previous_ema_100
        )

        if delta_target_ema_30_100 > 0:
            # Current - LONG
            if delta_previous_ema_30_100 <= 0:
                # Previous - SHORT
                signal = SignalType.STRONG_BUY
        else:
            # Current - SHORT
            if delta_previous_ema_30_100 >= 0:
                # Previous - LONG
                signal = SignalType.STRONG_SELL

        return signal


class EMA_8_CROSS_EMA_30_FILTER_EMA_100(Strategy_EMA_Base):
    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)

        limit = param.limit + self._strategy_config_mdl.display_rows
        history_limit = param.limit + self._strategy_config_mdl.history_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = history_limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        # Create your own Custom Strategy
        CustomStrategy = ta.Strategy(
            name="EMA_8_CROSS_EMA_30_FILTER_EMA_100",
            description="EMA 30 cross EMA 30 with filter EMA 100",
            ta=[
                {
                    "kind": "atr",
                    "length": 14,
                    "col_names": (Const.FLD_ATR, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "ema",
                    "length": 8,
                    "col_names": (Const.FLD_EMA_SHORT),
                },
                {
                    "kind": "ema",
                    "length": 30,
                    "col_names": (Const.FLD_EMA_MEDIUM),
                },
                {
                    "kind": "ema",
                    "length": 100,
                    "col_names": (Const.FLD_EMA_LONG),
                },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        # Remove initial values from DF
        df = df.dropna(
            subset=[
                Const.FLD_EMA_SHORT,
                Const.FLD_EMA_MEDIUM,
                Const.FLD_EMA_LONG,
            ]
        )

        # Calculate Strategy data only for requested limit + 3
        df = df.tail(limit)

        df.insert(df.shape[1], Const.FLD_TREND, self._determine_trend(df))

        df.insert(df.shape[1], Const.FLD_SIGNAL, self._determine_signal(df))

        # Determive Stop Loss Value
        df.insert(
            df.shape[1], Const.FLD_STOP_LOSS_VALUE, self._determine_stop_loss_value(df)
        )

        # Determive Take Profit Value
        df.insert(
            df.shape[1],
            Const.FLD_TAKE_PROFIT_VALUE,
            self._determine_take_profit_value(df),
        )

        return df

    def _determine_stop_loss_value(self, df):
        values = []
        lv_ema_100_shift = 0.002

        for i in range(len(df)):
            stop_loss_value = 0

            current_bar = df.iloc[i]
            current_close = current_bar[Const.FLD_CLOSE]
            current_ema_30 = current_bar[Const.FLD_EMA_MEDIUM]
            current_ema_100 = current_bar[Const.FLD_EMA_LONG]

            # Stop Loss calculation
            if current_ema_100 > current_ema_30:
                # SHORT
                # SL Price = EMA 100 + 0.5%
                stop_loss_price = (1 + lv_ema_100_shift) * current_ema_100
                if stop_loss_price > current_close:
                    stop_loss_value = stop_loss_price - current_close
                else:
                    stop_loss_value = lv_ema_100_shift * current_ema_100
            else:
                # LONG
                # SL Price = EMA 100 - 0.5%
                stop_loss_price = (1 - lv_ema_100_shift) * current_ema_100
                if stop_loss_price < current_close:
                    stop_loss_value = current_close - stop_loss_price
                else:
                    stop_loss_value = lv_ema_100_shift * current_ema_100

            values.append(stop_loss_value)

        return values

    def _determine_take_profit_value(self, df):
        values = []

        for i in range(len(df)):
            take_profit_value = 0

            current_bar = df.iloc[i]
            stop_loss_value = current_bar[Const.FLD_STOP_LOSS_VALUE]

            take_profit_value = 2 * stop_loss_value

            values.append(take_profit_value)

        return values

    def _determine_signal(self, df):
        signals = []

        for i in range(len(df)):
            signal = SignalType.NONE

            if i < 1:
                signals.append(signal)
                continue

            current_bar = df.iloc[i]
            previous_bar = df.iloc[i - 1]

            current_trend = current_bar[Const.FLD_TREND]
            previous_trend = previous_bar[Const.FLD_TREND]

            if current_trend == TrendDirectionType.STRONG_TREND_UP:
                if previous_trend in [
                    TrendDirectionType.TREND_DOWN,
                    TrendDirectionType.TREND_UP,
                ]:
                    # 8 upper 30 - this scenario is for open LONG position, when previous bar has TREND_UP
                    signal = SignalType.STRONG_BUY
                else:
                    signal = SignalType.NONE

            elif current_trend == TrendDirectionType.STRONG_TREND_DOWN:
                if previous_trend in [
                    TrendDirectionType.TREND_DOWN,
                    TrendDirectionType.TREND_UP,
                ]:
                    # 8 lower 30 - this scenario is for open SHORT position, when previous bar has TREND_DOWN
                    signal = SignalType.STRONG_SELL
                else:
                    signal = SignalType.NONE

            else:
                signal = SignalType.NONE

            signals.append(signal)

        return signals


class EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND(Strategy_EMA_Base):
    """
    SL = EMA_100_UP_LEVEL +/- ATR_UP_LEVEL
    TP = 2 * SL

    Close signal: EMA_100 / EMA_100_UP_LEVEL

    Open signal: EMA_50 / EMA_100

    When EMA_30_UP_LEVEL / EMA_100_UP_LEVEL

    Robot:
    TP increment = 4
    TP step = 15 % (0.15)
    TP limit = 70 % (0.7)
    """

    SUFFIX_UP_LEVEL = "_up_level"
    FLD_EMA_LONG_UP_LEVEL = Const.FLD_EMA_LONG + SUFFIX_UP_LEVEL
    FLD_SIGNAL_UP_LEVEL = Const.FLD_SIGNAL + SUFFIX_UP_LEVEL
    FLD_ATR_UP_LEVEL = Const.FLD_ATR + SUFFIX_UP_LEVEL

    def get_strategy_data(self, param: StrategyParamModel):
        super().get_strategy_data(param)

        limit = param.limit + self._strategy_config_mdl.display_rows
        history_limit = param.limit + self._strategy_config_mdl.history_limit

        history_data_param = HistoryDataParamModel(**param.model_dump())
        history_data_param.limit = history_limit

        history_data_mdl = buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

        # Create your own Custom Strategy
        CustomStrategy = ta.Strategy(
            name="EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND",
            description="EMA 50 cross EMA 100 with filter Up Level Trend",
            ta=[
                # {
                #     "kind": "bbands",
                #     "length": 20,
                #     "col_names": (
                #         Const.FLD_BB_LOWER,
                #         Const.FLD_BB_MID,
                #         Const.FLD_BB_UPPER,
                #         Const.FLD_BB_BANDWIDTH,
                #         Const.FLD_BB_PERCENT,
                #         "MULTIPROCESSING_OFF",
                #     ),
                # },
                {
                    "kind": "atr",
                    "length": 14,
                    "col_names": (Const.FLD_ATR, "MULTIPROCESSING_OFF"),
                },
                {
                    "kind": "ema",
                    "length": 50,
                    "col_names": (Const.FLD_EMA_SHORT),
                },
                {
                    "kind": "ema",
                    "length": 100,
                    "col_names": (Const.FLD_EMA_LONG),
                },
            ],
        )
        # To run your "Custom Strategy"
        df = pd.DataFrame(history_data_mdl.data)
        df.ta.strategy(CustomStrategy)

        # Remove initial values from DF
        df = df.dropna(
            subset=[
                Const.FLD_EMA_SHORT,
                Const.FLD_EMA_LONG,
            ]
        )

        # Exclude rest data from calculation
        df = df.tail(limit)

        df.insert(df.shape[1], Const.FLD_TREND, self._determine_trend(df))

        # Generate Up Trend Param
        up_level_param = self._get_up_level_param(param)
        up_level_param.strategy = StrategyType.EMA_8_CROSS_EMA_30_FILTER_EMA_100

        if not up_level_param:
            merged_df = df
        else:
            up_level_df = StrategyFactory.get_strategy_data(up_level_param)

            # Assuming cci and trend are your DataFrames
            # Reset index to make the datetime column a regular column
            df.reset_index(inplace=True)
            up_level_df.reset_index(inplace=True)

            # Merge the DataFrames based on the datetime column
            merged_df = pd.merge_asof(
                df,
                up_level_df[
                    [
                        Const.COLUMN_DATETIME,
                        Const.FLD_TREND,
                        Const.FLD_EMA_LONG,
                        Const.FLD_SIGNAL,
                        Const.FLD_ATR,
                    ]
                ],
                left_on=Const.COLUMN_DATETIME,
                right_on=Const.COLUMN_DATETIME,
                direction="backward",
                suffixes=("", "_up_level"),
            )

            merged_df = merged_df.rename(
                columns={Const.FLD_SIGNAL: self.FLD_SIGNAL_UP_LEVEL}
            )

            # Set the datetime column as the index again
            merged_df.set_index(Const.COLUMN_DATETIME, inplace=True)

        merged_df.insert(
            merged_df.shape[1], Const.FLD_SIGNAL, self._determine_signal(merged_df)
        )

        # Determive Stop Loss Value
        merged_df.insert(
            merged_df.shape[1],
            Const.FLD_STOP_LOSS_VALUE,
            self._determine_stop_loss_value(merged_df),
        )

        # Determive Take Profit Value
        merged_df.insert(
            merged_df.shape[1],
            Const.FLD_TAKE_PROFIT_VALUE,
            self._determine_take_profit_value(merged_df),
        )

        return merged_df

    def _determine_stop_loss_value(self, df):
        values = []

        for i in range(len(df)):
            stop_loss_value = 0

            current_bar = df.iloc[i]
            current_close = current_bar[Const.FLD_CLOSE]
            up_level_trend = current_bar[Const.FLD_TREND_UP_LEVEL]
            current_ema_long_up_level = current_bar[self.FLD_EMA_LONG_UP_LEVEL]
            up_level_atr_value = current_bar[self.FLD_ATR_UP_LEVEL]

            # Stop Loss calculation
            if up_level_trend in [
                TrendDirectionType.TREND_DOWN,
                TrendDirectionType.STRONG_TREND_DOWN,
            ]:
                # SHORT
                stop_loss_price = current_ema_long_up_level + up_level_atr_value
                stop_loss_value = stop_loss_price - current_close

            else:
                # LONG
                stop_loss_price = current_ema_long_up_level - up_level_atr_value
                stop_loss_value = current_close - stop_loss_price

            values.append(stop_loss_value)

        return values

    def _determine_take_profit_value(self, df):
        values = []

        for i in range(len(df)):
            take_profit_value = 0

            current_bar = df.iloc[i]
            # up_level_atr_value = current_bar[self.FLD_ATR_UP_LEVEL]
            stop_loss_value = current_bar[Const.FLD_STOP_LOSS_VALUE]

            take_profit_value = stop_loss_value

            values.append(take_profit_value)

        return values

    def _determine_signal(self, df):
        signals = []

        for i in range(len(df)):
            signal = SignalType.NONE

            if i < 1:
                signals.append(signal)
                continue

            current_bar = df.iloc[i]
            previous_bar = df.iloc[i - 1]

            current_trend = current_bar[Const.FLD_TREND]
            previous_trend = previous_bar[Const.FLD_TREND]

            trend_up_level = current_bar[Const.FLD_TREND_UP_LEVEL]
            signal_up_level = current_bar[self.FLD_SIGNAL_UP_LEVEL]

            if current_trend == TrendDirectionType.TREND_UP and trend_up_level in [
                TrendDirectionType.STRONG_TREND_UP,
                TrendDirectionType.TREND_UP,
            ]:
                if previous_trend == TrendDirectionType.TREND_DOWN:
                    signal = SignalType.STRONG_BUY

            elif current_trend == TrendDirectionType.TREND_DOWN and trend_up_level in [
                TrendDirectionType.STRONG_TREND_DOWN,
                TrendDirectionType.TREND_DOWN,
            ]:
                if previous_trend == TrendDirectionType.TREND_UP:
                    signal = SignalType.STRONG_SELL

            elif signal_up_level == SignalType.STRONG_BUY:
                signal = SignalType.BUY
            elif signal_up_level == SignalType.STRONG_SELL:
                signal = SignalType.SELL
            else:
                signal = SignalType.NONE

            signals.append(signal)

        return signals


class EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP(
    EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND
):
    def _determine_stop_loss_value(self, df):
        values = []

        for i in range(len(df)):
            stop_loss_value = 0

            current_bar = df.iloc[i]
            current_close = current_bar[Const.FLD_CLOSE]
            up_level_trend = current_bar[Const.FLD_TREND_UP_LEVEL]
            current_ema_long = current_bar[Const.FLD_EMA_LONG]
            up_level_atr_value = current_bar[self.FLD_ATR_UP_LEVEL]

            # Stop Loss calculation
            if up_level_trend in [
                TrendDirectionType.TREND_DOWN,
                TrendDirectionType.STRONG_TREND_DOWN,
            ]:
                # SHORT
                stop_loss_price = current_ema_long + up_level_atr_value
                stop_loss_value = stop_loss_price - current_close

            else:
                # LONG
                stop_loss_price = current_ema_long - up_level_atr_value
                stop_loss_value = current_close - stop_loss_price

            values.append(stop_loss_value)

        return values

    def _determine_take_profit_value(self, df):
        values = []

        for i in range(len(df)):
            take_profit_value = 0

            current_bar = df.iloc[i]
            up_level_atr_value = current_bar[self.FLD_ATR_UP_LEVEL]
            # stop_loss_value = current_bar[Const.FLD_STOP_LOSS_VALUE]

            take_profit_value = 2 * up_level_atr_value

            values.append(take_profit_value)

        return values
