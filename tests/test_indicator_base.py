import unittest
from unittest.mock import MagicMock

from trading_core.model import model
from trading_core.indicator import IndicatorBase
from tests_refactored import getHistoryDataTest
from trading_core.core import HistoryData


class TestIndicatorBase(unittest.TestCase):

    def setUp(self):
        self.symbol = 'BABA'
        self.interval = '1h'
        self.limit = 50
        self.model = model
        self.from_buffer = True
        self.closed_bars = False
        self.handler = self.model.get_handler()
        self.indicator = IndicatorBase()

    def test_getCode(self):
        self.assertEqual(self.indicator.get_code(), '')

    def test_getName(self):
        self.assertEqual(self.indicator.get_name(), '')

    def test_getIndicator(self):
        self.handler.getHistoryData = MagicMock(return_value=getHistoryDataTest(
            symbol=self.symbol, interval=self.interval, limit=self.limit, from_buffer=self.from_buffer, closed_bars=self.closed_bars))
        history_data = self.indicator.get_indicator(
            symbol=self.symbol, interval=self.interval, limit=self.limit, from_buffer=self.from_buffer, closed_bars=self.closed_bars)
        self.assertIsInstance(history_data, HistoryData)

        # Check that the returned value is a HistoryData object
        self.assertTrue(isinstance(history_data, HistoryData))

        # Check that the HistoryData object has the expected properties
        self.assertEqual(history_data.getSymbol(), self.symbol)
        self.assertEqual(history_data.getInterval(), self.interval)
        self.assertEqual(history_data.getLimit(), self.limit)

        # Check that the DataFrame in the HistoryData object has the expected shape
        self.assertEqual(history_data.getDataFrame().shape, (self.limit, 5))

        self.assertEqual(history_data.getDataFrame().tail(1).iloc[0, 4], 11)

    def test_getIndicatorByHistoryData(self):
        history_data = getHistoryDataTest(
            symbol=self.symbol, interval=self.interval, limit=self.limit, from_buffer=self.from_buffer, closed_bars=self.closed_bars)
        df = self.indicator.get_indicator_by_history_data(history_data)
        self.assertIsNotNone(df)
