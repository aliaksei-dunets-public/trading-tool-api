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

from trading_core.simulation import Const, SimulateOptions, Executor
from trading_core.core import config
from trading_core.model import (
    model,
    Symbols,
    ParamSimulation,
    ParamSymbolInterval,
    ParamSymbolIntervalList,
    ParamSymbolIntervalLimit,
    ParamSimulationList,
)
from trading_core.trend import TrendCCI, Indicator_CCI
from trading_core.handler import CurrencyComApi, LocalCurrencyComApi
from trading_core.common import TradingType, SessionType, StrategyType

from trading_core.robot import SessionManager, Robot, TraderBase
from trading_core.responser import (
    job_func_send_bot_notification,
    job_func_trading_robot,
)

# job_func_send_bot_notification("5m")

session_mdl = SessionHandler.get_session(id="6556ab4db98604c80d7104ee")

trader = TraderBase.get_manager(session_mdl)

trader.run()

# session_data = {
#     "trader_id": "65443f637b025235de0fb5d7",
#     "user_id": "65419b27e3a8c7e9690860cb",
#     # "status": "",
#     "trading_type": TradingType.LEVERAGE,
#     "session_type": SessionType.HISTORY,
#     "symbol": "BTC/USD_LEVERAGE",
#     "interval": "5m",
#     "strategy": StrategyType.CCI_20_TREND_100,
#     "take_profit_rate": 10,
#     "stop_loss_rate": 5,
# }

# session_mdl = SessionModel(**session_data)
# session_mng = SessionManager(session_mdl)
# session_mng.run()

# print(session_mng.get_balance_manager().get_balance_model())

# print("Positions:")
# print(session_mng.get_positions())


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

# symbol = "BTC/USD"
# interval = Const.TA_INTERVAL_30M
# strategy = Const.TA_STRATEGY_CCI_20_TREND_100

# param = ParamSymbolIntervalLimit(symbol=symbol, interval=interval, limit=100)

# params = [
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_5M),
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_15M),
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_30M),
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_1H),
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_4H),
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_1D),
#     ParamSymbolInterval(symbol=symbol, interval=Const.TA_INTERVAL_1WK),
# ]

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
