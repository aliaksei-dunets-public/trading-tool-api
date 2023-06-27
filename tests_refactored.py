import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import json
import os
from flask import Flask, jsonify, request

from trading_core.core import Symbol, HistoryData, Const, SimulateOptions, RuntimeBufferStore
from trading_core.model import config, Symbols
from trading_core.handler import CurrencyComApi, StockExchangeHandler
from trading_core.indicator import IndicatorBase, Indicator_CCI
from trading_core.strategy import StrategyConfig, StrategyFactory, Strategy_CCI

from app import app


def getHistoryDataTest(symbol, interval, limit, from_buffer, closed_bars):
    file_path = f'{os.getcwd()}/static/tests/{symbol}_{interval}.json'
    with open(file_path, 'r') as reader:
        testHistoryData = json.load(reader)

    with patch('trading_core.handler.CurrencyComApi.get_api_klines') as mock_getKlines:
        mock_response = testHistoryData
        mock_getKlines.return_value = mock_response

        history_data = config.get_stock_exchange_handler().getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars)
        return history_data


class ConstTestCase(unittest.TestCase):

    def test_signal_values(self):
        self.assertEqual(Const.STRONG_BUY, 'Strong Buy')
        self.assertEqual(Const.BUY, 'Buy')
        self.assertEqual(Const.STRONG_SELL, 'Strong Sell')
        self.assertEqual(Const.SELL, 'Sell')

    def test_direction_values(self):
        self.assertEqual(Const.LONG, 'LONG')
        self.assertEqual(Const.SHORT, 'SHORT')

    def test_column_names(self):
        self.assertEqual(Const.SIGNAL, 'signal')
        self.assertEqual(Const.SYMBOL, 'symbol')
        self.assertEqual(Const.CODE, 'code')
        self.assertEqual(Const.INTERVAL, 'interval')
        self.assertEqual(Const.STRATEGY, 'strategy')
        self.assertEqual(Const.NAME, 'name')
        self.assertEqual(Const.DESCR, 'descr')
        self.assertEqual(Const.STATUS, 'status')

    def test_order_statuses(self):
        self.assertEqual(Const.ORDER_STATUS_OPEN, 'Open')
        self.assertEqual(Const.ORDER_STATUS_CLOSE, 'Close')

    def test_order_close_reason(self):
        self.assertEqual(Const.ORDER_CLOSE_REASON_STOP_LOSS, 'Stop Loss')
        self.assertEqual(Const.ORDER_CLOSE_REASON_TAKE_PROFIT, 'Take Profit')
        self.assertEqual(Const.ORDER_CLOSE_REASON_SIGNAL, 'Signal')

    def test_intervals(self):
        self.assertEqual(Const.TA_INTERVAL_5M, '5m')
        self.assertEqual(Const.TA_INTERVAL_15M, '15m')
        self.assertEqual(Const.TA_INTERVAL_30M, '30m')
        self.assertEqual(Const.TA_INTERVAL_1H, '1h')
        self.assertEqual(Const.TA_INTERVAL_4H, '4h')
        self.assertEqual(Const.TA_INTERVAL_1D, '1d')
        self.assertEqual(Const.TA_INTERVAL_1WK, '1w')


class SymbolTestCase(unittest.TestCase):

    def setUp(self):
        self.code = 'AAPL'
        self.name = 'Apple Inc.'
        self.status = 'Active'
        self.type = 'Stock'
        self.tradingTime = 'UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 23:01 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -'

    def test_symbol_creation(self):
        symbol = Symbol(self.code, self.name, self.status,
                        self.type, self.tradingTime)

        self.assertEqual(symbol.code, self.code)
        self.assertEqual(symbol.name, self.name)
        self.assertEqual(symbol.descr, f'{self.name} ({self.code})')
        self.assertEqual(symbol.status, self.status)
        self.assertEqual(symbol.tradingTime, self.tradingTime)
        self.assertEqual(symbol.type, self.type)


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


class SimulateOptionsTestCase(unittest.TestCase):

    def setUp(self):
        self.balance = 10000
        self.limit = 10
        self.stopLossRate = 0.05
        self.takeProfitRate = 0.1
        self.feeRate = 0.01

    def test_simulate_options_creation(self):
        simulate_options = SimulateOptions(
            self.balance, self.limit, self.stopLossRate, self.takeProfitRate, self.feeRate)

        self.assertEqual(simulate_options.balance, self.balance)
        self.assertEqual(simulate_options.limit, self.limit)
        self.assertEqual(simulate_options.stopLossRate, self.stopLossRate)
        self.assertEqual(simulate_options.takeProfitRate, self.takeProfitRate)
        self.assertEqual(simulate_options.feeRate, self.feeRate)


class TestConfig(unittest.TestCase):

    def test_get_stock_exchange_handler_returns_handler(self):
        handler = config.get_stock_exchange_handler()
        self.assertIsInstance(handler, StockExchangeHandler)
        self.assertEqual(config.get_stock_exchange_id(),
                         handler.getStockExchangeName())

    def test_getIntervals_returns_list_of_intervals(self):
        intervals = config.get_intervals()
        expected_intervals = ['5m', '15m', '30m', '1h', '4h', '1d', '1w']
        self.assertEqual(intervals, expected_intervals)

    def test_get_intervals(self):
        self.assertEqual(config.get_intervals(), [
                         "5m", "15m", "30m", "1h", "4h", "1d", "1w"])
        self.assertEqual(config.get_intervals(
            importances=['LOW']), ["5m", "15m"])
        self.assertEqual(config.get_intervals(
            importances=['MEDIUM']), ["30m", "1h"])
        self.assertEqual(config.get_intervals(
            importances=['HIGH']), ["4h", "1d", "1w"])

    def test_get_interval_details(self):
        intervals = config.get_intervals_config()
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
        trading_time = 'UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59'
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_5M, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_15M, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_30M, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_1H, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_4H, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_1D, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_1WK, trading_time=trading_time))

    def test_is_trading_open_false_cases(self):
        trading_time = 'UTC; Sun 03:01 - 03:02'
        self.assertFalse(config.is_trading_open(
            interval=Const.TA_INTERVAL_5M, trading_time=trading_time))
        self.assertFalse(config.is_trading_open(
            interval=Const.TA_INTERVAL_15M, trading_time=trading_time))
        self.assertFalse(config.is_trading_open(
            interval=Const.TA_INTERVAL_30M, trading_time=trading_time))
        self.assertFalse(config.is_trading_open(
            interval=Const.TA_INTERVAL_1H, trading_time=trading_time))
        self.assertFalse(config.is_trading_open(
            interval=Const.TA_INTERVAL_4H, trading_time=trading_time))
        self.assertFalse(config.is_trading_open(
            interval=Const.TA_INTERVAL_1D, trading_time=trading_time))
        self.assertTrue(config.is_trading_open(
            interval=Const.TA_INTERVAL_1WK, trading_time=trading_time))

    def test_get_indicators(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]
        result = config.get_indicators()
        self.assertEqual(result, expected_result)

    def test_get_strategies_config(self):
        expected_result = {
            Const.TA_STRATEGY_CCI_14_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator value +/- 100",
                Const.LENGTH: 14,
                Const.VALUE: 100
            },
            Const.TA_STRATEGY_CCI_20_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator value +/- 100",
                Const.LENGTH: 20,
                Const.VALUE: 100
            },
            Const.TA_STRATEGY_CCI_50_TREND_0: {
                Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator value 0",
                Const.LENGTH: 50,
                Const.VALUE: 0
            }
        }
        result = config.get_strategies_config()
        self.assertEqual(result, expected_result)

    def test_get_strategy(self):
        expected_result = {
            Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.NAME: "CCI(14): Indicator value +/- 100",
            Const.LENGTH: 14,
            Const.VALUE: 100
        }

        result = config.get_strategy(Const.TA_STRATEGY_CCI_14_TREND_100)

        self.assertEqual(expected_result, result)

    def test_get_strategies(self):
        expected_result = [
            {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator value +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator value +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator value 0"}
        ]
        result = config.get_strategies()
        self.assertEqual(result, expected_result)

    def test_get_strategy_codes(self):
        expected_result = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_20_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0
        ]
        result = config.get_strategy_codes()
        self.assertEqual(result, expected_result)


class CurrencyComApiTest(unittest.TestCase):

    def setUp(self):
        self.api = CurrencyComApi()

    def test_getStockExchangeName(self):
        stock_exchange_name = self.api.getStockExchangeName()
        self.assertEqual(stock_exchange_name, Const.STOCK_EXCH_CURRENCY_COM)

    def test_getApiEndpoint(self):
        api_endpoint = self.api.getApiEndpoint()
        self.assertEqual(
            api_endpoint, "https://api-adapter.backend.currency.com/api/v2")

    def test_getHistoryData(self):
        symbol = "BTC/USD"
        interval = "1h"
        limit = 5

        history_data = self.api.getHistoryData(symbol, interval, limit)

        self.assertIsInstance(history_data, HistoryData)
        self.assertEqual(history_data.getSymbol(), symbol)
        self.assertEqual(history_data.getInterval(), interval)
        self.assertEqual(history_data.getLimit(), limit)
        self.assertEqual(len(history_data.getDataFrame()), limit)
        self.assertEqual(history_data.getEndDateTime(),
                         history_data.getDataFrame().index[-1])

        history_data_closed_bar = self.api.getHistoryData(
            symbol, interval, limit, closed_bars=True)

        self.assertIsInstance(history_data_closed_bar, HistoryData)
        self.assertEqual(history_data_closed_bar.getSymbol(), symbol)
        self.assertEqual(history_data_closed_bar.getInterval(), interval)
        self.assertEqual(history_data_closed_bar.getLimit(), limit)
        self.assertEqual(len(history_data_closed_bar.getDataFrame()), limit)

        self.assertEqual(history_data.getDataFrame().index[limit-2], history_data_closed_bar.getDataFrame().index[limit-1])

    @patch('trading_core.handler.requests.get')
    def test_getHistoryData_success(self, mock_get):
        symbol = "BTC"
        interval = "1h"
        limit = 3

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
        [
            [1623686400000, "36500", "36800", "36400", "36650", "100"],
            [1623690000000, "36650", "36800", "36500", "36750", "150"],
            [1623693600000, "36750", "37000", "36600", "36900", "200"]
        ]
        '''
        mock_get.return_value = mock_response

        history_data = self.api.getHistoryData(symbol, interval, limit)

        self.assertIsInstance(history_data, HistoryData)
        self.assertEqual(history_data.getSymbol(), symbol)
        self.assertEqual(history_data.getInterval(), interval)
        self.assertEqual(history_data.getLimit(), limit)

        expected_df = pd.DataFrame(
            {
                "Open": [36500, 36650, 36750],
                "High": [36800, 36800, 37000],
                "Low": [36400, 36500, 36600],
                "Close": [36650, 36750, 36900],
                "Volume": [100, 150, 200]
            },
            index=[
                self.api.getDatetimeByUnixTimeMs(1623686400000),
                self.api.getDatetimeByUnixTimeMs(1623690000000),
                self.api.getDatetimeByUnixTimeMs(1623693600000)],
            columns=["Open", "High", "Low", "Close", "Volume"]
        )

        expected_df = expected_df.astype(float)
        expected_df = expected_df.rename_axis("Datetime")

        pd.testing.assert_frame_equal(history_data.getDataFrame(), expected_df)

    @patch('trading_core.handler.requests.get')
    def test_getHistoryData_error(self, mock_get):
        symbol = "BTC"
        interval = "1h"
        limit = 100

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            self.api.getHistoryData(symbol, interval, limit)

    @patch('trading_core.handler.requests.get')
    def test_getSymbols_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
        {
            "symbols": [
                {
                    "quoteAssetId": "USD",
                    "assetType": "CRYPTOCURRENCY",
                    "marketModes": ["REGULAR"],
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "status": "ACTIVE",
                    "tradingHours": "UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00"
                },
                {
                    "quoteAssetId": "USD",
                    "assetType": "EQUITY",
                    "marketModes": ["REGULAR"],
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "status": "ACTIVE",
                    "tradingHours": "UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00"
                }
            ]
        }
        '''
        mock_get.return_value = mock_response

        symbols = self.api.getSymbols()

        self.assertEqual(len(symbols), 2)

        expected_symbols = {"BTC":
                            Symbol(code="BTC", name="Bitcoin",
                                   status="ACTIVE", tradingTime="UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00", type="CRYPTOCURRENCY"),
                            "AAPL":
                            Symbol(code="AAPL", name="Apple Inc.",
                                   status="ACTIVE", tradingTime="UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00", type="EQUITY")
                            }

        for row, symbol in symbols.items():
            code = symbol.code
            self.assertEqual(code, expected_symbols[code].code)
            self.assertEqual(symbol.name, expected_symbols[code].name)
            self.assertEqual(symbol.status, expected_symbols[code].status)
            self.assertEqual(
                symbol.tradingTime, expected_symbols[code].tradingTime)
            self.assertEqual(symbol.type, expected_symbols[code].type)

    @patch('trading_core.handler.requests.get')
    def test_getSymbols_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            self.api.getSymbols()

    def test_get_intervals(self):
        intervals = self.api.get_intervals()

        self.assertEqual(len(intervals), 7)

        expected_intervals = [
            {"interval": "5m", "name": "5 minutes",
                "order": 10, "importance": Const.IMPORTANCE_LOW},
            {"interval": "15m", "name": "15 minutes",
                "order": 20, "importance": Const.IMPORTANCE_LOW},
            {"interval": "30m", "name": "30 minutes",
                "order": 30, "importance": Const.IMPORTANCE_MEDIUM},
            {"interval": "1h", "name": "1 hour",
                "order": 40, "importance": Const.IMPORTANCE_MEDIUM},
            {"interval": "4h", "name": "4 hours",
                "order": 50, "importance": Const.IMPORTANCE_HIGH},
            {"interval": "1d", "name": "1 day",
                "order": 60, "importance": Const.IMPORTANCE_HIGH},
            {"interval": "1w", "name": "1 week",
                "order": 70, "importance": Const.IMPORTANCE_HIGH}
        ]

        for i in range(len(intervals)):
            self.assertEqual(intervals[i]["interval"],
                             expected_intervals[i]["interval"])
            self.assertEqual(intervals[i]["name"],
                             expected_intervals[i]["name"])
            self.assertEqual(intervals[i]["order"],
                             expected_intervals[i]["order"])
            self.assertEqual(intervals[i]["importance"],
                             expected_intervals[i]["importance"])

    def test_convertResponseToDataFrame(self):
        api_response = [
            [1623686400000, "36500", "36800", "36400", "36650", "100"],
            [1623690000000, "36650", "36800", "36500", "36750", "150"],
            [1623693600000, "36750", "37000", "36600", "36900", "200"]
        ]

        expected_df = pd.DataFrame(
            {
                "Open": [36500, 36650, 36750],
                "High": [36800, 36800, 37000],
                "Low": [36400, 36500, 36600],
                "Close": [36650, 36750, 36900],
                "Volume": [100, 150, 200]
            },
            index=[self.api.getDatetimeByUnixTimeMs(1623686400000),
                   self.api.getDatetimeByUnixTimeMs(1623690000000),
                   self.api.getDatetimeByUnixTimeMs(1623693600000)],
            columns=["Open", "High", "Low", "Close", "Volume"]
        )
        expected_df = expected_df.astype(float)
        expected_df = expected_df.rename_axis("Datetime")

        df = self.api.convertResponseToDataFrame(api_response)

        pd.testing.assert_frame_equal(df, expected_df)

    def test_getEndDatetime_with_closed_bar(self):
        # June 15, 2023, 10:30:00 AM
        original_datetime = datetime(2023, 6, 15, 10, 32, 0)

        # Test interval TA_INTERVAL_5M
        interval = self.api.TA_API_INTERVAL_5M
        # June 15, 2023, 10:25:00 AM
        expected_datetime = datetime(2023, 6, 15, 10, 25, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1H
        interval = self.api.TA_API_INTERVAL_1H
        # June 15, 2023, 09:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 9, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_4H
        interval = self.api.TA_API_INTERVAL_4H
        # June 15, 2023, 6:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 6, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1D
        interval = self.api.TA_API_INTERVAL_1D
        # June 14, 2023, 02:00:00 AM
        expected_datetime = datetime(2023, 6, 14, 2, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1WK
        interval = self.api.TA_API_INTERVAL_1WK
        # June 5, 2023, 2:00:00 AM
        expected_datetime = datetime(2023, 6, 5, 2, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

    def test_getEndDatetime(self):
        # June 15, 2023, 10:30:00 AM
        original_datetime = datetime(2023, 6, 15, 10, 32, 0)

        # Test interval TA_INTERVAL_5M
        interval = self.api.TA_API_INTERVAL_5M
        # June 15, 2023, 10:30:00 AM
        expected_datetime = datetime(2023, 6, 15, 10, 30, 0)
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_15M
        interval = self.api.TA_API_INTERVAL_15M
        # June 15, 2023, 10:30:00 AM
        expected_datetime = datetime(2023, 6, 15, 10, 30, 0)
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval 30
        interval = self.api.TA_API_INTERVAL_30M
        # June 15, 2023, 10:30:00 AM
        expected_datetime = datetime(2023, 6, 15, 10, 30, 0)
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1H
        interval = self.api.TA_API_INTERVAL_1H
        # June 15, 2023, 10:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 10, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_4H
        interval = self.api.TA_API_INTERVAL_4H
        # June 15, 2023, 10:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 10, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1D
        interval = self.api.TA_API_INTERVAL_1D
        # June 15, 2023, 02:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 2, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1WK
        interval = self.api.TA_API_INTERVAL_1WK
        # June 12, 2023, 2:00:00 AM
        expected_datetime = datetime(2023, 6, 12, 2, 0, 0)
        result = self.api.getEndDatetime(
            interval, original_datetime)
        self.assertEqual(result, expected_datetime)

    def test_get_completed_unix_time_ms_5m(self):
        test_time = datetime(2023, 5, 9, 13, 16, 34)  # 2023-05-09 13:16:34
        expected_result = datetime(
            2023, 5, 9, 13, 10, 0)  # 2023-05-09 13:10:00
        self.assertEqual(self.api.getEndDatetime(
            '5m', test_time, closed_bars=True), expected_result)

    def test_get_completed_unix_time_ms_15m(self):
        test_time = datetime(2023, 5, 9, 14, 22, 47)  # 2023-05-09 14:22:47
        expected_result = datetime(2023, 5, 9, 14, 0, 0)  # 2023-05-09 14:00:00
        self.assertEqual(self.api.getEndDatetime(
            '15m', test_time, closed_bars=True), expected_result)

    def test_get_completed_unix_time_ms_30m(self):
        test_time = datetime(2023, 5, 9, 18, 43, 51)  # 2023-05-09 18:43:51
        expected_result = datetime(
            2023, 5, 9, 18, 00, 0)  # 2023-05-09 18:00:00
        self.assertEqual(self.api.getEndDatetime(
            '30m', test_time, closed_bars=True), expected_result)

    def test_get_completed_unix_time_ms_1h(self):
        test_time = datetime(2023, 5, 9, 21, 57, 23)  # 2023-05-09 21:57:23
        expected_result = datetime(2023, 5, 9, 20, 0, 0)  # 2023-05-09 20:00:00
        self.assertEqual(self.api.getEndDatetime(
            '1h', test_time, closed_bars=True), expected_result)

    def test_get_completed_unix_time_ms_4h(self):
        self.assertEqual(self.api.getEndDatetime(
            '4h', datetime(2023, 5, 10, 7, 40, 13), closed_bars=True), datetime(2023, 5, 10, 2, 0, 0))
        self.assertEqual(self.api.getEndDatetime(
            '4h', datetime(2023, 5, 10, 12, 00, 9), closed_bars=True), datetime(2023, 5, 10, 6, 0, 0))
        self.assertEqual(self.api.getEndDatetime(
            '4h', datetime(2023, 5, 10, 3, 40, 13), closed_bars=True), datetime(2023, 5, 9, 22, 0, 0))
        self.assertEqual(self.api.getEndDatetime(
            '4h', datetime(2023, 5, 10, 20, 40, 13), closed_bars=True), datetime(2023, 5, 10, 14, 0, 0))

    def test_get_completed_unix_time_ms_1d(self):
        test_time = datetime(2023, 5, 10, 0, 31, 44)  # 2023-05-10 00:31:44
        expected_result = datetime(2023, 5, 9, 2, 0, 0)  # 2023-05-09 02:00:00
        self.assertEqual(self.api.getEndDatetime(
            '1d', test_time, closed_bars=True), expected_result)

    def test_get_completed_unix_time_ms_1w(self):
        test_time = datetime(2023, 5, 12, 18, 13, 27)  # 2023-05-12 18:13:27
        expected_result = datetime(2023, 5, 1, 2, 0)  # 2023-05-01 02:00:00
        self.assertEqual(self.api.getEndDatetime(
            '1w', test_time, closed_bars=True), expected_result)

    def test_getOffseUnixTimeMsByInterval(self):
        interval = self.api.TA_API_INTERVAL_1H

        with unittest.mock.patch('trading_core.handler.CurrencyComApi.getEndDatetime') as mock_offset:
            mock_offset.return_value = datetime(
                2023, 6, 15, 10, 0, 0)  # June 15, 2023, 10:00:00 AM
            expected_timestamp = int(
                datetime(2023, 6, 15, 10, 0, 0).timestamp() * 1000)
            result = self.api.getOffseUnixTimeMsByInterval(interval)
            self.assertEqual(result, expected_timestamp)

    def test_getTimezoneDifference(self):
        with unittest.mock.patch('trading_core.handler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(
                2023, 6, 15, 10, 30, 0)  # June 15, 2023, 10:30:00 AM
            mock_datetime.utcnow.return_value = datetime(
                2023, 6, 15, 7, 30, 0)  # June 15, 2023, 7:30:00 AM
            expected_difference = 3  # 10:30 AM local time - 7:30 AM UTC time = 3 hours
            result = self.api.getTimezoneDifference()
            self.assertEqual(result, expected_difference)

    def test_getDatetimeByUnixTimeMs(self):
        timestamp = 1683532800000  # 2023-05-08 10:00:00

        # 2023-05-08 10:00:00
        expected_datetime = datetime(2023, 5, 8, 10, 0, 0)
        result = self.api.getDatetimeByUnixTimeMs(timestamp)
        self.assertEqual(result, expected_datetime)

        converted_timestamp = self.api.getUnixTimeMsByDatetime(result)
        self.assertEqual(timestamp, converted_timestamp)

    def test_get_trading_timeframes(self):
        trading_time = 'UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00'

        timeframes = self.api.get_trading_timeframes(trading_time)

        self.assertTrue('mon' in timeframes)
        self.assertTrue('fri' in timeframes)
        self.assertEqual(
            timeframes['mon'][0][Const.START_TIME], datetime.strptime('01:05', '%H:%M'))
        self.assertEqual(
            timeframes['mon'][0][Const.END_TIME], datetime.strptime('19:00', '%H:%M'))

    def test_is_trading_open_true_cases(self):
        trading_time = 'UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59'
        timeframes = self.api.get_trading_timeframes(trading_time)
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_5M, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_15M, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_30M, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_1H, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_4H, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_1D, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_1WK, trading_timeframes=timeframes))

    def test_is_trading_open_false_cases(self):
        trading_time = 'UTC; Sun 03:01 - 03:02'
        timeframes = self.api.get_trading_timeframes(trading_time)
        self.assertFalse(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_5M, trading_timeframes=timeframes))
        self.assertFalse(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_15M, trading_timeframes=timeframes))
        self.assertFalse(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_30M, trading_timeframes=timeframes))
        self.assertFalse(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_1H, trading_timeframes=timeframes))
        self.assertFalse(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_4H, trading_timeframes=timeframes))
        self.assertFalse(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_1D, trading_timeframes=timeframes))
        self.assertTrue(self.api.is_trading_open(
            interval=self.api.TA_API_INTERVAL_1WK, trading_timeframes=timeframes))


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


class StockExchangeHandlerTests(unittest.TestCase):
    def setUp(self):
        # Initialize the StockExchangeHandler instance with a mock runtime_buffer and API implementation
        self.handler = StockExchangeHandler(Const.STOCK_EXCH_CURRENCY_COM)
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

        self.buffer.clearSymbolsBuffer()

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
        # Arrange

        # Mock the API call to return intervals

        # Act
        result = self.handler.get_intervals()

        # Assert
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


class SymbolsTestCase(unittest.TestCase):

    def setUp(self):
        self.mocked_handler = MagicMock()
        self.symbols = Symbols(from_buffer=False)
        self.symbols._Symbols__get_symbols = MagicMock(return_value={
            'BTC': Symbol('BTC', 'Bitcoin', 'active', 'crypto', '09:00-17:00'),
            'ETH': Symbol('ETH', 'Ethereum', 'active', 'crypto', '08:00-16:00'),
            'LTC': Symbol('LTC', 'Litecoin', 'inactive', 'crypto', '10:00-18:00')
        })

    def test_check_symbol_existing(self):
        self.assertTrue(self.symbols.check_symbol('BTC'))

    def test_check_symbol_non_existing(self):
        self.assertFalse(self.symbols.check_symbol('XYZ'))

    def test_get_symbol_existing(self):
        symbol = self.symbols.get_symbol('ETH')
        self.assertEqual(symbol.code, 'ETH')
        self.assertEqual(symbol.name, 'Ethereum')

    def test_get_symbol_non_existing(self):
        symbol = self.symbols.get_symbol('XYZ')
        self.assertIsNone(symbol)

    def test_get_symbols_from_buffer(self):
        self.symbols._Symbols__from_buffer = True
        symbols = self.symbols.get_symbols()
        self.assertEqual(len(symbols), 3)
        self.assertIsInstance(symbols['BTC'], Symbol)
        self.assertIsInstance(symbols['ETH'], Symbol)
        self.assertIsInstance(symbols['LTC'], Symbol)

    def test_get_symbols_force_fetch(self):
        self.symbols._Symbols__from_buffer = False
        symbols = self.symbols.get_symbols()
        self.assertEqual(len(symbols), 3)
        self.assertIsInstance(symbols['BTC'], Symbol)
        self.assertIsInstance(symbols['ETH'], Symbol)
        self.assertIsInstance(symbols['LTC'], Symbol)

    def test_get_symbol_list_with_code(self):
        symbols = self.symbols.get_symbol_list('BTC', '', '', '')
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].code, 'BTC')

    def test_get_symbol_list_with_name(self):
        symbols = self.symbols.get_symbol_list('', 'Ether', '', '')
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].name, 'Ethereum')

    def test_get_symbol_list_with_status(self):
        symbols = self.symbols.get_symbol_list('', '', 'inactive', '')
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].status, 'inactive')

    def test_get_symbol_list_with_type(self):
        symbols = self.symbols.get_symbol_list('', '', '', 'crypto')
        self.assertEqual(len(symbols), 3)
        self.assertEqual(symbols[0].type, 'crypto')


class TestIndicatorBase(unittest.TestCase):

    def setUp(self):
        self.symbol = 'BABA'
        self.interval = '1h'
        self.limit = 50
        self.config = config
        self.from_buffer = True
        self.closed_bars = False
        self.handler = self.config.get_stock_exchange_handler()
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


class TestIndicatorCCI(unittest.TestCase):

    def setUp(self):
        self.symbol = 'BABA'
        self.interval = '1h'
        self.limit = 50
        self.config = config
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


class StrategyConfigTests(unittest.TestCase):

    def setUp(self):
        self.config = config
        self.strategy_code = Const.TA_STRATEGY_CCI_14_TREND_100
        self.strategy_config = self.config.get_strategy(self.strategy_code)
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


class StrategyFactoryTests(unittest.TestCase):

    def setUp(self):
        self.factory = StrategyFactory(Const.TA_STRATEGY_CCI_14_TREND_100)

    def test_init_valid_strategy_code(self):
        strategy_code = Const.TA_STRATEGY_CCI_14_TREND_100
        factory = StrategyFactory(strategy_code)
        self.assertIsInstance(factory, StrategyFactory)

    def test_init_invalid_strategy_code(self):
        with self.assertRaises(Exception):
            # Test missing strategy code
            StrategyFactory('missing_strategy_code')

    def test_get_strategy(self):
        symbol = 'BTC/USD'
        interval = '1h'
        limit = 10
        closed_bar = False
        from_buffer = True
        strategy = self.factory.get_strategy_data(
            symbol, interval, limit, from_buffer, closed_bar)
        self.assertEqual(3, len(strategy))

    def test_get_strategy_by_history_data(self):
        symbol = 'BABA'
        interval = '1h'
        limit = 50
        from_buffer = True
        closed_bars = False

        history_data = getHistoryDataTest(symbol=symbol, interval=interval,
                                          limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

        strategy_data = self.factory.get_strategy_data_by_history_data(
            history_data)

        self.assertEqual(strategy_data.tail(1).iloc[0, 6], '')
        self.assertEqual(strategy_data.tail(8).iloc[0, 6], Const.STRONG_SELL)
        self.assertEqual(strategy_data.tail(11).iloc[0, 6], Const.BUY)


class FlaskAPITestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_get_symbols(self):
        response = self.client.get('/symbols?from_buffer=true')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertGreater(len(json_api_response), 1)

    def test_get_symbol_by_code(self):
        code = 'BTC/USD'
        response = self.client.get(f'/symbols?code={code}')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertEqual(json_api_response[0]['code'], code)

    def test_get_symbols_by_name(self):
        name = 'Bitcoin'
        expected_result = {'code': 'BTC/USD', 'name': 'Bitcoin / USD',
                           'descr': 'Bitcoin / USD (BTC/USD)', 'status': 'TRADING', 'tradingTime': 'UTC; Mon - 21:00, 21...0, 21:05 -', 'type': 'CRYPTOCURRENCY'}
        response = self.client.get(f'/symbols?name={name}&from_buffer=true')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertGreater(len(json_api_response), 1)
        self.assertTrue(expected_result, json_api_response)

    def test_get_intervals(self):
        expected_intervals = [{"interval": Const.TA_INTERVAL_5M,  "name": "5 minutes",  "order": 10, "importance": Const.IMPORTANCE_LOW},
                              {"interval": Const.TA_INTERVAL_15M, "name": "15 minutes",
                               "order": 20, "importance": Const.IMPORTANCE_LOW},
                              {"interval": Const.TA_INTERVAL_30M, "name": "30 minutes",
                               "order": 30, "importance": Const.IMPORTANCE_MEDIUM},
                              {"interval": Const.TA_INTERVAL_1H,  "name": "1 hour",
                               "order": 40, "importance": Const.IMPORTANCE_MEDIUM},
                              {"interval": Const.TA_INTERVAL_4H,  "name": "4 hours",
                               "order": 50, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1D,  "name": "1 day",
                               "order": 60, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1WK, "name": "1 week",     "order": 70, "importance": Const.IMPORTANCE_HIGH}]

        response = self.client.get(
            f'/intervals')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_intervals, json_api_response)

        expected_intervals = [{"interval": Const.TA_INTERVAL_4H,  "name": "4 hours",
                               "order": 50, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1D,  "name": "1 day",
                               "order": 60, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1WK, "name": "1 week",     "order": 70, "importance": Const.IMPORTANCE_HIGH}]

        response = self.client.get(
            f'/intervals?importance={Const.IMPORTANCE_HIGH}')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_intervals, json_api_response)

    def test_get_indicators(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]

        response = self.client.get(
            f'/indicators')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_result, json_api_response)

    def test_get_strategies(self):
        expected_result = [
            {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator value +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator value +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator value 0"}
        ]

        response = self.client.get(
            f'/strategies')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_result, json_api_response)

    def test_get_history_data(self):
        interval = '4h'
        limit = 20

        response = self.client.get(
            f'/historyData?symbol=BTC/USD&interval={interval}&limit={limit}')

        json_api_response = json.loads(response.text)['data']
        latest_bar = json_api_response[-1]

        end_datetime = config.get_stock_exchange_handler().getEndDatetime(interval)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(datetime.fromisoformat(
            latest_bar["Datetime"][:-1]), end_datetime)
        self.assertEqual(len(json_api_response), limit)

    def test_get_strategy_data(self):
        interval = '4h'
        limit = 20
        # /strategyData?code=CCI_20_TREND_100&symbol=BTC/USD&interval=4h&limit=20&closed_bars=true&from_buffer=true
        response = self.client.get(f'/strategyData?code=CCI_20_TREND_100&symbol=BTC/USD&interval={interval}&limit={limit}&closed_bars=true&from_buffer=true')

        json_api_response = json.loads(response.text)['data']
        latest_bar = json_api_response[-1]

        end_datetime = config.get_stock_exchange_handler().getEndDatetime(interval=interval, closed_bars=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(datetime.fromisoformat(
            latest_bar["Datetime"][:-1]), end_datetime)
        self.assertEqual(len(json_api_response), 3)


if __name__ == '__main__':
    unittest.main()
