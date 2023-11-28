from datetime import datetime, timedelta
import time
import requests
from requests.models import RequestEncodingMixin
import json
import pandas as pd
import math
import os
import hmac
import hashlib
from enum import Enum

from .common import (
    SymbolStatus,
    SymbolType,
    OrderType,
    OrderSideType,
    ExchangeId,
    HistoryDataParam,
    SymbolModel,
    TraderModel,
)
from .core import logger, config, HistoryData
from .constants import Const


class ExchangeApiBase:
    def __init__(self, trader_model: TraderModel):
        self._trader_model = trader_model

    def ping_server(self, **kwargs) -> bool:
        return False

    def get_api_endpoints(self) -> str:
        return None

    def get_intervals(self) -> list:
        pass

    def get_account_info(self) -> list:
        pass

    def get_leverage_settings(self, symbol: str) -> list:
        pass

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
        pass

    def get_history_data(
        self, history_data_param: HistoryDataParam, **kwargs
    ) -> HistoryData:
        pass

    def get_end_datetime(
        self, interval: str, original_datetime: datetime, **kwargs
    ) -> datetime:
        pass

    def calculate_trading_timeframe(self, trading_time: str) -> dict:
        pass

    def is_trading_available(self, interval: str, trading_timeframes: dict) -> bool:
        pass


class DzengiComApi(ExchangeApiBase):
    """
    A class representing the Dzengi.com API for retrieving historical data from the stock exchange.
    It inherits from the ExchangeApiBase class.
    """

    HEADER_API_KEY_NAME = "X-MBX-APIKEY"

    AGG_TRADES_MAX_LIMIT = 1000
    KLINES_MAX_LIMIT = 1000
    RECV_WINDOW_MAX_LIMIT = 60000

    # Public API Endpoints
    SERVER_TIME_ENDPOINT = "time"
    EXCHANGE_INFORMATION_ENDPOINT = "exchangeInfo"

    # Market data Endpoints
    ORDER_BOOK_ENDPOINT = "depth"
    AGGREGATE_TRADE_LIST_ENDPOINT = "aggTrades"
    KLINES_DATA_ENDPOINT = "klines"
    PRICE_CHANGE_24H_ENDPOINT = "ticker/24hr"

    # Account Endpoints
    ACCOUNT_INFORMATION_ENDPOINT = "account"
    ACCOUNT_TRADE_LIST_ENDPOINT = "myTrades"

    # Order Endpoints
    ORDER_ENDPOINT = "order"
    CURRENT_OPEN_ORDERS_ENDPOINT = "openOrders"

    # Leverage Endpoints
    CLOSE_TRADING_POSITION_ENDPOINT = "closeTradingPosition"
    TRADING_POSITIONS_ENDPOINT = "tradingPositions"
    LEVERAGE_SETTINGS_ENDPOINT = "leverageSettings"
    UPDATE_TRADING_ORDERS_ENDPOINT = "updateTradingOrder"
    UPDATE_TRADING_POSITION_ENDPOINT = "updateTradingPosition"

    TA_API_INTERVAL_5M = "5m"
    TA_API_INTERVAL_15M = "15m"
    TA_API_INTERVAL_30M = "30m"
    TA_API_INTERVAL_1H = "1h"
    TA_API_INTERVAL_4H = "4h"
    TA_API_INTERVAL_1D = "1d"
    TA_API_INTERVAL_1WK = "1w"

    def ping_server(self, **kwargs) -> bool:
        response = requests.get(self._get_url(self.SERVER_TIME_ENDPOINT))

        if response.status_code == 200:
            # json_api_response = json.loads(response.text)
            return True
        else:
            logger.error(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - ping_server -> {response.text}"
            )
            return False

    def get_api_endpoints(self) -> str:
        return "https://api-adapter.backend.currency.com/api/v2/"

    def get_account_info(
        self, show_zero_balance: bool = False, recv_window: int = None
    ):
        """
        Get current account information

        :param show_zero_balance: will or will not show accounts with zero
        balances. Default value False
        :param recv_window: the value cannot be greater than 60000
        Default value 5000
        :return: dict object
        Response:
        {
            "makerCommission":0.20,
            "takerCommission":0.20,
            "buyerCommission":0.20,
            "sellerCommission":0.20,
            "canTrade":true,
            "canWithdraw":true,
            "canDeposit":true,
            "updateTime":1586935521,
            "balances":[
                {
                    "accountId":"2376104765040206",
                    "collateralCurrency":true,
                    "asset":"BYN",
                    "free":0.0,
                    "locked":0.0,
                    "default":false
                },
                {
                    "accountId":"2376109060084932",
                    "collateralCurrency":true,
                    "asset":"USD",
                    "free":515.59092523,
                    "locked":0.0,
                    "default":true
                }
            ]
        }
        """
        self._validate_recv_window(recv_window)
        result = self._get(
            self.ACCOUNT_INFORMATION_ENDPOINT,
            showZeroBalance=show_zero_balance,
            recvWindow=recv_window,
        )
        return result["balances"]

    def get_leverage_settings(
        self, symbol: str, show_zero_balance: bool = False, recv_window: int = None
    ):
        self._validate_recv_window(recv_window)
        result = self._get(
            self.LEVERAGE_SETTINGS_ENDPOINT,
            symbol=symbol,
            showZeroBalance=show_zero_balance,
            recvWindow=recv_window,
        )
        return result["values"]

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
        symbols = {}

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - getSymbols()"
            )

        response = requests.get(self._get_url(self.EXCHANGE_INFORMATION_ENDPOINT))

        if response.status_code == 200:
            json_api_response = json.loads(response.text)

            # Create an instance of Symbol and add to the list
            for row in json_api_response["symbols"]:
                if (
                    row["quoteAsset"] == "USD"
                    and row["assetType"] in ["CRYPTOCURRENCY", "EQUITY", "COMMODITY"]
                    and "REGULAR" in row["marketModes"]
                ):
                    status_converted = (
                        SymbolStatus.open
                        if row["status"] == "TRADING"
                        else SymbolStatus.close
                    )

                    if "tradingFee" in row and row["tradingFee"]:
                        trading_fee = row["tradingFee"]
                    elif "exchangeFee" in row and row["exchangeFee"]:
                        trading_fee = row["exchangeFee"]
                    else:
                        trading_fee = 0

                    symbol_data = {
                        "symbol": row["symbol"],
                        "name": row["name"],
                        "status": status_converted,
                        "type": row["marketType"],
                        "trading_time": row["tradingHours"],
                        "currency": row["quoteAsset"],
                        "quote_precision": row["quotePrecision"],
                        "trading_fee": trading_fee,
                    }

                    symbol_model = SymbolModel(**symbol_data)

                    symbols[symbol_model.symbol] = symbol_model
                else:
                    continue

            return symbols

        else:
            logger.error(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - getSymbols -> {response.text}"
            )
            raise Exception(response.text)

    def get_history_data(
        self, history_data_param: HistoryDataParam, **kwargs
    ) -> HistoryData:
        # Prepare URL parameters
        url_params = {
            Const.API_FLD_SYMBOL: history_data_param.symbol,
            Const.API_FLD_INTERVAL: history_data_param.interval,
            Const.API_FLD_LIMIT: history_data_param.limit,
        }

        # Boolean importing parameters closed_bars in order to get only closed bar for the current moment
        closed_bar = kwargs.get(Const.FLD_CLOSED_BAR, False)

        # If closed_bars indicator is True -> calculated endTime for the API
        if closed_bar:
            url_params[Const.API_FLD_END_TIME] = self.getOffseUnixTimeMsByInterval(
                history_data_param.interval
            )
            url_params[Const.API_FLD_LIMIT] = url_params[Const.API_FLD_LIMIT] + 1

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - get_history_data()"
            )

        json_api_response = self._get_api_klines(url_params)

        # Convert API response to the DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        df = self.convertResponseToDataFrame(json_api_response)

        # Create an instance of HistoryData
        obj_history_data = HistoryData(
            symbol=history_data_param.symbol,
            interval=history_data_param.interval,
            limit=history_data_param.limit,
            dataFrame=df,
        )

        return obj_history_data

    def create_position(
        self,
        symbol,
        side: OrderSideType,
        order_type: OrderType,
        quantity: float,
        account_id: str = None,
        expire_timestamp: datetime = None,
        guaranteed_stop_loss: bool = False,
        stop_loss: float = None,
        take_profit: float = None,
        leverage: int = None,
        price: float = None,
        new_order_resp_type="FULL",
        recv_window=None,
    ):
        """
        To create a market or limit order in the exchange trading mode, and
        market, limit or stop order in the leverage trading mode.
        Please note that to open an order within the ‘leverage’ trading mode
        symbolLeverage should be used and additional accountId parameter should
        be mentioned in the request.
        :param symbol: In order to mention the right symbolLeverage it should
        be checked with the ‘symbol’ parameter value from the exchangeInfo
        endpoint. In case ‘symbol’ has currencies in its name then the
        following format should be used: ‘BTC%2FUSD_LEVERAGE’. In case
        ‘symbol’ has only an asset name then for the leverage trading mode the
        following format is correct: ‘Oil%20-%20Brent’.
        :param side:
        :param order_type:
        :param quantity:
        :param account_id:
        :param expire_timestamp:
        :param guaranteed_stop_loss:
        :param stop_loss:
        :param take_profit:
        :param leverage:
        :param price: Required for LIMIT orders
        :param new_order_resp_type: newOrderRespType in the exchange trading
        mode for MARKET order RESULT or FULL can be mentioned. MARKET order
        type default to FULL. LIMIT order type can be only RESULT. For the
        leverage trading mode only RESULT is available.
        :param recv_window: The value cannot be greater than 60000.
        :return: dict object

        Response RESULT:
        {
           "clientOrderId" : "00000000-0000-0000-0000-00000002cac8",
           "status" : "FILLED",
           "cummulativeQuoteQty" : null,
           "executedQty" : "0.001",
           "type" : "MARKET",
           "transactTime" : 1577446511069,
           "origQty" : "0.001",
           "symbol" : "BTC/USD",
           "timeInForce" : "FOK",
           "side" : "BUY",
           "price" : "7173.6186",
           "orderId" : "00000000-0000-0000-0000-00000002cac8"
        }
        Response FULL:
        {
          "orderId" : "00000000-0000-0000-0000-00000002ca43",
          "price" : "7183.3881",
          "clientOrderId" : "00000000-0000-0000-0000-00000002ca43",
          "side" : "BUY",
          "cummulativeQuoteQty" : null,
          "origQty" : "0.001",
          "transactTime" : 1577445603997,
          "type" : "MARKET",
          "executedQty" : "0.001",
          "status" : "FILLED",
          "fills" : [
           {
             "price" : "7169.05",
             "qty" : "0.001",
             "commissionAsset" : "dUSD",
             "commission" : "0"
           }
          ],
          "timeInForce" : "FOK",
          "symbol" : "BTC/USD"
        }
        """
        self._validate_recv_window(recv_window)
        self._validate_new_order_resp_type(new_order_resp_type, order_type)

        if order_type == OrderType.LIMIT:
            if not price:
                raise ValueError(
                    "For LIMIT orders price is required or "
                    f"should be greater than 0. Got {price}"
                )

        expire_timestamp_epoch = self.getUnixTimeMsByDatetime(expire_timestamp)

        return self._post(
            self.ORDER_ENDPOINT,
            accountId=account_id,
            expireTimestamp=expire_timestamp_epoch,
            guaranteedStopLoss=guaranteed_stop_loss,
            leverage=leverage,
            newOrderRespType=new_order_resp_type,
            price=price,
            quantity=quantity,
            recvWindow=recv_window,
            side=side.value,
            stopLoss=stop_loss,
            symbol=symbol,
            takeProfit=take_profit,
            type=order_type.value,
        )

    def get_end_datetime(
        self, interval: str, original_datetime: datetime, **kwargs
    ) -> datetime:
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
        closed_bar = kwargs.get(Const.FLD_CLOSED_BAR, False)

        if not original_datetime:
            original_datetime = datetime.now()

        if not isinstance(original_datetime, datetime):
            raise ValueError("Input parameter must be a datetime object.")

        if interval in [
            self.TA_API_INTERVAL_5M,
            self.TA_API_INTERVAL_15M,
            self.TA_API_INTERVAL_30M,
        ]:
            current_minute = original_datetime.minute

            if interval == self.TA_API_INTERVAL_5M:
                offset_value = 5
            elif interval == self.TA_API_INTERVAL_15M:
                offset_value = 15
            elif interval == self.TA_API_INTERVAL_30M:
                offset_value = 30

            delta_minutes = current_minute % offset_value

            if closed_bar:
                delta_minutes += offset_value

            offset_date_time = original_datetime - timedelta(minutes=delta_minutes)

            offset_date_time = offset_date_time.replace(second=0, microsecond=0)

        elif interval == self.TA_API_INTERVAL_1H:
            compared_datetime = original_datetime.replace(
                minute=0, second=30, microsecond=0
            )

            if original_datetime > compared_datetime and closed_bar:
                offset_date_time = original_datetime - timedelta(hours=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0
            )

        elif interval == self.TA_API_INTERVAL_4H:
            offset_value = 4
            hours_difference = self.getTimezoneDifference()
            current_hour = original_datetime.hour - hours_difference

            delta_hours = current_hour % offset_value

            if closed_bar:
                delta_hours += offset_value

            offset_date_time = original_datetime - timedelta(hours=delta_hours)

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0
            )

        elif interval == self.TA_API_INTERVAL_1D:
            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0
            )

            if original_datetime > compared_datetime and closed_bar:
                offset_date_time = original_datetime - timedelta(days=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0
            )

        elif interval == self.TA_API_INTERVAL_1WK:
            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0
            )

            offset_value = 7

            delta_days_until_monday = original_datetime.weekday() % offset_value

            if closed_bar:
                delta_days_until_monday += offset_value

            offset_date_time = original_datetime - timedelta(
                days=delta_days_until_monday
            )

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0
            )

        # if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #     other_attributes = ", ".join(
        #         f"{key}={value}" for key, value in kwargs.items()
        #     )

        #     logger.info(
        #         f"ExchangeApiBase: {self._trader_model.exchange_id} - getEndDatetime(interval: {interval}, {other_attributes}) -> Original: {original_datetime} | Closed: {offset_date_time}"
        #     )

        return offset_date_time

    def convertResponseToDataFrame(self, api_response: list) -> pd.DataFrame:
        """
        Converts the API response into a DataFrame containing historical data.
        Args:
            api_response (list): The API response as a list.
        Returns:
            DataFrame: DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        """

        COLUMN_DATETIME_FLOAT = "DatetimeFloat"

        df = pd.DataFrame(
            api_response,
            columns=[
                COLUMN_DATETIME_FLOAT,
                Const.COLUMN_OPEN,
                Const.COLUMN_HIGH,
                Const.COLUMN_LOW,
                Const.COLUMN_CLOSE,
                Const.COLUMN_VOLUME,
            ],
        )
        df[Const.COLUMN_DATETIME] = df.apply(
            lambda x: pd.to_datetime(
                self.getDatetimeByUnixTimeMs(x[COLUMN_DATETIME_FLOAT])
            ),
            axis=1,
        )
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
        offset_datetime = self.get_end_datetime(
            interval=interval, original_datetime=local_datetime, closed_bars=True
        )
        return self.getUnixTimeMsByDatetime(offset_datetime)

    @staticmethod
    def getUnixTimeMsByDatetime(original_datetime: datetime) -> int:
        """
        Calculates the Unix timestamp in milliseconds for the datetime.
        Args:
            original_datetime (datetime): The datetime object.
        Returns:
            int: The Unix timestamp in milliseconds.
        """
        if original_datetime:
            return int(original_datetime.timestamp() * 1000)
        else:
            return None

    @staticmethod
    def getTimezoneDifference() -> int:
        """
        Calculates the difference in hours between the local timezone and UTC.
        Returns:
            int: The timezone difference in hours.
        """

        local_time = datetime.now()
        utc_time = datetime.utcnow()
        delta = local_time - utc_time

        return math.ceil(delta.total_seconds() / 3600)

    @staticmethod
    def getDatetimeByUnixTimeMs(timestamp: int) -> datetime:
        """
        Converts a Unix timestamp in milliseconds to a datetime object.
        Args:
            timestamp (int): The Unix timestamp in milliseconds.
        Returns:
            datetime: The datetime object.
        """

        return datetime.fromtimestamp(timestamp / 1000.0)

    def calculate_trading_timeframe(self, trading_time: str) -> dict:
        timeframes = {}

        # Split the Trading Time string into individual entries
        time_entries = trading_time.split("; ")

        # Loop through each time entry and check if the current time aligns
        for entry in time_entries[1:]:
            day_time_frames = []

            # Split the time entry into day and time ranges
            day, time_ranges = entry.split(" ", 1)

            # Split the time ranges into time period
            time_periods = time_ranges.split(",")

            for time_period in time_periods:
                # Split the time period into start and end times
                start_time, end_time = time_period.split("-")
                start_time = "00:00" if start_time == "" else start_time
                start_time = datetime.strptime(start_time.strip(), "%H:%M")

                end_time = end_time.strip()
                end_time = "23:59" if end_time in ["", "00:00"] else end_time
                end_time = datetime.strptime(end_time, "%H:%M")

                day_time_frames.append(
                    {Const.START_TIME: start_time, Const.API_FLD_END_TIME: end_time}
                )

            timeframes[day.lower()] = day_time_frames

        return timeframes

    def is_trading_available(self, interval: str, trading_timeframes: dict) -> bool:
        # Skip trading time check
        if interval == self.TA_API_INTERVAL_1WK:
            return True

        # Get current time in UTC
        current_datetime_utc = datetime.utcnow()
        # Get name of a day in lower case
        current_day = current_datetime_utc.strftime("%a").lower()
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
                    if (
                        time_frame[Const.START_TIME].time() <= current_time
                        and current_time <= time_frame[Const.API_FLD_END_TIME].time()
                    ):
                        return True

        return False

    def _get_api_klines(self, url_params: dict) -> dict:
        response = requests.get(
            self._get_url(self.KLINES_DATA_ENDPOINT), params=url_params
        )

        if response.status_code == 200:
            # Get data from API
            return json.loads(response.text)
        else:
            logger.error(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - __get_api_klines -> {response.text}"
            )
            raise Exception(response.text)

    def _validate_recv_window(self, recv_window):
        max_value = self.RECV_WINDOW_MAX_LIMIT
        if recv_window and recv_window > max_value:
            raise ValueError(
                "recvValue cannot be greater than {}. Got {}.".format(
                    max_value, recv_window
                )
            )

    @staticmethod
    def _validate_new_order_resp_type(new_order_resp_type: str, order_type: OrderType):
        if new_order_resp_type == "ACK":
            raise ValueError("ACK mode no more available")

        if order_type == OrderType.market:
            if new_order_resp_type not in [
                "RESULT",
                "FULL",
            ]:
                raise ValueError(
                    "new_order_resp_type for MARKET order can be only RESULT"
                    f"or FULL. Got {new_order_resp_type.value}"
                )
        elif order_type == OrderType.limit:
            if new_order_resp_type != "RESULT":
                raise ValueError(
                    "new_order_resp_type for LIMIT order can be only RESULT."
                    f" Got {new_order_resp_type.value}"
                )

    def _get_params_with_signature(self, **kwargs):
        api_secret = self._trader_model.decrypt_key(self._trader_model.api_secret)

        # api_secret = config.get_env_value("CURRENCY_COM_API_SECRET")
        # if not api_secret:
        #     raise Exception(
        #         f"ExchangeApiBase: {self._trader_model.exchange_id} - API secret is not maintained"
        #     )

        t = self.getUnixTimeMsByDatetime(datetime.now())
        kwargs["timestamp"] = t
        # pylint: disable=no-member
        body = RequestEncodingMixin._encode_params(kwargs)
        sign = hmac.new(
            bytes(api_secret, "utf-8"), bytes(body, "utf-8"), hashlib.sha256
        ).hexdigest()

        return {"signature": sign, **kwargs}

    def _get_header(self, **kwargs):
        api_key = self._trader_model.decrypt_key(self._trader_model.api_key)

        # api_key = config.get_env_value("CURRENCY_COM_API_KEY")
        # if not api_key:
        #     raise Exception(
        #         f"ExchangeApiBase: {self._trader_model.exchange_id} - API key is not maintained"
        #     )

        return {**kwargs, self.HEADER_API_KEY_NAME: api_key}

    def _get(self, path, **kwargs):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - GET /{path}"
            )

        url = self._get_url(path)

        response = requests.get(
            url,
            params=self._get_params_with_signature(**kwargs),
            headers=self._get_header(),
        )

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - GET /{path} -> {response.status_code}: {response.text}"
            )
            raise Exception(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - GET /{path} -> {response.status_code}: {response.text}"
            )

    def _post(self, path, **kwargs):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - POST /{path}"
            )

        url = self._get_url(path)

        response = requests.post(
            url,
            params=self._get_params_with_signature(**kwargs),
            headers=self._get_header(),
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - POST /{path} -> {response.status_code}: {response.text}"
            )

    def _delete(self, path, **kwargs):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - DELETE /{path}"
            )

        url = self._get_url(path)

        response = requests.delete(
            url,
            params=self._get_params_with_signature(**kwargs),
            headers=self._get_header(),
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - DELETE /{path} -> {response.status_code}: {response.text}"
            )

    def _get_url(self, path: str) -> str:
        return self.get_api_endpoints() + path


class DemoDzengiComApi(DzengiComApi):
    def get_api_endpoints(self) -> str:
        return "https://demo-api-adapter.backend.currency.com/api/v2/"
