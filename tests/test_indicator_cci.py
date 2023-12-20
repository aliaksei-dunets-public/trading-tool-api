import unittest
from unittest.mock import patch

from trading_core.indicator import Indicator_CCI
from tests_refactored import getHistoryDataTest


class TestIndicatorCCI(unittest.TestCase):

    def setUp(self):
        self.symbol = 'BABA'
        self.interval = '1h'
        self.limit = 50
        self.from_buffer = True
        self.closed_bars = False

    def test_getIndicator(self):

        mock_history_data = getHistoryDataTest(
            symbol=self.symbol, interval=self.interval, limit=self.limit, from_buffer=self.from_buffer, closed_bars=self.closed_bars)

        with patch('trading_core.indicator.IndicatorBase.get_indicator') as mock_get_indicator:
            mock_get_indicator.return_value = mock_history_data

            cci_indicator = Indicator_CCI(length=4)
            indicator_df = cci_indicator.get_indicator(
                symbol=self.symbol, interval=self.interval, limit=self.limit, from_buffer=self.from_buffer, closed_bars=self.closed_bars)

            self.assertTrue('CCI' in indicator_df.columns)
            # Only entry with CCI are returned
            self.assertTrue(len(indicator_df) == 47)
            # All rows have CCI values
            self.assertTrue(all(indicator_df['CCI'].notna()))

            self.assertEqual(indicator_df.tail(
                1).iloc[0, 5], 50.179211469542025)

    def test_getIndicatorByHistoryData(self):

        history_data = getHistoryDataTest(
            symbol=self.symbol, interval=self.interval, limit=self.limit, from_buffer=self.from_buffer, closed_bars=self.closed_bars)

        cci_indicator = Indicator_CCI(length=4)
        indicator_df = cci_indicator.get_indicator_by_history_data(
            history_data)

        self.assertTrue('CCI' in indicator_df.columns)
        # Only entry with CCI are returned
        self.assertTrue(len(indicator_df) == 47)
        # All rows have CCI values
        self.assertTrue(all(indicator_df['CCI'].notna()))

        self.assertEqual(indicator_df.head(1).iloc[0, 5], 97.61904761904609)
        self.assertEqual(indicator_df.tail(1).iloc[0, 5], 50.179211469542025)
