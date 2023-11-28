import pandas as pd

from .constants import Const
from .model import model, ParamSymbolInterval, ParamSymbolIntervalLimit
from .indicator import Indicator_CCI

GLOBAL_TREND_COUNT = 16
LOCAL_TREND_COUNT = 8
QUICK_TREND_COUNT = 6


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
    def calculate_trends(self, param: ParamSymbolIntervalLimit):
        trends = []

        length_cci_50 = 50 if param.limit <= 50 else param.limit
        limit = length_cci_50 + GLOBAL_TREND_COUNT + 10

        param_new = ParamSymbolIntervalLimit(
            symbol=param.symbol,
            interval=param.interval,
            limit=limit,
            consistency_check=False,
        )

        # Get indecator CCI(50) data
        cci_50_df = self.__get_cci_data(length=50, param=param_new)

        for i in range(len(cci_50_df) + 1):
            if i < 16:
                continue

            cci_info = self.__get_cci_info(cci_50_df.iloc[i - 16 : i, 5])
            trend_info = self.__get_trend_info(cci_info)

            trends.append(trend_info)

        df = pd.DataFrame(trends)
        df.set_index(Const.COLUMN_DATETIME, inplace=True)

        return df

    def detect_trends(self, params: list[ParamSymbolInterval]):
        trends = []

        for param in params:
            trends.append(self.detect_trend(param))

        return trends

    def detect_trend(self, param: ParamSymbolInterval):
        length_cci_50 = 50
        limit = length_cci_50 + GLOBAL_TREND_COUNT + 15

        param_with_limit = ParamSymbolIntervalLimit(
            param.symbol, interval=param.interval, limit=limit, consistency_check=False
        )

        cci_50_df = self.__get_cci_data(length=50, param=param_with_limit)

        cci_info = self.__get_cci_info(cci_50_df[Const.TA_INDICATOR_CCI])

        trend_info = self.__get_trend_info(cci_info)

        return {
            Const.PARAM_SYMBOL: param.symbol,
            Const.INTERVAL: param.interval,
            Const.PARAM_TREND: trend_info[Const.PARAM_TREND],
            Const.PARAM_SIGNAL: trend_info[Const.PARAM_SIGNAL],
            # "CCI_50": cci_info
        }

    def __get_cci_data(
        self, length: int, param: ParamSymbolIntervalLimit
    ) -> pd.DataFrame:
        cci = Indicator_CCI(length)
        df_cci = cci.get_indicator(
            symbol=param.symbol,
            interval=param.interval,
            limit=param.limit,
            from_buffer=True,
            closed_bars=False,
        )

        return df_cci

    def __get_cci_info(self, df_cci: pd.DataFrame) -> dict:
        mean_16_cci = df_cci.tail(GLOBAL_TREND_COUNT).mean()
        mean_8_cci = df_cci.tail(LOCAL_TREND_COUNT).mean()

        return {
            Const.COLUMN_DATETIME: df_cci.tail(1).index[0],
            Const.TA_INDICATOR_CCI: df_cci[-1],
            GLOBAL_TREND_COUNT: mean_16_cci,
            LOCAL_TREND_COUNT: mean_8_cci,
        }

    def __get_trend_info(self, cci_info: dict) -> dict:
        trend = ""
        signal = ""

        mean_8_cci = cci_info[LOCAL_TREND_COUNT]
        mean_16_cci = cci_info[GLOBAL_TREND_COUNT]
        local_trend = self.__get_local_trend_descr(mean_8_cci)
        global_trend = self.__get_global_trend_descr(mean_16_cci)

        # Local trend (8) is UP
        if local_trend == Const.TREND_UP:
            # Global trend (16) is UP
            if global_trend == Const.TREND_UP:
                # Then Trend is UP
                trend = Const.TREND_UP
            # elif cci_info[Const.TA_INDICATOR_CCI] < 0:
            #     trend = Const.TREND_DOWN
            elif global_trend == Const.TREND_DOWN:
                # Else Global trend (16) is Down -> # Then Trend is UP and Trend changed
                trend = Const.TREND_UP
                signal = Const.TREND_CHANGED
            else:
                trend = None
                signal = None
        elif local_trend == Const.TREND_DOWN:
            # Local trend (8) is DOWN
            # Global trend (16) is UP
            if global_trend == Const.TREND_UP:
                # Global trend (16) is UP -> # Then Trend is DOWN and Trend changed
                trend = Const.TREND_DOWN
                signal = Const.TREND_CHANGED
            # elif cci_info[Const.TA_INDICATOR_CCI] > 0:
            #     trend = Const.TREND_UP
            elif global_trend == Const.TREND_DOWN:
                # Else Trend is DOWN
                trend = Const.TREND_DOWN
            else:
                trend = None
                signal = None

        cci_info[Const.PARAM_TREND] = trend
        cci_info[Const.PARAM_SIGNAL] = signal

        return cci_info

    def __get_local_trend_descr(self, value) -> str:
        if value < -30:
            return Const.TREND_DOWN
        elif value > 30:
            return Const.TREND_UP
        else:
            return None

    def __get_global_trend_descr(self, value) -> str:
        if value < -70:
            return Const.TREND_DOWN
        elif value > 70:
            return Const.TREND_UP
        else:
            return None
