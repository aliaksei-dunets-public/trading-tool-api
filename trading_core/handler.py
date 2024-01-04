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
from .core import logger, config
from .api import (
    ExchangeApiBase,
    DzengiComApi,
    DemoDzengiComApi,
    ByBitComApi,
    DemoByBitComApi,
)
from .common import (
    Importance,
    ChannelType,
    AlertType,
    IntervalType,
    IntervalModel,
    HistoryDataParamModel,
    TraderStatus,
    OrderStatus,
    SessionStatus,
    ExchangeId,
    SymbolModel,
    HistoryDataModel,
    UserModel,
    ChannelModel,
    AlertModel,
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
    MongoAlert,
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

    def remove_from_buffer(self, key: str):
        self._buffer.pop(key)


class BufferHistoryDataHandler(BufferBaseHandler):
    def get_buffer(
        self, history_data_param: HistoryDataParamModel, **kwargs
    ) -> HistoryDataModel:
        symbol = history_data_param.symbol
        interval = history_data_param.interval
        limit = history_data_param.limit
        end_datetime = kwargs.get(Const.FLD_END_DATETIME)

        buffer_key = self._get_buffer_key(symbol=symbol, interval=interval)
        history_data_mdl_buffer: HistoryDataModel = self._buffer[buffer_key]
        df_buffer = history_data_mdl_buffer.data

        df_required = df_buffer[df_buffer.index <= end_datetime]

        if limit > len(df_required):
            return None

        df_required = df_required.tail(limit)

        history_data_required = HistoryDataModel(
            symbol=symbol, interval=interval, limit=limit, data=df_required
        )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: getHistoryData({history_data_param.model_dump()})"
            )

        return history_data_required

    def is_data_in_buffer(self, symbol: str, interval: str) -> bool:
        buffer_key = self._get_buffer_key(symbol=symbol, interval=interval)
        if buffer_key in self._buffer:
            return True
        else:
            return False

    def set_buffer(self, buffer: HistoryDataModel):
        if buffer:
            buffer_key = self._get_buffer_key(
                symbol=buffer.symbol,
                interval=buffer.interval,
            )
            self._buffer[buffer_key] = buffer

    def validate_data_in_buffer(
        self, symbol: str, interval: str, limit: int, end_datetime: datetime
    ) -> bool:
        if self.is_data_in_buffer(symbol=symbol, interval=interval):
            buffer_key = self._get_buffer_key(symbol=symbol, interval=interval)
            history_data_mdl_buffer: HistoryDataModel = self._buffer[buffer_key]
            if (
                limit <= history_data_mdl_buffer.limit
                and end_datetime
                and end_datetime <= history_data_mdl_buffer.end_date_time
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

                except Exception as error:
                    logger.error(f"Trader {id} status check is failed - {error}")
                    trader_status = TraderStatus.PUBLIC
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

        MongoAlert().delete_many(query={"trader_id": id})

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


class ChannelHandler:
    @staticmethod
    def create_channel(channel: ChannelModel):
        id = MongoChannel().insert_one(channel.to_mongodb_doc())
        return ChannelHandler.get_channel(id)

    @staticmethod
    def update_channel(id: str, query: dict):
        return MongoChannel().update_one(id=id, query=query)

    @staticmethod
    def delete_channel(id: str):
        # Before deletion of the channel, removes all alerts
        MongoAlert().delete_many(query={"channel_id": id})
        return MongoChannel().delete_one(id=id)

    @staticmethod
    def get_channel(id: str) -> ChannelModel:
        entry = MongoChannel().get_one(id)
        if not entry:
            raise Exception(f"Channel {id} doesn't exists")
        return ChannelModel(**entry)

    @staticmethod
    def get_channels_by_email(user_email: str):
        user_id = None
        user_mdl = buffer_runtime_handler.get_user_handler().get_user_by_email(
            email=user_email
        )
        if not user_mdl.technical_user:
            user_id = user_mdl.id

        return ChannelHandler.get_channels(user_id=user_id)

    @staticmethod
    def get_channels(
        user_id: str = None,
        name: str = None,
        type: ChannelType = None,
        channel: str = None,
    ):
        query = {}

        if user_id:
            query[Const.DB_USER_ID] = user_id
        if name:
            query[Const.DB_NAME] = name
        if type:
            query[Const.DB_TYPE] = type
        if channel:
            query[Const.DB_CHANNEL] = channel

        entries_db = MongoChannel().get_many(query)
        result = [ChannelModel(**entry) for entry in entries_db]

        return result


class AlertHandler:
    @staticmethod
    def create_alert(alert: AlertModel):
        id = MongoAlert().insert_one(alert.to_mongodb_doc())
        return AlertHandler.get_alert(id)

    @staticmethod
    def update_alert(id: str, query: dict):
        return MongoAlert().update_one(id=id, query=query)

    @staticmethod
    def delete_alert(id: str):
        return MongoAlert().delete_one(id=id)

    @staticmethod
    def get_alert(id: str) -> AlertModel:
        entry = MongoAlert().get_one(id)
        if not entry:
            raise Exception(f"Alert {id} doesn't exists")
        return AlertModel(**entry)

    @staticmethod
    def get_alerts_by_email(user_email: str):
        user_id = None
        user_mdl = buffer_runtime_handler.get_user_handler().get_user_by_email(
            email=user_email
        )
        if not user_mdl.technical_user:
            user_id = user_mdl.id

        return AlertHandler.get_alerts(user_id=user_id)

    @staticmethod
    def get_alerts(
        user_id: str = None,
        trader_id: str = None,
        channel_ids: list = None,
        type: AlertType = None,
        symbol: str = None,
        interval: str = None,
        strategy: str = None,
    ):
        query = {}

        if user_id:
            query[Const.DB_USER_ID] = user_id
        if trader_id:
            query[Const.DB_TRADER_ID] = trader_id
        if channel_ids:
            query[Const.DB_CHANNEL_ID] = {"$in": channel_ids}
        if type:
            query[Const.DB_TYPE] = type
        if symbol:
            query["symbols"] = symbol
        if interval:
            query["intervals"] = interval
        if strategy:
            query["strategies"] = strategy

        entries_db = MongoAlert().get_many(query)
        result = [AlertModel(**entry) for entry in entries_db]

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
        user_id = None
        user_mdl = buffer_runtime_handler.get_user_handler().get_user_by_email(
            email=user_email
        )
        if not user_mdl.technical_user:
            user_id = user_mdl.id

        return SessionHandler.get_sessions(user_id=user_id)

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
        elif self.__trader_model.exchange_id == ExchangeId.bybit_com:
            self._api = ByBitComApi(self.__trader_model)
        elif self.__trader_model.exchange_id == ExchangeId.demo_bybit_com:
            self._api = DemoByBitComApi(self.__trader_model)
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

    def get_symbols(self, **kwargs) -> dict[SymbolModel]:
        # Send a request to an API to get symbols
        return self._api.get_symbols()

    def get_history_data(
        self, history_data_param: HistoryDataParamModel, **kwargs
    ) -> HistoryDataModel:
        return self._api.get_history_data(history_data_param, **kwargs)

    def get_open_orders(self, symbol: str) -> list[LeverageModel]:
        return self._api.get_open_orders(
            symbol=symbol,
        )

    def get_open_leverages(self, symbol: str, limit: int = 1) -> list[LeverageModel]:
        return self._api.get_open_leverages(symbol=symbol, limit=limit)

    def get_open_position(
        self,
        symbol: str,
        order_id: str = None,
        position_id: str = None,
    ) -> LeverageModel:
        return self._api.get_open_position(
            symbol=symbol, order_id=order_id, position_id=position_id
        )

    def get_close_leverages(
        self,
        symbol: str,
        limit: int = 1,
    ):
        return self._api.get_close_leverages(symbol=symbol, limit=limit)

    def get_close_position(
        self,
        symbol: str,
        order_id: str = None,
        position_id: str = None,
    ) -> LeverageModel:
        return self._api.get_close_position(
            symbol=symbol, order_id=order_id, position_id=position_id
        )

    def get_position(
        self,
        symbol: str,
        order_id: str = None,
        position_id: str = None,
    ) -> LeverageModel:
        return self._api.get_position(
            symbol=symbol, order_id=order_id, position_id=position_id
        )

    def create_order(self, position_mdl: OrderModel):
        return self._api.create_order(position_mdl)

    def create_leverage(self, position_mdl: LeverageModel) -> LeverageModel:
        return self._api.create_leverage(position_mdl)

    def close_order(self, position_id: str) -> OrderModel:
        return self._api.close_order(position_id)

    def close_leverage(
        self, symbol: str, order_id: str = None, position_id: str = None
    ) -> LeverageModel:
        return self._api.close_leverage(
            symbol=symbol, order_id=order_id, position_id=position_id
        )

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

        if trading_time == "":
            return True

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
        # currency = kwargs.get(Const.DB_CURRENCY, None)

        for symbol_model in symbol_models.values():
            if symbol and symbol != symbol_model.symbol:
                continue
            if name and name.lower() not in symbol_model.name.lower():
                continue
            if status and status != symbol_model.status:
                continue
            if type and type != symbol_model.type:
                continue
            # if currency and currency != symbol_model.currency:
            #     continue
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
        self, param: HistoryDataParamModel, **kwargs
    ) -> HistoryDataModel:
        history_data_mdl = None

        symbol = param.symbol
        interval = param.interval
        limit = param.limit
        is_buffer = param.from_buffer
        closed_bars = param.closed_bars

        # If Data is in buffer for Symbol and Interval
        if self.__buffer_inst.is_data_in_buffer(symbol=symbol, interval=interval):
            # Get endDatetime for History Data
            end_datetime = self._exchange_handler.get_end_datetime(
                interval=interval, closed_bars=closed_bars
            )

            # If it reruires to read from the buffer and buffer data is valid -> get hidtory data from the buffer
            if is_buffer and self.__buffer_inst.validate_data_in_buffer(
                symbol=symbol, interval=interval, limit=limit, end_datetime=end_datetime
            ):
                # Get history data from the buffer for the parameters
                history_data_mdl = self.__buffer_inst.get_buffer(
                    history_data_param=param, end_datetime=end_datetime
                )

        # If history data from the buffer doesn't exist
        if not history_data_mdl:
            # Send a request to an API to get history data
            history_data_mdl = self._exchange_handler.get_history_data(
                history_data_param=param,
                closed_bar=closed_bars,
            )
            # Set fetched history data to the buffer
            self.__buffer_inst.set_buffer(history_data_mdl)

        return history_data_mdl


class BufferRuntimeHandlers:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__symbol_handler = {}
            class_.__history_data_handler = {}
            class_.__signal_handler = BufferSingleDictionary()
            class_.__interval_handler = {}
            class_.__user_handler = UserHandler()
            class_.__job_handler = BufferSingleDictionary()
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

    def get_signal_handler(self) -> BufferSingleDictionary:
        return self.__signal_handler

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

    def get_job_handler(self):
        return self.__job_handler

    def clear_buffer(self):
        self.__symbol_handler = {}
        self.__history_data_handler = {}
        self.__signal_handler.clear_buffer()
        self.__interval_handler = {}
        self.__user_handler.get_buffer().clear_buffer()


buffer_runtime_handler = BufferRuntimeHandlers()
