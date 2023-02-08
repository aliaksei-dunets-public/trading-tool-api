from .core import Const
from .model import config, SymbolList
from .strategy import StrategyFactory


class Simulator():

    def determineSignal(self, symbol, interval, strategyCode):

        strategy_df = StrategyFactory(
            strategyCode).getStrategy(symbol, interval).tail(1)

        for index, strategy_row in strategy_df.iterrows():
            signal_value = strategy_row[Const.SIGNAL]
            if signal_value:
                return {'DateTime': index.isoformat(),
                        'Symbol': symbol,
                        'Interval': interval,
                        'Strategy': strategyCode,
                        'Signal': signal_value}
            else:
                return None

    def determineSignals(self, symbols=[], intervals=[], strategyCodes=[]):

        signals = []

        if not symbols:
            symbols = SymbolList().getSymbolCodes()

        if not intervals:
            intervals = config.getIntervals()

        if not strategyCodes:
            strategyCodes = config.getStrategyCodes()

        for symbol in symbols:
            for interval in intervals:
                for code in strategyCodes:
                    signal = self.determineSignal(symbol, interval, code)
                    if signal:
                        signals.append(signal)

        return signals
