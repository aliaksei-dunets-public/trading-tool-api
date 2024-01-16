from trading_core.handler import ExchangeHandler
import trading_core.common as cmn
import pandas_ta as ta
import pandas as pd

handler = ExchangeHandler.get_handler(trader_id="658dab8b3b0719ad3f9b53dd")
symbol = "LDOUSDT"

# closes = handler.get_close_leverages(symbol=symbol, limit=5)
# print(closes)

print(
    handler.get_close_position(
        symbol=symbol, order_id="8b13e11d-4bd1-4255-9c65-600d3416d23f"
    )
)

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
