from datetime import datetime, timedelta
import requests
import json
import pandas as pd
import os
import math

from .core import logger, Const, Symbol, HistoryData


class StockExchangeApiBase:
    def getStockExchangeName(self) -> str:
        """
        Returns the name of the stock exchange.
        """
        pass

    def getApiEndpoint(self):
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

    def getSymbols(self) -> list[Symbol]:
        """
        Retrieves a list of symbols available on the stock exchange.
        Returns:
            list[Symbol]: A list of Symbol objects representing the available symbols.
        """
        pass

    def getIntervals(self) -> list:
        """
        Returns a list of intervals available for retrieving historical data.
        Each interval is represented as a dictionary with keys: 'interval', 'name', 'order', and 'importance'.
        """

        pass

    def mapInterval(self, interval) -> str:
        return interval


class CurrencyComApi(StockExchangeApiBase):
    """
    A class representing the Currency.com API for retrieving historical data from the stock exchange.
    It inherits from the StockExchangeApiBase class.
    """

    TA_INTERVAL_5M = "5m"
    TA_INTERVAL_15M = "15m"
    TA_INTERVAL_30M = "30m"
    TA_INTERVAL_1H = "1h"
    TA_INTERVAL_4H = "4h"
    TA_INTERVAL_1D = "1d"
    TA_INTERVAL_1WK = "1w"

    def getStockExchangeName(self) -> str:
        """
        Returns the name of the stock exchange.
        """

        return 'currency.com'

    def getApiEndpoint(self):
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
            url_params[Const.END_TIME] = self.getUnixTimeMsByInterval(interval)

        logger.info(
            f'{self.getStockExchangeName()}: getHistoryData({url_params})')

        response = requests.get(
            f'{self.getApiEndpoint()}/klines', params=url_params)

        if response.status_code == 200:
            # Get data from API
            json_api_response = json.loads(response.text)
            # Convert API response to the DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
            df = self.convertResponseToDataFrame(json_api_response)
            # Create an instance of HistoryData
            obj_history_data = HistoryData(symbol, interval, limit, df)
            return obj_history_data
        else:
            logger.error(
                f'{self.getStockExchangeName()}: getHistoryData -> {response.text}')
            raise Exception(response.text)

    def getSymbols(self) -> list[Symbol]:
        """
        Retrieves a list of symbols available on the stock exchange.
        Returns:
            list[Symbol]: A list of Symbol objects representing the available symbols.
        """

        symbols = []

        logger.info(f'{self.getStockExchangeName()}: getSymbols()')

        # Get API data
        response = requests.get(f'{self.getApiEndpoint()}/exchangeInfo')

        if response.status_code == 200:
            json_api_response = json.loads(response.text)

            # Create an instance of Symbol and add to the list
            for row in json_api_response['symbols']:
                if row['quoteAssetId'] == 'USD' and row['assetType'] in ['CRYPTOCURRENCY', 'EQUITY', 'COMMODITY'] and 'REGULAR' in row['marketModes']:
                    obj_symbol = Symbol(code=row[Const.SYMBOL], name=row[Const.NAME],
                                        status=row[Const.STATUS], tradingTime=row['tradingTime'], type=row['assetType'])
                    symbols.append(obj_symbol)
                else:
                    continue

            return symbols

        else:
            logger.error(
                f'{self.getStockExchangeName()}: getSymbols -> {response.text}')
            raise Exception(response.text)

    def getIntervals(self) -> list:
        """
        Returns a list of intervals available for retrieving historical data.
        Each interval is represented as a dictionary with keys: 'interval', 'name', 'order', and 'importance'.
        """

        intervals = [{"interval": self.TA_INTERVAL_5M,  "name": "5 minutes",  "order": 10, "importance": Const.IMPORTANCE_LOW},
                     {"interval": self.TA_INTERVAL_15M, "name": "15 minutes",
                         "order": 20, "importance": Const.IMPORTANCE_LOW},
                     {"interval": self.TA_INTERVAL_30M, "name": "30 minutes",
                         "order": 30, "importance": Const.IMPORTANCE_MEDIUM},
                     {"interval": self.TA_INTERVAL_1H,  "name": "1 hour",
                         "order": 40, "importance": Const.IMPORTANCE_MEDIUM},
                     {"interval": self.TA_INTERVAL_4H,  "name": "4 hours",
                         "order": 50, "importance": Const.IMPORTANCE_HIGH},
                     {"interval": self.TA_INTERVAL_1D,  "name": "1 day",
                         "order": 60, "importance": Const.IMPORTANCE_HIGH},
                     {"interval": self.TA_INTERVAL_1WK, "name": "1 week",     "order": 70, "importance": Const.IMPORTANCE_HIGH}]

        return intervals

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

    def getOffsetDateTimeByInterval(self, interval: str, original_datetime: datetime) -> datetime:
        """
        Calculates the offset datetime based on the specified interval and original datetime.
        Args:
            interval (str): The interval for calculating the offset datetime.
            original_datetime (datetime): The original datetime.
        Returns:
            datetime: The offset datetime.
        Raises:
            ValueError: If the original_datetime parameter is not a datetime object.
        """

        if not isinstance(original_datetime, datetime):
            raise ValueError("Input parameter must be a datetime object.")

        if interval in [self.TA_INTERVAL_5M, self.TA_INTERVAL_15M, self.TA_INTERVAL_30M]:
            current_minute = original_datetime.minute

            if interval == self.TA_INTERVAL_5M:
                offset_value = 5
            elif interval == self.TA_INTERVAL_15M:
                offset_value = 15
            elif interval == self.TA_INTERVAL_30M:
                offset_value = 30

            delta_minutes = current_minute % offset_value + offset_value

            offset_date_time = original_datetime - \
                timedelta(minutes=delta_minutes)
            offset_date_time = offset_date_time.replace(
                second=0, microsecond=0)

        elif interval == self.TA_INTERVAL_1H:

            compared_datetime = original_datetime.replace(
                minute=0, second=30, microsecond=0)

            if original_datetime > compared_datetime:
                offset_date_time = original_datetime - timedelta(hours=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0)

        elif interval == self.TA_INTERVAL_4H:

            offset_value = 4
            hours_difference = self.getTimezoneDifference()
            current_hour = original_datetime.hour - hours_difference

            delta_hours = current_hour % offset_value + offset_value
            offset_date_time = original_datetime - timedelta(hours=delta_hours)

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0)

        elif interval == self.TA_INTERVAL_1D:

            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0)

            if original_datetime > compared_datetime:
                offset_date_time = original_datetime - timedelta(days=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0)

        elif interval == self.TA_INTERVAL_1WK:

            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0)

            offset_value = 7

            delta_days_until_monday = original_datetime.weekday() % 7 + offset_value
            offset_date_time = original_datetime - \
                timedelta(days=delta_days_until_monday)

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0)

        logger.info(
            f'Closed Bar time - {offset_date_time} for Current Time - {original_datetime}, interval - {interval}')

        return offset_date_time

    def getUnixTimeMsByInterval(self, interval: str) -> int:
        """
        Calculates the Unix timestamp in milliseconds for the offset datetime based on the specified interval.
        Args:
            interval (str): The interval for calculating the Unix timestamp.
        Returns:
            int: The Unix timestamp in milliseconds.
        """

        local_datetime = datetime.now()
        offset_datetime = self.getOffsetDateTimeByInterval(
            interval=interval, original_datetime=local_datetime)
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


class HandlerBase:
    def getHistoryData(self, symbol, interval, limit, closedBar: bool = False) -> HistoryData:
        pass

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> list:
        pass

    def getSymbolsDictionary(self, isBuffer: bool = True) -> dict:

        dictSymbols = {}
        listSymbols = []

        logger.info(
            f'getSymbolsDictionary(isBuffer={isBuffer})')

        file_path = f'{os.getcwd()}/static/symbolsDictionary.json'

        if isBuffer and os.path.exists(file_path):
            with open(file_path, 'r') as reader:
                dictSymbols = json.load(reader)

        if not dictSymbols:
            listSymbols = self.getSymbols(isBuffer=isBuffer)

            for symbol in listSymbols:
                dictSymbols[symbol.code] = symbol.__dict__

            with open(file_path, 'w') as writer:
                writer.write(json.dumps(dictSymbols))

        return dictSymbols

    def getIntervalsDetails(self) -> list:
        return []

    def _mapInterval(self, interval) -> str:
        return interval


class HandlerCurrencyCom(HandlerBase):
    def getHistoryData(self, symbol, interval, limit, closedBar: bool = False) -> HistoryData:

        logger.info(
            f'getHistoryData(symbol={symbol}, interval={interval}, limit={limit})')

        response = self.getKlines(
            symbol, self._mapInterval(interval), limit, closedBar)

        df = pd.DataFrame(response, columns=[
                          'DatetimeFloat', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Datetime'] = df.apply(lambda x: pd.to_datetime(
            datetime.fromtimestamp(x['DatetimeFloat'] / 1000.0)), axis=1)
        df.set_index('Datetime', inplace=True)
        df.drop(["DatetimeFloat"], axis=1, inplace=True)
        df = df.astype(float)

        return HistoryData(symbol, interval, limit, df)

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> list:

        symbols = []
        tempSymbols = []

        logger.info(
            f'getSymbols(code={code}, name={name}, status={status}, type={type}, isBuffer={isBuffer})')

        file_path = f'{os.getcwd()}/static/symbols.json'

        if isBuffer and os.path.exists(file_path):
            with open(file_path, 'r') as reader:
                tempSymbols = json.load(reader)

        if not tempSymbols:

            response = requests.get(
                "https://api-adapter.backend.currency.com/api/v2/exchangeInfo")

            if response.status_code == 200:
                jsonResponse = json.loads(response.text)

                for obj in jsonResponse['symbols']:
                    if obj['quoteAssetId'] == 'USD' and obj['assetType'] in ['CRYPTOCURRENCY', 'EQUITY', 'COMMODITY'] and 'REGULAR' in obj['marketModes']:
                        tempSymbols.append({'code': obj['symbol'],
                                            'name': obj['name'],
                                            'status': obj['status'],
                                            'tradingTime': obj['tradingHours'],
                                            'type': obj['assetType']})
                    else:
                        continue

                with open(file_path, 'w') as writer:
                    writer.write(json.dumps(
                        sorted(tempSymbols, key=lambda i: i['code'])))

        for row in tempSymbols:
            if code and row['code'] != code:
                continue
            elif name and name.lower() not in row['name'].lower():
                continue
            elif status and row['status'] != status:
                continue
            elif type and row['assetType'] != type:
                continue
            else:
                symbols.append(Symbol(
                    code=row['code'], name=row['name'], status=row['status'], tradingTime=row['tradingTime'], type=row['type']))

        return symbols

    def getKlines(self, symbol, interval, limit, closedBar: bool):
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        if closedBar:
            params["endTime"] = self.getCompletedUnixTimeMs(interval)

        response = requests.get(
            "https://api-adapter.backend.currency.com/api/v2/klines", params=params)

        if response.status_code == 200:
            # file_path = f'{os.getcwd()}/static/tests/{symbol}_{interval}.json'
            # with open(file_path, 'w') as writer:
            #     writer.write(response.text)

            return json.loads(response.text)
        else:
            raise Exception(response.text)

    def getOffsetDateTimeByInterval(self, interval, current_datetime: datetime):

        if not isinstance(current_datetime, datetime):
            raise ValueError(
                "Input parameter must be a datetime.datetime object.")

        if interval in ['5m', '15m', '30m']:
            current_minute = current_datetime.minute

            if interval == '5m':
                offset_value = 5
            elif interval == '15m':
                offset_value = 15
            elif interval == '30m':
                offset_value = 30

            delta_minutes = current_minute % offset_value + offset_value

            offset_date_time = current_datetime - \
                timedelta(minutes=delta_minutes)
            offset_date_time = offset_date_time.replace(
                second=0, microsecond=0)

        elif interval == '1h':

            compared_datetime = current_datetime.replace(
                minute=0, second=30, microsecond=0)

            if current_datetime > compared_datetime:
                offset_date_time = current_datetime - timedelta(hours=1)
            else:
                offset_date_time = current_datetime

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0)

        elif interval == '4h':

            offset_value = 4
            hours_difference = self.getTimezoneDifference()
            current_hour = current_datetime.hour - hours_difference

            delta_hours = current_hour % offset_value + offset_value
            offset_date_time = current_datetime - timedelta(hours=delta_hours)

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0)

        elif interval == '1d':

            compared_datetime = current_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0)

            if current_datetime > compared_datetime:
                offset_date_time = current_datetime - timedelta(days=1)
            else:
                offset_date_time = current_datetime

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0)

        elif interval == '1w':

            compared_datetime = current_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0)

            offset_value = 7

            delta_days_until_monday = current_datetime.weekday() % 7 + offset_value
            offset_date_time = current_datetime - \
                timedelta(days=delta_days_until_monday)

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0)

        logger.info(
            f'Closed Bar time - {offset_date_time} for Current Time - {current_datetime}, interval - {interval}')

        return offset_date_time

    def getCompletedUnixTimeMs(self, interval):
        offset_date_time = self.getOffsetDateTimeByInterval(
            interval, datetime.now())
        return int(offset_date_time.timestamp() * 1000)

    def getTimezoneDifference(self):
        local_time = datetime.now()
        utc_time = datetime.utcnow()
        delta = local_time - utc_time

        return math.ceil(delta.total_seconds() / 3600)
