import pandas as pd
import json

from trading_core.model import ParamSimulation
from trading_core.simulation import Const, SimulateOptions, Simulator, Executor

symbol = 'EPAM'
interval = Const.TA_INTERVAL_4H
strategy = Const.TA_STRATEGY_CCI_20_TREND_100

simulation_options = SimulateOptions(init_balance=100,
                                     limit=400,
                                     stop_loss_rate=10,
                                     take_profit_rate=30,
                                     fee_rate=3)

param = ParamSimulation(symbol=symbol,
                        interval=interval,
                        strategy=strategy,
                        simulation_options=simulation_options)

result = Executor().simulate(param)

df = pd.DataFrame(result['orders'])

file_name = f'static/{param.symbol}_{param.interval}_{param.strategy}.xlsx'

with pd.ExcelWriter(file_name) as writer:
    df.to_excel(writer, sheet_name="simulation")

print(result['summary'])
print(json.dumps(result['analysis']))
