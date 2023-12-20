import unittest

from trading_core.model import model
from trading_core.constants import Const
from trading_core.strategy import StrategyConfig


class StrategyConfigTests(unittest.TestCase):

    def setUp(self):
        self.model = model
        self.strategy_code = Const.TA_STRATEGY_CCI_14_TREND_100
        self.strategy_config = self.model.get_strategy(self.strategy_code)
        self.strategy = StrategyConfig(self.strategy_code)

    def test_init(self):
        with self.assertRaises(Exception):
            # Test missing strategy config
            StrategyConfig('missing_strategy_code')

    def test_get_code(self):
        expected_result = self.strategy_config[Const.CODE]
        result = self.strategy.get_code()
        self.assertEqual(result, expected_result)

    def test_get_name(self):
        expected_result = self.strategy_config[Const.NAME]
        result = self.strategy.get_name()
        self.assertEqual(result, expected_result)

    def test_get_length(self):
        expected_result = int(self.strategy_config[Const.LENGTH])
        result = self.strategy.get_length()
        self.assertEqual(result, expected_result)

    def test_get_config(self):
        expected_result = self.strategy_config
        result = self.strategy.get_config()
        self.assertEqual(result, expected_result)

    def test_get_property(self):
        property_name = Const.VALUE
        expected_result = self.strategy_config[property_name]
        result = self.strategy.get_property(property_name)
        self.assertEqual(result, expected_result)

    def test_get_property_missing(self):
        with self.assertRaises(Exception):
            # Test missing property in strategy config
            self.strategy.get_property('missing_property')
