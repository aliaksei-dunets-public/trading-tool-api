import pandas as pd
import json
import requests
import os
from copy import deepcopy

from trading_core.core import config
from trading_core.model import model, Symbols, ParamSimulation, ParamSymbolInterval, ParamSymbolIntervalLimit
from trading_core.simulation import Const, SimulateOptions, Executor
from trading_core.trend import TrendCCI, Indicator_CCI
from trading_core.handler import CurrencyComApi, LocalCurrencyComApi

# symbol = 'Natural Gas'
# interval = Const.TA_INTERVAL_4H
# strategy = Const.TA_STRATEGY_CCI_20_TREND_100

########################### Trend ###############################################

# param = ParamSymbolIntervalLimit(symbol=symbol,
#                                  interval=interval,
#                                  limit=100)

# params = [
#     ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_5M),
#           ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_15M),
#           ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_30M),
#           ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_1H),
#           ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_4H),
#           ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_1D),
#           ParamSymbolInterval(symbol=symbol,
#                               interval=Const.TA_INTERVAL_1WK)
#                               ]

# trends = TrendCCI().detect_trends(params)
# print(trends)

# trend_df = TrendCCI().calculate_trends(param)
# print(trend_df)

########################### Trend ###############################################

########################## Simulation ###############################################

# simulation_options_1 = SimulateOptions(init_balance=100,
#                                        limit=350,
#                                        stop_loss_rate=0,
#                                        take_profit_rate=11,
#                                        fee_rate=3)

# simulation_options_2 = SimulateOptions(init_balance=100,
#                                        limit=300,
#                                        stop_loss_rate=0,
#                                        take_profit_rate=0,
#                                        fee_rate=3)

params = []

symbols = Symbols(from_buffer=False).get_symbol_codes()
intervals = model.get_intervals()
sorted_strategies = model.get_sorted_strategy_codes()

for symbol in symbols:
    for interval in intervals:
        for strategy in sorted_strategies:
            for option in config.get_default_simulation_options(interval):
                params.append(ParamSimulation(symbol=symbol,
                                              interval=interval,
                                              strategy=strategy,
                                              simulation_options=deepcopy(option)))

# print(len(params))                                             

simulators = Executor().simulate_many_and_db_save(params)

print(len(simulators))

# for simulator in simulators:

#     df = pd.DataFrame(simulator.get_orders())

#     file_name = f'static/simulation.xlsx'

#     with pd.ExcelWriter(file_name) as writer:
#         df.to_excel(writer, sheet_name='analysis')

#     print(simulator.get_summary())
#     print(json.dumps(simulator.get_analysis()))

########################## Simulation ###############################################


########################### Write History Data to Local ###############################################

# api = LocalCurrencyComApi()

# api.write_symbols_to_local()

# symbol = 'BTC/USD'
# interval = Const.TA_INTERVAL_1WK
# limit = 500

# for interval in model.get_intervals():
#     api.write_to_local(symbol, interval, limit)

# url_params = {Const.PARAM_SYMBOL: symbol,
#               Const.INTERVAL: interval,
#               Const.LIMIT: limit}

# api_data = api.getHistoryData(symbol, interval, limit)

# print(api_data.getDataFrame())

########################### Write History Data to Local ###############################################
