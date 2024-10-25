from trading_core.handler import ExchangeHandler
import trading_core.common as cmn
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta
import trading_core.responser as responser

responser.job_func_run_history_simulation(
    symbols=["AVAXUSDT"],
    intervals=[cmn.IntervalType.MIN_5],
    strategies=[
        cmn.StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND,
    ],
)

# handler = ExchangeHandler.get_handler(trader_id="658dab8b3b0719ad3f9b53dd")
# symbol = "LDOUSDT"

# params = cmn.HistoryDataParamModel(
#     symbol=symbol, interval=cmn.IntervalType.MIN_5, limit=1200
# )

# history_data = handler.get_history_data(history_data_param=params, start="", end="")

# print(history_data.data)

# local_datetime = datetime.now()
# closd_datetime = handler.get_end_datetime(interval=params.interval)

# offset_date_time = local_datetime - timedelta(minutes=525600)

# print(closd_datetime)
# print(offset_date_time)

# params = cmn.HistoryDataParamModel(
#     symbol=symbol, interval=cmn.IntervalType.MIN_5, limit=500
# )

# history_data_mdl = handler.get_history_data(params)
# df = history_data_mdl.data

# print(df)

# # Create your own Custom Strategy
# CustomStrategy = ta.Strategy(
#     name="Momo and Volatility",
#     description="SMA 50,200, BBANDS, RSI, MACD and Volume SMA 20",
#     ta=[
#         # {
#         #     "kind": "dema",
#         #     "length": 50,
#         # },
#         # {
#         #     "kind": "dema",
#         #     "length": 100,
#         # },
#         {
#             "kind": "cci",
#             "length": 20,
#             "col_names": ("CCI_20"),
#         },
#         {
#             "kind": "cci",
#             "length": 50,
#             "col_names": ("CCI_50"),
#         },
#         # {
#         #     "kind": "atr",
#         #     "length": 14,
#         # },
#         {
#             "kind": "macd",
#             "fast": 8,
#             "slow": 21,
#             "col_names": ("MACD", "MACD_H", "MACD_S"),
#         },
#     ],
# )
# # To run your "Custom Strategy"
# df.ta.strategy(CustomStrategy)

# print(df)

# import statistics
# import numpy as np

# take_profit_rates = [1, 2.3, 0.4, 1.5, 0.1, 0.9, 1.1, 0.9, 0.92, 1.56]

# print(f"Mean {statistics.mean(take_profit_rates)}")
# print(f"Median {statistics.median(take_profit_rates)}")
# print(f"Persintale {np.percentile(take_profit_rates, 80)}")
