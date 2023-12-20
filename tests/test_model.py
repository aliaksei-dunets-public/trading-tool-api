import unittest

from trading_core.model import model
from trading_core.handler import StockExchangeHandler
from trading_core.core import config
from trading_core.constants import Const


class TestModel(unittest.TestCase):

    def test_get_handler_returns_handler(self):
        handler = model.get_handler()
        self.assertIsInstance(handler, StockExchangeHandler)
        self.assertEqual(config.get_stock_exchange_id(),
                         handler.getStockExchangeName())

    def test_getIntervals_returns_list_of_intervals(self):
        intervals = model.get_intervals()
        expected_intervals = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']
        self.assertEqual(intervals, expected_intervals)

    def test_get_intervals(self):
        self.assertEqual(model.get_intervals(), [
            "5m", "15m", "30m", "1h", "4h", "1d", "1w"])
        self.assertEqual(model.get_intervals(
            importances=['LOW']), ["5m", "15m"])
        self.assertEqual(model.get_intervals(
            importances=['MEDIUM']), ["30m", "1h"])
        self.assertEqual(model.get_intervals(
            importances=['HIGH']), ["4h", "1d", "1w"])

    def test_get_interval_details(self):
        intervals = model.get_intervals_config()
        self.assertEqual(len(intervals), 7)
        self.assertEqual(intervals[0]["interval"], "5m")
        self.assertEqual(intervals[0]["name"], "5 minutes")
        self.assertEqual(intervals[0]["order"], 10)
        self.assertEqual(intervals[0]["importance"], "LOW")
        self.assertEqual(intervals[1]["interval"], "15m")
        self.assertEqual(intervals[1]["name"], "15 minutes")
        self.assertEqual(intervals[1]["order"], 20)
        self.assertEqual(intervals[1]["importance"], "LOW")

    def test_is_trading_open_true_cases(self):
        handler = model.get_handler()
        trading_time = 'UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59'
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_5M, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_15M, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_30M, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_1H, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_4H, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_1D, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_1WK, trading_time=trading_time))

    def test_is_trading_open_false_cases(self):
        handler = model.get_handler()
        trading_time = 'UTC; Sun 03:01 - 03:02'
        self.assertFalse(handler.is_trading_open(
            interval=Const.TA_INTERVAL_5M, trading_time=trading_time))
        self.assertFalse(handler.is_trading_open(
            interval=Const.TA_INTERVAL_15M, trading_time=trading_time))
        self.assertFalse(handler.is_trading_open(
            interval=Const.TA_INTERVAL_30M, trading_time=trading_time))
        self.assertFalse(handler.is_trading_open(
            interval=Const.TA_INTERVAL_1H, trading_time=trading_time))
        self.assertFalse(handler.is_trading_open(
            interval=Const.TA_INTERVAL_4H, trading_time=trading_time))
        self.assertFalse(handler.is_trading_open(
            interval=Const.TA_INTERVAL_1D, trading_time=trading_time))
        self.assertTrue(handler.is_trading_open(
            interval=Const.TA_INTERVAL_1WK, trading_time=trading_time))

    def test_get_indicators(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]
        result = model.get_indicators_config()
        self.assertEqual(result, expected_result)

    def test_get_strategy(self):
        expected_result = {
            Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.NAME: "CCI(14): Indicator against Trend +/- 100",
            Const.LENGTH: 14,
            Const.VALUE: 100
        }

        result = model.get_strategy(Const.TA_STRATEGY_CCI_14_TREND_100)

        self.assertEqual(expected_result, result)

    def test_get_strategies(self):
        expected_result = [
            {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
             Const.NAME: "CCI(14): Indicator against Trend +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_170_165,
             Const.NAME: "CCI(14): Indicator direction Trend +/- 170 | 165"},
            {Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
             Const.NAME: "CCI(20): Indicator against Trend +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
             Const.NAME: "CCI(50): Indicator direction Trend 0"}
        ]
        result = model.get_strategies()
        self.assertEqual(result, expected_result)

    def test_get_strategy_codes(self):
        expected_result = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_14_TREND_170_165,
            Const.TA_STRATEGY_CCI_20_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0
        ]
        result = model.get_strategy_codes()
        self.assertEqual(result, expected_result)

    def test_get_sorted_strategy_codes_with_default_arguments(self):
        expected_result = [
            Const.TA_STRATEGY_CCI_50_TREND_0,
            Const.TA_STRATEGY_CCI_20_TREND_100,
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_14_TREND_170_165
        ]
        self.assertEqual(
            model.get_sorted_strategy_codes(), expected_result)

    def test_get_sorted_strategy_codes_with_custom_strategies(self):
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0
        ]
        expected_result = [
            Const.TA_STRATEGY_CCI_50_TREND_0,
            Const.TA_STRATEGY_CCI_14_TREND_100
        ]
        self.assertEqual(model.get_sorted_strategy_codes(
            strategies), expected_result)

    def test_get_sorted_strategy_codes_with_custom_strategies_and_ascending_order(self):
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0
        ]
        expected_result = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0
        ]
        self.assertEqual(model.get_sorted_strategy_codes(
            strategies, desc=False), expected_result)
