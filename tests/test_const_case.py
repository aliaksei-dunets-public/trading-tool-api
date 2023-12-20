import unittest
from trading_core.constants import Const


class ConstTestCase(unittest.TestCase):

    def test_signal_values(self):
        self.assertEqual(Const.STRONG_BUY, 'Strong Buy')
        self.assertEqual(Const.BUY, 'Buy')
        self.assertEqual(Const.STRONG_SELL, 'Strong Sell')
        self.assertEqual(Const.SELL, 'Sell')

    def test_direction_values(self):
        self.assertEqual(Const.LONG, 'LONG')
        self.assertEqual(Const.SHORT, 'SHORT')

    def test_column_names(self):
        self.assertEqual(Const.PARAM_SIGNAL, 'signal')
        self.assertEqual(Const.PARAM_SYMBOL, 'symbol')
        self.assertEqual(Const.CODE, 'code')
        self.assertEqual(Const.INTERVAL, 'interval')
        self.assertEqual(Const.STRATEGY, 'strategy')
        self.assertEqual(Const.NAME, 'name')
        self.assertEqual(Const.DESCR, 'descr')
        self.assertEqual(Const.STATUS, 'status')

    def test_order_statuses(self):
        self.assertEqual(Const.STATUS_OPEN, 'Open')
        self.assertEqual(Const.STATUS_CLOSE, 'Close')

    def test_order_close_reason(self):
        self.assertEqual(Const.ORDER_CLOSE_REASON_STOP_LOSS, 'STOP_LOSS')
        self.assertEqual(Const.ORDER_CLOSE_REASON_TAKE_PROFIT, 'TAKE_PROFIT')
        self.assertEqual(Const.ORDER_CLOSE_REASON_SIGNAL, 'SIGNAL')

    def test_intervals(self):
        self.assertEqual(Const.TA_INTERVAL_5M, '5m')
        self.assertEqual(Const.TA_INTERVAL_15M, '15m')
        self.assertEqual(Const.TA_INTERVAL_30M, '30m')
        self.assertEqual(Const.TA_INTERVAL_1H, '1h')
        self.assertEqual(Const.TA_INTERVAL_4H, '4h')
        self.assertEqual(Const.TA_INTERVAL_1D, '1d')
        self.assertEqual(Const.TA_INTERVAL_1WK, '1w')
