import unittest


from trading_core.strategy import StrategyFactory
from trading_core.constants import Const
from tests_refactored import getHistoryDataTest


class StrategyFactoryTests(unittest.TestCase):

    def setUp(self):
        self.factory = StrategyFactory(Const.TA_STRATEGY_CCI_14_TREND_100)

    def test_init_valid_strategy_code(self):
        strategy_code = Const.TA_STRATEGY_CCI_14_TREND_100
        factory = StrategyFactory(strategy_code)
        self.assertIsInstance(factory, StrategyFactory)

    def test_init_invalid_strategy_code(self):
        with self.assertRaises(Exception):
            # Test missing strategy code
            StrategyFactory('missing_strategy_code')

    def test_get_strategy(self):
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 10
        closed_bar = False
        from_buffer = True
        strategy = self.factory.get_strategy_data(
            symbol, interval, limit, from_buffer, closed_bar)
        self.assertEqual(3, len(strategy))

    def test_get_strategy_by_history_data(self):
        symbol = 'BABA'
        interval = '1h'
        limit = 50
        from_buffer = True
        closed_bars = False

        history_data = getHistoryDataTest(symbol=symbol, interval=interval,
                                          limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

        strategy_data = self.factory.get_strategy_data_by_history_data(
            history_data)

        self.assertEqual(strategy_data.tail(1).iloc[0, 6], '')
        self.assertEqual(strategy_data.tail(8).iloc[0, 6], Const.STRONG_SELL)
        self.assertEqual(strategy_data.tail(11).iloc[0, 6], Const.BUY)
