from trading_core.handler import ExchangeHandler
import trading_core.common as cmn
import pandas_ta as ta
import pandas as pd

handler = ExchangeHandler.get_handler(trader_id="658048536aed0b022350af0b")
symbol = "SOLUSDT"

params = cmn.HistoryDataParamModel(
    symbol=symbol, interval=cmn.IntervalType.MIN_5, limit=500
)

history_data_mdl = handler.get_history_data(params)
df = history_data_mdl.data

print(df)

# Create your own Custom Strategy
CustomStrategy = ta.Strategy(
    name="Momo and Volatility",
    description="SMA 50,200, BBANDS, RSI, MACD and Volume SMA 20",
    ta=[
        # {
        #     "kind": "dema",
        #     "length": 50,
        # },
        # {
        #     "kind": "dema",
        #     "length": 100,
        # },
        {
            "kind": "cci",
            "length": 20,
            "col_names": ("CCI_20"),
        },
        {
            "kind": "cci",
            "length": 50,
            "col_names": ("CCI_50"),
        },
        # {
        #     "kind": "atr",
        #     "length": 14,
        # },
        {
            "kind": "macd",
            "fast": 8,
            "slow": 21,
            "col_names": ("MACD", "MACD_H", "MACD_S"),
        },
    ],
)
# To run your "Custom Strategy"
df.ta.strategy(CustomStrategy)

print(df)
