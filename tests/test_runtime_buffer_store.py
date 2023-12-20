import unittest
import pandas as pd
from datetime import datetime
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler

from trading_core.core import Symbol, HistoryData, Signal, RuntimeBufferStore


class RuntimeBufferStoreTests(unittest.TestCase):
    def setUp(self):
        self.buffer_store = RuntimeBufferStore()
        self.test_data_frame = pd.DataFrame(
            {
                "Open": [36500, 36650, 36750],
                "High": [36800, 36800, 37000],
                "Low": [36400, 36500, 36600],
                "Close": [36650, 36750, 36900],
                "Volume": [100, 150, 200]
            },
            index=[
                datetime(2021, 6, 14, 18, 0, 0),
                datetime(2021, 6, 14, 19, 0, 0),
                datetime(2021, 6, 14, 20, 0, 0)],
            columns=["Open", "High", "Low", "Close", "Volume"]
        )

    def tearDown(self):
        self.buffer_store.clearHistoryDataBuffer()
        self.buffer_store.checkSymbolsInBuffer()

    def test_getHistoryDataFromBuffer_existingData_returnsCorrectData(self):
        # Arrange
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 3
        end_datetime = datetime(2021, 6, 14, 20, 0, 0)
        data_frame = self.test_data_frame
        history_data = HistoryData(symbol, interval, limit, data_frame)
        self.buffer_store.setHistoryDataToBuffer(history_data)

        # Act
        result = self.buffer_store.getHistoryDataFromBuffer(
            symbol, interval, limit, end_datetime)

        # Assert
        self.assertEqual(result.getSymbol(), history_data.getSymbol())
        self.assertEqual(result.getInterval(), history_data.getInterval())
        self.assertEqual(result.getLimit(), history_data.getLimit())
        self.assertEqual(result.getEndDateTime(),
                         history_data.getEndDateTime())

    def test_getHistoryDataFromBuffer_nonExistingData_returnsNone(self):
        # Arrange
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 3
        end_datetime = datetime(2021, 6, 14, 20, 0, 0)

        # Act
        result = self.buffer_store.validateHistoryDataInBuffer(
            symbol, interval, limit, end_datetime)

        # Assert
        self.assertIsNotNone(result)

    def test_validateHistoryDataInBuffer_existingData_returnsTrue(self):
        # Arrange
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 3
        end_datetime = datetime(2021, 6, 14, 20, 0, 0)
        data_frame = self.test_data_frame
        history_data = HistoryData(symbol, interval, limit, data_frame)
        self.buffer_store.setHistoryDataToBuffer(history_data)

        # Act
        result = self.buffer_store.validateHistoryDataInBuffer(
            symbol, interval, limit, end_datetime)

        # Assert
        self.assertTrue(result)

    def test_validateHistoryDataInBuffer_existingData_returnsFalse(self):
        # Arrange
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 3
        data_frame = self.test_data_frame
        history_data = HistoryData(symbol, interval, limit, data_frame)
        self.buffer_store.setHistoryDataToBuffer(history_data)

        # Assert
        self.assertFalse(self.buffer_store.validateHistoryDataInBuffer(
            symbol, interval, 4, datetime(2021, 6, 14, 20, 0, 0)))
        # Assert
        self.assertFalse(self.buffer_store.validateHistoryDataInBuffer(
            symbol, interval, 3, datetime(2021, 6, 14, 21, 0, 0)))

    def test_getSymbolsFromBuffer_noSymbols_returnsEmptyDict(self):
        expected_symbols = {}
        self.buffer_store.clearSymbolsBuffer()
        result = self.buffer_store.getSymbolsFromBuffer()
        self.assertEqual(result, expected_symbols)

    def test_checkSymbolsInBuffer_noSymbols_returnsFalse(self):
        self.buffer_store.clearSymbolsBuffer()
        result = self.buffer_store.checkSymbolsInBuffer()
        self.assertFalse(result)

    def test_getSymbolsFromBuffer_withSymbols_returnsCorrectDict(self):
        # Arrange
        symbols = {"BTC": Symbol(code="BTC", name="Bitcoin",
                                 status="ACTIVE", tradingTime="UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00", type="CRYPTOCURRENCY"),
                   "AAPL": Symbol(code="AAPL", name="Apple Inc.",
                                  status="ACTIVE", tradingTime="UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00", type="EQUITY")
                   }
        self.buffer_store.setSymbolsToBuffer(symbols)
        expected_symbols = symbols

        # Act
        result = self.buffer_store.getSymbolsFromBuffer()

        # Assert
        self.assertEqual(result, expected_symbols)

        # Act
        result = self.buffer_store.checkSymbolsInBuffer()

        # Assert
        self.assertTrue(result)

    def test_timeframes_functionality(self):
        trading_time = 'UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59'
        self.buffer_store.clearTimeframeBuffer()
        self.assertFalse(
            self.buffer_store.checkTimeframeInBuffer(trading_time))
        self.assertIsNone(
            self.buffer_store.getTimeFrameFromBuffer(trading_time))

        self.buffer_store.setTimeFrameToBuffer(trading_time, {"mon": [1, 2]})
        self.assertTrue(self.buffer_store.checkTimeframeInBuffer(trading_time))
        self.assertIsNotNone(
            self.buffer_store.getTimeFrameFromBuffer(trading_time))
        self.buffer_store.clearTimeframeBuffer()

    def test_signal_functionality(self):
        date_time = datetime(2023, 6, 1, 12, 0, 0)
        symbol = 'BTC/USD'
        interval = '1h'
        strategy = 'CCI_14_TREND_100'
        signal = 'BUY'
        self.signal = Signal(date_time, symbol, interval, strategy, signal)

        buffer_key = (symbol, interval, strategy)

        self.assertEqual(buffer_key, self.buffer_store.get_signal_buffer_key(
            symbol=symbol, interval=interval, strategy=strategy))

        self.buffer_store.clear_signal_buffer()
        self.assertFalse(self.buffer_store.check_signal_in_buffer(
            symbol=symbol, interval=interval, strategy=strategy))
        self.assertIsNone(self.buffer_store.get_signal_from_buffer(
            symbol=symbol, interval=interval, strategy=strategy, date_time=date_time))

        self.buffer_store.set_signal_to_buffer(self.signal)
        self.assertTrue(self.buffer_store.check_signal_in_buffer(
            symbol=symbol, interval=interval, strategy=strategy))
        self.assertIsNotNone(self.buffer_store.get_signal_from_buffer(
            symbol=symbol, interval=interval, strategy=strategy, date_time=date_time))
        self.buffer_store.clearTimeframeBuffer()

    def test_job_functionality(self):
        scheduler = BackgroundScheduler()
        job_id = 'job_id_001'
        job = Job(scheduler, job_id)

        self.buffer_store.set_job_to_buffer(job)

        result_job = self.buffer_store.get_job_from_buffer(job_id)

        self.assertIsInstance(result_job, Job)
        self.assertEqual(result_job.id, job_id)

        self.buffer_store.remove_job_from_buffer(job_id)
        result_job = self.buffer_store.get_job_from_buffer(job_id)

        self.assertIsNone(result_job)
