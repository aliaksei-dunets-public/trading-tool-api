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

        self.assertEqual(history_data.getDataFrame(
        ).index[limit-2], history_data_closed_bar.getDataFrame().index[limit-1])

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
        '''
        mock_get.return_value = mock_response

        symbols = self.api.getSymbols()

        self.assertEqual(len(symbols), 2)

        expected_symbols = {"BTC":
                            Symbol(code="BTC", name="Bitcoin",
                                   status="Open", tradingTime="UTC; Mon 13:30 - 20:00; Tue 13:30 - 20:00; Wed 13:30 - 20:00; Thu 13:30 - 20:00; Fri 13:30 - 20:00", type="CRYPTOCURRENCY"),
                            "AAPL":
                            Symbol(code="AAPL", name="Apple Inc.",
                                   status="Close", tradingTime="UTC; Mon 08:10 - 00:00; Tue 08:10 - 00:00; Wed 08:10 - 00:00; Thu 08:10 - 00:00; Fri 08:10 - 21:00", type="EQUITY")
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
