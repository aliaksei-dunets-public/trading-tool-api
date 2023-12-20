import unittest

from trading_core.core import Signal, RuntimeBufferStore
from trading_core.strategy import SignalFactory
from trading_core.model import model
from trading_core.constants import Const


class SignalFactoryTests(unittest.TestCase):

    def setUp(self):
        self.signal_factory = SignalFactory()
        self.runtime_buffer = RuntimeBufferStore()
        self.runtime_buffer.clearSymbolsBuffer()

    def tearDown(self):
        pass

    def test_get_signal_with_buffer(self):
        symbol = 'BTC/USD'
        interval = '1h'
        strategy_14 = 'CCI_14_TREND_100'
        strategy_20 = 'CCI_20_TREND_100'
        signals_config = []
        closed_bars = False

        # Add a signals to the buffer
        date_time = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=closed_bars)
        self.runtime_buffer.set_signal_to_buffer(
            Signal(date_time, symbol, interval, strategy_14, Const.BUY))
        self.runtime_buffer.set_signal_to_buffer(
            Signal(date_time, symbol, interval, strategy_20, ''))

        # Check signal with signals_config
        signal_inst = self.signal_factory.get_signal(
            symbol, interval, strategy_14, signals_config, closed_bars)

        self.assertIsInstance(signal_inst, Signal)
        self.assertEqual(signal_inst.get_date_time(), date_time)
        self.assertEqual(signal_inst.get_symbol(), 'BTC/USD')
        self.assertEqual(signal_inst.get_interval(), '1h')
        self.assertEqual(signal_inst.get_strategy(), 'CCI_14_TREND_100')
        self.assertEqual(signal_inst.get_signal(), Const.BUY)

        # Get None because the signal is empty
        signal_inst_20 = self.signal_factory.get_signal(
            symbol, interval, strategy_20, [Const.BUY], closed_bars)

        self.assertIsNone(signal_inst_20)

    def test_get_signal_without_buffer(self):
        symbol = 'BTC/USD'
        interval = '1h'
        strategy = 'CCI_14_TREND_100'
        signals_config = [Const.DEBUG_SIGNAL]
        closed_bars = True

        # Remove any existing signals from the buffer
        self.runtime_buffer.clear_signal_buffer()

        date_time = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=closed_bars)

        signal_inst = self.signal_factory.get_signal(
            symbol, interval, strategy, signals_config, closed_bars)

        self.assertIsNotNone(signal_inst)
        self.assertEqual(signal_inst.get_date_time(), date_time)
        self.assertEqual(signal_inst.get_symbol(), 'BTC/USD')
        self.assertEqual(signal_inst.get_interval(), '1h')
        self.assertEqual(signal_inst.get_strategy(), 'CCI_14_TREND_100')

    def test_get_signals(self):
        symbols = ['BTC/USD', 'BAL/USD']
        intervals = [Const.TA_INTERVAL_1H, Const.TA_INTERVAL_4H]
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100,
                      Const.TA_STRATEGY_CCI_20_TREND_100]
        signals_config = [Const.DEBUG_SIGNAL]
        closed_bars = False

        date_time_1h = model.get_handler().getEndDatetime(
            interval=Const.TA_INTERVAL_1H, closed_bars=closed_bars)

        date_time_4h = model.get_handler().getEndDatetime(
            interval=Const.TA_INTERVAL_4H, closed_bars=closed_bars)

        signals_list = self.signal_factory.get_signals(
            symbols, intervals, strategies, signals_config, closed_bars)

        self.assertEqual(len(signals_list), 8)

        for signal_inst in signals_list:
            if signal_inst.get_interval() == Const.TA_INTERVAL_1H:
                self.assertEqual(signal_inst.get_date_time(), date_time_1h)
            elif signal_inst.get_interval() == Const.TA_INTERVAL_4H:
                self.assertEqual(signal_inst.get_date_time(), date_time_4h)
