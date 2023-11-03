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
    SymbolModel,
    TraderModel,
    ExchangeId,
)
from .core import logger
from .constants import Const


class ExchangeApiBase:
    def __init__(self, trader_model: TraderModel):
        self.__trader_model = trader_model

    def ping_server(self, **kwargs) -> bool:
        return False

    def get_api_endpoints(self) -> str:
        return None

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
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

    def ping_server(self, **kwargs) -> bool:
        return True

    def get_api_endpoints(self) -> str:
        return "https://api-adapter.backend.currency.com/api/v2/"

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
        symbols = {}

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

                    symbol_data = {
                        "symbol": row["symbol"],
                        "name": row["name"],
                        "status": status_converted,
                        "type": row["marketType"],
                        "trading_time": row["tradingHours"],
                        "currency": row["quoteAssetId"],
                        # "trading_fee": row["tradingFee"],
                    }

                    symbol_model = SymbolModel(**symbol_data)

                    symbols[symbol_model.symbol] = symbol_model
                else:
                    continue

            return symbols

        else:
            logger.error(
                f"ExchangeApiBase: {self.__trader_model.exchange_id} - getSymbols -> {response.text}"
            )
            raise Exception(response.text)

    def _get_url(self, path: str) -> str:
        return self.get_api_endpoints() + path

    # def _get(self, path, **kwargs):
    #     url = self._get_url(path)

    #     response = requests.get(
    #         url,
    #         params=self._get_params_with_signature(**kwargs),
    #         headers=self._get_header(),
    #     )

    #     if response.status_code == 200:
    #         return response.json()
    #     else:
    #         raise Exception(
    #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - GET /{path} -> {response.status_code}: {response.text}"
    #         )


class DemoDzengiComApi(DzengiComApi):
    def get_api_endpoints(self) -> str:
        return "https://demo-api-adapter.backend.currency.com/api/v2/"
