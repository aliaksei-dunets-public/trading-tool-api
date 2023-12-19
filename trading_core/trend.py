import pandas as pd

from .core import logger, config, Const
from .indicator import Indicator_CCI
from .common import TraderSymbolIntervalLimitModel, IndicatorParamModel, IndicatorType

GLOBAL_TREND_COUNT = 10
# LOCAL_TREND_COUNT = 8
# QUICK_TREND_COUNT = 6


class TrendBase:
    def __init__(self):
        pass


# Sum of the 16 bars:
# > 0 - UpTrend
# < 0 - DonwTrend

# Sum of the 8 bars:
# > 0 - UpTrend
# < 0 - DonwTrend


class TrendCCI(TrendBase):
    def calculate_trends(self, param: TraderSymbolIntervalLimitModel):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: calculate_trends({param.model_dump()})"
            )

        trends = []

        limit = param.limit + GLOBAL_TREND_COUNT - 1
        param.limit = limit

        # Get indecator CCI(50) data
        cci_50_df = self.__get_cci_data(length=50, param=param)

        for i in range(len(cci_50_df) + 1):
            if i < GLOBAL_TREND_COUNT:
                continue

            cci_info = self.__get_cci_info(
                cci_50_df.iloc[i - GLOBAL_TREND_COUNT : i, 5]
            )
            trend_info = self.__get_trend_info(cci_info)

            trends.append(trend_info)

        df = pd.DataFrame(trends)
        df.set_index(Const.COLUMN_DATETIME, inplace=True)

        return df

    def detect_trends(self, params: list[TraderSymbolIntervalLimitModel]):
        trends = []

        for param in params:
            trends.append(self.detect_trend(param))

        return trends

    def detect_trend(self, param: TraderSymbolIntervalLimitModel):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: detect_trend({param.model_dump()})"
            )

        length_cci_50 = 50
        limit = length_cci_50 + GLOBAL_TREND_COUNT + 1

        param_with_limit = TraderSymbolIntervalLimitModel(
            param.symbol, interval=param.interval, limit=limit, consistency_check=False
        )

        cci_50_df = self.__get_cci_data(length=50, param=param_with_limit)
        cci_info = self.__get_cci_info(cci_50_df[IndicatorType.CCI.name])
        trend_info = self.__get_trend_info(cci_info)

        return {
            Const.PARAM_SYMBOL: param.symbol,
            Const.INTERVAL: param.interval,
            Const.PARAM_TREND: trend_info[Const.PARAM_TREND],
            Const.PARAM_SIGNAL: trend_info[Const.PARAM_SIGNAL],
        }

    def __get_cci_data(
        self, length: int, param: TraderSymbolIntervalLimitModel
    ) -> pd.DataFrame:
        cci = Indicator_CCI(length)
        indicator_param = IndicatorParamModel(**param.model_dump())
        df_cci = cci.get_indicator(indicator_param)
        return df_cci

    def __get_cci_info(self, df_cci: pd.DataFrame) -> dict:
        mean_global_cci = df_cci.tail(GLOBAL_TREND_COUNT).mean()

        return {
            Const.COLUMN_DATETIME: df_cci.tail(1).index[0],
            IndicatorType.CCI.name: df_cci.iloc[-1],
            GLOBAL_TREND_COUNT: mean_global_cci,
        }

    def __get_trend_info(self, cci_info: dict) -> dict:
        mean_global_cci = cci_info[GLOBAL_TREND_COUNT]
        cci_info[Const.PARAM_TREND] = self.__get_trend_descr(mean_global_cci, 70)
        return cci_info

    def __get_trend_descr(self, value, length) -> str:
        if value < -length:
            return Const.STRONG_TREND_DOWN
        elif value <= 0:
            return Const.TREND_DOWN
        elif value > length:
            return Const.STRONG_TREND_UP
        elif value > 0:
            return Const.TREND_UP
