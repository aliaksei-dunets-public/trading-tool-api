import unittest
from datetime import datetime

from trading_core.core import Signal
from trading_core.constants import Const


class SignalTests(unittest.TestCase):

    def setUp(self):
        date_time = datetime(2023, 6, 1, 12, 0, 0)
        symbol = 'BTC/USD'
        interval = '1h'
        strategy = 'CCI_14_TREND_100'
        signal = 'BUY'
        self.signal = Signal(date_time, symbol, interval, strategy, signal)

    def test_get_signal(self):
        expected_signal = {
            Const.DATETIME: '2023-06-01T12:00:00',
            Const.PARAM_SYMBOL: 'BTC/USD',
            Const.INTERVAL: '1h',
            Const.STRATEGY: 'CCI_14_TREND_100',
            Const.PARAM_SIGNAL: 'BUY'
        }
        self.assertEqual(self.signal.get_signal_dict(), expected_signal)

    def test_get_date_time(self):
        expected_date_time = datetime(2023, 6, 1, 12, 0, 0)
        self.assertEqual(self.signal.get_date_time(), expected_date_time)

    def test_get_symbol(self):
        expected_symbol = 'BTC/USD'
        self.assertEqual(self.signal.get_symbol(), expected_symbol)

    def test_get_interval(self):
        expected_interval = '1h'
        self.assertEqual(self.signal.get_interval(), expected_interval)

    def test_get_strategy(self):
        expected_strategy = 'CCI_14_TREND_100'
        self.assertEqual(self.signal.get_strategy(), expected_strategy)

    def test_is_compatible_debug_signal(self):
        signals_config = [Const.DEBUG_SIGNAL]
        self.assertTrue(self.signal.is_compatible(signals_config))

    def test_is_compatible_no_signals_config(self):
        self.assertTrue(self.signal.is_compatible())

    def test_is_compatible_matching_signal(self):
        signals_config = ['BUY']
        self.assertTrue(self.signal.is_compatible(signals_config))

    def test_is_compatible_non_matching_signal(self):
        signals_config = ['SELL']
        self.assertFalse(self.signal.is_compatible(signals_config))
