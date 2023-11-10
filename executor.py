########################## New Model ###############################################
from trading_core.handler import (
    ExchangeId,
    TraderModel,
    SymbolHandler,
    TraderHandler,
    ExchangeHandler,
    HistoryDataParam,
    HistoryDataHandler,
    SessionModel,
    SessionHandler,
)

from trading_core.robot import SessionManager

session_mdl = SessionHandler.get_session(id="654bc2351536fced145c3cfa")
session_mng = SessionManager(session_mdl)
session_mng.run()


########################## New Model ###############################################


########################## Demo Accaunt ###############################################
# import requests
# import time
# import datetime
# import hmac
# import hashlib
# from datetime import datetime, timedelta
# import math

# from trading_core.core import config
# from trading_core.model import model
# from trading_core.handler import DemoCurrencyComApi, OrderSide, OrderType

# try:
#     handler = DemoCurrencyComApi()

#     # print(handler.get_account_info())

#     # print(
#     #     handler.new_order(
#     #         symbol="LTC/USD_LEVERAGE",
#     #         side=OrderSide.BUY,
#     #         order_type=OrderType.MARKET,
#     #         quantity=1,
#     #         account_id="167893441795404062",
#     #     )
#     # )

#     print(handler.close_trading_position("00a0c503-1e55-311e-0000-0000802c029b"))

#     # print(handler.get_open_orders())

#     print(handler.get_trading_positions())

# except Exception as err:
#     print(err)

########################## Demo Accaunt ###############################################


# import pandas as pd
# import json
# import requests
# import os
# from copy import deepcopy

# from trading_core.core import config
# from trading_core.model import model, Symbols, ParamSimulation, ParamSymbolInterval, ParamSymbolIntervalList, ParamSymbolIntervalLimit, ParamSimulationList
# from trading_core.simulation import Const, SimulateOptions, Executor
# from trading_core.trend import TrendCCI, Indicator_CCI
# from trading_core.handler import CurrencyComApi, LocalCurrencyComApi

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
#
# params = []
#
# symbols = Symbols(from_buffer=False).get_symbol_codes()
# intervals = model.get_intervals()
# sorted_strategies = model.get_sorted_strategy_codes()

# objParamSimulationList = ParamSimulationList(symbols=['EPAM'])

# params = objParamSimulationList.get_param_simulation_list()

# simulators = Executor().simulate_many_and_db_save(params)

# print(len(simulators))

# for simulator in simulators:

#     df = pd.DataFrame(simulator.get_orders())

#     file_name = f'static/simulation.xlsx'

#     with pd.ExcelWriter(file_name) as writer:
#         df.to_excel(writer, sheet_name='analysis')

#     print(simulator.get_summary())
#     print(json.dumps(simulator.get_analysis()))

########################## Simulation ###############################################

########################### Trend ###############################################

# symbol = 'Natural Gas'
# interval = Const.TA_INTERVAL_4H
# strategy = Const.TA_STRATEGY_CCI_20_TREND_100

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
