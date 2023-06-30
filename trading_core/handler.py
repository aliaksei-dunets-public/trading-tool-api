from datetime import datetime, timedelta
import requests
import json
import pandas as pd
import math

from .constants import Const
from .core import logger, config, Symbol, HistoryData, RuntimeBufferStore


class StockExchangeHandler():
    def __init__(self):
        self.__buffer_inst = RuntimeBufferStore()
        self.__api_inst = None

        stock_exchange_id = config.get_stock_exchange_id()

        if not stock_exchange_id:
            raise Exception(
                f'Stock Exchange is not configured')

        if stock_exchange_id == Const.STOCK_EXCH_CURRENCY_COM:
            self.__api_inst = CurrencyComApi()
        else:
            raise Exception(
                f'Stock Exchange: {stock_exchange_id} implementation is missed')

    def getStockExchangeName(self) -> str:
        return self.__api_inst.getStockExchangeName()

    def getHistoryData(self, symbol: str, interval: str, limit: int, from_buffer: bool = True, closed_bars: bool = False, **kwargs) -> HistoryData:
        history_data_inst = None

        # Get endDatetime for History Data
        endDatetime = self.getEndDatetime(
            interval=interval, closed_bars=closed_bars)

        # If it reruires to read from the buffer and buffer data is valid -> get hidtory data from the buffer
        if from_buffer and self.__buffer_inst.validateHistoryDataInBuffer(symbol=symbol, interval=interval, limit=limit, endDatetime=endDatetime):

            logger.info(
                f'BUFFER: getHistoryData(symbol={symbol}, interval={interval}, limit={limit}, closed_bars={closed_bars}, endDatetime={endDatetime})')

            # Get history data from the buffer for the parameters
            history_data_inst = self.__buffer_inst.getHistoryDataFromBuffer(
                symbol=symbol, interval=interval, limit=limit, endDatetime=endDatetime)

        # If history data from the buffer doesn't exist
        if not history_data_inst:
            # Send a request to an API to get history data
            history_data_inst = self.__api_inst.getHistoryData(
                symbol=symbol, interval=interval, limit=limit, closed_bars=closed_bars, **kwargs)
            # Set fetched history data to the buffer
            self.__buffer_inst.setHistoryDataToBuffer(history_data_inst)

        return history_data_inst

    def getSymbols(self, from_buffer: bool) -> dict[Symbol]:

        symbols = {}

        # If it reruires to read data from the buffer and buffer data is existing -> get symbols from the buffer
        if from_buffer and self.__buffer_inst.checkSymbolsInBuffer():

            logger.info(
                f'BUFFER: getSymbols()')

            #  Get symbols from the buffer
            symbols = self.__buffer_inst.getSymbolsFromBuffer()
        else:
            # Send a request to an API to get symbols
            symbols = self.__api_inst.getSymbols()
            # Set fetched symbols to the buffer
            self.__buffer_inst.setSymbolsToBuffer(symbols)

        return symbols

    def get_intervals(self) -> list:
        return self.__api_inst.get_intervals()

    def getEndDatetime(self, interval: str, **kwargs) -> datetime:
        original_datetime = datetime.now()
        return self.__api_inst.getEndDatetime(interval=interval, original_datetime=original_datetime, **kwargs)

    def is_trading_open(self, interval: str, trading_time: str) -> bool:
        if self.__buffer_inst.checkTimeframeInBuffer(trading_time):
            timeframes = self.__buffer_inst.getTimeFrameFromBuffer(
                trading_time)
        else:
            timeframes = self.__api_inst.get_trading_timeframes(trading_time)
            self.__buffer_inst.setTimeFrameToBuffer(trading_time, timeframes)

        return self.__api_inst.is_trading_open(interval=interval, trading_timeframes=timeframes)


class StockExchangeApiBase:
    def getStockExchangeName(self) -> str:
        """
        Returns the name of the stock exchange.
        """
        pass

    def getApiEndpoint(self) -> str:
        """
        Returns the API endpoint.
        """
        pass

    def getHistoryData(self, symbol: str, interval: str, limit: int, **kwargs) -> HistoryData:
        """
        Retrieves historical data for a given symbol and interval from the stock exchange API.
        Args:
            symbol (str): The symbol of the asset to retrieve historical data for.
            interval (str): The interval of the historical data (e.g., "5m", "1h", etc.).
            limit (int): The number of data points to retrieve.
            **kwargs: Additional keyword arguments.
        Returns:
            HistoryData: An instance of the HistoryData class containing the retrieved historical data.
        Raises:
            Exception: If there is an error in retrieving the historical data.
        """
        pass

    def getSymbols(self) -> dict[Symbol]:
        """
        Retrieves a list of symbols available on the stock exchange.
        Returns:
            dict[Symbol]: A dictionary of Symbol objects representing the available symbols. The format is {"<symbol_code>": <Symbol obhject>}
        """
        pass

    def get_intervals(self) -> list:
        """
        Returns a list of intervals available for retrieving historical data.
        Each interval is represented as a dictionary with keys: 'interval', 'name', 'order', and 'importance'.
        """
        pass

    def mapInterval(self, interval: str) -> str:
        """
        Map Trading Tool interval to API interval
        Args:
            interval (str): The Trading Tool interval.
        Returns:
            api_interval: The API interval
        """
        return interval

    def getEndDatetime(self, interval: str, original_datetime: datetime, **kwargs) -> datetime:
        """
        Calculates the datetime based on the specified interval, original datetime and additional parameters.
        Args:
            interval (str): The interval for calculating the end datetime.
            original_datetime (datetime): The original datetime.
             **kwargs: Additional keyword arguments.
        Returns:
            datetime: The end datetime.
        Raises:
            ValueError: If the original_datetime parameter is not a datetime object.
        """
        pass

    def get_trading_timeframes(self, trading_time: str) -> dict:
        pass

    def is_trading_open(self, interval: str, trading_timeframes: dict) -> bool:
        pass


class CurrencyComApi(StockExchangeApiBase):
    """
    A class representing the Currency.com API for retrieving historical data from the stock exchange.
    It inherits from the StockExchangeApiBase class.
    """

    TA_API_INTERVAL_5M = "5m"
    TA_API_INTERVAL_15M = "15m"
    TA_API_INTERVAL_30M = "30m"
    TA_API_INTERVAL_1H = "1h"
    TA_API_INTERVAL_4H = "4h"
    TA_API_INTERVAL_1D = "1d"
    TA_API_INTERVAL_1WK = "1w"

    def getStockExchangeName(self) -> str:
        """
        Returns the name of the stock exchange.
        """

        return Const.STOCK_EXCH_CURRENCY_COM

    def getApiEndpoint(self) -> str:
        """
        Returns the API endpoint.
        """

        return 'https://api-adapter.backend.currency.com/api/v2'

    def getHistoryData(self, symbol: str, interval: str, limit: int, **kwargs) -> HistoryData:
        """
        Retrieves historical data for a given symbol and interval from the stock exchange API.
        Args:
            symbol (str): The symbol of the asset to retrieve historical data for.
            interval (str): The interval of the historical data (e.g., "5m", "1h", etc.).
            limit (int): The number of data points to retrieve.
            closed_bars (bool): Indicator for generation of endTime for API
            **kwargs: Additional keyword arguments.
        Returns:
            HistoryData: An instance of the HistoryData class containing the retrieved historical data.
        Raises:
            Exception: If there is an error in retrieving the historical data.
        """

        # Boolean importing parameters closed_bars in order to get only closed bar for the current moment
        if Const.CLOSED_BARS in kwargs:
            closed_bars = kwargs[Const.CLOSED_BARS]
        else:
            closed_bars = False

        interval_api = self.mapInterval(interval)

        # Prepare URL parameters
        url_params = {"symbol": symbol,
                      "interval": interval_api,
                      "limit": limit}

        # If closed_bars indicator is True -> calculated endTime for the API
        if closed_bars:
            url_params[Const.END_TIME] = self.getOffseUnixTimeMsByInterval(
                interval_api)
            url_params[Const.LIMIT] = url_params[Const.LIMIT] + 1

        logger.info(
            f'{self.getStockExchangeName()}: getHistoryData({url_params})')

        json_api_response = self.get_api_klines(url_params)

        # Convert API response to the DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        df = self.convertResponseToDataFrame(json_api_response)

        # Create an instance of HistoryData
        obj_history_data = HistoryData(
            symbol=symbol, interval=interval, limit=limit, dataFrame=df)

        return obj_history_data

    def get_api_klines(self, url_params: dict) -> dict:
        response = requests.get(
            f'{self.getApiEndpoint()}/klines', params=url_params)

        if response.status_code == 200:
            # Get data from API
            return json.loads(response.text)

        else:
            logger.error(
                f'{self.getStockExchangeName()}: getHistoryData -> {response.text}')
            raise Exception(response.text)

    def getSymbols(self) -> dict[Symbol]:
        """
        Retrieves a list of symbols available on the stock exchange.
        Returns:
            dict[Symbol]: A dictionary of Symbol objects representing the available symbols. The format is {"<symbol_code>": <Symbol obhject>}
        """

        symbols = {}

        logger.info(f'{self.getStockExchangeName()}: getSymbols()')

        # Get API data
        response = requests.get(f'{self.getApiEndpoint()}/exchangeInfo')

        if response.status_code == 200:
            json_api_response = json.loads(response.text)

            # Create an instance of Symbol and add to the list
            for row in json_api_response['symbols']:
                if row['quoteAssetId'] == 'USD' and row['assetType'] in ['CRYPTOCURRENCY', 'EQUITY', 'COMMODITY'] and 'REGULAR' in row['marketModes']:
                    symbol_inst = Symbol(code=row[Const.SYMBOL], name=row[Const.NAME],
                                         status=row[Const.STATUS], tradingTime=row['tradingHours'], type=row['assetType'])
                    symbols[symbol_inst.code] = symbol_inst
                else:
                    continue

            return symbols

        else:
            logger.error(
                f'{self.getStockExchangeName()}: getSymbols -> {response.text}')
            raise Exception(response.text)

    def get_intervals(self) -> list:
        """
        Returns a list of intervals available for retrieving historical data.
        Each interval is represented as a dictionary with keys: 'interval', 'name', 'order', and 'importance'.
        """

        intervals = [{"interval": self.TA_API_INTERVAL_5M,  "name": "5 minutes",  "order": 10, "importance": Const.IMPORTANCE_LOW},
                     {"interval": self.TA_API_INTERVAL_15M, "name": "15 minutes",
                         "order": 20, "importance": Const.IMPORTANCE_LOW},
                     {"interval": self.TA_API_INTERVAL_30M, "name": "30 minutes",
                         "order": 30, "importance": Const.IMPORTANCE_MEDIUM},
                     {"interval": self.TA_API_INTERVAL_1H,  "name": "1 hour",
                         "order": 40, "importance": Const.IMPORTANCE_MEDIUM},
                     {"interval": self.TA_API_INTERVAL_4H,  "name": "4 hours",
                         "order": 50, "importance": Const.IMPORTANCE_HIGH},
                     {"interval": self.TA_API_INTERVAL_1D,  "name": "1 day",
                         "order": 60, "importance": Const.IMPORTANCE_HIGH},
                     {"interval": self.TA_API_INTERVAL_1WK, "name": "1 week",     "order": 70, "importance": Const.IMPORTANCE_HIGH}]

        return intervals

    def getEndDatetime(self, interval: str, original_datetime: datetime, **kwargs) -> datetime:
        """
        Calculates the datetime based on the specified interval, original datetime and additional parameters.
        Args:
            interval (str): The interval for calculating the end datetime.
            original_datetime (datetime): The original datetime.
            closed_bars (bool): Indicator for generation of endTime with offset to get the only already closed bars
        Returns:
            datetime: The end datetime.
        Raises:
            ValueError: If the original_datetime parameter is not a datetime object.
        """

        # Boolean importing parameters closed_bars in order to get only closed bar for the current moment
        if Const.CLOSED_BARS in kwargs:
            closed_bars = kwargs[Const.CLOSED_BARS]
        else:
            closed_bars = False

        if not original_datetime:
            original_datetime = datetime.now()

        if not isinstance(original_datetime, datetime):
            raise ValueError("Input parameter must be a datetime object.")

        if interval in [self.TA_API_INTERVAL_5M, self.TA_API_INTERVAL_15M, self.TA_API_INTERVAL_30M]:
            current_minute = original_datetime.minute

            if interval == self.TA_API_INTERVAL_5M:
                offset_value = 5
            elif interval == self.TA_API_INTERVAL_15M:
                offset_value = 15
            elif interval == self.TA_API_INTERVAL_30M:
                offset_value = 30

            delta_minutes = current_minute % offset_value

            if closed_bars:
                delta_minutes += offset_value

            offset_date_time = original_datetime - \
                timedelta(minutes=delta_minutes)

            offset_date_time = offset_date_time.replace(
                second=0, microsecond=0)

        elif interval == self.TA_API_INTERVAL_1H:

            compared_datetime = original_datetime.replace(
                minute=0, second=30, microsecond=0)

            if original_datetime > compared_datetime and closed_bars:
                offset_date_time = original_datetime - timedelta(hours=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0)

        elif interval == self.TA_API_INTERVAL_4H:

            offset_value = 4
            hours_difference = self.getTimezoneDifference()
            current_hour = original_datetime.hour - hours_difference

            delta_hours = current_hour % offset_value

            if closed_bars:
                delta_hours += offset_value

            offset_date_time = original_datetime - \
                timedelta(hours=delta_hours)

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0)

        elif interval == self.TA_API_INTERVAL_1D:

            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0)

            if original_datetime > compared_datetime and closed_bars:
                offset_date_time = original_datetime - timedelta(days=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0)

        elif interval == self.TA_API_INTERVAL_1WK:

            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0)

            offset_value = 7

            delta_days_until_monday = original_datetime.weekday() % offset_value

            if closed_bars:
                delta_days_until_monday += offset_value

            offset_date_time = original_datetime - \
                timedelta(days=delta_days_until_monday)

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0)

        other_attributes = ", ".join(
            f'{key}={value}' for key, value in kwargs.items())

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f'getEndDatetime(interval:{interval}, {other_attributes}) -> Original: {original_datetime} | Closed: {offset_date_time}')

        return offset_date_time

    def convertResponseToDataFrame(self, api_response: list) -> pd.DataFrame:
        """
        Converts the API response into a DataFrame containing historical data.
        Args:
            api_response (list): The API response as a list.
        Returns:
            DataFrame: DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        """

        COLUMN_DATETIME_FLOAT = 'DatetimeFloat'

        df = pd.DataFrame(api_response, columns=[COLUMN_DATETIME_FLOAT, Const.COLUMN_OPEN,
                          Const.COLUMN_HIGH, Const.COLUMN_LOW, Const.COLUMN_CLOSE, Const.COLUMN_VOLUME])
        df[Const.COLUMN_DATETIME] = df.apply(lambda x: pd.to_datetime(
            self.getDatetimeByUnixTimeMs(x[COLUMN_DATETIME_FLOAT])), axis=1)
        df.set_index(Const.COLUMN_DATETIME, inplace=True)
        df.drop([COLUMN_DATETIME_FLOAT], axis=1, inplace=True)
        df = df.astype(float)

        return df

    def getOffseUnixTimeMsByInterval(self, interval: str) -> int:
        """
        Calculates the Unix timestamp in milliseconds for the offset datetime based on the specified interval.
        Args:
            interval (str): The interval for calculating the Unix timestamp.
        Returns:
            int: The Unix timestamp in milliseconds.
        """

        local_datetime = datetime.now()
        offset_datetime = self.getEndDatetime(
            interval=interval, original_datetime=local_datetime, closed_bars=True)
        return self.getUnixTimeMsByDatetime(offset_datetime)

    def getUnixTimeMsByDatetime(self, original_datetime: datetime) -> int:
        """
        Calculates the Unix timestamp in milliseconds for the datetime.
        Args:
            original_datetime (datetime): The datetime object.
        Returns:
            int: The Unix timestamp in milliseconds.
        """

        return int(original_datetime.timestamp() * 1000)

    def getTimezoneDifference(self) -> int:
        """
        Calculates the difference in hours between the local timezone and UTC.
        Returns:
            int: The timezone difference in hours.
        """

        local_time = datetime.now()
        utc_time = datetime.utcnow()
        delta = local_time - utc_time

        return math.ceil(delta.total_seconds() / 3600)

    def getDatetimeByUnixTimeMs(self, timestamp: int) -> datetime:
        """
        Converts a Unix timestamp in milliseconds to a datetime object.
        Args:
            timestamp (int): The Unix timestamp in milliseconds.
        Returns:
            datetime: The datetime object.
        """

        return datetime.fromtimestamp(timestamp / 1000.0)

    def get_trading_timeframes(self, trading_time: str) -> dict:
        timeframes = {}

        # Split the Trading Time string into individual entries
        time_entries = trading_time.split('; ')

        # Loop through each time entry and check if the current time aligns
        for entry in time_entries[1:]:

            day_time_frames = []

            # Split the time entry into day and time ranges
            day, time_ranges = entry.split(' ', 1)

            # Split the time ranges into time period
            time_periods = time_ranges.split(',')

            for time_period in time_periods:
                # Split the time period into start and end times
                start_time, end_time = time_period.split('-')
                start_time = '00:00' if start_time == '' else start_time
                start_time = datetime.strptime(start_time.strip(), '%H:%M')

                end_time = end_time.strip()
                end_time = '23:59' if end_time in ['', '00:00'] else end_time
                end_time = datetime.strptime(end_time, '%H:%M')

                day_time_frames.append({Const.START_TIME: start_time,
                                        Const.END_TIME: end_time})

            timeframes[day.lower()] = day_time_frames

        return timeframes

    def is_trading_open(self, interval: str, trading_timeframes: dict) -> bool:
        # Skip trading time check
        if interval == self.TA_API_INTERVAL_1WK:
            return True

        # Get current time in UTC
        current_datetime_utc = datetime.utcnow()
        # Get name of a day in lower case
        current_day = current_datetime_utc.strftime('%a').lower()
        current_time = current_datetime_utc.time()

        # Check if today matches the day in the timeframes
        if current_day in trading_timeframes:
            # Check only day for 1 day interval and skip trading time check
            if interval == self.TA_API_INTERVAL_1D:
                return True
            else:
                # Run trading time check- for rest of the intervals
                time_frames = trading_timeframes[current_day]
                for time_frame in time_frames:
                    if time_frame[Const.START_TIME].time() <= current_time and current_time <= time_frame[Const.END_TIME].time():
                        return True

        return False
