import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json
import pandas as pd
import os

from trading_core.core import Const, TradingTimeframe, Symbol, HistoryData, SimulateOptions
from trading_core.handler import HandlerBase, HandlerCurrencyCom
from trading_core.model import Config, SymbolList
from trading_core.indicator import IndicatorBase, Indicator_CCI

# from app import app


def getHistoryDataTest(config, symbol, interval, limit):
    file_path = f'{os.getcwd()}/static/tests/{symbol}_{interval}.json'
    with open(file_path, 'r') as reader:
        testHistoryData = json.load(reader)

    with patch('trading_core.handler.HandlerCurrencyCom.getKlines') as mock_getKlines:
        # Define a mock return value for the __getKlines method
        mock_response = testHistoryData
        mock_getKlines.return_value = mock_response

        history_data = config.getHandler().getHistoryData(symbol, interval, limit)
        return history_data

# class ConstTestCase(unittest.TestCase):

#     def test_signal_values(self):
#         self.assertEqual(Const.STRONG_BUY, 'Strong Buy')
#         self.assertEqual(Const.BUY, 'Buy')
#         self.assertEqual(Const.STRONG_SELL, 'Strong Sell')
#         self.assertEqual(Const.SELL, 'Sell')

#     def test_direction_values(self):
#         self.assertEqual(Const.LONG, 'LONG')
#         self.assertEqual(Const.SHORT, 'SHORT')

#     def test_column_names(self):
#         self.assertEqual(Const.SIGNAL, 'signal')
#         self.assertEqual(Const.SYMBOL, 'symbol')
#         self.assertEqual(Const.CODE, 'code')
#         self.assertEqual(Const.INTERVAL, 'interval')
#         self.assertEqual(Const.STRATEGY, 'strategy')
#         self.assertEqual(Const.NAME, 'name')
#         self.assertEqual(Const.DESCR, 'descr')
#         self.assertEqual(Const.STATUS, 'status')

#     def test_order_statuses(self):
#         self.assertEqual(Const.ORDER_STATUS_OPEN, 'Open')
#         self.assertEqual(Const.ORDER_STATUS_CLOSE, 'Close')

#     def test_order_close_reason(self):
#         self.assertEqual(Const.ORDER_CLOSE_REASON_STOP_LOSS, 'Stop Loss')
#         self.assertEqual(Const.ORDER_CLOSE_REASON_TAKE_PROFIT, 'Take Profit')
#         self.assertEqual(Const.ORDER_CLOSE_REASON_SIGNAL, 'Signal')


# class SymbolTestCase(unittest.TestCase):

#     def setUp(self):
#         self.code = 'AAPL'
#         self.name = 'Apple Inc.'
#         self.status = 'Active'
#         self.type = 'Stock'
#         self.tradingTime = 'UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 23:01 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -'

#     def test_symbol_creation(self):
#         symbol = Symbol(self.code, self.name, self.status,
#                         self.type, self.tradingTime)

#         self.assertEqual(symbol.code, self.code)
#         self.assertEqual(symbol.name, self.name)
#         self.assertEqual(symbol.descr, f'{self.name} ({self.code})')
#         self.assertEqual(symbol.status, self.status)
#         self.assertEqual(symbol.tradingTime, self.tradingTime)
#         self.assertEqual(symbol.type, self.type)


# class HistoryDataTestCase(unittest.TestCase):

#     def setUp(self):
#         self.symbol = 'BABA'
#         self.interval = Config.TA_INTERVAL_1H
#         self.limit = 50
#         self.data = pd.read_json(
#             f'{os.getcwd()}/static/tests/{self.symbol}_{self.interval}.json')

#     def test_history_data_creation(self):
#         history_data = HistoryData(
#             self.symbol, self.interval, self.limit, self.data)

#         self.assertEqual(history_data.getSymbol(), self.symbol)
#         self.assertEqual(history_data.getInterval(), self.interval)
#         self.assertEqual(history_data.getLimit(), self.limit)
#         self.assertEqual(history_data.getDataFrame().equals(self.data), True)


# class SimulateOptionsTestCase(unittest.TestCase):

#     def setUp(self):
#         self.balance = 10000
#         self.limit = 10
#         self.stopLossRate = 0.05
#         self.takeProfitRate = 0.1
#         self.feeRate = 0.01

#     def test_simulate_options_creation(self):
#         simulate_options = SimulateOptions(
#             self.balance, self.limit, self.stopLossRate, self.takeProfitRate, self.feeRate)

#         self.assertEqual(simulate_options.balance, self.balance)
#         self.assertEqual(simulate_options.limit, self.limit)
#         self.assertEqual(simulate_options.stopLossRate, self.stopLossRate)
#         self.assertEqual(simulate_options.takeProfitRate, self.takeProfitRate)
#         self.assertEqual(simulate_options.feeRate, self.feeRate)


# class TradingTimeframeTestCase(unittest.TestCase):

#     def test_is_trading_open(self):
#         trading_timeframe_true = TradingTimeframe(
#             'UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 23:01 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -')
#         self.assertTrue(trading_timeframe_true.isTradingOpen())

#         trading_timeframe_false = TradingTimeframe('UTC; Sun 02:00 - 02:05')
#         self.assertFalse(trading_timeframe_false.isTradingOpen())


# class TestConfig(unittest.TestCase):

#     def setUp(self):
#         self.config = Config()

#     def test_getHandler_returns_handler(self):
#         handler = self.config.getHandler()
#         self.assertIsInstance(handler, HandlerBase)

#     def test_get_handler(self):
#         self.assertIsInstance(self.config.getHandler(), HandlerCurrencyCom)

#     def test_getIntervals_returns_list_of_intervals(self):
#         intervals = self.config.getIntervals()
#         expected_intervals = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']
#         self.assertEqual(intervals, expected_intervals)

#     def test_get_intervals(self):
#         self.assertEqual(self.config.getIntervals(), [
#                          "5m", "15m", "30m", "1h", "4h", "1d", "1w"])
#         self.assertEqual(self.config.getIntervals(
#             importance='LOW'), ["5m", "15m"])
#         self.assertEqual(self.config.getIntervals(
#             importance='MEDIUM'), ["30m", "1h"])
#         self.assertEqual(self.config.getIntervals(
#             importance='HIGH'), ["4h", "1d", "1w"])

#     def test_get_interval_details(self):
#         intervals = self.config.getIntervalDetails()
#         self.assertEqual(len(intervals), 7)
#         self.assertEqual(intervals[0]["interval"], "5m")
#         self.assertEqual(intervals[0]["name"], "5 minutes")
#         self.assertEqual(intervals[0]["order"], 10)
#         self.assertEqual(intervals[0]["importance"], "LOW")
#         self.assertEqual(intervals[1]["interval"], "15m")
#         self.assertEqual(intervals[1]["name"], "15 minutes")
#         self.assertEqual(intervals[1]["order"], 20)
#         self.assertEqual(intervals[1]["importance"], "LOW")

#     def test_is_trading_open(self):
#         trading_time = 'UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00'
#         trading_timeframe = 'UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00'
#         self.config._Config__tradingTimeframes[trading_time] = MagicMock()
#         self.config._Config__tradingTimeframes[trading_time].isTradingOpen.return_value = True
#         self.assertTrue(self.config.isTradingOpen(trading_timeframe))


# class FlaskAPITestCase(unittest.TestCase):

#     def setUp(self):
#         app.config['TESTING'] = True
#         self.client = app.test_client()

#     def test_get_intervals(self):
#         response = self.client.get(
#             f'/intervals?importance={Const.IMPORTANCE_HIGH}')
#         self.assertEqual(response.status_code, 200)

#     def test_get_symbols(self):
#         response = self.client.get('/symbols?code=GOOGL')
#         self.assertEqual(response.status_code, 200)

#     def test_get_history_data(self):
#         response = self.client.get('/historyData?symbol=GOOGL&interval=5m&limit=20')
#         self.assertEqual(response.status_code, 200)

#     def test_get_indicator_data(self):
#         response = self.client.get(
#             '/indicatorData?code=ma&length=10&symbol=GOOGL&interval=5m&limit=15')
#         self.assertEqual(response.status_code, 200)

#     def test_get_strategy_data(self):
#         response = self.client.get(
#             '/strategyData?code=CCI_14_TREND_100&symbol=GOOGL&interval=5m&limit=15')
#         self.assertEqual(response.status_code, 200)

#     def test_get_signals(self):
#         response = self.client.get(
#             '/signals?symbol=GOOGL&interval=5m&code=CCI_14_TREND_100')
#         self.assertEqual(response.status_code, 200)

#     def test_get_simulate(self):
#         response = self.client.get(
#             '/simulate?symbol=GOOGL&interval=5m&code=CCI_14_TREND_100')
#         self.assertEqual(response.status_code, 200)

#     def test_get_simulations(self):
#         response = self.client.get(
#             '/simulations?symbol=GOOGL&interval=5m&code=CCI_14_TREND_100')
#         self.assertEqual(response.status_code, 200)

#     def test_get_signals_by_simulation(self):
#         response = self.client.get(
#             '/signalsBySimulation?symbol=GOOGL&interval=5m&code=CCI_14_TREND_100')
#         self.assertEqual(response.status_code, 200)

#     def test_create_delete_job(self):
#         response = self.client.post('/jobs', json={'interval': {'minutes': 5}})
#         self.assertEqual(response.status_code, 201)
#         job_id = response.json['job_id']
#         response = self.client.delete(f'/jobs/{job_id}')
#         self.assertEqual(response.status_code, 200)

#     def test_get_jobs(self):
#         response = self.client.get('/jobs')
#         self.assertEqual(response.status_code, 200)


# class TestSymbolList(unittest.TestCase):

#     def setUp(self):
#         self.symbol_list = SymbolList()
#         self.config = Config()

#     def test_checkSymbol(self):
#         # Test that checkSymbol returns True when a symbol exists
#         symbol_code = "BTC/USD"
#         result = self.symbol_list.checkSymbol(symbol_code)
#         self.assertTrue(result)

#         # Test that checkSymbol returns False when a symbol does not exist
#         symbol_code = "NONEXISTENT"
#         result = self.symbol_list.checkSymbol(symbol_code)
#         self.assertFalse(result)

#     def test_getSymbol(self):
#         # Test that getSymbol returns a Symbol object when a symbol exists
#         symbol_code = "BTC/USD"
#         result = self.symbol_list.getSymbol(symbol_code)
#         self.assertIsInstance(result, Symbol)

#         # Test that getSymbol raises an exception when a symbol does not exist
#         symbol_code = "NONEXISTENT"
#         with self.assertRaises(Exception):
#             self.symbol_list.getSymbol(symbol_code)

#     def test_getSymbols(self):
#         # Mock the getSymbols method of the handler to return a list of symbols
#         symbol = {"code": "BTC/USD", "name": "Bitcoin/USD",
#                   "status": "ACTIVE", "tradingTime": "24/7", "type": "CRYPTO"}
#         symbols = [Symbol(code=symbol['code'], name=symbol['name'], status=symbol['status'],
#                           tradingTime=symbol['tradingTime'], type=symbol['type'])]

#         self.config.getHandler().getSymbols = MagicMock(return_value=symbols)

#         # Test that getSymbols returns a list of Symbol objects
#         result = self.symbol_list.getSymbols()
#         self.assertIsInstance(result, list)

#     def test_getSymbolsDictionary(self):
#         # Mock the getSymbolsDictionary method of the handler to return a dictionary of symbols
#         symbol = {"code": "BTC/USD", "name": "Bitcoin/USD",
#                   "status": "ACTIVE", "tradingTime": "24/7", "type": "CRYPTO"}
#         symbols = {symbol['code']: symbol}

#         self.config.getHandler().getSymbolsDictionary = MagicMock(return_value=symbols)

#         # Test that getSymbolsDictionary returns a dictionary of Symbol objects
#         result = self.symbol_list.getSymbolsDictionary()
#         self.assertIsInstance(result, dict)
#         self.assertIsInstance(result["BTC/USD"], dict)

#     def test_getSymbolCodes(self):
#         # Mock the getSymbols method of the handler to return a list of symbols
#         symbols = [{"code": "BTC/USD", "name": "Bitcoin/USD",
#                     "status": "ACTIVE", "tradingTime": "24/7", "type": "CRYPTO"}]
#         self.config.getHandler().getSymbols = MagicMock(return_value=symbols)

#         # Test that getSymbolCodes returns a list of symbol codes
#         result = self.symbol_list.getSymbolCodes()
#         self.assertIsInstance(result, list)
#         self.assertEqual(result, ["BTC/USD"])


# class TestHandlerCurrencyCom(unittest.TestCase):

#     def setUp(self):
#         self.handler = HandlerCurrencyCom()
#         self.symbol = 'BABA'
#         self.interval = '1h'
#         self.limit = 50

#     def test_getHistoryData(self):

#         file_path = f'{os.getcwd()}/static/tests/{self.symbol}_{self.interval}.json'
#         with open(file_path, 'r') as reader:
#             testHistoryData = json.load(reader)

#         with patch('trading_core.handler.HandlerCurrencyCom.getKlines') as mock_getKlines:
#             # Define a mock return value for the __getKlines method
#             mock_response = testHistoryData
#             mock_getKlines.return_value = mock_response

#             history_data = self.handler.getHistoryData(
#                 self.symbol, self.interval, self.limit)

#             # Check that the returned value is a HistoryData object
#             self.assertTrue(isinstance(history_data, HistoryData))

#             # Check that the HistoryData object has the expected properties
#             self.assertEqual(history_data.getSymbol(), self.symbol)
#             self.assertEqual(history_data.getInterval(), self.interval)
#             self.assertEqual(history_data.getLimit(), self.limit)

#             # Check that the DataFrame in the HistoryData object has the expected shape
#             self.assertEqual(
#                 history_data.getDataFrame().shape, (self.limit, 5))

#             self.assertEqual(
#                 history_data.getDataFrame().tail(1).iloc[0, 3], 83.18)

#     def test_getSymbols_from_buffer(self):

#         file_path = f'{os.getcwd()}/static/symbols.json'
#         with open(file_path, 'r') as reader:
#             testSymbols = json.load(reader)

#         symbols = self.handler.getSymbols(isBuffer=True)
#         self.assertIsInstance(symbols, list)
#         self.assertEqual(len(symbols), len(testSymbols))
#         self.assertIsInstance(symbols[0], Symbol)

#     def test_getSymbols_handles_request(self):
#         symbols = self.handler.getSymbols(isBuffer=False)
#         self.assertIsInstance(symbols, list)
#         self.assertGreaterEqual(len(symbols), 1)
#         self.assertIsInstance(symbols[0], Symbol)

#     def test_getSymbols_handles_by_code(self):
#         symbols = self.handler.getSymbols(code='BABA', isBuffer=True)
#         self.assertIsInstance(symbols, list)
#         self.assertEqual(len(symbols), 1)
#         self.assertIsInstance(symbols[0], Symbol)
#         self.assertEqual(symbols[0].code, 'BABA')
#         self.assertEqual(symbols[0].name, 'Alibaba')
#         self.assertEqual(symbols[0].status, 'TRADING')
#         self.assertEqual(symbols[0].type, 'EQUITY')

#     def test_get_completed_unix_time_ms_5m(self):
#         test_time = datetime(2023, 5, 9, 13, 16, 34)  # 2023-05-09 13:16:34
#         expected_result = datetime(
#             2023, 5, 9, 13, 10, 0)  # 2023-05-09 13:10:00
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '5m', test_time), expected_result)

#     def test_get_completed_unix_time_ms_15m(self):
#         test_time = datetime(2023, 5, 9, 14, 22, 47)  # 2023-05-09 14:22:47
#         expected_result = datetime(2023, 5, 9, 14, 0, 0)  # 2023-05-09 14:00:00
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '15m', test_time), expected_result)

#     def test_get_completed_unix_time_ms_30m(self):
#         test_time = datetime(2023, 5, 9, 18, 43, 51)  # 2023-05-09 18:43:51
#         expected_result = datetime(
#             2023, 5, 9, 18, 00, 0)  # 2023-05-09 18:00:00
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '30m', test_time), expected_result)

#     def test_get_completed_unix_time_ms_1h(self):
#         test_time = datetime(2023, 5, 9, 21, 57, 23)  # 2023-05-09 21:57:23
#         expected_result = datetime(2023, 5, 9, 20, 0, 0)  # 2023-05-09 20:00:00
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '1h', test_time), expected_result)

#     def test_get_completed_unix_time_ms_4h(self):
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '4h', datetime(2023, 5, 10, 7, 40, 13)), datetime(2023, 5, 10, 2, 0, 0))
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '4h', datetime(2023, 5, 10, 12, 00, 9)), datetime(2023, 5, 10, 6, 0, 0))
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '4h', datetime(2023, 5, 10, 3, 40, 13)), datetime(2023, 5, 9, 22, 0, 0))
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '4h', datetime(2023, 5, 10, 20, 40, 13)), datetime(2023, 5, 10, 14, 0, 0))

#     def test_get_completed_unix_time_ms_1d(self):
#         test_time = datetime(2023, 5, 10, 0, 31, 44)  # 2023-05-10 00:31:44
#         expected_result = datetime(2023, 5, 9, 2, 0, 0)  # 2023-05-09 02:00:00
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '1d', test_time), expected_result)

#     def test_get_completed_unix_time_ms_1w(self):
#         test_time = datetime(2023, 5, 12, 18, 13, 27)  # 2023-05-12 18:13:27
#         expected_result = datetime(2023, 5, 1, 2, 0)  # 2023-05-01 02:00:00
#         self.assertEqual(self.handler.getOffsetDateTimeByInterval(
#             '1w', test_time), expected_result)

#     def test_getCompletedUnixTimeMs(self):
#         # Test for the current time
#         interval = Config.TA_INTERVAL_5M
#         current_time = self.handler.getOffsetDateTimeByInterval(
#             interval, datetime.now())
#         expected_result = int(current_time.timestamp() * 1000)
#         result = self.handler.getCompletedUnixTimeMs(interval)
#         self.assertEqual(result, expected_result)


# class TestIndicatorBase(unittest.TestCase):

#     def setUp(self):
#         self.symbol = 'BABA'
#         self.interval = '1h'
#         self.limit = 50
#         self.config = Config()
#         self.handler = self.config.getHandler()
#         self.indicator = IndicatorBase()

#     def test_getCode(self):
#         self.assertEqual(self.indicator.getCode(), '')

#     def test_getName(self):
#         self.assertEqual(self.indicator.getName(), '')

#     def test_getIndicator(self):
#         self.handler.getHistoryData = MagicMock(return_value=getHistoryDataTest(
#             self.config, symbol=self.symbol, interval=self.interval, limit=self.limit))
#         history_data = self.indicator.getIndicator(
#             symbol=self.symbol, interval=self.interval, limit=self.limit)
#         self.assertIsInstance(history_data, HistoryData)

#         # Check that the returned value is a HistoryData object
#         self.assertTrue(isinstance(history_data, HistoryData))

#         # Check that the HistoryData object has the expected properties
#         self.assertEqual(history_data.getSymbol(), self.symbol)
#         self.assertEqual(history_data.getInterval(), self.interval)
#         self.assertEqual(history_data.getLimit(), self.limit)

#         # Check that the DataFrame in the HistoryData object has the expected shape
#         self.assertEqual(history_data.getDataFrame().shape, (self.limit, 5))

#         self.assertEqual(history_data.getDataFrame().tail(1).iloc[0, 4], 11)

#     def test_getIndicatorByHistoryData(self):
#         history_data = getHistoryDataTest(
#             self.config, symbol=self.symbol, interval=self.interval, limit=self.limit)
#         df = self.indicator.getIndicatorByHistoryData(history_data)
#         self.assertIsNotNone(df)
    

class TestIndicatorCCI(unittest.TestCase):

    def setUp(self):
        self.symbol = 'BABA'
        self.interval = '1h'
        self.limit = 50
        self.config = Config()

    def test_getIndicator(self):

        mock_history_data = getHistoryDataTest(self.config, symbol=self.symbol, interval=self.interval, limit=self.limit)

        with patch('trading_core.indicator.IndicatorBase.getIndicator') as mock_get_indicator:
            mock_get_indicator.return_value = mock_history_data

            cci_indicator = Indicator_CCI(length=4)
            indicator_df = cci_indicator.getIndicator(symbol=self.symbol, interval=self.interval, limit=self.limit)

            self.assertTrue('CCI' in indicator_df.columns)
            self.assertTrue(len(indicator_df) == 47)  # Only entry with CCI are returned
            self.assertTrue(all(indicator_df['CCI'].notna()))  # All rows have CCI values

            self.assertEqual(indicator_df.tail(1).iloc[0, 5], 50.179211469542025)
    
    def test_getIndicatorByHistoryData(self):

        history_data = getHistoryDataTest(self.config, symbol=self.symbol, interval=self.interval, limit=self.limit)

        cci_indicator = Indicator_CCI(length=4)
        indicator_df = cci_indicator.getIndicatorByHistoryData(history_data)

        self.assertTrue('CCI' in indicator_df.columns)
        self.assertTrue(len(indicator_df) == 47)  # Only entry with CCI are returned
        self.assertTrue(all(indicator_df['CCI'].notna()))  # All rows have CCI values

        self.assertEqual(indicator_df.head(1).iloc[0, 5], 97.61904761904609)
        self.assertEqual(indicator_df.tail(1).iloc[0, 5], 50.179211469542025)


if __name__ == '__main__':
    unittest.main()
