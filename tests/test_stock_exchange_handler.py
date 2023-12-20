import unittest

from trading_core.handler import StockExchangeHandler
from trading_core.core import RuntimeBufferStore
from trading_core.constants import Const


class StockExchangeHandlerTests(unittest.TestCase):
    def setUp(self):
        # Initialize the StockExchangeHandler instance with a mock runtime_buffer and API implementation
        self.handler = StockExchangeHandler()
        self.buffer = RuntimeBufferStore()

    def test_getStockExchangeName_returnsCorrectName(self):
        # Arrange
        expected_name = Const.STOCK_EXCH_CURRENCY_COM

        # Act
        result = self.handler.getStockExchangeName()

        # Assert
        self.assertEqual(result, expected_name)

    def test_getHistoryData_fromBufferExistingData_returnsCorrectData(self):
        # Arrange
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 22
        from_buffer = True
        closed_bars = True
        end_datetime = self.handler.getEndDatetime(
            interval=interval, closed_bars=closed_bars)

        self.buffer.clearHistoryDataBuffer()

        is_buffer = self.buffer.checkHistoryDataInBuffer(
            symbol=symbol, interval=interval)
        self.assertFalse(is_buffer)

        # Act
        result = self.handler.getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.getSymbol(), symbol)
        self.assertEqual(result.getInterval(), interval)
        self.assertEqual(result.getLimit(), limit)
        self.assertEqual(result.getEndDateTime(), end_datetime)

        is_buffer = self.buffer.checkHistoryDataInBuffer(
            symbol=symbol, interval=interval)
        self.assertTrue(is_buffer)

        is_buffer_valid = self.buffer.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=end_datetime)
        self.assertTrue(is_buffer_valid)

        limit = 25
        is_buffer_valid = self.buffer.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=end_datetime)
        self.assertFalse(is_buffer_valid)

        limit = 20
        result = self.handler.getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars)
        self.assertIsNotNone(result)
        self.assertEqual(result.getSymbol(), symbol)
        self.assertEqual(result.getInterval(), interval)
        self.assertEqual(result.getLimit(), limit)
        self.assertEqual(result.getEndDateTime(), end_datetime)

    def test_getHistoryData_noBufferExistingData_returnsCorrectData(self):
        # Arrange
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 10
        from_buffer = False
        end_datetime = self.handler.getEndDatetime(interval=interval)

        # Act
        result = self.handler.getHistoryData(
            symbol, interval, limit, from_buffer)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.getSymbol(), symbol)
        self.assertEqual(result.getInterval(), interval)
        self.assertEqual(result.getLimit(), limit)
        self.assertEqual(result.getEndDateTime(), end_datetime)

        is_buffer = self.buffer.checkHistoryDataInBuffer(
            symbol=symbol, interval='4h')
        self.assertFalse(is_buffer)

        end_datetime = self.handler.getEndDatetime(
            interval=interval, closed_bars=True)
        is_buffer_valid = self.buffer.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=end_datetime)
        self.assertTrue(is_buffer_valid)

    def test_getSymbols_fromBufferExistingSymbols_returnsCorrectSymbols(self):
        # Arrange
        from_buffer = True

        self.buffer.clearSymbolsBuffer()
        self.assertFalse(self.buffer.checkSymbolsInBuffer())

        # Act
        result = self.handler.getSymbols(from_buffer)

        # Assert
        self.assertIsNotNone(result)
        self.assertTrue(self.buffer.checkSymbolsInBuffer())

        result = self.handler.getSymbols(from_buffer)
        self.assertIsNotNone(result)

    def test_getSymbols_noBufferExistingSymbols_returnsCorrectSymbols(self):
        # Arrange
        from_buffer = False

        # Mock the API call to return symbols

        # Act
        result = self.handler.getSymbols(from_buffer)

        # Assert
        self.assertIsNotNone(result)
        # Assert the symbols returned from the API

    def test_getIntervals_returnsCorrectIntervals(self):
        result = self.handler.get_intervals()
        self.assertIsNotNone(result)

    def test_is_trading_open_true_cases(self):
        trading_time = 'UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59'
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_5M, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_15M, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_30M, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_1H, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_4H, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_1D, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_1WK, trading_time=trading_time))

    def test_is_trading_open_false_cases(self):
        trading_time = 'UTC; Sun 03:01 - 03:02'
        self.assertFalse(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_5M, trading_time=trading_time))
        self.assertFalse(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_15M, trading_time=trading_time))
        self.assertFalse(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_30M, trading_time=trading_time))
        self.assertFalse(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_1H, trading_time=trading_time))
        self.assertFalse(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_4H, trading_time=trading_time))
        self.assertFalse(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_1D, trading_time=trading_time))
        self.assertTrue(self.handler.is_trading_open(
            interval=Const.TA_INTERVAL_1WK, trading_time=trading_time))
