import unittest
import pandas as pd
import os


from trading_core.constants import Const
from trading_core.core import HistoryData


class HistoryDataTestCase(unittest.TestCase):

    def setUp(self):
        self.symbol = 'BABA'
        self.interval = Const.TA_INTERVAL_1H
        self.limit = 50
        self.data = pd.read_json(
            f'{os.getcwd()}/static/tests/{self.symbol}_{self.interval}.json')

    def test_history_data_creation(self):
        history_data = HistoryData(
            self.symbol, self.interval, self.limit, self.data)

        self.assertEqual(history_data.getSymbol(), self.symbol)
        self.assertEqual(history_data.getInterval(), self.interval)
        self.assertEqual(history_data.getLimit(), self.limit)
        self.assertEqual(history_data.getDataFrame().equals(self.data), True)
