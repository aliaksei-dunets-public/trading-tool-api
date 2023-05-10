import unittest
from unittest.mock import MagicMock
from datetime import datetime
from trading_core.handler import HandlerBase, HandlerCurrencyCom
from trading_core.model import Config

class TestConfig(unittest.TestCase):

    def setUp(self):
        self.config = Config()

    def test_getHandler_returns_handler(self):
        handler = self.config.getHandler()
        self.assertIsInstance(handler, HandlerBase)
    
    def test_get_handler(self):
        self.assertIsInstance(self.config.getHandler(), HandlerCurrencyCom)

    def test_getIntervals_returns_list_of_intervals(self):
        intervals = self.config.getIntervals()
        expected_intervals = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']
        self.assertEqual(intervals, expected_intervals)

    def test_get_intervals(self):
        self.assertEqual(self.config.getIntervals(), ["5m", "15m", "30m", "1h", "4h", "1d", "1w"])
        self.assertEqual(self.config.getIntervals(importance='LOW'), ["5m", "15m"])
        self.assertEqual(self.config.getIntervals(importance='MEDIUM'), ["30m", "1h"])
        self.assertEqual(self.config.getIntervals(importance='HIGH'), ["4h", "1d", "1w"])

    def test_get_interval_details(self):
        intervals = self.config.getIntervalDetails()
        self.assertEqual(len(intervals), 7)
        self.assertEqual(intervals[0]["interval"], "5m")
        self.assertEqual(intervals[0]["name"], "5 minutes")
        self.assertEqual(intervals[0]["order"], 10)
        self.assertEqual(intervals[0]["importance"], "LOW")
        self.assertEqual(intervals[1]["interval"], "15m")
        self.assertEqual(intervals[1]["name"], "15 minutes")
        self.assertEqual(intervals[1]["order"], 20)
        self.assertEqual(intervals[1]["importance"], "LOW")

    def test_is_trading_open(self):
        trading_time = 'UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00'
        trading_timeframe = 'UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00'
        self.config._Config__tradingTimeframes[trading_time] = MagicMock()
        self.config._Config__tradingTimeframes[trading_time].isTradingOpen.return_value = True
        self.assertTrue(self.config.isTradingOpen(trading_timeframe))
    
    def test_get_completed_unix_time_ms_5m(self):
        test_time = datetime(2023, 5, 9, 13, 16, 34) # 2023-05-09 13:16:34
        expected_result = datetime(2023, 5, 9, 13, 10, 0) # 2023-05-09 13:10:00
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('5m', test_time), expected_result)

    def test_get_completed_unix_time_ms_15m(self):
        test_time = datetime(2023, 5, 9, 14, 22, 47) # 2023-05-09 14:22:47
        expected_result = datetime(2023, 5, 9, 14, 0, 0) # 2023-05-09 14:00:00
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('15m', test_time), expected_result)

    def test_get_completed_unix_time_ms_30m(self):
        test_time = datetime(2023, 5, 9, 18, 43, 51) # 2023-05-09 18:43:51
        expected_result = datetime(2023, 5, 9, 18, 00, 0) # 2023-05-09 18:00:00
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('30m', test_time), expected_result)

    def test_get_completed_unix_time_ms_1h(self):
        test_time = datetime(2023, 5, 9, 21, 57, 23) # 2023-05-09 21:57:23
        expected_result = datetime(2023, 5, 9, 20, 0, 0) # 2023-05-09 20:00:00
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('1h', test_time), expected_result)

    def test_get_completed_unix_time_ms_4h(self):
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('4h', datetime(2023, 5, 10, 7, 40, 13)), datetime(2023, 5, 10, 4, 0, 0))
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('4h', datetime(2023, 5, 10, 0, 40, 13)), datetime(2023, 5, 9, 20, 0, 0))
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('4h', datetime(2023, 5, 10, 3, 40, 13)), datetime(2023, 5, 10, 0, 0, 0))
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('4h', datetime(2023, 5, 10, 20, 40, 13)), datetime(2023, 5, 10, 16, 0, 0))

    def test_get_completed_unix_time_ms_1d(self):
        test_time = datetime(2023, 5, 10, 0, 31, 44) # 2023-05-10 00:31:44
        expected_result = datetime(2023, 5, 9, 0, 0, 0) # 2023-05-09 00:00:00
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('1d', test_time), expected_result)

    def test_get_completed_unix_time_ms_1w(self):
        test_time = datetime(2023, 5, 12, 18, 13, 27) # 2023-05-12 18:13:27
        expected_result = datetime(2023, 5, 8, 0, 0 ) # 2023-05-08 00:00:00
        self.assertEqual(self.config.getHandler().getOffsetDateTimeByInterval('1w', test_time), expected_result)

if __name__ == '__main__':
    unittest.main()
