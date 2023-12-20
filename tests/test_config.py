import unittest
from trading_core.constants import Const
from trading_core.core import config


class TestConfig(unittest.TestCase):

    def test_get_config_value(self):
        self.assertEqual(config.get_config_value(
            Const.CONFIG_DEBUG_LOG), True)
        self.assertIsNone(config.get_config_value('Test'))

    def test_get_stock_exchange_id(self):
        self.assertEqual(config.get_stock_exchange_id(),
                         Const.STOCK_EXCH_CURRENCY_COM)

    def test_get_indicators_config(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]
        result = config.get_indicators_config()
        self.assertEqual(result, expected_result)

    def test_get_strategies_config(self):
        expected_result = {
            Const.TA_STRATEGY_CCI_14_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator against Trend +/- 100",
                Const.LENGTH: 14,
                Const.VALUE: 100
            },
            Const.TA_STRATEGY_CCI_14_TREND_170_165: {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_170_165,
                Const.NAME: "CCI(14): Indicator direction Trend +/- 170 | 165",
                Const.LENGTH: 14,
                Const.VALUE: 170,
                Const.OPEN_VALUE: 170,
                Const.CLOSE_VALUE: 165,
            },
            Const.TA_STRATEGY_CCI_20_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator against Trend +/- 100",
                Const.LENGTH: 20,
                Const.VALUE: 100
            },
            Const.TA_STRATEGY_CCI_50_TREND_0: {
                Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator direction Trend 0",
                Const.LENGTH: 50,
                Const.VALUE: 0
            }
        }
        result = config.get_strategies_config()
        self.assertEqual(result, expected_result)
