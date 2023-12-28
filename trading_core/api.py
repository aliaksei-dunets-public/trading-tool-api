from datetime import datetime, timedelta
import requests
from requests.models import RequestEncodingMixin
import json
import pandas as pd
import math
import hmac
import hashlib
from pybit.unified_trading import HTTP

from trading_core.common import TraderModel

from .common import (
    SymbolStatus,
    SymbolType,
    OrderStatus,
    OrderType,
    OrderReason,
    OrderSideType,
    IntervalType,
    IntervalModel,
    HistoryDataParamModel,
    SymbolModel,
    HistoryDataModel,
    TraderModel,
    OrderModel,
    OrderCloseModel,
    LeverageModel,
)
from .core import logger, config
from .constants import Const


class ExchangeApiBase:
    def __init__(self, trader_model: TraderModel):
        self._trader_model = trader_model

    def ping_server(self, **kwargs) -> bool:
        return False

    def get_api_endpoints(self) -> str:
        return None

    def get_intervals(self) -> list[IntervalModel]:
        pass

    def get_accounts(self) -> list:
        pass

    def get_leverage_settings(self, symbol: str) -> list:
        pass

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
        pass

    def get_history_data(
        self, history_data_param: HistoryDataParamModel, **kwargs
    ) -> HistoryDataModel:
        pass

    def get_open_leverages(
        self, symbol: str = None, order_id: str = None
    ) -> list[LeverageModel]:
        pass

    def get_close_leverages(
        self, position_id: str, symbol: str = None, limit: int = 1, recv_window=None
    ):
        pass

    def get_position(self, symbol: str, order_id: str) -> LeverageModel:
        pass

    def create_order(self, position_mdl: OrderModel) -> OrderModel:
        pass

    def create_leverage(self, position_mdl: LeverageModel) -> LeverageModel:
        pass

    def close_order(self, position_id: str) -> OrderModel:
        pass

    def close_leverage(self, symbol: str, position_id: str) -> LeverageModel:
        pass

    def get_end_datetime(
        self, interval: str, original_datetime: datetime, **kwargs
    ) -> datetime:
        """
        Calculates the datetime based on the specified interval, original datetime and additional parameters.
        """

        # Boolean importing parameters closed_bars in order to get only closed bar for the current moment
        closed_bars = kwargs.get(Const.FLD_CLOSED_BARS, False)

        if not original_datetime:
            original_datetime = datetime.now()

        if not isinstance(original_datetime, datetime):
            raise ValueError("Input parameter must be a datetime object.")

        if interval in [
            IntervalType.MIN_1,
            IntervalType.MIN_3,
            IntervalType.MIN_5,
            IntervalType.MIN_15,
            IntervalType.MIN_30,
        ]:
            current_minute = original_datetime.minute

            if interval == IntervalType.MIN_1:
                offset_value = 1
            if interval == IntervalType.MIN_3:
                offset_value = 3
            if interval == IntervalType.MIN_5:
                offset_value = 5
            elif interval == IntervalType.MIN_15:
                offset_value = 15
            elif interval == IntervalType.MIN_30:
                offset_value = 30

            delta_minutes = current_minute % offset_value

            if closed_bars:
                delta_minutes += offset_value

            offset_date_time = original_datetime - timedelta(minutes=delta_minutes)

            offset_date_time = offset_date_time.replace(second=0, microsecond=0)

        elif interval == IntervalType.HOUR_1:
            compared_datetime = original_datetime.replace(
                minute=0, second=30, microsecond=0
            )

            if original_datetime > compared_datetime and closed_bars:
                offset_date_time = original_datetime - timedelta(hours=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0
            )

        elif interval == IntervalType.HOUR_2:
            compared_datetime = original_datetime.replace(
                minute=0, second=30, microsecond=0
            )

            if original_datetime > compared_datetime and closed_bars:
                offset_date_time = original_datetime - timedelta(hours=2)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0
            )

        elif interval == IntervalType.HOUR_4:
            offset_value = 4
            hours_difference = self.getTimezoneDifference()
            current_hour = original_datetime.hour - hours_difference

            delta_hours = current_hour % offset_value

            if closed_bars:
                delta_hours += offset_value

            offset_date_time = original_datetime - timedelta(hours=delta_hours)

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0
            )

        elif interval == IntervalType.HOUR_12:
            offset_value = 12
            hours_difference = self.getTimezoneDifference()
            current_hour = original_datetime.hour - hours_difference

            delta_hours = current_hour % offset_value

            if closed_bars:
                delta_hours += offset_value

            offset_date_time = original_datetime - timedelta(hours=delta_hours)

            offset_date_time = offset_date_time.replace(
                minute=0, second=0, microsecond=0
            )

        elif interval == IntervalType.DAY_1:
            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0
            )

            if original_datetime > compared_datetime and closed_bars:
                offset_date_time = original_datetime - timedelta(days=1)
            else:
                offset_date_time = original_datetime

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0
            )

        elif interval == IntervalType.WEEK_1:
            compared_datetime = original_datetime.replace(
                hour=0, minute=0, second=30, microsecond=0
            )

            offset_value = 7

            delta_days_until_monday = original_datetime.weekday() % offset_value

            if closed_bars:
                delta_days_until_monday += offset_value

            offset_date_time = original_datetime - timedelta(
                days=delta_days_until_monday
            )

            offset_date_time = offset_date_time.replace(
                hour=self.getTimezoneDifference(), minute=0, second=0, microsecond=0
            )

        else:
            raise Exception(
                f"{self.__class__.__name__}: {self._trader_model.exchange_id} - In the get_end_datetime Interval: {interval} is not determined"
            )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            other_attributes = ", ".join(
                f"{key}={value}" for key, value in kwargs.items()
            )

            logger.info(
                f"{self.__class__.__name__}: {self._trader_model.exchange_id} - get_end_datetime(interval: {interval}, {other_attributes}) -> Original: {original_datetime} | Closed: {offset_date_time}"
            )

        return offset_date_time

    def calculate_trading_timeframe(self, trading_time: str) -> dict:
        pass

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
    def getDatetimeByUnixTimeMs(timestamp: int) -> datetime:
        """
        Converts a Unix timestamp in milliseconds to a datetime object.
        Args:
            timestamp (int): The Unix timestamp in milliseconds.
        Returns:
            datetime: The datetime object.
        """

        return datetime.fromtimestamp(timestamp / 1000.0)

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

    def is_trading_available(self, interval: str, trading_timeframes: dict) -> bool:
        pass

    def _map_interval(self, api_interval: str = None, interval: IntervalType = None):
        if api_interval:
            return interval
        elif interval:
            return api_interval

    def _get_api_klines(self, url_params: dict) -> dict:
        response = requests.get(
            self._get_url(self.KLINES_DATA_ENDPOINT), params=url_params
        )

        if response.status_code == 200:
            # Get data from API
            return json.loads(response.text)
        else:
            logger.error(
                f"{self.__class__.__name__}: {self._trader_model.exchange_id} - __get_api_klines({url_params}) -> {response.text}"
            )
            raise Exception(response.text)

    def _get_url(self, path: str) -> str:
        return self.get_api_endpoints() + path


class ByBitComApi(ExchangeApiBase):
    # Public API Endpoints
    SERVER_TIME_ENDPOINT = "market/time"

    TA_API_INTERVAL_1 = "1"
    TA_API_INTERVAL_3 = "3"
    TA_API_INTERVAL_5 = "5"
    TA_API_INTERVAL_15 = "15"
    TA_API_INTERVAL_30 = "30"
    TA_API_INTERVAL_60 = "60"
    TA_API_INTERVAL_120 = "120"
    TA_API_INTERVAL_240 = "240"
    TA_API_INTERVAL_360 = "360"
    TA_API_INTERVAL_720 = "720"
    TA_API_INTERVAL_D = "D"
    TA_API_INTERVAL_W = "W"
    TA_API_INTERVAL_M = "M"

    CATEGORY_LINEAR = "linear"

    def get_api_endpoints(self) -> str:
        return "https://api.bybit.com/v5/"

    def ping_server(self, **kwargs) -> bool:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._trader_model.exchange_id} - ping_server({kwargs})"
            )

        response = requests.get(self._get_url(self.SERVER_TIME_ENDPOINT))

        if response.status_code == 200:
            return True
        else:
            logger.error(f"{self.__class__.__name__}: ping_server - {response.text}")
            return False

    def get_intervals(self) -> list[IntervalType]:
        return [
            self._map_interval(api_interval=self.TA_API_INTERVAL_5),
            self._map_interval(api_interval=self.TA_API_INTERVAL_15),
            self._map_interval(api_interval=self.TA_API_INTERVAL_30),
            self._map_interval(api_interval=self.TA_API_INTERVAL_60),
            self._map_interval(api_interval=self.TA_API_INTERVAL_240),
            self._map_interval(api_interval=self.TA_API_INTERVAL_720),
            self._map_interval(api_interval=self.TA_API_INTERVAL_D),
            self._map_interval(api_interval=self.TA_API_INTERVAL_W),
        ]

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
        symbols_leverages = self._get_symbols(category=self.CATEGORY_LINEAR)
        # symbols_spot = self._get_symbols(category="spot")
        return symbols_leverages

    def get_history_data(
        self, history_data_param: HistoryDataParamModel, **kwargs
    ) -> HistoryDataModel:
        # Prepare URL parameters
        url_params = {
            Const.API_FLD_CATEGORY: self.CATEGORY_LINEAR,
            Const.API_FLD_SYMBOL: history_data_param.symbol,
            Const.API_FLD_INTERVAL: self._map_interval(
                interval=history_data_param.interval
            ),
            Const.API_FLD_LIMIT: history_data_param.limit,
        }

        # Boolean importing parameters closed_bars in order to get only closed bar for the current moment
        # If closed_bars indicator is True -> calculated endTime for the API
        if history_data_param.closed_bars:
            url_params[Const.API_FLD_END] = self.getOffseUnixTimeMsByInterval(
                history_data_param.interval
            )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._trader_model.exchange_id} - get_history_data({url_params})"
            )

        json_api_response = self._get_api_http_session().get_kline(**url_params)

        klines_data = json_api_response["result"]["list"]

        # Convert API response to the DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        df = self._convertResponseToDataFrame(klines_data)

        # Create an instance of HistoryDataModel
        obj_history_data = HistoryDataModel(
            symbol=history_data_param.symbol,
            interval=history_data_param.interval,
            limit=history_data_param.limit,
            data=df,
        )

        return obj_history_data

    def get_leverage_settings(self, symbol: str):
        return [1, 2, 5, 10, 20, 50]

    def get_accounts(self):
        account = {
            "accountId": "USDT",
            "asset": "USDT",
            "free": 0,
        }

        json_api_response = self._get_api_http_session(
            private_mode=True
        ).get_wallet_balance(
            accountType="SPOT",
            coin="USDT",
        )

        spot_accounts = json_api_response["result"]["list"]
        if spot_accounts:
            coins = spot_accounts[0]["coin"]
            if coins:
                usdt_coin = coins[0]
                account["free"] = usdt_coin["free"]

        return [account]

    def _convertResponseToDataFrame(self, api_response: list) -> pd.DataFrame:
        """
        Converts the API response into a DataFrame containing historical data.
        Args:
            api_response (list): The API response as a list.
        Returns:
            DataFrame: DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        """

        COLUMN_DATETIME_FLOAT = "DatetimeFloat"
        COLUMN_TURNOVER = "Turnover"

        df = pd.DataFrame(
            api_response,
            columns=[
                COLUMN_DATETIME_FLOAT,
                Const.COLUMN_OPEN,
                Const.COLUMN_HIGH,
                Const.COLUMN_LOW,
                Const.COLUMN_CLOSE,
                Const.COLUMN_VOLUME,
                COLUMN_TURNOVER,
            ],
        )
        df.drop([COLUMN_TURNOVER], axis=1, inplace=True)

        df[Const.COLUMN_DATETIME] = df.apply(
            lambda x: pd.to_datetime(
                self.getDatetimeByUnixTimeMs(int(x[COLUMN_DATETIME_FLOAT]))
            ),
            axis=1,
        )
        df.set_index(Const.COLUMN_DATETIME, inplace=True)
        df.drop([COLUMN_DATETIME_FLOAT], axis=1, inplace=True)
        df = df.astype(float)
        df = df.sort_index(ascending=True)

        return df

    def _get_symbols(self, **kwargs) -> dict[SymbolModel]:
        symbols = {}

        params = {
            "category": kwargs.get("category", self.CATEGORY_LINEAR),
            "status": "Trading",
        }

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._trader_model.exchange_id} - getSymbols({params})"
            )

        json_api_response = self._get_api_http_session().get_instruments_info(**params)

        result = json_api_response["result"]
        category = result["category"]

        # Create an instance of Symbol and add to the list
        for row in result["list"]:
            if row["quoteCoin"] == "USDT":
                status_converted = (
                    SymbolStatus.open
                    if row["status"] == "TRADING"
                    else SymbolStatus.close
                )

                quantity_step = (
                    row["lotSizeFilter"]["qtyStep"]
                    if category == self.CATEGORY_LINEAR
                    else row["quotePrecision"]
                )

                symbol_data = {
                    "symbol": row["symbol"],
                    "name": row["symbol"],
                    "status": status_converted,
                    "type": SymbolType.leverage
                    if category == self.CATEGORY_LINEAR
                    else SymbolType.spot,
                    "trading_time": "",
                    "currency": row["quoteCoin"],
                    "quote_precision": len(quantity_step.split(".")[1])
                    if "." in quantity_step
                    else 0,
                    "trading_fee": 0,
                }

                symbol_model = SymbolModel(**symbol_data)

                symbols[symbol_model.symbol] = symbol_model
            else:
                continue

        return symbols

    def _map_interval(
        self, api_interval: str = None, interval: IntervalType = None
    ) -> str:
        if api_interval:
            if api_interval == self.TA_API_INTERVAL_1:
                return IntervalType.MIN_1
            elif api_interval == self.TA_API_INTERVAL_3:
                return IntervalType.MIN_3
            elif api_interval == self.TA_API_INTERVAL_5:
                return IntervalType.MIN_5
            elif api_interval == self.TA_API_INTERVAL_15:
                return IntervalType.MIN_15
            elif api_interval == self.TA_API_INTERVAL_30:
                return IntervalType.MIN_30
            elif api_interval == self.TA_API_INTERVAL_60:
                return IntervalType.HOUR_1
            elif api_interval == self.TA_API_INTERVAL_120:
                return IntervalType.HOUR_2
            elif api_interval == self.TA_API_INTERVAL_240:
                return IntervalType.HOUR_4
            elif api_interval == self.TA_API_INTERVAL_360:
                return IntervalType.HOUR_6
            elif api_interval == self.TA_API_INTERVAL_720:
                return IntervalType.HOUR_12
            elif api_interval == self.TA_API_INTERVAL_D:
                return IntervalType.DAY_1
            elif api_interval == self.TA_API_INTERVAL_W:
                return IntervalType.WEEK_1
            elif api_interval == self.TA_API_INTERVAL_M:
                return IntervalType.MONTH_1
        elif interval:
            if interval == IntervalType.MIN_1:
                return self.TA_API_INTERVAL_1
            elif interval == IntervalType.MIN_3:
                return self.TA_API_INTERVAL_3
            elif interval == IntervalType.MIN_5:
                return self.TA_API_INTERVAL_5
            elif interval == IntervalType.MIN_15:
                return self.TA_API_INTERVAL_15
            elif interval == IntervalType.MIN_30:
                return self.TA_API_INTERVAL_30
            elif interval == IntervalType.HOUR_1:
                return self.TA_API_INTERVAL_60
            elif interval == IntervalType.HOUR_2:
                return self.TA_API_INTERVAL_120
            elif interval == IntervalType.HOUR_4:
                return self.TA_API_INTERVAL_240
            elif interval == IntervalType.HOUR_6:
                return self.TA_API_INTERVAL_360
            elif interval == IntervalType.HOUR_12:
                return self.TA_API_INTERVAL_720
            elif interval == IntervalType.DAY_1:
                return self.TA_API_INTERVAL_D
            elif interval == IntervalType.WEEK_1:
                return self.TA_API_INTERVAL_W
            elif interval == IntervalType.MONTH_1:
                return self.TA_API_INTERVAL_M

    def _get_api_http_session(
        self, private_mode: bool = False, tesnet: bool = False
    ) -> HTTP:
        if private_mode:
            api_key = self._trader_model.decrypt_key(self._trader_model.api_key)
            api_secret = self._trader_model.decrypt_key(self._trader_model.api_secret)
            api_session = HTTP(
                testnet=tesnet,
                api_key=api_key,
                api_secret=api_secret,
            )
        else:
            api_session = HTTP(
                testnet=tesnet,
            )
        return api_session


class DemoByBitComApi(ByBitComApi):
    def get_api_endpoints(self) -> str:
        return "https://api-testnet.bybit.com/v5/"

    def _get_api_http_session(self, private_mode: bool = False) -> HTTP:
        return super()._get_api_http_session(private_mode=private_mode, tesnet=True)

    def get_accounts(self):
        json_api_response = self._get_api_http_session(
            private_mode=True
        ).get_wallet_balance(
            accountType="UNIFIED",
            # coin="USDT",
        )
        return json_api_response


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
    GET_ORDER_ENDPOINT = "fetchOrder"
    CANCEL_ORDER = "cancelOrder"

    # Leverage Endpoints
    CLOSE_TRADING_POSITION_ENDPOINT = "closeTradingPosition"
    TRADING_POSITIONS_ENDPOINT = "tradingPositions"
    TRADING_POSITIONS_HISTORY_ENDPOINT = "tradingPositionsHistory"
    LEVERAGE_SETTINGS_ENDPOINT = "leverageSettings"
    UPDATE_TRADING_ORDERS_ENDPOINT = "updateTradingOrder"
    UPDATE_TRADING_POSITION_ENDPOINT = "updateTradingPosition"

    PRICE_TYPE_BID = "bid"
    PRICE_TYPE_ASK = "ask"

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

    def get_accounts(self, show_zero_balance: bool = False, recv_window: int = None):
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

    def get_intervals(self) -> list[IntervalType]:
        return [
            self._map_interval(api_interval=self.TA_API_INTERVAL_5M),
            self._map_interval(api_interval=self.TA_API_INTERVAL_15M),
            self._map_interval(api_interval=self.TA_API_INTERVAL_30M),
            self._map_interval(api_interval=self.TA_API_INTERVAL_1H),
            self._map_interval(api_interval=self.TA_API_INTERVAL_4H),
            self._map_interval(api_interval=self.TA_API_INTERVAL_1D),
            self._map_interval(api_interval=self.TA_API_INTERVAL_1WK),
        ]

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
        self, history_data_param: HistoryDataParamModel, **kwargs
    ) -> HistoryDataModel:
        # Prepare URL parameters
        url_params = {
            Const.API_FLD_SYMBOL: history_data_param.symbol,
            Const.API_FLD_INTERVAL: self._map_interval(
                interval=history_data_param.interval
            ),
            Const.API_FLD_LIMIT: history_data_param.limit,
        }

        # If closed_bars indicator is True -> calculated endTime for the API
        if history_data_param.closed_bars:
            url_params[Const.API_FLD_END_TIME] = self.getOffseUnixTimeMsByInterval(
                history_data_param.interval
            )
            url_params[Const.API_FLD_LIMIT] = url_params[Const.API_FLD_LIMIT] + 1

        # Importing parameters price_type: bid, ask
        price_type = kwargs.get(Const.FLD_PRICE_TYPE, self.PRICE_TYPE_BID)
        url_params[Const.API_FLD_PRICE_TYPE] = price_type

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"ExchangeApiBase: {self._trader_model.exchange_id} - get_history_data({url_params})"
            )

        json_api_response = self._get_api_klines(url_params)

        # Convert API response to the DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        df = self.convertResponseToDataFrame(json_api_response)

        # Create an instance of HistoryDataModel
        obj_history_data = HistoryDataModel(
            symbol=history_data_param.symbol,
            interval=history_data_param.interval,
            limit=history_data_param.limit,
            data=df,
        )

        return obj_history_data

    def create_order(self, position_mdl: OrderModel) -> OrderModel:
        pass

    def create_leverage(self, position_mdl: LeverageModel) -> LeverageModel:
        created_position = self._create_position(
            account_id=position_mdl.account_id,
            symbol=position_mdl.symbol,
            side=position_mdl.side,
            order_type=position_mdl.type,
            quantity=position_mdl.quantity,
            leverage=position_mdl.leverage,
            stop_loss=position_mdl.stop_loss if position_mdl.stop_loss > 0 else None,
            take_profit=position_mdl.take_profit
            if position_mdl.take_profit > 0
            else None,
        )

        order_id = created_position[Const.API_FLD_ORDER_ID]
        open_leverages = self.get_open_leverages(
            symbol=position_mdl.symbol, order_id=order_id
        )

        position_mdl.position_id = open_leverages[0].position_id
        position_mdl.order_id = order_id
        position_mdl.open_datetime = self.getDatetimeByUnixTimeMs(
            created_position[Const.API_FLD_TRANSACT_TIME]
        )
        position_mdl.open_price = float(created_position[Const.API_FLD_PRICE])
        position_mdl.quantity = float(created_position[Const.API_FLD_EXECUTED_QUANTITY])
        position_mdl.fee = float(open_leverages[0].fee)

        return position_mdl

    def close_order(self):
        pass

    def close_leverage(
        self, symbol: str, position_id: str, recv_window=None
    ) -> OrderCloseModel:
        self._validate_recv_window(recv_window)

        response = self._post(
            self.CLOSE_TRADING_POSITION_ENDPOINT,
            positionId=position_id,
            recvWindow=recv_window,
        )

        closed_mdl = self.get_close_leverages(
            position_id=position_id, symbol=symbol, limit=2
        )

        return closed_mdl

    # Orders
    def get_open_orders(self, symbol=None, recv_window=None):
        """
        Get all open orders on a symbol. Careful when accessing this with no
        symbol.
        If the symbol is not sent, orders for all symbols will be returned in
        an array.
        """

        self._validate_recv_window(recv_window)

        return self._get(
            self.CURRENT_OPEN_ORDERS_ENDPOINT,
            symbol=symbol,
            recvWindow=recv_window,
        )

    def cancel_order(self, symbol, order_id, recv_window=None):
        """
        Cancel an active order within exchange and leverage trading modes.

        :param symbol:
        :param order_id:
        :param recv_window: The value cannot be greater than 60000.
        :return: dict object

        Response:
        {
          "symbol": "LTC/BTC",
          "origClientOrderId": "myOrder1",
          "orderId": "4",
          "orderListId": -1,
          "clientOrderId": "cancelMyOrder1",
          "price": "2.00000000",
          "origQty": "1.00000000",
          "executedQty": "0.00000000",
          "cummulativeQuoteQty": "0.00000000",
          "status": "CANCELED",
          "timeInForce": "GTC",
          "type": "LIMIT",
          "side": "BUY"
        }
        """

        self._validate_recv_window(recv_window)
        return self._delete(
            self.ORDER_ENDPOINT,
            symbol=symbol,
            orderId=order_id,
            recvWindow=recv_window,
        )

    def get_position(
        self, symbol: str, order_id: str, recv_window=None
    ) -> LeverageModel:
        self._validate_recv_window(recv_window)
        position = self._get(
            self.GET_ORDER_ENDPOINT,
            symbol=symbol,
            orderId=order_id,
            recvWindow=recv_window,
        )

        if position[Const.API_FLD_STATUS] == "FILLED":
            status = OrderStatus.opened
        else:
            status = OrderStatus.closed

        position_data = {
            Const.DB_SESSION_ID: "1",
            Const.DB_SYMBOL: position[Const.API_FLD_SYMBOL],
            Const.DB_ORDER_ID: position[Const.API_FLD_ORDER_ID],
            Const.DB_STATUS: status,
            Const.DB_ACCOUNT_ID: str(position[Const.API_FLD_ACCOUNT_ID]),
            Const.DB_SIDE: position[Const.API_FLD_SIDE],
            Const.DB_TYPE: position[Const.API_FLD_TYPE],
            Const.DB_OPEN_PRICE: position[Const.API_FLD_EXECUTED_PRICE],
            Const.DB_QUANTITY: position[Const.API_FLD_EXEC_QUANTITY],
            Const.DB_FEE: position[Const.API_FLD_MARGIN],
        }
        position_mdl = LeverageModel(**position_data)

        return position_mdl

    # Leverage
    def get_open_leverages(
        self, symbol: str = None, order_id: str = None, recv_window=None
    ) -> list[LeverageModel]:
        position_models = []

        self._validate_recv_window(recv_window)
        api_positions = self._get(
            self.TRADING_POSITIONS_ENDPOINT, recvWindow=recv_window
        )

        for position in api_positions["positions"]:
            if (symbol and symbol != position[Const.API_FLD_SYMBOL]) or (
                order_id and order_id != position[Const.API_FLD_ORDER_ID]
            ):
                continue

            side = OrderSideType.buy
            quantity = position[Const.API_FLD_OPEN_QUANTITY]
            if quantity < 0:
                quantity = -quantity
                side = OrderSideType.sell

            position_data = {
                Const.DB_SESSION_ID: "1",
                Const.DB_POSITION_ID: position[Const.API_FLD_ID],
                Const.DB_ORDER_ID: position[Const.API_FLD_ORDER_ID],
                Const.DB_ACCOUNT_ID: str(position[Const.API_FLD_ACCOUNT_ID]),
                Const.DB_SYMBOL: position[Const.API_FLD_SYMBOL],
                Const.DB_STATUS: OrderStatus.opened,
                Const.DB_SIDE: side,
                Const.DB_TYPE: OrderType.market,
                Const.DB_OPEN_PRICE: position[Const.API_FLD_OPEN_PRICE],
                Const.DB_OPEN_DATETIME: self.getDatetimeByUnixTimeMs(
                    position[Const.API_FLD_OPEN_TIMESTAMP]
                ),
                Const.DB_QUANTITY: quantity,
                Const.DB_FEE: position[Const.API_FLD_FEE],
                Const.DB_STOP_LOSS: position[Const.API_FLD_STOP_LOSS]
                if Const.API_FLD_STOP_LOSS in position
                else 0,
                Const.DB_TAKE_PROFIT: position[Const.API_FLD_TAKE_PROFIT]
                if Const.API_FLD_TAKE_PROFIT in position
                else 0,
            }
            position_models.append(LeverageModel(**position_data))

        return position_models

    # Leverage
    def get_close_leverages(
        self, position_id: str, symbol: str = None, limit: int = 1, recv_window=None
    ) -> OrderCloseModel:
        position_models = []

        self._validate_recv_window(recv_window)
        api_positions = self._get(
            self.TRADING_POSITIONS_HISTORY_ENDPOINT,
            recvWindow=recv_window,
            symbol=symbol,
            limit=limit,
        )

        for position in api_positions["history"]:
            if position_id != position[Const.API_FLD_POSITION_ID]:
                continue

            order_reason = OrderReason.TRADER
            if position[Const.API_FLD_SOURCE] == "TP":
                order_reason = OrderReason.TAKE_PROFIT
            elif position[Const.API_FLD_SOURCE] == "SL":
                order_reason = OrderReason.STOP_LOSS
            elif position[Const.API_FLD_SOURCE] == "USER":
                order_reason = OrderReason.MANUAL

            close_details_data = {
                Const.DB_STATUS: OrderStatus.closed,
                Const.DB_CLOSE_DATETIME: self.getDatetimeByUnixTimeMs(
                    position[Const.API_FLD_EXECUTED_TIMESTAMP]
                ),
                Const.DB_CLOSE_PRICE: position[Const.API_FLD_PRICE],
                Const.DB_CLOSE_REASON: order_reason,
                Const.DB_TOTAL_PROFIT: position[Const.API_FLD_RPL],
                Const.DB_FEE: position[Const.API_FLD_FEE],
            }

            return OrderCloseModel(**close_details_data)

    def update_trading_position(
        self,
        position_id,
        stop_loss: float = None,
        take_profit: float = None,
        guaranteed_stop_loss=False,
        recv_window=None,
    ):
        """
        To edit current leverage trade by changing stop loss and take profit
        levels.

        :return: dict object
        Example:
        {
            "requestId": 242040,
            "state": “PROCESSED”
        }
        """
        self._validate_recv_window(recv_window)
        return self._post(
            self.UPDATE_TRADING_POSITION_ENDPOINT,
            positionId=position_id,
            guaranteedStopLoss=guaranteed_stop_loss,
            stopLoss=stop_loss,
            takeProfit=take_profit,
        )

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

    def _create_position(
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

        if order_type == OrderType.limit:
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
                f"ExchangeApiBase: {self._trader_model.exchange_id} - GET /{path}({kwargs})"
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
                f"ExchangeApiBase: {self._trader_model.exchange_id} - POST /{path}({kwargs})"
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

    def _map_interval(
        self, api_interval: str = None, interval: IntervalType = None
    ) -> str:
        if api_interval:
            return api_interval
        elif interval:
            return interval


class DemoDzengiComApi(DzengiComApi):
    def get_api_endpoints(self) -> str:
        return "https://demo-api-adapter.backend.currency.com/api/v2/"
