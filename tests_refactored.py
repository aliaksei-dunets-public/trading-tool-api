import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import pandas as pd
import json
import os
from flask import Flask, jsonify, request
from bson import ObjectId
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler

from trading_core.constants import Const
from trading_core.core import (
    config,
    Symbol,
    CandelBar,
    CandelBarSignal,
    HistoryData,
    SimulateOptions,
    Signal,
    RuntimeBufferStore,
)
from trading_core.model import model, Symbols, ParamBase, ParamSymbol
from trading_core.mongodb import MongoBase, MongoAlerts, MongoJobs, MongoOrders
from trading_core.handler import CurrencyComApi, StockExchangeHandler
from trading_core.indicator import IndicatorBase, Indicator_CCI
from trading_core.strategy import StrategyConfig, StrategyFactory, SignalFactory
from trading_core.responser import (
    ResponserBase,
    ResponserWeb,
    ResponserEmail,
    ResponserBot,
    MessageBase,
    MessageEmail,
    Messages,
)
from trading_core.simulation import (
    Order,
    SimulationBase,
    SimulationLong,
    SimulationShort,
    Simulator,
)

from app import app


def getHistoryDataTest(symbol, interval, limit, from_buffer, closed_bars):
    file_path = f"{os.getcwd()}/static/tests/{symbol}_{interval}.json"
    with open(file_path, "r") as reader:
        testHistoryData = json.load(reader)

    with patch("trading_core.handler.CurrencyComApi.get_api_klines") as mock_getKlines:
        mock_response = testHistoryData
        mock_getKlines.return_value = mock_response

        history_data = model.get_handler().getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars
        )
        return history_data


class ConstTestCase(unittest.TestCase):
    def test_signal_values(self):
        self.assertEqual(Const.STRONG_BUY, "Strong Buy")
        self.assertEqual(Const.BUY, "Buy")
        self.assertEqual(Const.STRONG_SELL, "Strong Sell")
        self.assertEqual(Const.SELL, "Sell")

    def test_direction_values(self):
        self.assertEqual(Const.LONG, "LONG")
        self.assertEqual(Const.SHORT, "SHORT")

    def test_column_names(self):
        self.assertEqual(Const.PARAM_SIGNAL, "signal")
        self.assertEqual(Const.PARAM_SYMBOL, "symbol")
        self.assertEqual(Const.CODE, "code")
        self.assertEqual(Const.INTERVAL, "interval")
        self.assertEqual(Const.STRATEGY, "strategy")
        self.assertEqual(Const.NAME, "name")
        self.assertEqual(Const.DESCR, "descr")
        self.assertEqual(Const.STATUS, "status")

    def test_order_statuses(self):
        self.assertEqual(Const.STATUS_OPEN, "Open")
        self.assertEqual(Const.STATUS_CLOSE, "Close")

    def test_order_close_reason(self):
        self.assertEqual(Const.ORDER_CLOSE_REASON_STOP_LOSS, "STOP_LOSS")
        self.assertEqual(Const.ORDER_CLOSE_REASON_TAKE_PROFIT, "TAKE_PROFIT")
        self.assertEqual(Const.ORDER_CLOSE_REASON_SIGNAL, "SIGNAL")

    def test_intervals(self):
        self.assertEqual(Const.TA_INTERVAL_5M, "5m")
        self.assertEqual(Const.TA_INTERVAL_15M, "15m")
        self.assertEqual(Const.TA_INTERVAL_30M, "30m")
        self.assertEqual(Const.TA_INTERVAL_1H, "1h")
        self.assertEqual(Const.TA_INTERVAL_4H, "4h")
        self.assertEqual(Const.TA_INTERVAL_1D, "1d")
        self.assertEqual(Const.TA_INTERVAL_1WK, "1w")


class TestConfig(unittest.TestCase):
    def test_get_config_value(self):
        self.assertEqual(config.get_config_value(Const.CONFIG_DEBUG_LOG), True)
        self.assertIsNone(config.get_config_value("Test"))

    def test_get_stock_exchange_id(self):
        self.assertEqual(config.get_stock_exchange_id(), Const.STOCK_EXCH_CURRENCY_COM)

    def test_get_indicators_config(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}
        ]
        result = config.get_indicators_config()
        self.assertEqual(result, expected_result)

    def test_get_strategies_config(self):
        expected_result = {
            Const.TA_STRATEGY_CCI_14_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator against Trend +/- 100",
                Const.LENGTH: 14,
                Const.VALUE: 100,
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
                Const.VALUE: 100,
            },
            Const.TA_STRATEGY_CCI_50_TREND_0: {
                Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator direction Trend 0",
                Const.LENGTH: 50,
                Const.VALUE: 0,
            },
        }
        result = config.get_strategies_config()
        self.assertEqual(result, expected_result)


class SymbolTestCase(unittest.TestCase):
    def setUp(self):
        self.code = "AAPL"
        self.name = "Apple Inc."
        self.status = "Active"
        self.type = "Stock"
        self.tradingTime = "UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 23:01 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -"

    def test_symbol_creation(self):
        symbol = Symbol(self.code, self.name, self.status, self.type, self.tradingTime)

        self.assertEqual(symbol.code, self.code)
        self.assertEqual(symbol.name, self.name)
        self.assertEqual(symbol.descr, f"{self.name} ({self.code})")
        self.assertEqual(symbol.status, self.status)
        self.assertEqual(symbol.tradingTime, self.tradingTime)
        self.assertEqual(symbol.type, self.type)


class HistoryDataTestCase(unittest.TestCase):
    def setUp(self):
        self.symbol = "BABA"
        self.interval = Const.TA_INTERVAL_1H
        self.limit = 50
        self.data = pd.read_json(
            f"{os.getcwd()}/static/tests/{self.symbol}_{self.interval}.json"
        )

    def test_history_data_creation(self):
        history_data = HistoryData(self.symbol, self.interval, self.limit, self.data)

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
            self.balance,
            self.limit,
            self.stopLossRate,
            self.takeProfitRate,
            self.feeRate,
        )

        self.assertEqual(simulate_options.init_balance, self.balance)
        self.assertEqual(simulate_options.limit, self.limit)
        self.assertEqual(simulate_options.stop_loss_rate, self.stopLossRate)
        self.assertEqual(simulate_options.take_profit_rate, self.takeProfitRate)
        self.assertEqual(simulate_options.fee_rate, self.feeRate)


class SignalTests(unittest.TestCase):
    def setUp(self):
        date_time = datetime(2023, 6, 1, 12, 0, 0)
        symbol = "BTC/USD"
        interval = "1h"
        strategy = "CCI_14_TREND_100"
        signal = "BUY"
        self.signal = Signal(date_time, symbol, interval, strategy, signal)

    def test_get_signal(self):
        expected_signal = {
            Const.DATETIME: "2023-06-01T12:00:00",
            Const.PARAM_SYMBOL: "BTC/USD",
            Const.INTERVAL: "1h",
            Const.STRATEGY: "CCI_14_TREND_100",
            Const.PARAM_SIGNAL: "BUY",
        }
        self.assertEqual(self.signal.get_signal_dict(), expected_signal)

    def test_get_date_time(self):
        expected_date_time = datetime(2023, 6, 1, 12, 0, 0)
        self.assertEqual(self.signal.get_date_time(), expected_date_time)

    def test_get_symbol(self):
        expected_symbol = "BTC/USD"
        self.assertEqual(self.signal.get_symbol(), expected_symbol)

    def test_get_interval(self):
        expected_interval = "1h"
        self.assertEqual(self.signal.get_interval(), expected_interval)

    def test_get_strategy(self):
        expected_strategy = "CCI_14_TREND_100"
        self.assertEqual(self.signal.get_strategy(), expected_strategy)

    def test_is_compatible_debug_signal(self):
        signals_config = [Const.DEBUG_SIGNAL]
        self.assertTrue(self.signal.is_compatible(signals_config))

    def test_is_compatible_no_signals_config(self):
        self.assertTrue(self.signal.is_compatible())

    def test_is_compatible_matching_signal(self):
        signals_config = ["BUY"]
        self.assertTrue(self.signal.is_compatible(signals_config))

    def test_is_compatible_non_matching_signal(self):
        signals_config = ["SELL"]
        self.assertFalse(self.signal.is_compatible(signals_config))


class RuntimeBufferStoreTests(unittest.TestCase):
    def setUp(self):
        self.buffer_store = RuntimeBufferStore()
        self.test_data_frame = pd.DataFrame(
            {
                "Open": [36500, 36650, 36750],
                "High": [36800, 36800, 37000],
                "Low": [36400, 36500, 36600],
                "Close": [36650, 36750, 36900],
                "Volume": [100, 150, 200],
            },
            index=[
                datetime(2021, 6, 14, 18, 0, 0),
                datetime(2021, 6, 14, 19, 0, 0),
                datetime(2021, 6, 14, 20, 0, 0),
            ],
            columns=["Open", "High", "Low", "Close", "Volume"],
        )

    def tearDown(self):
        self.buffer_store.clearHistoryDataBuffer()
        self.buffer_store.checkSymbolsInBuffer()

    def test_getHistoryDataFromBuffer_existingData_returnsCorrectData(self):
        # Arrange
        symbol = "BTC/USD"
        interval = "1h"
        limit = 3
        end_datetime = datetime(2021, 6, 14, 20, 0, 0)
        data_frame = self.test_data_frame
        history_data = HistoryData(symbol, interval, limit, data_frame)
        self.buffer_store.setHistoryDataToBuffer(history_data)

        # Act
        result = self.buffer_store.getHistoryDataFromBuffer(
            symbol, interval, limit, end_datetime
        )

        # Assert
        self.assertEqual(result.getSymbol(), history_data.getSymbol())
        self.assertEqual(result.getInterval(), history_data.getInterval())
        self.assertEqual(result.getLimit(), history_data.getLimit())
        self.assertEqual(result.getEndDateTime(), history_data.getEndDateTime())

    def test_getHistoryDataFromBuffer_nonExistingData_returnsNone(self):
        # Arrange
        symbol = "BTC/USD"
        interval = "1h"
        limit = 3
        end_datetime = datetime(2021, 6, 14, 20, 0, 0)

        # Act
        result = self.buffer_store.validateHistoryDataInBuffer(
            symbol, interval, limit, end_datetime
        )

        # Assert
        self.assertIsNotNone(result)

    def test_validateHistoryDataInBuffer_existingData_returnsTrue(self):
        # Arrange
        symbol = "BTC/USD"
        interval = "1h"
        limit = 3
        end_datetime = datetime(2021, 6, 14, 20, 0, 0)
        data_frame = self.test_data_frame
        history_data = HistoryData(symbol, interval, limit, data_frame)
        self.buffer_store.setHistoryDataToBuffer(history_data)

        # Act
        result = self.buffer_store.validateHistoryDataInBuffer(
            symbol, interval, limit, end_datetime
        )

        # Assert
        self.assertTrue(result)

    def test_validateHistoryDataInBuffer_existingData_returnsFalse(self):
        # Arrange
        symbol = "BTC/USD"
        interval = "1h"
        limit = 3
        data_frame = self.test_data_frame
        history_data = HistoryData(symbol, interval, limit, data_frame)
        self.buffer_store.setHistoryDataToBuffer(history_data)

        # Assert
        self.assertFalse(
            self.buffer_store.validateHistoryDataInBuffer(
                symbol, interval, 4, datetime(2021, 6, 14, 20, 0, 0)
            )
        )
        # Assert
        self.assertFalse(
            self.buffer_store.validateHistoryDataInBuffer(
                symbol, interval, 3, datetime(2021, 6, 14, 21, 0, 0)
            )
        )

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
        symbols = {
            "BTC": Symbol(
                code="BTC",
                name="Bitcoin",
                status="ACTIVE",
                tradingTime="UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00",
                type="CRYPTOCURRENCY",
            ),
            "AAPL": Symbol(
                code="AAPL",
                name="Apple Inc.",
                status="ACTIVE",
                tradingTime="UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00",
                type="EQUITY",
            ),
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
        trading_time = "UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59"
        self.buffer_store.clearTimeframeBuffer()
        self.assertFalse(self.buffer_store.checkTimeframeInBuffer(trading_time))
        self.assertIsNone(self.buffer_store.getTimeFrameFromBuffer(trading_time))

        self.buffer_store.setTimeFrameToBuffer(trading_time, {"mon": [1, 2]})
        self.assertTrue(self.buffer_store.checkTimeframeInBuffer(trading_time))
        self.assertIsNotNone(self.buffer_store.getTimeFrameFromBuffer(trading_time))
        self.buffer_store.clearTimeframeBuffer()

    def test_signal_functionality(self):
        date_time = datetime(2023, 6, 1, 12, 0, 0)
        symbol = "BTC/USD"
        interval = "1h"
        strategy = "CCI_14_TREND_100"
        signal = "BUY"
        self.signal = Signal(date_time, symbol, interval, strategy, signal)

        buffer_key = (symbol, interval, strategy)

        self.assertEqual(
            buffer_key,
            self.buffer_store.get_signal_buffer_key(
                symbol=symbol, interval=interval, strategy=strategy
            ),
        )

        self.buffer_store.clear_signal_buffer()
        self.assertFalse(
            self.buffer_store.check_signal_in_buffer(
                symbol=symbol, interval=interval, strategy=strategy
            )
        )
        self.assertIsNone(
            self.buffer_store.get_signal_from_buffer(
                symbol=symbol, interval=interval, strategy=strategy, date_time=date_time
            )
        )

        self.buffer_store.set_signal_to_buffer(self.signal)
        self.assertTrue(
            self.buffer_store.check_signal_in_buffer(
                symbol=symbol, interval=interval, strategy=strategy
            )
        )
        self.assertIsNotNone(
            self.buffer_store.get_signal_from_buffer(
                symbol=symbol, interval=interval, strategy=strategy, date_time=date_time
            )
        )
        self.buffer_store.clearTimeframeBuffer()

    def test_job_functionality(self):
        scheduler = BackgroundScheduler()
        job_id = "job_id_001"
        job = Job(scheduler, job_id)

        self.buffer_store.set_job_to_buffer(job)

        result_job = self.buffer_store.get_job_from_buffer(job_id)

        self.assertIsInstance(result_job, Job)
        self.assertEqual(result_job.id, job_id)

        self.buffer_store.remove_job_from_buffer(job_id)
        result_job = self.buffer_store.get_job_from_buffer(job_id)

        self.assertIsNone(result_job)


class TestModel(unittest.TestCase):
    def test_get_handler_returns_handler(self):
        handler = model.get_handler()
        self.assertIsInstance(handler, StockExchangeHandler)
        self.assertEqual(config.get_stock_exchange_id(), handler.getStockExchangeName())

    def test_getIntervals_returns_list_of_intervals(self):
        intervals = model.get_intervals()
        expected_intervals = ["5m", "15m", "30m", "1h", "4h", "1d", "1w"]
        self.assertEqual(intervals, expected_intervals)

    def test_get_intervals(self):
        self.assertEqual(
            model.get_intervals(), ["5m", "15m", "30m", "1h", "4h", "1d", "1w"]
        )
        self.assertEqual(model.get_intervals(importances=["LOW"]), ["5m", "15m"])
        self.assertEqual(model.get_intervals(importances=["MEDIUM"]), ["30m", "1h"])
        self.assertEqual(model.get_intervals(importances=["HIGH"]), ["4h", "1d", "1w"])

    def test_get_interval_details(self):
        intervals = model.get_intervals_config()
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
        handler = model.get_handler()
        trading_time = "UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59"
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_5M, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_15M, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_30M, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_1H, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_4H, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_1D, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_1WK, trading_time=trading_time
            )
        )

    def test_is_trading_open_false_cases(self):
        handler = model.get_handler()
        trading_time = "UTC; Sun 03:01 - 03:02"
        self.assertFalse(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_5M, trading_time=trading_time
            )
        )
        self.assertFalse(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_15M, trading_time=trading_time
            )
        )
        self.assertFalse(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_30M, trading_time=trading_time
            )
        )
        self.assertFalse(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_1H, trading_time=trading_time
            )
        )
        self.assertFalse(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_4H, trading_time=trading_time
            )
        )
        self.assertFalse(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_1D, trading_time=trading_time
            )
        )
        self.assertTrue(
            handler.is_trading_open(
                interval=Const.TA_INTERVAL_1WK, trading_time=trading_time
            )
        )

    def test_get_indicators(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}
        ]
        result = model.get_indicators_config()
        self.assertEqual(result, expected_result)

    def test_get_strategy(self):
        expected_result = {
            Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.NAME: "CCI(14): Indicator against Trend +/- 100",
            Const.LENGTH: 14,
            Const.VALUE: 100,
        }

        result = model.get_strategy(Const.TA_STRATEGY_CCI_14_TREND_100)

        self.assertEqual(expected_result, result)

    def test_get_strategies(self):
        expected_result = [
            {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator against Trend +/- 100",
            },
            {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_170_165,
                Const.NAME: "CCI(14): Indicator direction Trend +/- 170 | 165",
            },
            {
                Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator against Trend +/- 100",
            },
            {
                Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator direction Trend 0",
            },
        ]
        result = model.get_strategies()
        self.assertEqual(result, expected_result)

    def test_get_strategy_codes(self):
        expected_result = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_14_TREND_170_165,
            Const.TA_STRATEGY_CCI_20_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0,
        ]
        result = model.get_strategy_codes()
        self.assertEqual(result, expected_result)

    def test_get_sorted_strategy_codes_with_default_arguments(self):
        expected_result = [
            Const.TA_STRATEGY_CCI_50_TREND_0,
            Const.TA_STRATEGY_CCI_20_TREND_100,
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_14_TREND_170_165,
        ]
        self.assertEqual(model.get_sorted_strategy_codes(), expected_result)

    def test_get_sorted_strategy_codes_with_custom_strategies(self):
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0,
        ]
        expected_result = [
            Const.TA_STRATEGY_CCI_50_TREND_0,
            Const.TA_STRATEGY_CCI_14_TREND_100,
        ]
        self.assertEqual(model.get_sorted_strategy_codes(strategies), expected_result)

    def test_get_sorted_strategy_codes_with_custom_strategies_and_ascending_order(self):
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0,
        ]
        expected_result = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_50_TREND_0,
        ]
        self.assertEqual(
            model.get_sorted_strategy_codes(strategies, desc=False), expected_result
        )


class TestParamBase(unittest.TestCase):
    def test_copy_instance(self):
        # Create an instance of ParamBase
        param_base = ParamBase()

        # Copy the instance using copy_instance
        copied_param_base = ParamBase.copy_instance(param_base)

        # Check if the original and copied instances are not the same object
        self.assertIsNot(param_base, copied_param_base)


class TestParamSymbol(unittest.TestCase):
    def test_init(self):
        # Test initializing ParamSymbol with consistency_check=True
        symbol = "BABA"
        param_symbol = ParamSymbol(symbol)

        # Check if the symbol attribute is set correctly
        self.assertEqual(param_symbol.symbol, symbol)

    def test_get_symbol_config(self):
        # Test get_symbol_config when symbol config exists
        symbol = "BABA"
        param_symbol = ParamSymbol(symbol, consistency_check=False)

        # Manually set the symbol_config for testing
        param_symbol._ParamSymbol__symbol_config = "MockSymbolConfig"

        symbol_config = param_symbol.get_symbol_config()

        # Check if get_symbol_config returns the correct symbol config
        self.assertEqual(symbol_config, "MockSymbolConfig")

    def test_get_symbol_config_exception(self):
        # Test get_symbol_config when symbol config doesn't exist
        symbol = "INVALID_SYMBOL"
        param_symbol = ParamSymbol(symbol, consistency_check=False)

        # Ensure that symbol_config is None (not set manually)
        self.assertIsNone(param_symbol._ParamSymbol__symbol_config)

        # Attempt to get the symbol config and expect an exception
        with self.assertRaises(Exception):
            param_symbol.get_symbol_config()


class MongoBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.mongo_base = MongoBase()
        collection_name = Const.DB_COLLECTION_ALERTS
        self.mongo_base._collection = self.mongo_base.get_collection(collection_name)

    def test_get_collection(self):
        collection_name = Const.DB_COLLECTION_ALERTS
        collection = self.mongo_base.get_collection(collection_name)
        self.assertEqual(collection.name, collection_name)

    def test_functionality(self):
        query = {
            Const.DB_ALERT_TYPE: Const.ALERT_TYPE_BOT,
            Const.DB_CHANNEL_ID: 689916629,
            Const.DB_SYMBOL: "BTC/USD",
            Const.DB_INTERVAL: Const.TA_INTERVAL_5M,
            Const.DB_STRATEGIES: [
                Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.TA_STRATEGY_CCI_20_TREND_100,
            ],
            Const.DB_SIGNALS: [Const.DEBUG_SIGNAL],
            Const.DB_COMMENT: "Test comments",
        }
        self.document_id = self.mongo_base.insert_one(query)
        self.assertIsInstance(self.document_id, str)
        self.assertTrue(ObjectId.is_valid(self.document_id))

        result_get_one = self.mongo_base.get_one(self.document_id)
        self.assertEqual(result_get_one[Const.DB_ALERT_TYPE], Const.ALERT_TYPE_BOT)
        self.assertEqual(result_get_one[Const.DB_CHANNEL_ID], 689916629)
        self.assertEqual(result_get_one[Const.DB_SYMBOL], "BTC/USD")
        self.assertEqual(result_get_one[Const.DB_INTERVAL], Const.TA_INTERVAL_5M)
        self.assertEqual(
            result_get_one[Const.DB_STRATEGIES],
            [Const.TA_STRATEGY_CCI_14_TREND_100, Const.TA_STRATEGY_CCI_20_TREND_100],
        )
        self.assertEqual(result_get_one[Const.DB_SIGNALS], [Const.DEBUG_SIGNAL])
        self.assertEqual(result_get_one[Const.DB_COMMENT], "Test comments")

        query_update = {
            Const.DB_STRATEGIES: [Const.TA_STRATEGY_CCI_14_TREND_100],
            Const.DB_SIGNALS: [],
            Const.DB_COMMENT: "Test comments updated",
        }
        result = self.mongo_base.update_one(self.document_id, query_update)
        self.assertTrue(result)

        result_get_one = self.mongo_base.get_one(self.document_id)
        self.assertEqual(
            result_get_one[Const.DB_STRATEGIES], [Const.TA_STRATEGY_CCI_14_TREND_100]
        )
        self.assertEqual(result_get_one[Const.DB_SIGNALS], [])
        self.assertEqual(result_get_one[Const.DB_COMMENT], "Test comments updated")

        query = {Const.DB_INTERVAL: Const.TA_INTERVAL_5M}
        result = self.mongo_base.get_many(query)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        result = self.mongo_base.delete_one(self.document_id)
        self.assertTrue(result)

        result_get_one = self.mongo_base.get_one(self.document_id)
        self.assertIsNone(result_get_one)


class MongoJobsTestCase(unittest.TestCase):
    def setUp(self):
        self.mongo_jobs = MongoJobs()

    def test_funtionality(self):
        job_type = Const.JOB_TYPE_BOT
        interval = Const.TA_INTERVAL_1D
        is_active = True
        self.job_id = self.mongo_jobs.create_job(job_type, interval, is_active)
        self.assertTrue(ObjectId.is_valid(self.job_id))

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertEqual(result_get_one[Const.DB_ID], ObjectId(self.job_id))
        self.assertEqual(result_get_one[Const.DB_JOB_TYPE], job_type)
        self.assertEqual(result_get_one[Const.DB_INTERVAL], interval)
        self.assertEqual(result_get_one[Const.DB_IS_ACTIVE], is_active)

        result = self.mongo_jobs.deactivate_job(self.job_id)
        self.assertTrue(result)

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertEqual(result_get_one[Const.DB_IS_ACTIVE], False)

        result = self.mongo_jobs.activate_job(self.job_id)
        self.assertTrue(result)

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertEqual(result_get_one[Const.DB_IS_ACTIVE], True)

        result = self.mongo_jobs.delete_job(self.job_id)
        self.assertTrue(result)

        result_get_one = self.mongo_jobs.get_one(self.job_id)
        self.assertIsNone(result_get_one)


class MongoAlertsTestCase(unittest.TestCase):
    def setUp(self):
        self.mongo_alerts = MongoAlerts()

    def test_db_alerts_functionality(self):
        alert_type = Const.ALERT_TYPE_BOT
        channel_id = 689916629
        symbol = "BTC/USD"
        interval = Const.TA_INTERVAL_5M
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_20_TREND_100,
        ]
        signals = [Const.DEBUG_SIGNAL]
        comment = "Test comments"

        self.document_id = self.mongo_alerts.create_alert(
            alert_type, channel_id, symbol, interval, strategies, signals, comment
        )

        self.assertTrue(ObjectId.is_valid(self.document_id))

        result = self.mongo_alerts.get_alerts(alert_type=alert_type, interval=interval)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        result = self.mongo_alerts.get_alerts(symbol=symbol)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        self.mongo_alerts.delete_one(self.document_id)
        result_get_one = self.mongo_alerts.get_one(self.document_id)
        self.assertIsNone(result_get_one)


class MongoOrdersTestCase(unittest.TestCase):
    def setUp(self):
        self.mongo_orders = MongoOrders()

    def test_db_orders_functionality(self):
        order_type = Const.LONG
        open_date_time = ""
        symbol = "BTC/USD"
        interval = Const.TA_INTERVAL_5M
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_20_TREND_100,
        ]

        self.document_id = self.mongo_orders.create_order(
            order_type, open_date_time, symbol, interval, 100, 1.1, strategies
        )

        result = self.mongo_orders.get_orders(interval=interval)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        result = self.mongo_orders.get_orders(symbol=symbol)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        self.mongo_orders.delete_one(self.document_id)
        result_get_one = self.mongo_orders.get_one(self.document_id)
        self.assertIsNone(result_get_one)


class CurrencyComApiTest(unittest.TestCase):
    def setUp(self):
        self.api = CurrencyComApi()

    def test_getStockExchangeName(self):
        stock_exchange_name = self.api.getStockExchangeName()
        self.assertEqual(stock_exchange_name, Const.STOCK_EXCH_CURRENCY_COM)

    def test_getApiEndpoint(self):
        api_endpoint = self.api.getApiEndpoint()
        self.assertEqual(
            api_endpoint, "https://api-adapter.backend.currency.com/api/v2"
        )

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
        self.assertEqual(
            history_data.getEndDateTime(), history_data.getDataFrame().index[-1]
        )

        history_data_closed_bar = self.api.getHistoryData(
            symbol, interval, limit, closed_bars=True
        )

        self.assertIsInstance(history_data_closed_bar, HistoryData)
        self.assertEqual(history_data_closed_bar.getSymbol(), symbol)
        self.assertEqual(history_data_closed_bar.getInterval(), interval)
        self.assertEqual(history_data_closed_bar.getLimit(), limit)
        self.assertEqual(len(history_data_closed_bar.getDataFrame()), limit)

        self.assertEqual(
            history_data.getDataFrame().index[limit - 2],
            history_data_closed_bar.getDataFrame().index[limit - 1],
        )

    @patch("trading_core.handler.requests.get")
    def test_getHistoryData_success(self, mock_get):
        symbol = "BTC"
        interval = "1h"
        limit = 3

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        [
            [1623686400000, "36500", "36800", "36400", "36650", "100"],
            [1623690000000, "36650", "36800", "36500", "36750", "150"],
            [1623693600000, "36750", "37000", "36600", "36900", "200"]
        ]
        """
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
                "Volume": [100, 150, 200],
            },
            index=[
                self.api.getDatetimeByUnixTimeMs(1623686400000),
                self.api.getDatetimeByUnixTimeMs(1623690000000),
                self.api.getDatetimeByUnixTimeMs(1623693600000),
            ],
            columns=["Open", "High", "Low", "Close", "Volume"],
        )

        expected_df = expected_df.astype(float)
        expected_df = expected_df.rename_axis("Datetime")

        pd.testing.assert_frame_equal(history_data.getDataFrame(), expected_df)

    @patch("trading_core.handler.requests.get")
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

    @patch("trading_core.handler.requests.get")
    def test_getSymbols_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        {
            "symbols": [
                {
                    "quoteAssetId": "USD",
                    "assetType": "CRYPTOCURRENCY",
                    "marketModes": ["REGULAR"],
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "status": "TRADING",
                    "tradingHours": "UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00"
                },
                {
                    "quoteAssetId": "USD",
                    "assetType": "EQUITY",
                    "marketModes": ["REGULAR"],
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "status": "BREAK",
                    "tradingHours": "UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00"
                }
            ]
        }
        """
        mock_get.return_value = mock_response

        symbols = self.api.getSymbols()

        self.assertEqual(len(symbols), 2)

        expected_symbols = {
            "BTC": Symbol(
                code="BTC",
                name="Bitcoin",
                status="Open",
                tradingTime="UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00",
                type="CRYPTOCURRENCY",
            ),
            "AAPL": Symbol(
                code="AAPL",
                name="Apple Inc.",
                status="Close",
                tradingTime="UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00",
                type="EQUITY",
            ),
        }

        for row, symbol in symbols.items():
            code = symbol.code
            self.assertEqual(code, expected_symbols[code].code)
            self.assertEqual(symbol.name, expected_symbols[code].name)
            self.assertEqual(symbol.status, expected_symbols[code].status)
            self.assertEqual(symbol.tradingTime, expected_symbols[code].tradingTime)
            self.assertEqual(symbol.type, expected_symbols[code].type)

    @patch("trading_core.handler.requests.get")
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
            {
                "interval": "5m",
                "name": "5 minutes",
                "order": 10,
                "importance": Const.IMPORTANCE_LOW,
            },
            {
                "interval": "15m",
                "name": "15 minutes",
                "order": 20,
                "importance": Const.IMPORTANCE_LOW,
            },
            {
                "interval": "30m",
                "name": "30 minutes",
                "order": 30,
                "importance": Const.IMPORTANCE_MEDIUM,
            },
            {
                "interval": "1h",
                "name": "1 hour",
                "order": 40,
                "importance": Const.IMPORTANCE_MEDIUM,
            },
            {
                "interval": "4h",
                "name": "4 hours",
                "order": 50,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": "1d",
                "name": "1 day",
                "order": 60,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": "1w",
                "name": "1 week",
                "order": 70,
                "importance": Const.IMPORTANCE_HIGH,
            },
        ]

        for i in range(len(intervals)):
            self.assertEqual(
                intervals[i]["interval"], expected_intervals[i]["interval"]
            )
            self.assertEqual(intervals[i]["name"], expected_intervals[i]["name"])
            self.assertEqual(intervals[i]["order"], expected_intervals[i]["order"])
            self.assertEqual(
                intervals[i]["importance"], expected_intervals[i]["importance"]
            )

    def test_convertResponseToDataFrame(self):
        api_response = [
            [1623686400000, "36500", "36800", "36400", "36650", "100"],
            [1623690000000, "36650", "36800", "36500", "36750", "150"],
            [1623693600000, "36750", "37000", "36600", "36900", "200"],
        ]

        expected_df = pd.DataFrame(
            {
                "Open": [36500, 36650, 36750],
                "High": [36800, 36800, 37000],
                "Low": [36400, 36500, 36600],
                "Close": [36650, 36750, 36900],
                "Volume": [100, 150, 200],
            },
            index=[
                self.api.getDatetimeByUnixTimeMs(1623686400000),
                self.api.getDatetimeByUnixTimeMs(1623690000000),
                self.api.getDatetimeByUnixTimeMs(1623693600000),
            ],
            columns=["Open", "High", "Low", "Close", "Volume"],
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
        result = self.api.getEndDatetime(interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1H
        interval = self.api.TA_API_INTERVAL_1H
        # June 15, 2023, 09:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 9, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_4H
        interval = self.api.TA_API_INTERVAL_4H
        # June 15, 2023, 6:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 6, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1D
        interval = self.api.TA_API_INTERVAL_1D
        # June 14, 2023, 02:00:00 AM
        expected_datetime = datetime(2023, 6, 14, 2, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime, closed_bars=True)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1WK
        interval = self.api.TA_API_INTERVAL_1WK
        # June 5, 2023, 2:00:00 AM
        expected_datetime = datetime(2023, 6, 5, 2, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime, closed_bars=True)
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
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1D
        interval = self.api.TA_API_INTERVAL_1D
        # June 15, 2023, 02:00:00 AM
        expected_datetime = datetime(2023, 6, 15, 2, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

        # Test interval TA_INTERVAL_1WK
        interval = self.api.TA_API_INTERVAL_1WK
        # June 12, 2023, 2:00:00 AM
        expected_datetime = datetime(2023, 6, 12, 2, 0, 0)
        result = self.api.getEndDatetime(interval, original_datetime)
        self.assertEqual(result, expected_datetime)

    def test_get_completed_unix_time_ms_5m(self):
        test_time = datetime(2023, 5, 9, 13, 16, 34)  # 2023-05-09 13:16:34
        expected_result = datetime(2023, 5, 9, 13, 10, 0)  # 2023-05-09 13:10:00
        self.assertEqual(
            self.api.getEndDatetime("5m", test_time, closed_bars=True), expected_result
        )

    def test_get_completed_unix_time_ms_15m(self):
        test_time = datetime(2023, 5, 9, 14, 22, 47)  # 2023-05-09 14:22:47
        expected_result = datetime(2023, 5, 9, 14, 0, 0)  # 2023-05-09 14:00:00
        self.assertEqual(
            self.api.getEndDatetime("15m", test_time, closed_bars=True), expected_result
        )

    def test_get_completed_unix_time_ms_30m(self):
        test_time = datetime(2023, 5, 9, 18, 43, 51)  # 2023-05-09 18:43:51
        expected_result = datetime(2023, 5, 9, 18, 00, 0)  # 2023-05-09 18:00:00
        self.assertEqual(
            self.api.getEndDatetime("30m", test_time, closed_bars=True), expected_result
        )

    def test_get_completed_unix_time_ms_1h(self):
        test_time = datetime(2023, 5, 9, 21, 57, 23)  # 2023-05-09 21:57:23
        expected_result = datetime(2023, 5, 9, 20, 0, 0)  # 2023-05-09 20:00:00
        self.assertEqual(
            self.api.getEndDatetime("1h", test_time, closed_bars=True), expected_result
        )

    def test_get_completed_unix_time_ms_4h(self):
        self.assertEqual(
            self.api.getEndDatetime(
                "4h", datetime(2023, 5, 10, 7, 40, 13), closed_bars=True
            ),
            datetime(2023, 5, 10, 2, 0, 0),
        )
        self.assertEqual(
            self.api.getEndDatetime(
                "4h", datetime(2023, 5, 10, 12, 00, 9), closed_bars=True
            ),
            datetime(2023, 5, 10, 6, 0, 0),
        )
        self.assertEqual(
            self.api.getEndDatetime(
                "4h", datetime(2023, 5, 10, 3, 40, 13), closed_bars=True
            ),
            datetime(2023, 5, 9, 22, 0, 0),
        )
        self.assertEqual(
            self.api.getEndDatetime(
                "4h", datetime(2023, 5, 10, 20, 40, 13), closed_bars=True
            ),
            datetime(2023, 5, 10, 14, 0, 0),
        )

    def test_get_completed_unix_time_ms_1d(self):
        test_time = datetime(2023, 5, 10, 0, 31, 44)  # 2023-05-10 00:31:44
        expected_result = datetime(2023, 5, 9, 2, 0, 0)  # 2023-05-09 02:00:00
        self.assertEqual(
            self.api.getEndDatetime("1d", test_time, closed_bars=True), expected_result
        )

    def test_get_completed_unix_time_ms_1w(self):
        test_time = datetime(2023, 5, 12, 18, 13, 27)  # 2023-05-12 18:13:27
        expected_result = datetime(2023, 5, 1, 2, 0)  # 2023-05-01 02:00:00
        self.assertEqual(
            self.api.getEndDatetime("1w", test_time, closed_bars=True), expected_result
        )

    def test_getOffseUnixTimeMsByInterval(self):
        interval = self.api.TA_API_INTERVAL_1H

        with unittest.mock.patch(
            "trading_core.handler.CurrencyComApi.getEndDatetime"
        ) as mock_offset:
            mock_offset.return_value = datetime(
                2023, 6, 15, 10, 0, 0
            )  # June 15, 2023, 10:00:00 AM
            expected_timestamp = int(datetime(2023, 6, 15, 10, 0, 0).timestamp() * 1000)
            result = self.api.getOffseUnixTimeMsByInterval(interval)
            self.assertEqual(result, expected_timestamp)

    def test_getTimezoneDifference(self):
        with unittest.mock.patch("trading_core.handler.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(
                2023, 6, 15, 10, 30, 0
            )  # June 15, 2023, 10:30:00 AM
            mock_datetime.utcnow.return_value = datetime(
                2023, 6, 15, 7, 30, 0
            )  # June 15, 2023, 7:30:00 AM
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
        trading_time = "UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00"

        timeframes = self.api.get_trading_timeframes(trading_time)

        self.assertTrue("mon" in timeframes)
        self.assertTrue("fri" in timeframes)
        self.assertEqual(
            timeframes["mon"][0][Const.START_TIME], datetime.strptime("01:05", "%H:%M")
        )
        self.assertEqual(
            timeframes["mon"][0][Const.API_FLD_END_TIME],
            datetime.strptime("19:00", "%H:%M"),
        )

    def test_is_trading_open_true_cases(self):
        trading_time = "UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59"
        timeframes = self.api.get_trading_timeframes(trading_time)
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_5M, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_15M, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_30M, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_1H, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_4H, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_1D, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_1WK, trading_timeframes=timeframes
            )
        )

    def test_is_trading_open_false_cases(self):
        trading_time = "UTC; Sun 03:01 - 03:02"
        timeframes = self.api.get_trading_timeframes(trading_time)
        self.assertFalse(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_5M, trading_timeframes=timeframes
            )
        )
        self.assertFalse(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_15M, trading_timeframes=timeframes
            )
        )
        self.assertFalse(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_30M, trading_timeframes=timeframes
            )
        )
        self.assertFalse(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_1H, trading_timeframes=timeframes
            )
        )
        self.assertFalse(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_4H, trading_timeframes=timeframes
            )
        )
        self.assertFalse(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_1D, trading_timeframes=timeframes
            )
        )
        self.assertTrue(
            self.api.is_trading_open(
                interval=self.api.TA_API_INTERVAL_1WK, trading_timeframes=timeframes
            )
        )


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
        symbol = "BTC/USD"
        interval = "1h"
        limit = 22
        from_buffer = True
        closed_bars = True
        end_datetime = self.handler.getEndDatetime(
            interval=interval, closed_bars=closed_bars
        )

        self.buffer.clearHistoryDataBuffer()

        is_buffer = self.buffer.checkHistoryDataInBuffer(
            symbol=symbol, interval=interval
        )
        self.assertFalse(is_buffer)

        # Act
        result = self.handler.getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars
        )

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.getSymbol(), symbol)
        self.assertEqual(result.getInterval(), interval)
        self.assertEqual(result.getLimit(), limit)
        self.assertEqual(result.getEndDateTime(), end_datetime)

        is_buffer = self.buffer.checkHistoryDataInBuffer(
            symbol=symbol, interval=interval
        )
        self.assertTrue(is_buffer)

        is_buffer_valid = self.buffer.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=end_datetime
        )
        self.assertTrue(is_buffer_valid)

        limit = 25
        is_buffer_valid = self.buffer.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=end_datetime
        )
        self.assertFalse(is_buffer_valid)

        limit = 20
        result = self.handler.getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.getSymbol(), symbol)
        self.assertEqual(result.getInterval(), interval)
        self.assertEqual(result.getLimit(), limit)
        self.assertEqual(result.getEndDateTime(), end_datetime)

    def test_getHistoryData_noBufferExistingData_returnsCorrectData(self):
        # Arrange
        symbol = "BTC/USD"
        interval = "1h"
        limit = 10
        from_buffer = False
        end_datetime = self.handler.getEndDatetime(interval=interval)

        # Act
        result = self.handler.getHistoryData(symbol, interval, limit, from_buffer)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.getSymbol(), symbol)
        self.assertEqual(result.getInterval(), interval)
        self.assertEqual(result.getLimit(), limit)
        self.assertEqual(result.getEndDateTime(), end_datetime)

        is_buffer = self.buffer.checkHistoryDataInBuffer(symbol=symbol, interval="4h")
        self.assertFalse(is_buffer)

        end_datetime = self.handler.getEndDatetime(interval=interval, closed_bars=True)
        is_buffer_valid = self.buffer.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=end_datetime
        )
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
        trading_time = "UTC; Mon 00:01 - 23:59; Tue 00:01 - 23:59; Wed 00:01 - 23:59; Thu 00:01 - 23:59; Fri 00:01 - 23:59"
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_5M, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_15M, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_30M, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_1H, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_4H, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_1D, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_1WK, trading_time=trading_time
            )
        )

    def test_is_trading_open_false_cases(self):
        trading_time = "UTC; Sun 03:01 - 03:02"
        self.assertFalse(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_5M, trading_time=trading_time
            )
        )
        self.assertFalse(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_15M, trading_time=trading_time
            )
        )
        self.assertFalse(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_30M, trading_time=trading_time
            )
        )
        self.assertFalse(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_1H, trading_time=trading_time
            )
        )
        self.assertFalse(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_4H, trading_time=trading_time
            )
        )
        self.assertFalse(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_1D, trading_time=trading_time
            )
        )
        self.assertTrue(
            self.handler.is_trading_open(
                interval=Const.TA_INTERVAL_1WK, trading_time=trading_time
            )
        )


class SymbolsTestCase(unittest.TestCase):
    def setUp(self):
        self.mocked_handler = MagicMock()
        self.symbols = Symbols(from_buffer=False)
        self.symbols._Symbols__get_symbols = MagicMock(
            return_value={
                "BTC": Symbol("BTC", "Bitcoin", "active", "crypto", "09:00-17:00"),
                "ETH": Symbol("ETH", "Ethereum", "active", "crypto", "08:00-16:00"),
                "LTC": Symbol("LTC", "Litecoin", "inactive", "crypto", "10:00-18:00"),
            }
        )

    def tearDown(self) -> None:
        RuntimeBufferStore().clearSymbolsBuffer()

    def test_check_symbol_existing(self):
        self.assertTrue(self.symbols.check_symbol("BTC"))

    def test_check_symbol_non_existing(self):
        self.assertFalse(self.symbols.check_symbol("XYZ"))

    def test_get_symbol_existing(self):
        symbol = self.symbols.get_symbol("ETH")
        self.assertEqual(symbol.code, "ETH")
        self.assertEqual(symbol.name, "Ethereum")

    def test_get_symbol_non_existing(self):
        symbol = self.symbols.get_symbol("XYZ")
        self.assertIsNone(symbol)

    def test_get_symbols_from_buffer(self):
        self.symbols._Symbols__from_buffer = True
        symbols = self.symbols.get_symbols()
        self.assertEqual(len(symbols), 3)
        self.assertIsInstance(symbols["BTC"], Symbol)
        self.assertIsInstance(symbols["ETH"], Symbol)
        self.assertIsInstance(symbols["LTC"], Symbol)

    def test_get_symbols_force_fetch(self):
        self.symbols._Symbols__from_buffer = False
        symbols = self.symbols.get_symbols()
        self.assertEqual(len(symbols), 3)
        self.assertIsInstance(symbols["BTC"], Symbol)
        self.assertIsInstance(symbols["ETH"], Symbol)
        self.assertIsInstance(symbols["LTC"], Symbol)

    def test_get_symbol_list_with_code(self):
        symbols = self.symbols.get_symbol_list("BTC", "", "", "")
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].code, "BTC")

    def test_get_symbol_list_with_name(self):
        symbols = self.symbols.get_symbol_list("", "Ether", "", "")
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].name, "Ethereum")

    def test_get_symbol_list_with_status(self):
        symbols = self.symbols.get_symbol_list("", "", "inactive", "")
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].status, "inactive")

    def test_get_symbol_list_with_type(self):
        symbols = self.symbols.get_symbol_list("", "", "", "crypto")
        self.assertEqual(len(symbols), 3)
        self.assertEqual(symbols[0].type, "crypto")

    def test_get_symbol_list_json(self):
        expected_result = {
            "code": "BTC",
            "name": "Bitcoin / USD",
            "descr": "Bitcoin / USD (BTC/USD)",
            "status": "TRADING",
            "tradingTime": "UTC; Mon - 21:00, 21:05 -; Tue - 21:00, 21:05 -; Wed - 21:00, 21:05 -; Thu - 21:00, 21:05 -; Fri - 21:00, 22:01 -; Sat - 05:00, 07:00 - 21:00, 21:05 -; Sun - 21:00, 21:05 -",
            "type": "CRYPTOCURRENCY",
        }

        symbols = self.symbols.get_symbol_list_json(code="BTC")
        self.assertEqual(symbols[0]["code"], expected_result["code"])

    def test_get_symbol_code(self):
        symbols = self.symbols.get_symbol_codes()
        self.assertGreaterEqual(len(symbols), 1)
        self.assertIn("BTC", symbols)


class TestIndicatorBase(unittest.TestCase):
    def setUp(self):
        self.symbol = "BABA"
        self.interval = "1h"
        self.limit = 50
        self.model = model
        self.from_buffer = True
        self.closed_bars = False
        self.handler = self.model.get_handler()
        self.indicator = IndicatorBase()

    def test_getCode(self):
        self.assertEqual(self.indicator.get_code(), "")

    def test_getName(self):
        self.assertEqual(self.indicator.get_name(), "")

    def test_getIndicator(self):
        self.handler.getHistoryData = MagicMock(
            return_value=getHistoryDataTest(
                symbol=self.symbol,
                interval=self.interval,
                limit=self.limit,
                from_buffer=self.from_buffer,
                closed_bars=self.closed_bars,
            )
        )
        history_data = self.indicator.get_indicator(
            symbol=self.symbol,
            interval=self.interval,
            limit=self.limit,
            from_buffer=self.from_buffer,
            closed_bars=self.closed_bars,
        )
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
            symbol=self.symbol,
            interval=self.interval,
            limit=self.limit,
            from_buffer=self.from_buffer,
            closed_bars=self.closed_bars,
        )
        df = self.indicator.get_indicator_by_history_data(history_data)
        self.assertIsNotNone(df)


class TestIndicatorCCI(unittest.TestCase):
    def setUp(self):
        self.symbol = "BABA"
        self.interval = "1h"
        self.limit = 50
        self.from_buffer = True
        self.closed_bars = False

    def test_getIndicator(self):
        mock_history_data = getHistoryDataTest(
            symbol=self.symbol,
            interval=self.interval,
            limit=self.limit,
            from_buffer=self.from_buffer,
            closed_bars=self.closed_bars,
        )

        with patch(
            "trading_core.indicator.IndicatorBase.get_indicator"
        ) as mock_get_indicator:
            mock_get_indicator.return_value = mock_history_data

            cci_indicator = Indicator_CCI(length=4)
            indicator_df = cci_indicator.get_indicator(
                symbol=self.symbol,
                interval=self.interval,
                limit=self.limit,
                from_buffer=self.from_buffer,
                closed_bars=self.closed_bars,
            )

            self.assertTrue("CCI" in indicator_df.columns)
            # Only entry with CCI are returned
            self.assertTrue(len(indicator_df) == 47)
            # All rows have CCI values
            self.assertTrue(all(indicator_df["CCI"].notna()))

            self.assertEqual(indicator_df.tail(1).iloc[0, 5], 50.179211469542025)

    def test_getIndicatorByHistoryData(self):
        history_data = getHistoryDataTest(
            symbol=self.symbol,
            interval=self.interval,
            limit=self.limit,
            from_buffer=self.from_buffer,
            closed_bars=self.closed_bars,
        )

        cci_indicator = Indicator_CCI(length=4)
        indicator_df = cci_indicator.get_indicator_by_history_data(history_data)

        self.assertTrue("CCI" in indicator_df.columns)
        # Only entry with CCI are returned
        self.assertTrue(len(indicator_df) == 47)
        # All rows have CCI values
        self.assertTrue(all(indicator_df["CCI"].notna()))

        self.assertEqual(indicator_df.head(1).iloc[0, 5], 97.61904761904609)
        self.assertEqual(indicator_df.tail(1).iloc[0, 5], 50.179211469542025)


class StrategyConfigTests(unittest.TestCase):
    def setUp(self):
        self.model = model
        self.strategy_code = Const.TA_STRATEGY_CCI_14_TREND_100
        self.strategy_config = self.model.get_strategy(self.strategy_code)
        self.strategy = StrategyConfig(self.strategy_code)

    def test_init(self):
        with self.assertRaises(Exception):
            # Test missing strategy config
            StrategyConfig("missing_strategy_code")

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
            self.strategy.get_property("missing_property")


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
            StrategyFactory("missing_strategy_code")

    def test_get_strategy(self):
        symbol = "BTC/USD"
        interval = "1h"
        limit = 10
        closed_bar = False
        from_buffer = True
        strategy = self.factory.get_strategy_data(
            symbol, interval, limit, from_buffer, closed_bar
        )
        self.assertEqual(3, len(strategy))

    def test_get_strategy_by_history_data(self):
        symbol = "BABA"
        interval = "1h"
        limit = 50
        from_buffer = True
        closed_bars = False

        history_data = getHistoryDataTest(
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )

        strategy_data = self.factory.get_strategy_data_by_history_data(history_data)

        self.assertEqual(strategy_data.tail(1).iloc[0, 6], "")
        self.assertEqual(strategy_data.tail(8).iloc[0, 6], Const.STRONG_SELL)
        self.assertEqual(strategy_data.tail(11).iloc[0, 6], Const.BUY)


class SignalFactoryTests(unittest.TestCase):
    def setUp(self):
        self.signal_factory = SignalFactory()
        self.runtime_buffer = RuntimeBufferStore()
        self.runtime_buffer.clearSymbolsBuffer()

    def tearDown(self):
        pass

    def test_get_signal_with_buffer(self):
        symbol = "BTC/USD"
        interval = "1h"
        strategy_14 = "CCI_14_TREND_100"
        strategy_20 = "CCI_20_TREND_100"
        signals_config = []
        closed_bars = False

        # Add a signals to the buffer
        date_time = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=closed_bars
        )
        self.runtime_buffer.set_signal_to_buffer(
            Signal(date_time, symbol, interval, strategy_14, Const.BUY)
        )
        self.runtime_buffer.set_signal_to_buffer(
            Signal(date_time, symbol, interval, strategy_20, "")
        )

        # Check signal with signals_config
        signal_inst = self.signal_factory.get_signal(
            symbol, interval, strategy_14, signals_config, closed_bars
        )

        self.assertIsInstance(signal_inst, Signal)
        self.assertEqual(signal_inst.get_date_time(), date_time)
        self.assertEqual(signal_inst.get_symbol(), "BTC/USD")
        self.assertEqual(signal_inst.get_interval(), "1h")
        self.assertEqual(signal_inst.get_strategy(), "CCI_14_TREND_100")
        self.assertEqual(signal_inst.get_signal(), Const.BUY)

        # Get None because the signal is empty
        signal_inst_20 = self.signal_factory.get_signal(
            symbol, interval, strategy_20, [Const.BUY], closed_bars
        )

        self.assertIsNone(signal_inst_20)

    def test_get_signal_without_buffer(self):
        symbol = "BTC/USD"
        interval = "1h"
        strategy = "CCI_14_TREND_100"
        signals_config = [Const.DEBUG_SIGNAL]
        closed_bars = True

        # Remove any existing signals from the buffer
        self.runtime_buffer.clear_signal_buffer()

        date_time = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=closed_bars
        )

        signal_inst = self.signal_factory.get_signal(
            symbol, interval, strategy, signals_config, closed_bars
        )

        self.assertIsNotNone(signal_inst)
        self.assertEqual(signal_inst.get_date_time(), date_time)
        self.assertEqual(signal_inst.get_symbol(), "BTC/USD")
        self.assertEqual(signal_inst.get_interval(), "1h")
        self.assertEqual(signal_inst.get_strategy(), "CCI_14_TREND_100")

    def test_get_signals(self):
        symbols = ["BTC/USD", "BAL/USD"]
        intervals = [Const.TA_INTERVAL_1H, Const.TA_INTERVAL_4H]
        strategies = [
            Const.TA_STRATEGY_CCI_14_TREND_100,
            Const.TA_STRATEGY_CCI_20_TREND_100,
        ]
        signals_config = [Const.DEBUG_SIGNAL]
        closed_bars = False

        date_time_1h = model.get_handler().getEndDatetime(
            interval=Const.TA_INTERVAL_1H, closed_bars=closed_bars
        )

        date_time_4h = model.get_handler().getEndDatetime(
            interval=Const.TA_INTERVAL_4H, closed_bars=closed_bars
        )

        signals_list = self.signal_factory.get_signals(
            symbols, intervals, strategies, signals_config, closed_bars
        )

        self.assertEqual(len(signals_list), 8)

        for signal_inst in signals_list:
            if signal_inst.get_interval() == Const.TA_INTERVAL_1H:
                self.assertEqual(signal_inst.get_date_time(), date_time_1h)
            elif signal_inst.get_interval() == Const.TA_INTERVAL_4H:
                self.assertEqual(signal_inst.get_date_time(), date_time_4h)


class MessageBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.channel_id = "channel_001"
        self.message_text = "Hello, World!"
        self.message_base = MessageBase(self.channel_id, self.message_text)

    def test_get_channel_id(self):
        result = self.message_base.get_channel_id()
        self.assertEqual(result, self.channel_id)

    def test_get_message_text(self):
        result = self.message_base.get_message_text()
        self.assertEqual(result, self.message_text)

    def test_set_message_text(self):
        new_text = "New message text"
        self.message_base.set_message_text(new_text)
        result = self.message_base.get_message_text()
        self.assertEqual(result, new_text)

    def test_add_message_text(self):
        additional_text = " More text"
        self.message_base.add_message_text(additional_text)
        result = self.message_base.get_message_text()
        self.assertEqual(result, self.message_text + additional_text)


class MessageEmailTestCase(unittest.TestCase):
    def setUp(self):
        self.channel_id = "channel_001"
        self.subject = "Important Email"
        self.message_text = "Hello, World!"
        self.message_email = MessageEmail(
            self.channel_id, self.subject, self.message_text
        )

    def test_get_channel_id(self):
        result = self.message_email.get_channel_id()
        self.assertEqual(result, self.channel_id)

    def test_get_message_text(self):
        result = self.message_email.get_message_text()
        self.assertEqual(result, self.message_text)

    def test_set_message_text(self):
        new_text = "New message text"
        self.message_email.set_message_text(new_text)
        result = self.message_email.get_message_text()
        self.assertEqual(result, new_text)

    def test_add_message_text(self):
        additional_text = " More text"
        self.message_email.add_message_text(additional_text)
        result = self.message_email.get_message_text()
        self.assertEqual(result, self.message_text + additional_text)

    def test_get_subject(self):
        result = self.message_email.get_subject()
        self.assertEqual(result, self.subject)


class MessagesTestCase(unittest.TestCase):
    def setUp(self):
        self.messages = Messages()
        self.channel_id = "channel_001"
        self.message_text = "Hello, World!"
        self.message_base = MessageBase(self.channel_id, self.message_text)

    def test_check_message(self):
        result = self.messages.check_message(self.channel_id)
        self.assertFalse(result)

        result = self.messages.get_message(self.channel_id)
        self.assertIsNone(result)

        result = self.messages.get_messages()
        self.assertEqual(result, {})

        self.messages.add_message(self.message_base)
        result = self.messages.check_message(self.channel_id)
        self.assertTrue(result)

        result = self.messages.get_message(self.channel_id)
        self.assertEqual(result, self.message_base)

        additional_text = " More text"
        result = self.messages.add_message_text(self.channel_id, additional_text)
        self.assertEqual(result.get_message_text(), self.message_text + additional_text)

        new_text = "New message text"
        result = self.messages.set_message_text(self.channel_id, new_text)
        self.assertEqual(result.get_message_text(), new_text)

        self.channel_id = "channel_002"
        message_inst = self.messages.create_message(self.channel_id, self.message_text)
        self.assertIsInstance(message_inst, MessageBase)
        self.assertEqual(message_inst.get_channel_id(), self.channel_id)
        self.assertEqual(message_inst.get_message_text(), self.message_text)
        self.assertEqual(self.messages.get_message(self.channel_id), message_inst)

        result = self.messages.get_messages()
        self.assertIn(self.channel_id, result)
        self.assertEqual(result[self.channel_id], message_inst)


# class CandelBarTestCase(unittest.TestCase):

#     def test_candle_bar_init(self):
#         date_time = datetime(2022, 1, 1, 12, 0, 0)
#         open_price = 100.0
#         high_price = 110.0
#         low_price = 90.0
#         close_price = 105.0
#         volume = 1000.0

#         candle_bar = CandelBar(date_time=date_time,
#                                open=open_price,
#                                high=high_price,
#                                low=low_price,
#                                close=close_price,
#                                volume=volume)

#         self.assertEqual(candle_bar.date_time, date_time)
#         self.assertEqual(candle_bar.open, open_price)
#         self.assertEqual(candle_bar.high, high_price)
#         self.assertEqual(candle_bar.low, low_price)
#         self.assertEqual(candle_bar.close, close_price)
#         self.assertEqual(candle_bar.volume, volume)


# class CandelBarSignalTestCase(unittest.TestCase):

#     def test_candle_bar_signal_init(self):
#         date_time = datetime(2022, 1, 1, 12, 0, 0)
#         open_price = 100.0
#         high_price = 110.0
#         low_price = 90.0
#         close_price = 105.0
#         volume = 1000.0
#         signal = Const.STRONG_BUY

#         candle_bar_signal = CandelBarSignal(date_time=date_time,
#                                             open=open_price,
#                                             high=high_price,
#                                             low=low_price,
#                                             close=close_price,
#                                             volume=volume,
#                                             signal=signal)

#         self.assertEqual(candle_bar_signal.date_time, date_time)
#         self.assertEqual(candle_bar_signal.open, open_price)
#         self.assertEqual(candle_bar_signal.high, high_price)
#         self.assertEqual(candle_bar_signal.low, low_price)
#         self.assertEqual(candle_bar_signal.close, close_price)
#         self.assertEqual(candle_bar_signal.volume, volume)
#         self.assertEqual(candle_bar_signal.signal, signal)


# class OrderTestCase(unittest.TestCase):

#     def test_order_init(self):
#         order_type = Const.LONG
#         open_date_time = datetime(2022, 1, 1, 12, 0, 0)
#         open_price = 100.0
#         quantity = 10.0

#         order = Order(type=order_type,
#                       open_date_time=open_date_time,
#                       open_price=open_price,
#                       quantity=quantity)

#         self.assertIsNone(order.id)
#         self.assertEqual(order.type, order_type)
#         self.assertEqual(order.open_date_time, open_date_time)
#         self.assertEqual(order.open_price, open_price)
#         self.assertEqual(order.quantity, quantity)
#         self.assertEqual(order.status, Const.STATUS_OPEN)
#         self.assertIsNone(order.close_date_time)
#         self.assertEqual(order.close_price, 0)

#     def test_order_close(self):
#         order_type = Const.LONG
#         open_date_time = datetime(2022, 1, 1, 12, 0, 0)
#         open_price = 100.0
#         quantity = 10.0

#         order = Order(type=order_type, open_date_time=open_date_time,
#                       open_price=open_price, quantity=quantity)

#         close_date_time = datetime(2022, 1, 2, 12, 0, 0)
#         close_price = 110.0

#         order.close(close_date_time=close_date_time, close_price=close_price)

#         self.assertEqual(order.status, Const.STATUS_CLOSE)
#         self.assertEqual(order.close_date_time, close_date_time)
#         self.assertEqual(order.close_price, close_price)


# class SimulationBaseTestCase(unittest.TestCase):

#     def setUp(self):
#         options_inst = SimulateOptions(init_balance=100,
#                                        limit=200,
#                                        stop_loss_rate=10,
#                                        take_profit_rate=30,
#                                        fee_rate=2)
#         self.simulation_base = SimulationBase(options_inst=options_inst)

#     def test_simulation_base_init(self):
#         self.assertIsNone(self.simulation_base._order)
#         self.assertIsInstance(self.simulation_base._options_inst, SimulateOptions)
#         self.assertEqual(self.simulation_base.close_reason, '')
#         self.assertEqual(self.simulation_base.fee_value, self.simulation_base._options_inst.get_fee_value())
#         self.assertEqual(self.simulation_base.balance, self.simulation_base._options_inst.get_balance())
#         self.assertEqual(self.simulation_base.profit, 0)
#         self.assertEqual(self.simulation_base.percent_change, 0)
#         self.assertEqual(self.simulation_base.stop_loss_value, 0)
#         self.assertEqual(self.simulation_base.stop_loss_price, 0)
#         self.assertEqual(self.simulation_base.take_profit_value, 0)
#         self.assertEqual(self.simulation_base.take_profit_price, 0)
#         self.assertEqual(self.simulation_base.max_loss_value, 0)
#         self.assertEqual(self.simulation_base.max_profit_value, 0)
#         self.assertEqual(self.simulation_base.max_price, 0)
#         self.assertEqual(self.simulation_base.min_price, 0)
#         self.assertEqual(self.simulation_base.max_percent_change, 0)
#         self.assertEqual(self.simulation_base.min_percent_change, 0)

#     def test_simulation_base_open_simulation(self):
#         open_date_time = datetime(2022, 1, 1, 12, 0, 0)
#         open_price = 100.0

#         self.simulation_base.open_simulation(type=Const.LONG,
#                                              open_date_time=open_date_time,
#                                              open_price=open_price)

#         self.assertIsInstance(self.simulation_base._order, Order)
#         self.assertEqual(self.simulation_base._order.type, Const.LONG)
#         self.assertEqual(self.simulation_base._order.open_date_time, open_date_time)
#         self.assertEqual(self.simulation_base._order.open_price, open_price)
#         self.assertEqual(self.simulation_base._order.quantity,self.simulation_base._options_inst.get_quantity(open_price))
#         self.assertEqual(self.simulation_base.stop_loss_value,self.simulation_base._options_inst.get_stop_loss_value(open_price))
#         self.assertEqual(self.simulation_base.take_profit_value,self.simulation_base._options_inst.get_take_profit_value(open_price))
#         self.assertEqual(self.simulation_base.max_price, open_price)
#         self.assertEqual(self.simulation_base.min_price, open_price)

#     def test_simulation_base_close_simulation(self):
#         candler_bar = CandelBarSignal(date_time=datetime(2022, 1, 1, 12, 0, 0),
#                                       open=100.0,
#                                       high=110.0,
#                                       low=90.0,
#                                       close=105.0,
#                                       volume=1000.0,
#                                       signal=Const.STRONG_BUY)

#         self.simulation_base._order = Order(type=Const.LONG,
#                                             open_date_time=datetime(2022, 1, 1, 12, 0, 0),
#                                             open_price=100.0,
#                                             quantity=10.0)

#         self.simulation_base.close_simulation(candler_bar)

#         self.assertEqual(self.simulation_base._order.status,Const.STATUS_CLOSE)
#         self.assertEqual(self.simulation_base._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(self.simulation_base._order.close_price, candler_bar.close)
#         self.assertEqual(self.simulation_base.close_reason, '')


# class SimulationLongTestCase(unittest.TestCase):

#     def setUp(self):
#         options_inst = SimulateOptions()
#         self.simulation_long = SimulationLong(options_inst=options_inst)

#     def test_simulation_long_open_simulation(self):
#         open_date_time = datetime(2022, 1, 1, 12, 0, 0)
#         open_price = 100.0

#         self.simulation_long.open_simulation(
#             open_date_time=open_date_time, open_price=open_price)

#         self.assertEqual(self.simulation_long.stop_loss_price,
#                          open_price - self.simulation_long.stop_loss_value)
#         self.assertEqual(self.simulation_long.take_profit_price,
#                          open_price + self.simulation_long.take_profit_value)

#     def test_simulation_long_close_simulation_stop_loss(self):
#         candler_bar = CandelBarSignal(date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open=100.0, high=110.0, low=90.0, close=95.0, volume=1000.0, signal=Const.STRONG_BUY)

#         self.simulation_long._order = Order(type=Const.LONG, open_date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open_price=100.0, quantity=10.0)
#         self.simulation_long.stop_loss_price = 90.0

#         self.simulation_long.close_simulation(candler_bar)

#         self.assertEqual(self.simulation_long._order.status,
#                          Const.STATUS_CLOSE)
#         self.assertEqual(
#             self.simulation_long._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(self.simulation_long._order.close_price,
#                          self.simulation_long.stop_loss_price)
#         self.assertEqual(self.simulation_long.close_reason,
#                          Const.ORDER_CLOSE_REASON_STOP_LOSS)

#     def test_simulation_long_close_simulation_take_profit(self):
#         candler_bar = CandelBarSignal(date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open=100.0, high=110.0, low=90.0, close=115.0, volume=1000.0, signal=Const.STRONG_BUY)

#         self.simulation_long._order = Order(type=Const.LONG, open_date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open_price=100.0, quantity=10.0)
#         self.simulation_long.take_profit_price = 110.0

#         self.simulation_long.close_simulation(candler_bar)

#         self.assertEqual(self.simulation_long._order.status,
#                          Const.STATUS_CLOSE)
#         self.assertEqual(
#             self.simulation_long._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(self.simulation_long._order.close_price,
#                          self.simulation_long.take_profit_price)
#         self.assertEqual(self.simulation_long.close_reason,
#                          Const.ORDER_CLOSE_REASON_TAKE_PROFIT)

#     def test_simulation_long_close_simulation_signal(self):
#         candler_bar = CandelBarSignal(date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open=100.0, high=110.0, low=90.0, close=105.0, volume=1000.0, signal=Const.STRONG_BUY)

#         self.simulation_long._order = Order(type=Const.LONG, open_date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open_price=100.0, quantity=10.0)

#         self.simulation_long.close_simulation(candler_bar)

#         self.assertEqual(selfContinuing from where I left off:

#         self.assertEqual(self.simulation_long._order.status,
#                          Const.STATUS_CLOSE)
#         self.assertEqual(
#             self.simulation_long._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(
#             self.simulation_long._order.close_price, candler_bar.close)
#         self.assertEqual(self.simulation_long.close_reason,
#                          Const.ORDER_CLOSE_REASON_SIGNAL)


# class SimulationShortTestCase(unittest.TestCase):

#     def setUp(self):
#         options_inst=SimulateOptions()
#         self.simulation_short=SimulationShort(options_inst=options_inst)

#     def test_simulation_short_open_simulation(self):
#         open_date_time=datetime(2022, 1, 1, 12, 0, 0)
#         open_price=100.0

#         self.simulation_short.open_simulation(
#             open_date_time=open_date_time, open_price=open_price)

#         self.assertEqual(self.simulation_short.stop_loss_price,
#                          open_price + self.simulation_short.stop_loss_value)
#         self.assertEqual(self.simulation_short.take_profit_price,
#                          open_price - self.simulation_short.take_profit_value)

#     def test_simulation_short_close_simulation_stop_loss(self):
#         candler_bar=CandelBarSignal(date_time=datetime(2022, 1, 1, 12, 0, 0), open=100.0,
#                                     high=110.0, low=90.0, close=105.0, volume=1000.0, signal=Const.STRONG_SELL)

#         self.simulation_short._order=Order(type=Const.SHORT, open_date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open_price=100.0, quantity=10.0)
#         self.simulation_short.stop_loss_price=110.0

#         self.simulation_short.close_simulation(candler_bar)

#         self.assertEqual(self.simulation_short._order.status,
#                          Const.STATUS_CLOSE)
#         self.assertEqual(
#             self.simulation_short._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(self.simulation_short._order.close_price,
#                          self.simulation_short.stop_loss_price)
#         self.assertEqual(self.simulation_short.close_reason,
#                          Const.ORDER_CLOSE_REASON_STOP_LOSS)

#     def test_simulation_short_close_simulation_take_profit(self):
#         candler_bar=CandelBarSignal(date_time=datetime(2022, 1, 1, 12, 0, 0), open=100.0,
#                                     high=110.0, low=90.0, close=85.0, volume=1000.0, signal=Const.STRONG_SELL)

#         self.simulation_short._order=Order(type=Const.SHORT, open_date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open_price=100.0, quantity=10.0)
#         self.simulation_short.take_profit_price=90.0

#         self.simulation_short.close_simulation(candler_bar)

#         self.assertEqual(self.simulation_short._order.status,
#                          Const.STATUS_CLOSE)
#         self.assertEqual(
#             self.simulation_short._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(self.simulation_short._order.close_price,
#                          self.simulation_short.take_profit_price)
#         self.assertEqual(self.simulation_short.close_reason,
#                          Const.ORDER_CLOSE_REASON_TAKE_PROFIT)

#     def test_simulation_short_close_simulation_signal(self):
#         candler_bar=CandelBarSignal(date_time=datetime(2022, 1, 1, 12, 0, 0), open=100.0,
#                                     high=110.0, low=90.0, close=95.0, volume=1000.0, signal=Const.STRONG_SELL)

#         self.simulation_short._order=Order(type=Const.SHApologies, it seems that the last line was cut off. Here's the complete code for the `SimulationShort` unit tests:

# ```python
#         self.simulation_short._order=Order(type=Const.SHORT, open_date_time=datetime(
#             2022, 1, 1, 12, 0, 0), open_price=100.0, quantity=10.0)

#         self.simulation_short.close_simulation(candler_bar)

#         self.assertEqual(self.simulation_short._order.status,
#                          Const.STATUS_CLOSE)
#         self.assertEqual(
#             self.simulation_short._order.close_date_time, candler_bar.date_time)
#         self.assertEqual(
#             self.simulation_short._order.close_price, candler_bar.close)
#         self.assertEqual(self.simulation_short.close_reason,
#                          Const.ORDER_CLOSE_REASON_SIGNAL)


class FlaskAPITestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_get_symbols(self):
        response = self.client.get("/symbols?from_buffer=true")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertGreater(len(json_api_response), 1)

    def test_get_symbol_by_code(self):
        code = "BTC/USD"
        response = self.client.get(f"/symbols?code={code}")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertEqual(json_api_response[0]["code"], code)

    def test_get_symbols_by_name(self):
        name = "Bitcoin"
        expected_result = {
            "code": "BTC/USD",
            "name": "Bitcoin / USD",
            "descr": "Bitcoin / USD (BTC/USD)",
            "status": "TRADING",
            "tradingTime": "UTC; Mon - 21:00, 21...0, 21:05 -",
            "type": "CRYPTOCURRENCY",
        }
        response = self.client.get(f"/symbols?name={name}&from_buffer=true")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertGreater(len(json_api_response), 1)
        self.assertTrue(expected_result, json_api_response)

    def test_get_intervals(self):
        expected_intervals = [
            {
                "interval": Const.TA_INTERVAL_5M,
                "name": "5 minutes",
                "order": 10,
                "importance": Const.IMPORTANCE_LOW,
            },
            {
                "interval": Const.TA_INTERVAL_15M,
                "name": "15 minutes",
                "order": 20,
                "importance": Const.IMPORTANCE_LOW,
            },
            {
                "interval": Const.TA_INTERVAL_30M,
                "name": "30 minutes",
                "order": 30,
                "importance": Const.IMPORTANCE_MEDIUM,
            },
            {
                "interval": Const.TA_INTERVAL_1H,
                "name": "1 hour",
                "order": 40,
                "importance": Const.IMPORTANCE_MEDIUM,
            },
            {
                "interval": Const.TA_INTERVAL_4H,
                "name": "4 hours",
                "order": 50,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": Const.TA_INTERVAL_1D,
                "name": "1 day",
                "order": 60,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": Const.TA_INTERVAL_1WK,
                "name": "1 week",
                "order": 70,
                "importance": Const.IMPORTANCE_HIGH,
            },
        ]

        response = self.client.get(f"/intervals")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_intervals, json_api_response)

        expected_intervals = [
            {
                "interval": Const.TA_INTERVAL_4H,
                "name": "4 hours",
                "order": 50,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": Const.TA_INTERVAL_1D,
                "name": "1 day",
                "order": 60,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": Const.TA_INTERVAL_1WK,
                "name": "1 week",
                "order": 70,
                "importance": Const.IMPORTANCE_HIGH,
            },
        ]

        response = self.client.get(f"/intervals?importance={Const.IMPORTANCE_HIGH}")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_intervals, json_api_response)

    def test_get_indicators(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}
        ]

        response = self.client.get(f"/indicators")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_result, json_api_response)

    def test_get_strategies(self):
        expected_result = [
            {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator against Trend +/- 100",
            },
            {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_170_165,
                Const.NAME: "CCI(14): Indicator direction Trend +/- 170 | 165",
            },
            {
                Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator against Trend +/- 100",
            },
            {
                Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator direction Trend 0",
            },
        ]

        response = self.client.get(f"/strategies")
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_result, json_api_response)

    def test_get_history_data(self):
        interval = "4h"
        limit = 20

        response = self.client.get(
            f"/historyData?symbol=BTC/USD&interval={interval}&limit={limit}"
        )

        json_api_response = json.loads(response.text)["data"]
        latest_bar = json_api_response[-1]

        end_datetime = model.get_handler().getEndDatetime(interval)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            datetime.fromisoformat(latest_bar["Datetime"][:-1]), end_datetime
        )
        self.assertEqual(len(json_api_response), limit)

    def test_get_strategy_data(self):
        interval = "4h"
        limit = 20
        # /strategyData?code=CCI_20_TREND_100&symbol=BTC/USD&interval=4h&limit=20&closed_bars=true&from_buffer=true
        response = self.client.get(
            f"/strategyData?code=CCI_20_TREND_100&symbol=BTC/USD&interval={interval}&limit={limit}&closed_bars=true&from_buffer=true"
        )

        json_api_response = json.loads(response.text)["data"]
        latest_bar = json_api_response[-1]

        end_datetime = model.get_handler().getEndDatetime(
            interval=interval, closed_bars=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            datetime.fromisoformat(latest_bar["Datetime"][:-1]), end_datetime
        )
        self.assertEqual(len(json_api_response), 3)

    def test_get_signals(self):
        symbol = "BTC/USD"
        strategy = "CCI_20_TREND_100"
        interval_1h = Const.TA_INTERVAL_1H
        interval_4h = Const.TA_INTERVAL_4H
        closed_bars = True

        # /signals?symbol=BTC/USD&interval=4h&interval=1h&strategy=CCI_20_TREND_100&signal=Debug&closed_bars=true
        response = self.client.get(
            f"/signals?symbol={symbol}&interval={interval_1h}&interval={interval_4h}&strategy={strategy}&signal=Debug&closed_bars={closed_bars}"
        )

        json_api_response = json.loads(response.text)

        end_datetime_1h = model.get_handler().getEndDatetime(
            interval=interval_1h, closed_bars=closed_bars
        )
        end_datetime_4h = model.get_handler().getEndDatetime(
            interval=interval_4h, closed_bars=closed_bars
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_api_response), 2)
        self.assertEqual(
            json_api_response[0][Const.DATETIME], end_datetime_1h.isoformat()
        )
        self.assertEqual(json_api_response[0][Const.PARAM_SYMBOL], symbol)
        self.assertEqual(json_api_response[0][Const.INTERVAL], interval_1h)
        self.assertEqual(json_api_response[0][Const.STRATEGY], strategy)

        self.assertEqual(
            json_api_response[1][Const.DATETIME], end_datetime_4h.isoformat()
        )
        self.assertEqual(json_api_response[1][Const.PARAM_SYMBOL], symbol)
        self.assertEqual(json_api_response[1][Const.INTERVAL], interval_4h)
        self.assertEqual(json_api_response[1][Const.STRATEGY], strategy)

    def test_jobs_functionality(self):
        job_type = Const.JOB_TYPE_BOT
        interval = Const.TA_INTERVAL_1D

        payload = {Const.DB_JOB_TYPE: job_type, Const.DB_INTERVAL: interval}

        # Create job
        response = self.client.post(
            "/jobs", data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_api_response = json.loads(response.text)

        job_id = json_api_response[Const.JOB_ID]
        self.assertIsNotNone(job_id)

        # Get jobs
        response = self.client.get("/jobs")
        json_api_response = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(json_api_response), 1)

        # Deactivate job
        response = self.client.post(f"/jobs/{job_id}/deactivate")
        self.assertEqual(response.status_code, 200)

        # Activate job
        response = self.client.post(f"/jobs/{job_id}/activate")
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f"/jobs/{job_id}")
        self.assertEqual(response.status_code, 200)

    def test_alerts_functionality(self):
        alert_type = Const.ALERT_TYPE_BOT
        channel_id = 1658698044
        symbol = "BTC/USD"
        interval = Const.TA_INTERVAL_1D
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100]
        signals = [Const.STRONG_BUY]
        comment = "Test comments"

        payload = {
            Const.DB_ALERT_TYPE: alert_type,
            Const.DB_CHANNEL_ID: channel_id,
            Const.DB_SYMBOL: symbol,
            Const.DB_INTERVAL: interval,
            Const.DB_STRATEGIES: strategies,
            Const.DB_SIGNALS: signals,
            Const.DB_COMMENT: comment,
        }

        # Create
        response = self.client.post(
            "/alerts", data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_api_response = json.loads(response.text)

        _id = json_api_response[Const.DB_ID]
        self.assertIsNotNone(_id)

        # Get jobs
        response = self.client.get("/alerts")
        json_api_response = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(json_api_response), 1)

        # Update
        payload = {
            Const.DB_INTERVAL: interval,
            Const.DB_STRATEGIES: strategies,
            Const.DB_SIGNALS: signals,
            Const.DB_COMMENT: "Updated comment",
        }

        response = self.client.put(
            f"/alerts/{_id}", data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f"/alerts/{_id}")
        self.assertEqual(response.status_code, 200)

    def test_orders_functionality(self):
        order_type = Const.LONG
        symbol = "BTC/USD"
        interval = Const.TA_INTERVAL_1D
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100]
        price = 100
        quantity = 0.5

        payload = {
            Const.DB_ORDER_TYPE: order_type,
            Const.DB_SYMBOL: symbol,
            Const.DB_INTERVAL: interval,
            Const.DB_PRICE: price,
            Const.DB_QUANTITY: quantity,
            Const.DB_STRATEGIES: strategies,
        }

        # Create
        response = self.client.post(
            "/orders", data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        json_api_response = json.loads(response.text)

        _id = json_api_response[Const.DB_ID]
        self.assertIsNotNone(_id)

        # Get orders
        response = self.client.get("/orders")
        json_api_response = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(json_api_response), 1)

        response = self.client.delete(f"/orders/{_id}")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
