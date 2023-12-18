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

from .constants import Const
from .core import logger, config, Symbol, HistoryData, RuntimeBufferStore
from .api import ExchangeApiBase, DzengiComApi, DemoDzengiComApi
from .common import (
    Importance,
    IntervalType,
    IntervalModel,
    SymbolIntervalLimitModel,
    TraderStatus,
    OrderStatus,
    SessionStatus,
    ExchangeId,
    SymbolModel,
    UserModel,
    TraderModel,
    SessionModel,
    SessionType,
    BalanceModel,
    OrderModel,
    LeverageModel,
    TransactionModel,
)
from .mongodb import (
    MongoUser,
    MongoChannel,
    MongoTrader,
    MongoSession,
    MongoBalance,
    MongoOrder,
    MongoLeverage,
    MongoTransaction,
)


class BufferBaseHandler:
    def __init__(self):
        self._buffer = {}

    def get_buffer(self, **kwargs) -> dict:
        return self._buffer

    def is_data_in_buffer(self, **kwargs) -> bool:
        return True if self._buffer else False

    def set_buffer(self, buffer: dict):
        if buffer:
            self._buffer = buffer

    def clear_buffer(self):
        self._buffer.clear()


class BufferSingleDictionary(BufferBaseHandler):
    def get_buffer(self, key: str) -> dict:
        if self.is_data_in_buffer(key):
            return self._buffer[key]
        else:
            None

    def is_data_in_buffer(self, key: str) -> bool:
        return key in self._buffer

    def set_buffer(self, key: str, data: dict):
        self._buffer[key] = data


class BufferHistoryDataHandler(BufferBaseHandler):
    def get_buffer(
        self, history_data_param: SymbolIntervalLimitModel, **kwargs
    ) -> HistoryData:
        symbol = history_data_param.symbol
        interval = history_data_param.interval
        limit = history_data_param.limit
        end_datetime = kwargs.get(Const.FLD_END_DATETIME)

        buffer_key = self._get_buffer_key(symbol=symbol, interval=interval)
        history_data_buffer = self._buffer[buffer_key]
        df_buffer = history_data_buffer.getDataFrame()

        df_required = df_buffer[df_buffer.index <= end_datetime]

        if limit > len(df_required):
            return None

        df_required = df_required.tail(limit)

        history_data_required = HistoryData(
            symbol=symbol, interval=interval, limit=limit, dataFrame=df_required
        )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"BUFFER: getHistoryData(symbol={symbol}, interval={interval}, limit={limit}, endDatetime={end_datetime})"
            )

        return history_data_required

    def is_data_in_buffer(self, symbol: str, interval: str) -> bool:
        buffer_key = self._get_buffer_key(symbol=symbol, interval=interval)
        if buffer_key in self._buffer:
            return True
        else:
            return False

    def set_buffer(self, buffer: HistoryData):
        if buffer:
            buffer_key = self._get_buffer_key(
                symbol=buffer.getSymbol(),
                interval=buffer.getInterval(),
            )
            self._buffer[buffer_key] = buffer

    def validate_data_in_buffer(
        self, symbol: str, interval: str, limit: int, end_datetime: datetime
    ) -> bool:
        buffer_key = self._get_buffer_key(symbol=symbol, interval=interval)
        if self.is_data_in_buffer(symbol=symbol, interval=interval):
            history_data_buffer = self._buffer[buffer_key]
            if (
                limit <= history_data_buffer.getLimit()
                and end_datetime <= history_data_buffer.getEndDateTime()
            ):
                return True
            else:
                return False
        else:
            return False

    def _get_buffer_key(self, symbol: str, interval: str) -> tuple:
        if not symbol or not interval:
            Exception(
                f"History Data buffer key is invalid: symbol: {symbol}, interval: {interval}"
            )
        buffer_key = (symbol, interval)
        return buffer_key


class BufferTimeFrame(BufferBaseHandler):
    def get_buffer(self, trading_time: str) -> dict:
        if self.is_data_in_buffer(trading_time):
            return self._buffer[trading_time]
        else:
            None

    def is_data_in_buffer(self, trading_time: str) -> bool:
        return trading_time in self._buffer

    def set_buffer(self, trading_time: str, timeframe: dict):
        self._buffer[trading_time] = timeframe


class UserHandler:
    def __init__(self):
        self.__buffer_users: BufferSingleDictionary = BufferSingleDictionary()

    def get_buffer(self) -> BufferSingleDictionary:
        return self.__buffer_users

    def get_user_by_email(self, email: str) -> UserModel:
        if not self.__buffer_users.is_data_in_buffer(email):
            user_mdl = self._get_user_by_email(email)
            self.__buffer_users.set_buffer(email, user_mdl)

        return self.__buffer_users.get_buffer(email)

    @staticmethod
    def create_user(user: UserModel) -> UserModel:
        try:
            id = MongoUser().insert_one(user.to_mongodb_doc())
        except Exception as error:
            logger.error(f"UserHandler: {error}")
            raise Exception(f"User {user.email} already exists")

        return UserHandler.get_user_by_id(id)

    @staticmethod
    def update_user(id: str, query: dict):
        return MongoUser().update_one(id=id, query=query)

    @staticmethod
    def delete_user(id: str):
        query = {Const.DB_USER_ID: id}

        # Remove User's Channels
        MongoChannel().delete_many(query)
        # Remove User's Traders
        MongoTrader().delete_many(query)
        # Remove User's Sessions, Balances, Orders, Leverages
        sessions = SessionHandler.get_sessions(user_id=id)
        for session_mdl in sessions:
            SessionHandler.delete_session(id=session_mdl.id)
        # Remove User
        user_deletion = MongoUser().delete_one(id=id)
        # CLear buffer after removing of a user
        buffer_runtime_handler.get_user_handler().get_buffer().clear_buffer()

        return user_deletion

    @staticmethod
    def get_user_by_id(id: str) -> UserModel:
        user_db = MongoUser().get_one(id)
        if not user_db:
            raise Exception(f"User {id} doesn't exists")
        return UserModel(**user_db)

    def _get_user_by_email(self, email: str) -> UserModel:
        user_db = MongoUser().get_one_by_filter({"email": email})
        if not user_db:
            raise Exception(f"User {email} doesn't exists")
        return UserModel(**user_db)

    @staticmethod
    def get_technical_user() -> UserModel:
        technical_user_db_list = MongoUser().get_many({"technical_user": True})
        if not technical_user_db_list:
            raise Exception(f"Technical User isn't maintained")
        return UserModel(**technical_user_db_list[0])

    @staticmethod
    def get_users(search: str = None) -> list:
        search_query = {}

        # Construct a regular expression pattern for partial text matching
        search_pattern = f".*{search}.*"

        if search:
            search_query = {
                "$or": [
                    {"email": {"$regex": search_pattern, "$options": "i"}},
                    {"first_name": {"$regex": search_pattern, "$options": "i"}},
                    {"second_name": {"$regex": search_pattern, "$options": "i"}},
                ]
            }

        user_db_list = MongoUser().get_many(search_query)
        users = [UserModel(**user_db) for user_db in user_db_list]

        return users


class TraderHandler:
    @staticmethod
    def check_status(id: str) -> dict:
        trader_status = TraderStatus.NEW
        exchange_handler = ExchangeHandler.get_handler(trader_id=id)
        trader_mdl = exchange_handler.get_trader_model()

        if exchange_handler.ping_server():
            trader_status = TraderStatus.PUBLIC

            if trader_mdl.expired_dt < datetime.now():
                trader_status = TraderStatus.EXPIRED

            elif trader_mdl.api_key and trader_mdl.api_secret:
                try:
                    exchange_handler.get_accounts()
                    trader_status = TraderStatus.PRIVATE

                except Exception:
                    pass
        else:
            trader_status = TraderStatus.FAILED

        TraderHandler.update_trader(
            id=trader_mdl.id, query={"status": trader_status.value}
        )
        return {"status": trader_status.value}

    @staticmethod
    def create_trader(trader: TraderModel):
        if trader.api_key:
            trader.api_key = trader.encrypt_key(key=trader.api_key)
        if trader.api_secret:
            trader.api_secret = trader.encrypt_key(key=trader.api_secret)

        id = MongoTrader().insert_one(trader.to_mongodb_doc())
        return TraderHandler.get_trader(id)

    @staticmethod
    def update_trader(id: str, query: dict):
        trader_mdl = TraderHandler.get_trader(id)

        if "api_key" in query and query["api_key"]:
            query["api_key"] = trader_mdl.encrypt_key(key=query["api_key"])
        if "api_secret" in query and query["api_secret"]:
            query["api_secret"] = trader_mdl.encrypt_key(key=query["api_secret"])

        return MongoTrader().update_one(id=id, query=query)

    @staticmethod
    def delete_trader(id: str):
        # Remove Trader's Sessions, Balances, Orders, Leverages
        sessions = SessionHandler.get_sessions(trader_id=id)
        for session_mdl in sessions:
            SessionHandler.delete_session(id=session_mdl.id)

        # Remove Trader
        trader_deletion = MongoTrader().delete_one(id=id)

        return trader_deletion

    @staticmethod
    def get_trader(id: str) -> TraderModel:
        entry = MongoTrader().get_one(id)
        if not entry:
            raise Exception(f"Trader {id} doesn't exists")
        return TraderModel(**entry)

    @staticmethod
    def get_default_user_trader(user_id: str) -> TraderModel:
        trader_model_list = TraderHandler._read_traders(user_id=user_id, default=True)
        if not trader_model_list:
            raise Exception(f"User {user_id} doesn't have default trader")
        return trader_model_list[0]

    @staticmethod
    def get_default_trader(exchange_id: ExchangeId) -> TraderModel:
        trader_model_list = TraderHandler._read_traders(exchange_id=exchange_id)
        if not trader_model_list:
            raise Exception(f"Exchange Id {exchange_id} doesn't maintained")
        return trader_model_list[0]

    @staticmethod
    def get_traders(user_id: str = None) -> list[TraderModel]:
        return TraderHandler._read_traders(user_id=user_id)

    @staticmethod
    def get_traders_by_email(
        user_email: str = None, status: int = None
    ) -> list[TraderModel]:
        user_mdl = buffer_runtime_handler.get_user_handler().get_user_by_email(
            email=user_email
        )
        if user_mdl.technical_user:
            return TraderHandler._read_traders()
        else:
            return TraderHandler._read_traders(user_id=user_mdl.id, status=status)

    @staticmethod
    def _read_traders(**kwargs) -> list[TraderModel]:
        query = {**kwargs}
        status = kwargs.get(Const.DB_STATUS)
        if Const.DB_STATUS in query:
            if status in ["", "undefined", None]:
                status = -2

            query[Const.DB_STATUS] = {"$gte": int(status)}

        entries_db = MongoTrader().get_many(query)
        result = [TraderModel(**entry) for entry in entries_db]
        return result


class SessionHandler:
    @staticmethod
    def create_session(session: SessionModel):
        id = MongoSession().insert_one(session.to_mongodb_doc())
        return SessionHandler.get_session(id)

    @staticmethod
    def update_session(id: str, query: dict):
        return MongoSession().update_one(id=id, query=query)

    @staticmethod
    def delete_session(id: str):
        query = {"session_id": id}

        MongoOrder().delete_many(query)
        MongoLeverage().delete_many(query)
        MongoTransaction().delete_many(query)
        MongoBalance().delete_many(query)
        session_deletion = MongoSession().delete_one(id=id)

        return session_deletion

    @staticmethod
    def get_session(id: str) -> SessionModel:
        entry = MongoSession().get_one(id)
        if not entry:
            raise Exception(f"Session {id} doesn't exists")
        return SessionModel(**entry)

    @staticmethod
    def get_sessions_by_email(user_email: str):
        user_mdl = buffer_runtime_handler.get_user_handler().get_user_by_email(
            email=user_email
        )
        return SessionHandler.get_sessions(user_id=user_mdl.id)

    @staticmethod
    def get_sessions(
        user_id: str = None,
        trader_id: str = None,
        symbol: str = None,
        interval: str = None,
        status: SessionStatus = None,
        session_type: SessionType = None,
    ):
        query = {}

        if user_id:
            query[Const.DB_USER_ID] = user_id
        if trader_id:
            query[Const.DB_TRADER_ID] = trader_id
        if session_type:
            query[Const.DB_SESSION_TYPE] = session_type
        if symbol:
            query[Const.DB_SYMBOL] = symbol
        if interval:
            query[Const.DB_INTERVAL] = interval
        if status:
            query[Const.DB_STATUS] = status

        entries_db = MongoSession().get_many(query)
        result = [SessionModel(**entry) for entry in entries_db]

        return result


class BalanceHandler:
    @staticmethod
    def create_balance(balance: BalanceModel):
        id = MongoBalance().insert_one(balance.to_mongodb_doc())
        return BalanceHandler.get_balance(id)

    @staticmethod
    def update_balance(id: str, query: dict) -> bool:
        result = MongoBalance().update_one(id=id, query=query)
        if not result:
            raise Exception(f"Update balance {id} has been failed")
        return result

    @staticmethod
    def get_balance(id: str) -> BalanceModel:
        entry = MongoBalance().get_one(id)
        if not entry:
            raise Exception(f"Balance {id} doesn't exists")
        return BalanceModel(**entry)

    @staticmethod
    def get_balances(session_id: str = None):
        query = {Const.DB_SESSION_ID: session_id} if session_id else {}
        entries_db = MongoBalance().get_many(query)
        result = [BalanceModel(**entry) for entry in entries_db]

        return result

    @staticmethod
    def get_balance_4_session(session_id: str):
        entriy_db = MongoBalance().get_one_by_filter({Const.DB_SESSION_ID: session_id})
        result = BalanceModel(**entriy_db)
        return result

    @staticmethod
    def get_account_balance(account_id: str, init_balance: float) -> float:
        query = [
            {"$match": {Const.DB_ACCOUNT_ID: account_id}},
            {
                "$group": {
                    "_id": "$account_id",
                    "total_balance": {"$sum": "$total_balance"},
                }
            },
        ]
        aggregates_db = MongoBalance().aggregate(query)

        if aggregates_db:
            return aggregates_db[0][Const.DB_TOTAL_BALANCE] + init_balance
        else:
            return init_balance


class OrderHandler:
    @staticmethod
    def create_order(order: OrderModel):
        id = MongoOrder().insert_one(order.to_mongodb_doc())
        return OrderHandler.get_order(id)

    @staticmethod
    def update_order(id: str, query: dict) -> bool:
        result = MongoOrder().update_one(id=id, query=query)
        if not result:
            raise Exception(f"Update order {id} has been failed")
        return result

    @staticmethod
    def get_order(id: str) -> OrderModel:
        entry = MongoOrder().get_one(id)
        if not entry:
            raise Exception(f"Order {id} doesn't exists")
        return OrderModel(**entry)

    @staticmethod
    def get_orders(session_id: str = None, status: OrderStatus = None):
        query = {}
        result = []

        if session_id:
            query[Const.DB_SESSION_ID] = session_id
        if status:
            query[Const.DB_STATUS] = status

        entries_db = MongoOrder().get_many(query)

        for entry in entries_db:
            order_mdl = OrderModel(**entry)

            order_mdl.calculate_balance()
            order_mdl.calculate_percent()
            order_mdl.calculate_high_percent()
            order_mdl.calculate_low_percent()

            result.append(order_mdl)

        return result


class LeverageHandler:
    @staticmethod
    def create_leverage(leverage: LeverageModel):
        id = MongoLeverage().insert_one(leverage.to_mongodb_doc())
        return LeverageHandler.get_leverage(id)

    @staticmethod
    def update_leverage(id: str, query: dict) -> bool:
        result = MongoLeverage().update_one(id=id, query=query)
        if not result:
            raise Exception(f"Update leverage {id} has been failed")
        return result

    @staticmethod
    def get_leverage(id: str) -> LeverageModel:
        entry = MongoLeverage().get_one(id)
        if not entry:
            raise Exception(f"Leverage {id} doesn't exists")
        return LeverageModel(**entry)

    @staticmethod
    def get_leverages(session_id: str = None, status: OrderStatus = None):
        query = {}
        result = []

        if session_id:
            query[Const.DB_SESSION_ID] = session_id
        if status:
            query[Const.DB_STATUS] = status

        entries_db = MongoLeverage().get_many(query)

        for entry in entries_db:
            leverage_mdl = LeverageModel(**entry)

            leverage_mdl.calculate_balance()
            leverage_mdl.calculate_percent()
            leverage_mdl.calculate_high_percent()
            leverage_mdl.calculate_low_percent()

            result.append(leverage_mdl)

        return result


class TransactionHandler:
    @staticmethod
    def create_transaction(transaction: TransactionModel):
        id = MongoTransaction().insert_one(transaction.to_mongodb_doc())
        return TransactionHandler.get_transaction(id)

    @staticmethod
    def create_transactions(transactions_mdl: list[TransactionModel]):
        transactions = []
        for transaction_mdl in transactions_mdl:
            transactions.append(transaction_mdl.to_mongodb_doc())
        ids = MongoTransaction().insert_many(transactions)
        if not ids:
            raise Exception(f"Error during create_transactions operation")
        return ids

    @staticmethod
    def get_transaction(id: str) -> TransactionModel:
        entry = MongoTransaction().get_one(id)
        if not entry:
            raise Exception(f"Transaction {id} doesn't exists")
        return TransactionModel(**entry)

    @staticmethod
    def get_transactions(
        user_id: str = None, session_id: str = None, local_order_id: str = None
    ):
        query = {}
        if user_id:
            query[Const.DB_USER_ID] = user_id
        elif not query and session_id:
            query[Const.DB_SESSION_ID] = session_id
        elif not query and local_order_id:
            query[Const.DB_LOCAL_ORDER_ID] = local_order_id

        entries_db = MongoTransaction().get_many(query)
        result = [TransactionModel(**entry) for entry in entries_db]

        return result


class ExchangeHandler:
    def __init__(self, trader_id: str):
        self._api: ExchangeApiBase = None
        self.__trader_model: TraderModel = TraderHandler.get_trader(trader_id)

        if not self.__trader_model.exchange_id:
            raise Exception(f"ExchangeHandler: Exchange Id is missed")

        if self.__trader_model.exchange_id == ExchangeId.dzengi_com:
            self._api = DzengiComApi(self.__trader_model)
        elif self.__trader_model.exchange_id == ExchangeId.demo_dzengi_com:
            self._api = DemoDzengiComApi(self.__trader_model)
        else:
            raise Exception(
                f"ExchangeHandler: {self.__trader_model.exchange_id} implementation is missed"
            )

    @staticmethod
    def get_handler(trader_id: str = None, user_id: str = None):
        if trader_id:
            return ExchangeHandler(trader_id)
        elif user_id:
            trader = TraderHandler.get_default_user_trader(user_id=user_id)
            trader_id = trader.id
        else:
            technical_user = UserHandler.get_technical_user()
            trader = TraderHandler.get_default_user_trader(user_id=technical_user.id)
            trader_id = trader.id

        return ExchangeHandler(trader.id)

    def get_trader_id(self) -> str:
        return self.__trader_model.id

    def get_trader_model(self) -> TraderModel:
        return self.__trader_model

    def ping_server(self, **kwargs) -> bool:
        return self._api.ping_server()

    def get_accounts(self) -> list:
        return self._api.get_accounts()

    def get_account_info(self, account_id) -> dict:
        accounts = self.get_accounts()
        for account in accounts:
            if account[Const.API_FLD_ACCOUNT_ID] == account_id:
                return account

        raise Exception(f"ExchangeHandler: {account_id} can't be determined")

    def get_leverage_settings(self, symbol: str) -> list:
        if not symbol:
            raise Exception(
                f"ExchangeHandler: {self.__trader_model.exchange_id} symbol is missed"
            )
        return self._api.get_leverage_settings(symbol=symbol)

    def get_intervals(self) -> list[IntervalModel]:
        return self._api.get_intervals()

    def get_symbols(self, **kwargs) -> dict[Symbol]:
        # Send a request to an API to get symbols
        return self._api.get_symbols()

    def get_history_data(
        self, history_data_param: SymbolIntervalLimitModel, **kwargs
    ) -> HistoryData:
        return self._api.get_history_data(history_data_param, **kwargs)

    def get_open_leverages(
        self, symbol: str = None, order_id: str = None
    ) -> list[LeverageModel]:
        return self._api.get_open_leverages(symbol=symbol, order_id=order_id)

    def get_close_leverages(self, position_id: str, symbol: str = None, limit: int = 1):
        return self._api.get_close_leverages(
            position_id=position_id, symbol=symbol, limit=limit
        )

    def get_position(self, symbol: str, order_id: str) -> LeverageModel:
        return self._api.get_position(symbol=symbol, order_id=order_id)

    def create_order(self, position_mdl: OrderModel):
        return self._api.create_order(position_mdl)

    def create_leverage(self, position_mdl: LeverageModel) -> LeverageModel:
        return self._api.create_leverage(position_mdl)

    def close_order(self, position_id: str) -> OrderModel:
        return self._api.close_order(position_id)

    def close_leverage(self, symbol: str, position_id: str) -> LeverageModel:
        return self._api.close_leverage(symbol=symbol, position_id=position_id)

    def get_end_datetime(self, interval: str, **kwargs) -> datetime:
        original_datetime = datetime.now()
        return self._api.get_end_datetime(interval, original_datetime, **kwargs)

    def calculate_trading_timeframe(self, trading_time: str, **kwargs) -> dict:
        return self._api.calculate_trading_timeframe(trading_time, **kwargs)

    def is_trading_available(
        self, interval: str, trading_timeframes: dict, **kwargs
    ) -> bool:
        return self._api.is_trading_available(interval, trading_timeframes, **kwargs)


class BaseOnExchangeHandler:
    def __init__(self, exchange_handler: ExchangeHandler = None):
        self._exchange_handler: ExchangeHandler = None

        if exchange_handler:
            self._exchange_handler = exchange_handler
        else:
            self._exchange_handler: ExchangeHandler = ExchangeHandler.get_handler()

    def get_exchange_id(self) -> ExchangeId:
        return self._exchange_handler.get_exchange_id()


class IntervalHandler(BaseOnExchangeHandler):
    def __init__(self, exchange_handler: ExchangeHandler = None):
        super().__init__(exchange_handler)

        self.__interval_mdls: list[IntervalModel] = []
        intervals = self._exchange_handler.get_intervals()
        for interval in intervals:
            self.__interval_mdls.append(self.get_interval_vh(interval))

    @staticmethod
    def get_intervals_dict_vh() -> dict:
        return {
            # 1m - LOW
            IntervalType.MIN_1: IntervalModel(
                interval=IntervalType.MIN_1,
                name="1 minute",
                order=10,
                importance=Importance.LOW,
            ),
            # 3m - LOW
            IntervalType.MIN_3: IntervalModel(
                interval=IntervalType.MIN_3,
                name="3 minutes",
                order=20,
                importance=Importance.LOW,
            ),
            # 5m - LOW
            IntervalType.MIN_5: IntervalModel(
                interval=IntervalType.MIN_5,
                name="5 minutes",
                order=30,
                importance=Importance.LOW,
            ),
            # 15m - LOW
            IntervalType.MIN_15: IntervalModel(
                interval=IntervalType.MIN_15,
                name="15 minutes",
                order=40,
                importance=Importance.LOW,
            ),
            # 30m - LOW
            IntervalType.MIN_30: IntervalModel(
                interval=IntervalType.MIN_30,
                name="30 minutes",
                order=50,
                importance=Importance.LOW,
            ),
            # 1h - MEDIUM
            IntervalType.HOUR_1: IntervalModel(
                interval=IntervalType.HOUR_1,
                name="1 hour",
                order=60,
                importance=Importance.MEDIUM,
            ),
            # 2h - MEDIUM
            IntervalType.HOUR_2: IntervalModel(
                interval=IntervalType.HOUR_2,
                name="2 hours",
                order=70,
                importance=Importance.MEDIUM,
            ),
            # 4h - MEDIUM
            IntervalType.HOUR_4: IntervalModel(
                interval=IntervalType.HOUR_4,
                name="4 hours",
                order=80,
                importance=Importance.MEDIUM,
            ),
            # 6h - MEDIUM
            IntervalType.HOUR_6: IntervalModel(
                interval=IntervalType.HOUR_6,
                name="6 hours",
                order=90,
                importance=Importance.MEDIUM,
            ),
            # 12h - HIGH
            IntervalType.HOUR_12: IntervalModel(
                interval=IntervalType.HOUR_12,
                name="12 hours",
                order=100,
                importance=Importance.HIGH,
            ),
            # 1d - HIGH
            IntervalType.DAY_1: IntervalModel(
                interval=IntervalType.DAY_1,
                name="1 day",
                order=110,
                importance=Importance.HIGH,
            ),
            # 1w - HIGH
            IntervalType.WEEK_1: IntervalModel(
                interval=IntervalType.WEEK_1,
                name="1 week",
                order=120,
                importance=Importance.HIGH,
            ),
            # 1month - HIGH
            IntervalType.MONTH_1: IntervalModel(
                interval=IntervalType.MONTH_1,
                name="1 month",
                order=130,
                importance=Importance.HIGH,
            ),
        }

    @staticmethod
    def get_intervals_list_vh() -> list[IntervalModel]:
        return [
            interval_mdl
            for interval_mdl in IntervalHandler.get_intervals_dict_vh().values()
        ]

    @staticmethod
    def get_interval_vh(interval: IntervalType) -> IntervalModel:
        intervals_dict_vh = IntervalHandler.get_intervals_dict_vh()
        if not interval in intervals_dict_vh:
            raise Exception(f"Interval {interval.value} doesn't exist")
        else:
            return intervals_dict_vh[interval]

    def get_intervals(self, importances: list[Importance] = None) -> list:
        return [
            interval_mdl.interval
            for interval_mdl in self.get_interval_models(importances)
        ]

    def get_interval_model(self, interval: IntervalType) -> IntervalModel:
        for interval_mdl in self.__interval_mdls:
            if interval_mdl.interval == interval:
                return interval_mdl

        raise Exception(
            f"Interval {interval.value} doesn't exist for {self.get_exchange_id()}"
        )

    def get_interval_models(
        self, importances: list[Importance] = None
    ) -> list[IntervalModel]:
        interval_mdls = []

        for interval_mdl in self.__interval_mdls:
            if importances and interval_mdl.importance not in importances:
                continue
            else:
                interval_mdls.append(interval_mdl)

        return interval_mdls


class SymbolHandler(BaseOnExchangeHandler):
    def __init__(self, exchange_handler: ExchangeHandler = None):
        super().__init__(exchange_handler)
        self._buffer_symbols: BufferBaseHandler = BufferBaseHandler()
        self._buffer_timeframes: BufferSingleDictionary = BufferSingleDictionary()

    def is_valid_symbol(self, symbol: str) -> bool:
        return symbol in self.get_symbols()

    def is_trading_available(self, interval: str, symbol: str) -> bool:
        timeframe = {}
        symbol_mdl = self.get_symbol(symbol=symbol)
        trading_time = symbol_mdl.trading_time
        if self._buffer_timeframes.is_data_in_buffer(trading_time):
            timeframe = self._buffer_timeframes.get_buffer(trading_time)
        else:
            # Send a request to an API to get symbols
            timeframe = self._exchange_handler.calculate_trading_timeframe(trading_time)
            # Set fetched symbols to the buffer
            self._buffer_timeframes.set_buffer(key=trading_time, data=timeframe)

        return self._exchange_handler.is_trading_available(
            interval=interval, trading_timeframes=timeframe
        )

    def get_symbol(self, symbol: str) -> SymbolModel:
        symbol_model = self.get_symbols()[symbol]
        return symbol_model

    def get_symbols(self) -> dict[SymbolModel]:
        symbols = {}

        # If buffer data is existing -> get symbols from the buffer
        if self._buffer_symbols.is_data_in_buffer():
            #  Get symbols from the buffer
            symbols = self._buffer_symbols.get_buffer()
        else:
            # Send a request to an API to get symbols
            symbols = self._exchange_handler.get_symbols()
            # Set fetched symbols to the buffer
            self._buffer_symbols.set_buffer(symbols)

        return symbols

    def get_symbol_list(self, **kwargs) -> list:
        symbol_list = []
        symbol_models = self.get_symbols()

        symbol = kwargs.get(Const.DB_SYMBOL, None)
        name = kwargs.get(Const.DB_NAME, None)
        status = kwargs.get(Const.DB_STATUS, None)
        type = kwargs.get(Const.DB_TYPE, None)
        currency = kwargs.get(Const.DB_CURRENCY, None)

        for symbol_model in symbol_models.values():
            if symbol and symbol != symbol_model.symbol:
                continue
            if name and name.lower() not in symbol_model.name.lower():
                continue
            if status and status != symbol_model.status:
                continue
            if type and type != symbol_model.type:
                continue
            if currency and currency != symbol_model.currency:
                continue
            else:
                symbol_list.append(symbol_model)

        return sorted(symbol_list, key=lambda x: x.symbol)

    def get_symbol_id_list(self, **kwargs) -> list:
        symbol_id_list = []
        symbol_list = self.get_symbol_list(**kwargs)

        symbol_id_list = [element[Const.DB_SYMBOL] for element in symbol_list]

        return symbol_id_list


class HistoryDataHandler(BaseOnExchangeHandler):
    def __init__(self, exchange_handler: ExchangeHandler = None):
        super().__init__(exchange_handler)
        self.__buffer_inst = BufferHistoryDataHandler()

    def get_history_data(
        self, history_data_param: SymbolIntervalLimitModel, **kwargs
    ) -> HistoryData:
        history_data_inst = None

        symbol = history_data_param.symbol
        interval = history_data_param.interval
        limit = history_data_param.limit
        is_buffer = kwargs.get(Const.FLD_IS_BUFFER, True)
        closed_bar = kwargs.get(Const.FLD_CLOSED_BAR, False)

        # Get endDatetime for History Data
        end_datetime = self._exchange_handler.get_end_datetime(
            interval=interval, closed_bar=closed_bar
        )

        # If it reruires to read from the buffer and buffer data is valid -> get hidtory data from the buffer
        if is_buffer and self.__buffer_inst.validate_data_in_buffer(
            symbol=symbol, interval=interval, limit=limit, end_datetime=end_datetime
        ):
            # Get history data from the buffer for the parameters
            history_data_inst = self.__buffer_inst.get_buffer(
                history_data_param=history_data_param, end_datetime=end_datetime
            )

        # If history data from the buffer doesn't exist
        if not history_data_inst:
            # Send a request to an API to get history data
            history_data_inst = self._exchange_handler.get_history_data(
                history_data_param=history_data_param,
                closed_bar=closed_bar,
            )
            # Set fetched history data to the buffer
            self.__buffer_inst.set_buffer(history_data_inst)

        return history_data_inst


class BufferRuntimeHandlers:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__symbol_handler = {}
            class_.__history_data_handler = {}
            class_.__interval_handler = {}
            class_.__user_handler = UserHandler()
        return class_._instance

    def get_symbol_handler(
        self, trader_id: str = None, user_id: str = None
    ) -> SymbolHandler:
        exchange_handler = ExchangeHandler.get_handler(
            trader_id=trader_id, user_id=user_id
        )
        trader_id = exchange_handler.get_trader_id()
        if not trader_id in self.__symbol_handler:
            symbol_handler = SymbolHandler(exchange_handler=exchange_handler)
            self.__symbol_handler[trader_id] = symbol_handler

        return self.__symbol_handler[trader_id]

    def get_history_data_handler(
        self, trader_id: str = None, user_id: str = None
    ) -> HistoryDataHandler:
        exchange_handler = ExchangeHandler.get_handler(
            trader_id=trader_id, user_id=user_id
        )
        trader_id = exchange_handler.get_trader_id()
        if not trader_id in self.__history_data_handler:
            history_data_handler = HistoryDataHandler(exchange_handler=exchange_handler)
            self.__history_data_handler[trader_id] = history_data_handler

        return self.__history_data_handler[trader_id]

    def get_user_handler(self):
        return self.__user_handler

    def get_interval_handler(
        self, trader_id: str = None, user_id: str = None
    ) -> IntervalHandler:
        exchange_handler = ExchangeHandler.get_handler(
            trader_id=trader_id, user_id=user_id
        )
        trader_id = exchange_handler.get_trader_id()
        if not trader_id in self.__interval_handler:
            interval_handler = IntervalHandler(exchange_handler=exchange_handler)
            self.__interval_handler[trader_id] = interval_handler

        return self.__interval_handler[trader_id]

    def clear_buffer(self):
        self.__symbol_handler = {}
        self.__history_data_handler = {}
        self.__interval_handler = {}
        self.__user_handler.get_buffer().clear_buffer()


########################### Legacy code ####################################


class OrderStatus(Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(Enum):
    GTC = "GTC"


class NewOrderResponseType(Enum):
    ACK = "ACK"
    RESULT = "RESULT"
    FULL = "FULL"


class StockExchangeHandler:
    def __init__(self):
        self.__buffer_inst = RuntimeBufferStore()
        self.__api_inst = None

        stock_exchange_id = config.get_stock_exchange_id()

        if not stock_exchange_id:
            raise Exception(f"STOCK_EXCHANGE: Id is not configured")

        if stock_exchange_id == Const.STOCK_EXCH_CURRENCY_COM:
            self.__api_inst = CurrencyComApi()
        elif stock_exchange_id == Const.STOCK_EXCH_LOCAL_CURRENCY_COM:
            self.__api_inst = LocalCurrencyComApi()
        else:
            raise Exception(
                f"STOCK_EXCHANGE: {stock_exchange_id} implementation is missed"
            )

    def getStockExchangeName(self) -> str:
        return self.__api_inst.getStockExchangeName()

    def getHistoryData(
        self,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool = True,
        closed_bars: bool = False,
        **kwargs,
    ) -> HistoryData:
        history_data_inst = None

        # Get endDatetime for History Data
        endDatetime = self.getEndDatetime(interval=interval, closed_bars=closed_bars)

        # If it reruires to read from the buffer and buffer data is valid -> get hidtory data from the buffer
        if from_buffer and self.__buffer_inst.validateHistoryDataInBuffer(
            symbol=symbol, interval=interval, limit=limit, endDatetime=endDatetime
        ):
            # Get history data from the buffer for the parameters
            history_data_inst = self.__buffer_inst.getHistoryDataFromBuffer(
                symbol=symbol, interval=interval, limit=limit, endDatetime=endDatetime
            )

        # If history data from the buffer doesn't exist
        if not history_data_inst:
            # Send a request to an API to get history data
            history_data_inst = self.__api_inst.getHistoryData(
                symbol=symbol,
                interval=interval,
                limit=limit,
                closed_bars=closed_bars,
                **kwargs,
            )
            # Set fetched history data to the buffer
            self.__buffer_inst.setHistoryDataToBuffer(history_data_inst)

        return history_data_inst

    def getSymbols(self, from_buffer: bool) -> dict[Symbol]:
        symbols = {}

        # If it reruires to read data from the buffer and buffer data is existing -> get symbols from the buffer
        if from_buffer and self.__buffer_inst.checkSymbolsInBuffer():
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
        return self.__api_inst.getEndDatetime(
            interval=interval, original_datetime=original_datetime, **kwargs
        )

    def is_trading_open(self, interval: str, trading_time: str) -> bool:
        if self.__buffer_inst.checkTimeframeInBuffer(trading_time):
            timeframes = self.__buffer_inst.getTimeFrameFromBuffer(trading_time)
        else:
            timeframes = self.__api_inst.get_trading_timeframes(trading_time)
            self.__buffer_inst.setTimeFrameToBuffer(trading_time, timeframes)

        return self.__api_inst.is_trading_open(
            interval=interval, trading_timeframes=timeframes
        )


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

    def getHistoryData(
        self, symbol: str, interval: str, limit: int, **kwargs
    ) -> HistoryData:
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

    def getEndDatetime(
        self, interval: str, original_datetime: datetime, **kwargs
    ) -> datetime:
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

    def getStockExchangeName(self) -> str:
        """
        Returns the name of the stock exchange.
        """

        return Const.STOCK_EXCH_CURRENCY_COM

    def getApiEndpoint(self) -> str:
        """
        Returns the API endpoint.
        """

        return "https://api-adapter.backend.currency.com/api/v2/"

    def getHistoryData(
        self, symbol: str, interval: str, limit: int, **kwargs
    ) -> HistoryData:
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
        url_params = {
            Const.PARAM_SYMBOL: symbol,
            Const.INTERVAL: interval_api,
            Const.LIMIT: limit,
        }

        # If closed_bars indicator is True -> calculated endTime for the API
        if closed_bars:
            url_params[Const.API_FLD_END_TIME] = self.getOffseUnixTimeMsByInterval(
                interval_api
            )
            url_params[Const.LIMIT] = url_params[Const.LIMIT] + 1

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - getHistoryData({url_params})"
            )

        json_api_response = self.get_api_klines(url_params)

        # Convert API response to the DataFrame with columns: 'Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'
        df = self.convertResponseToDataFrame(json_api_response)

        # Create an instance of HistoryData
        obj_history_data = HistoryData(
            symbol=symbol, interval=interval, limit=limit, dataFrame=df
        )

        return obj_history_data

    def get_api_klines(self, url_params: dict) -> dict:
        response = requests.get(f"{self.getApiEndpoint()}/klines", params=url_params)

        if response.status_code == 200:
            # Get data from API
            return json.loads(response.text)

        else:
            logger.error(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - get_api_klines -> {response.text}"
            )
            raise Exception(response.text)

    def getSymbols(self) -> dict[Symbol]:
        """
        Retrieves a list of symbols available on the stock exchange.
        Returns:
            dict[Symbol]: A dictionary of Symbol objects representing the available symbols. The format is {"<symbol_code>": <Symbol obhject>}
        """

        symbols = {}

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"STOCK_EXCHANGE: {self.getStockExchangeName()} - getSymbols()")

        # Get API data
        response = requests.get(f"{self.getApiEndpoint()}/exchangeInfo")

        if response.status_code == 200:
            json_api_response = json.loads(response.text)

            # Create an instance of Symbol and add to the list
            for row in json_api_response["symbols"]:
                if (
                    row["quoteAssetId"] == "USD"
                    and row["assetType"] in ["CRYPTOCURRENCY", "EQUITY", "COMMODITY"]
                    and "REGULAR" in row["marketModes"]
                ):
                    status_converted = (
                        Const.STATUS_OPEN
                        if row[Const.STATUS] == "TRADING"
                        else Const.STATUS_CLOSE
                    )

                    symbol_inst = Symbol(
                        code=row[Const.PARAM_SYMBOL],
                        name=row[Const.NAME],
                        status=status_converted,
                        tradingTime=row["tradingHours"],
                        type=row["assetType"],
                    )
                    symbols[symbol_inst.code] = symbol_inst
                else:
                    continue

            return symbols

        else:
            logger.error(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - getSymbols -> {response.text}"
            )
            raise Exception(response.text)

    def get_intervals(self) -> list:
        """
        Returns a list of intervals available for retrieving historical data.
        Each interval is represented as a dictionary with keys: 'interval', 'name', 'order', and 'importance'.
        """

        intervals = [
            {
                "interval": self.TA_API_INTERVAL_5M,
                "name": "5 minutes",
                "order": 10,
                "importance": Const.IMPORTANCE_LOW,
            },
            {
                "interval": self.TA_API_INTERVAL_15M,
                "name": "15 minutes",
                "order": 20,
                "importance": Const.IMPORTANCE_LOW,
            },
            {
                "interval": self.TA_API_INTERVAL_30M,
                "name": "30 minutes",
                "order": 30,
                "importance": Const.IMPORTANCE_MEDIUM,
            },
            {
                "interval": self.TA_API_INTERVAL_1H,
                "name": "1 hour",
                "order": 40,
                "importance": Const.IMPORTANCE_MEDIUM,
            },
            {
                "interval": self.TA_API_INTERVAL_4H,
                "name": "4 hours",
                "order": 50,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": self.TA_API_INTERVAL_1D,
                "name": "1 day",
                "order": 60,
                "importance": Const.IMPORTANCE_HIGH,
            },
            {
                "interval": self.TA_API_INTERVAL_1WK,
                "name": "1 week",
                "order": 70,
                "importance": Const.IMPORTANCE_HIGH,
            },
        ]

        return intervals

        # def get_accounts(self) -> dict:
        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - get_accounts()"
        #         )

        #     query_params = self.__sign_query_params(
        #         {
        #             "recvWindow": 5000,
        #             "timestamp": int(time.time() * 1000),
        #         }
        #     )

        #     # Get API data
        #     response = requests.get(
        #         f"{self.getApiEndpoint()}/account",
        #         params=query_params,
        #         headers=self.__get_header_api_key(),
        #     )

        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - {response.url}"
        #         )

        #     # Check the response status code
        #     if response.status_code == 200:
        #         data = response.json()
        #         return data
        #     else:
        #         raise Exception(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - Failed to retrieve account information: {response.status_code} - {response.text}"
        #         )

        # def get_open_orders(self, symbol: str = None) -> dict:
        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - get_open_orders()"
        #         )

        #     query_params = {
        #         "recvWindow": 10000,
        #         "timestamp": int(time.time() * 1000),
        #     }

        #     if symbol:
        #         query_params[Const.API_FLD_SYMBOL] = symbol

        #     query_params = self.__sign_query_params(query_params)

        #     # Get API data
        #     response = requests.get(
        #         f"{self.getApiEndpoint()}/openOrders",
        #         params=query_params,
        #         headers=self.__get_header_api_key(),
        #     )

        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - {response.url}"
        #         )

        #     # Check the response status code
        #     if response.status_code == 200:
        #         data = response.json()
        #         return data
        #     else:
        #         raise Exception(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - Failed to retrieve open orders: {response.status_code} - {response.text}"
        #         )

        # def get_my_trades(self, symbol: str) -> dict:
        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - get_my_trades()"
        #         )

        #     query_params = {
        #         "recvWindow": 10000,
        #         "symbol": symbol,
        #         "timestamp": int(time.time() * 1000),
        #     }

        #     query_params = self.__sign_query_params(query_params)

        #     # Get API data
        #     response = requests.get(
        #         f"{self.getApiEndpoint()}/myTrades",
        #         params=query_params,
        #         headers=self.__get_header_api_key(),
        #     )

        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - {response.url}"
        #         )

        #     # Check the response status code
        #     if response.status_code == 200:
        #         data = response.json()
        #         return data
        #     else:
        #         raise Exception(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - Failed to retrieve my trades: {response.status_code} - {response.text}"
        #         )

        # def get_trading_positions(self) -> list:
        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - get_trading_positions()"
        #         )

        #     query_params = self.__sign_query_params(
        #         {
        #             "recvWindow": 5000,
        #             "timestamp": int(time.time() * 1000),
        #         }
        #     )

        #     # Get API data
        #     response = requests.get(
        #         f"{self.getApiEndpoint()}/tradingPositions",
        #         params=query_params,
        #         headers=self.__get_header_api_key(),
        #     )

        #     if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #         logger.info(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - {response.url}"
        #         )

        #     # Check the response status code
        #     if response.status_code == 200:
        #         data = response.json()
        #         return data
        #     else:
        #         raise Exception(
        #             f"STOCK_EXCHANGE: {self.getStockExchangeName()} - Failed to retrieve trading positions: {response.status_code} - {response.text}"
        #         )

    def create_order(self) -> dict:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - create_order()"
            )

        query_params = self.__sign_query_params(
            {
                # "recvWindow": 5000,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "accountId": "167893441795404062",
                # "expireTimestamp": int(time.time() * 1000),
                "guaranteedStopLoss": False,
                # "leverage": 2,
                "newOrderRespType": "FULL",
                # price=price,
                "quantity": 2,
                "side": "BUY",
                # "stopLoss": 65.0,
                "symbol": "LTC/USD_LEVERAGE",
                # "takeProfit": 68.3,
                "type": "MARKET",
            }
        )

        # Get API data
        response = requests.post(
            f"{self.getApiEndpoint()}/order",
            params=query_params,
            headers=self.__get_header_api_key(),
        )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - {response.url}"
            )

        # Check the response status code
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            raise Exception(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - Failed to create an order: {response.status_code} - {response.text}"
            )

    @staticmethod
    def get_24h_price_change(symbol=None):
        """
        24-hour rolling window price change statistics. Careful when accessing
        this with no symbol.
        If the symbol is not sent, tickers for all symbols will be returned in
        an array.
        :param symbol:
        :return: dict object

        Response:
        {
          "symbol": "LTC/USD",
          "priceChange": "0.88",
          "priceChangePercent": "1.49",
          "weightedAvgPrice": "59.29",
          "prevClosePrice": "58.37",
          "lastPrice": "59.25",
          "lastQty": "220.0",
          "bidPrice": "59.25",
          "askPrice": "59.32",
          "openPrice": "58.37",
          "highPrice": "61.39",
          "lowPrice": "58.37",
          "volume": "22632",
          "quoteVolume": "440.0",
          "openTime": 1580169600000,
          "closeTime": 1580205307222,
          "firstId": 0,
          "lastId": 0,
          "count": 0
        }

        OR

        {
          "symbol": "LTC/USD",
          "priceChange": null,
          "priceChangePercent": null,
          "weightedAvgPrice": "59.29",
          "prevClosePrice": null,
          "lastPrice": "59.23",
          "lastQty": "220.0",
          "bidPrice": "59.23",
          "askPrice": "59.35",
          "openPrice": null,
          "highPrice": null,
          "lowPrice": null,
          "volume": null,
          "quoteVolume": "432.18",
          "openTime": 0,
          "closeTime": 0,
          "firstId": 0,
          "lastId": 0,
          "count": 0
        }
        """
        return requests.get(
            CurrencyComApi.PRICE_CHANGE_24H_ENDPOINT,
            params={"symbol": symbol} if symbol else {},
        )

    @staticmethod
    def get_server_time():
        """
        Test connectivity to the API and get the current server time.

        :return: dict object
        Response:
        {
          "serverTime": 1499827319559
        }
        """
        return requests.get(CurrencyComApi.SERVER_TIME_ENDPOINT)

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
        return self._get(
            CurrencyComApi.ACCOUNT_INFORMATION_ENDPOINT,
            showZeroBalance=show_zero_balance,
            recvWindow=recv_window,
        )

    def get_account_trade_list(
        self,
        symbol,
        start_time: datetime = None,
        end_time: datetime = None,
        limit=500,
        recv_window=None,
    ):
        """
        Get trades for a specific account and symbol.

        :param symbol: Symbol - In order to receive orders within an ‘exchange’
        trading mode ‘symbol’ parameter value from the exchangeInfo endpoint:
        ‘BTC%2FUSD’.
        In order to mention the right symbolLeverage it should be checked with
        the ‘symbol’ parameter value from the exchangeInfo endpoint. In case
        ‘symbol’ has currencies in its name then the following format should be
        used: ‘BTC%2FUSD_LEVERAGE’. In case ‘symbol’ has only an asset name
        then for the leverage trading mode the following format is correct:
         ‘Oil%20-%20Brent.’
        :param start_time:
        :param end_time:
        :param limit: 	Default Value: 500; Max Value: 1000.
        :param recv_window: The value cannot be greater than 60000.
        Default value : 5000
        :return: dict object
        Response:
        [
          {
            "symbol": "BTC/USD",
            "orderId": "100234",
            "orderListId": -1,
            "price": "4.00000100",
            "qty": "12.00000000",
            "quoteQty": "48.000012",
            "commission": "10.10000000",
            "commissionAsset": "BTC",
            "time": 1499865549590,
            "isBuyer": true,
            "isMaker": false
          }
        ]
        """
        self._validate_limit(limit)
        self._validate_recv_window(recv_window)

        params = {"symbol": symbol, "limit": limit, "recvWindow": recv_window}

        if start_time:
            params["startTime"] = self.getUnixTimeMsByDatetime(start_time)

        if end_time:
            params["endTime"] = self.getUnixTimeMsByDatetime(end_time)

        return self._get(CurrencyComApi.ACCOUNT_TRADE_LIST_ENDPOINT, **params)

    # Orders
    def get_open_orders(self, symbol=None, recv_window=None):
        """
        Get all open orders on a symbol. Careful when accessing this with no
        symbol.
        If the symbol is not sent, orders for all symbols will be returned in
        an array.

        :param symbol: Symbol - In order to receive orders within an ‘exchange’
        trading mode ‘symbol’ parameter value from the exchangeInfo endpoint:
        ‘BTC%2FUSD’.
        In order to mention the right symbolLeverage it should be checked with
        the ‘symbol’ parameter value from the exchangeInfo endpoint. In case
        ‘symbol’ has currencies in its name then the following format should be
        used: ‘BTC%2FUSD_LEVERAGE’. In case ‘symbol’ has only an asset name
        then for the leverage trading mode the following format is correct:
         ‘Oil%20-%20Brent.’
        :param recv_window: The value cannot be greater than 60000.
        :return: dict object

        Response:
        [
          {
            "symbol": "LTC/BTC",
            "orderId": "1",
            "orderListId": -1,
            "clientOrderId": "myOrder1",
            "price": "0.1",
            "origQty": "1.0",
            "executedQty": "0.0",
            "cummulativeQuoteQty": "0.0",
            "status": "NEW",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY",
            "stopPrice": "0.0",
            "time": 1499827319559,
            "updateTime": 1499827319559,
            "isWorking": true,
            "origQuoteOrderQty": "0.000000"
          }
        ]
        """

        self._validate_recv_window(recv_window)

        return self._get(
            CurrencyComApi.CURRENT_OPEN_ORDERS_ENDPOINT,
            symbol=symbol,
            recvWindow=recv_window,
        )

    def new_order(
        self,
        symbol,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        account_id: str = None,
        expire_timestamp: datetime = None,
        guaranteed_stop_loss: bool = False,
        stop_loss: float = None,
        take_profit: float = None,
        leverage: int = None,
        price: float = None,
        new_order_resp_type: NewOrderResponseType = NewOrderResponseType.FULL,
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
            CurrencyComApi.ORDER_ENDPOINT,
            accountId=account_id,
            expireTimestamp=expire_timestamp_epoch,
            guaranteedStopLoss=guaranteed_stop_loss,
            leverage=leverage,
            newOrderRespType=new_order_resp_type.value,
            price=price,
            quantity=quantity,
            recvWindow=recv_window,
            side=side.value,
            stopLoss=stop_loss,
            symbol=symbol,
            takeProfit=take_profit,
            type=order_type.value,
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
            CurrencyComApi.ORDER_ENDPOINT,
            symbol=symbol,
            orderId=order_id,
            recvWindow=recv_window,
        )

    # Leverage
    def get_trading_positions(self, recv_window=None):
        self._validate_recv_window(recv_window)
        return self._get(
            CurrencyComApi.TRADING_POSITIONS_ENDPOINT, recvWindow=recv_window
        )

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
            CurrencyComApi.UPDATE_TRADING_POSITION_ENDPOINT,
            positionId=position_id,
            guaranteedStopLoss=guaranteed_stop_loss,
            stopLoss=stop_loss,
            takeProfit=take_profit,
        )

    def close_trading_position(self, position_id, recv_window=None):
        """
        Close an active leverage trade.

        :param position_id:
        :param recv_window: The value cannot be greater than 60000.
        :return: dict object

        Response example:
        Example:
        {
            "request": [
                {
                "id": 242057,
                "accountId": 2376109060084932,
                "instrumentId": "45076691096786116",
                "rqType": "ORDER_NEW",
                "state": "PROCESSED",
                "createdTimestamp": 1587031306969
                }
            ]
        }
        """
        self._validate_recv_window(recv_window)

        return self._post(
            CurrencyComApi.CLOSE_TRADING_POSITION_ENDPOINT,
            positionId=position_id,
            recvWindow=recv_window,
        )

    def getEndDatetime(
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
        if Const.CLOSED_BARS in kwargs:
            closed_bars = kwargs[Const.CLOSED_BARS]
        else:
            closed_bars = False

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

            if closed_bars:
                delta_minutes += offset_value

            offset_date_time = original_datetime - timedelta(minutes=delta_minutes)

            offset_date_time = offset_date_time.replace(second=0, microsecond=0)

        elif interval == self.TA_API_INTERVAL_1H:
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

        elif interval == self.TA_API_INTERVAL_4H:
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

        elif interval == self.TA_API_INTERVAL_1D:
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

        elif interval == self.TA_API_INTERVAL_1WK:
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

        # if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        #     other_attributes = ", ".join(
        #         f"{key}={value}" for key, value in kwargs.items()
        #     )

        #     logger.info(
        #         f"STOCK_EXCHANGE: {self.getStockExchangeName()} - getEndDatetime(interval: {interval}, {other_attributes}) -> Original: {original_datetime} | Closed: {offset_date_time}"
        #     )

        return offset_date_time

    ########################### Private methods - refactor ###################

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
        offset_datetime = self.getEndDatetime(
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

    def get_trading_timeframes(self, trading_time: str) -> dict:
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

    def is_trading_open(self, interval: str, trading_timeframes: dict) -> bool:
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

    def _validate_recv_window(self, recv_window):
        max_value = CurrencyComApi.RECV_WINDOW_MAX_LIMIT
        if recv_window and recv_window > max_value:
            raise ValueError(
                "recvValue cannot be greater than {}. Got {}.".format(
                    max_value, recv_window
                )
            )

    @staticmethod
    def _validate_new_order_resp_type(
        new_order_resp_type: NewOrderResponseType, order_type: OrderType
    ):
        if new_order_resp_type == NewOrderResponseType.ACK:
            raise ValueError("ACK mode no more available")

        if order_type == OrderType.MARKET:
            if new_order_resp_type not in [
                NewOrderResponseType.RESULT,
                NewOrderResponseType.FULL,
            ]:
                raise ValueError(
                    "new_order_resp_type for MARKET order can be only RESULT"
                    f"or FULL. Got {new_order_resp_type.value}"
                )
        elif order_type == OrderType.LIMIT:
            if new_order_resp_type != NewOrderResponseType.RESULT:
                raise ValueError(
                    "new_order_resp_type for LIMIT order can be only RESULT."
                    f" Got {new_order_resp_type.value}"
                )

    def _get_params_with_signature(self, **kwargs):
        api_secret = config.get_env_value("CURRENCY_COM_API_SECRET")
        if not api_secret:
            raise Exception(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - API secret is not maintained"
            )

        t = self.getUnixTimeMsByDatetime(datetime.now())
        kwargs["timestamp"] = t
        # pylint: disable=no-member
        body = RequestEncodingMixin._encode_params(kwargs)
        sign = hmac.new(
            bytes(api_secret, "utf-8"), bytes(body, "utf-8"), hashlib.sha256
        ).hexdigest()

        return {"signature": sign, **kwargs}

    def _get_header(self, **kwargs):
        api_key = config.get_env_value("CURRENCY_COM_API_KEY")
        if not api_key:
            raise Exception(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - API key is not maintained"
            )

        return {**kwargs, CurrencyComApi.HEADER_API_KEY_NAME: api_key}

    def _get(self, path, **kwargs):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"STOCK_EXCHANGE: {self.getStockExchangeName()} - GET /{path}")

        url = self._get_url(path)

        response = requests.get(
            url,
            params=self._get_params_with_signature(**kwargs),
            headers=self._get_header(),
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - GET /{path} -> {response.status_code}: {response.text}"
            )

    def _post(self, path, **kwargs):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"STOCK_EXCHANGE: {self.getStockExchangeName()} - POST /{path}")

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
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - POST /{path} -> {response.status_code}: {response.text}"
            )

    def _delete(self, path, **kwargs):
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - DELETE /{path}"
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
                f"STOCK_EXCHANGE: {self.getStockExchangeName()} - DELETE /{path} -> {response.status_code}: {response.text}"
            )

    def _get_url(self, path: str) -> str:
        return self.getApiEndpoint() + path


class DemoCurrencyComApi(CurrencyComApi):
    def getStockExchangeName(self) -> str:
        return Const.STOCK_EXCH_DEMO_CURRENCY_COM

    def getApiEndpoint(self) -> str:
        return "https://demo-api-adapter.backend.currency.com/api/v2/"


class LocalCurrencyComApi(CurrencyComApi):
    def write_symbols_to_local(self):
        api = CurrencyComApi()

        response = requests.get(f"{api.getApiEndpoint()}/exchangeInfo")

        file_path = self.__get_file_path("symbols")

        with open(file_path, "w") as writer:
            writer.write(response.text)

    def write_history_data_to_local(
        self, symbol: str, interval: str, limit: int
    ) -> bool:
        api = CurrencyComApi()

        url_params = {
            Const.PARAM_SYMBOL: symbol,
            Const.INTERVAL: interval,
            Const.LIMIT: limit,
        }

        response = api.get_api_klines(url_params)

        file_name = self.__get_file_name(symbol=symbol, interval=interval)
        file_path = self.__get_file_path(file_name)

        with open(file_path, "w") as writer:
            writer.write(json.dumps(response))

    def get_api_klines(self, url_params: dict) -> dict:
        file_name = self.__get_file_name(
            symbol=url_params[Const.PARAM_SYMBOL], interval=url_params[Const.INTERVAL]
        )
        file_path = self.__get_file_path(file_name)

        with open(file_path, "r") as reader:
            local_data = json.load(reader)

        index = -1 * int(url_params[Const.LIMIT])

        return local_data[index:]

    def getSymbols(self) -> dict[Symbol]:
        symbols = {}

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"STOCK_EXCHANGE: {self.getStockExchangeName()} - getSymbols()")

        file_path = self.__get_file_path("symbols")

        # Get API data from local
        with open(file_path, "r") as reader:
            json_api_response = json.load(reader)

        # json_api_response = json.loads(response)

        # Create an instance of Symbol and add to the list
        for row in json_api_response["symbols"]:
            if (
                row["quoteAssetId"] == "USD"
                and row["assetType"] in ["CRYPTOCURRENCY", "EQUITY", "COMMODITY"]
                and "REGULAR" in row["marketModes"]
            ):
                status_converted = (
                    Const.STATUS_OPEN
                    if row[Const.STATUS] == "TRADING"
                    else Const.STATUS_CLOSE
                )

                symbol_inst = Symbol(
                    code=row[Const.PARAM_SYMBOL],
                    name=row[Const.NAME],
                    status=status_converted,
                    tradingTime=row["tradingHours"],
                    type=row["assetType"],
                )
                symbols[symbol_inst.code] = symbol_inst
            else:
                continue

        return symbols

    def __get_file_name(self, symbol: str, interval: str) -> str:
        symbol = symbol.replace("/", "_")
        return f"history_data_{symbol}_{interval}"

    def __get_file_path(self, file_name: str) -> str:
        return r"{}\static\local\{}.json".format(os.getcwd(), file_name)


buffer_runtime_handler = BufferRuntimeHandlers()
