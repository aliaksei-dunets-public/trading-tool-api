from enum import Enum
from bson import ObjectId
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field, validator
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import base64

from .core import config


class IntervalType(str, Enum):
    MIN_1 = "1m"  # 1
    MIN_3 = "3m"  # 3
    MIN_5 = "5m"  # 5
    MIN_15 = "15m"  # 15
    MIN_30 = "30m"  # 30
    HOUR_1 = "1h"  # 60
    HOUR_2 = "2h"  # 120
    HOUR_4 = "4h"  # 240
    HOUR_6 = "6h"  # 360
    HOUR_12 = "12h"  # 720
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1month"


class IndicatorType(str, Enum):
    CCI = "CCI"
    ATR = "ATR"
    CCI_ATR = "CCI_ATR"


class StrategyType(str, Enum):
    CCI_14_CROSS_100 = "CCI_14_CROSS_100"
    CCI_20_CROSS_100 = "CCI_20_CROSS_100"
    CCI_50_CROSS_0 = "CCI_50_CROSS_0"
    EMA_30_CROSS_EMA_100 = "EMA_30_CROSS_EMA_100"
    EMA_8_CROSS_EMA_30_FILTER_CCI_14 = "EMA_8_CROSS_EMA_30_FILTER_CCI_14"
    EMA_8_CROSS_EMA_30_FILTER_EMA_100 = "EMA_8_CROSS_EMA_30_FILTER_EMA_100"
    EMA_30_CROSS_EMA_100_FILTER_CCI_20 = "EMA_30_CROSS_EMA_100_FILTER_CCI_20"


class Importance(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SymbolType(str, Enum):
    leverage = "LEVERAGE"
    spot = "SPOT"


class PriceType(str, Enum):
    BID = "bid"
    ASK = "ask"


class ChannelType(str, Enum):
    EMAIL = "Email"
    TELEGRAM_BOT = "Telegram"


class AlertType(str, Enum):
    SIGNAL = "Signal"
    TRADING = "Trading"
    ERROR = "Error"


class TradingType(str, Enum):
    LEVERAGE = "LEVERAGE"
    SPOT = "SPOT"


class SessionType(str, Enum):
    TRADING = "Trading"
    SIMULATION = "Real Simulation"
    HISTORY = "History Simulation"


class OrderType(str, Enum):
    limit = "LIMIT"
    market = "MARKET"
    stop = "STOP"


class OrderSideType(str, Enum):
    buy = "BUY"
    sell = "SELL"


class OrderReason(str, Enum):
    STOP_LOSS = "Stop Loss"
    TAKE_PROFIT = "Take Profit"
    SIGNAL = "Signal"
    MANUAL = "Manual"
    CANCEL = "Cancel"
    TRADER = "Trader"
    NONE = ""


class TransactionType(str, Enum):
    ERROR = "Error"
    DB_CREATE_POSITION = "DB: Position Create"
    DB_UPDATE_POSITION = "DB: Position Update"
    DB_SYNC_POSITION = "DB: Position Synchronize"
    DB_CLOSE_POSITION = "DB: Position Close"
    DB_UPDATE_BALANCE = "DB: Balance Update"
    API_CREATE_POSITION = "API: Position Create"
    API_UPDATE_POSITION = "API: Position Update"
    API_CLOSE_POSITION = "API: Position Close"


class SignalType(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    STRONG_SELL = "Strong Sell"
    SELL = "Sell"
    DEBUG_SIGNAL = "Debug"
    NONE = ""


class TrendDirectionType(str, Enum):
    TREND_UP = "UpTrend"
    TREND_DOWN = "DownTrend"
    STRONG_TREND_UP = "StrongUpTrend"
    STRONG_TREND_DOWN = "StrongDownTrend"


class SymbolStatus(str, Enum):
    open = "OPEN"
    close = "CLOSE"


class TraderStatus(int, Enum):
    NEW = "0"
    PUBLIC = "1"
    PRIVATE = "2"
    EXPIRED = "-1"
    FAILED = "-2"


class SessionStatus(str, Enum):
    new = "NEW"
    active = "ACTIVE"
    closed = "CLOSED"
    failed = "FAILED"


class OrderStatus(str, Enum):
    new = "NEW"
    opened = "OPENED"
    canceled = "CANCELED"
    closed = "CLOSED"


class ExchangeId(str, Enum):
    demo_dzengi_com = "DEMO_DZENGI_COM"
    dzengi_com = "DZENGI_COM"
    demo_bybit_com = "DEMO_BYBIT_COM"
    bybit_com = "BYBIT_COM"


ExchangeId.demo_dzengi_com.__doc__ = "Demo: Dzengi.com"
ExchangeId.dzengi_com.__doc__ = "Dzengi.com"
ExchangeId.demo_bybit_com.__doc__ = "Demo: ByBit.com"
ExchangeId.bybit_com.__doc__ = "ByBit.com"


################## ID models #######################
class TraderIdModel(BaseModel):
    trader_id: str


class SymbolIdModel(BaseModel):
    symbol: str

    @validator("symbol")
    def check_symbol(cls, value):
        if not value or value == "null":
            raise ValueError("The symbol is missed")
        return value


class IntervalIdModel(BaseModel):
    interval: IntervalType


class StrategyIdModel(BaseModel):
    strategy: StrategyType


################## ID models #######################


################## Parameter models ################
class SymbolIntervalModel(SymbolIdModel, IntervalIdModel):
    pass


class SymbolIntervalStrategyModel(SymbolIntervalModel, StrategyIdModel):
    pass


class SymbolIntervalLimitModel(SymbolIntervalModel):
    limit: int = 0


class SymbolIntervalStrategyLimitModel(SymbolIntervalLimitModel, StrategyIdModel):
    pass


class TraderSymbolIntervalLimitModel(TraderIdModel, SymbolIntervalLimitModel):
    pass


class TraderSymbolIntervalStrategyLimitModel(
    TraderIdModel, SymbolIntervalStrategyLimitModel
):
    pass


class HistoryDataOptionsModel(BaseModel):
    from_buffer: bool = True
    closed_bars: bool = False

    @validator("from_buffer", pre=True, always=True)
    def convert_from_buffer(cls, value):
        return cls.convert_to_bool(value)

    @validator("closed_bars", pre=True, always=True)
    def convert_closed_bars(cls, value):
        return cls.convert_to_bool(value)

    def convert_to_bool(value):
        if type(value) == bool:
            return value
        elif type(value) == str:
            return bool(value.lower() == "true")


class StrategyParamModel(
    TraderSymbolIntervalStrategyLimitModel, HistoryDataOptionsModel
):
    pass


class SignalParamModel(StrategyParamModel):
    types: list[SignalType] = []


class IndicatorParamModel(TraderSymbolIntervalLimitModel, HistoryDataOptionsModel):
    pass


class HistoryDataParamModel(SymbolIntervalLimitModel, HistoryDataOptionsModel):
    pass


################## Parameter models ################


class IntervalModel(IntervalIdModel):
    name: str
    order: int
    importance: Importance


class StrategyConfigModel(StrategyIdModel):
    name: str
    length: int = 0
    display_rows: int = 2
    history_limit: int
    miv_value: float = 0
    max_value: float = 0


class HistoryDataModel(SymbolIntervalLimitModel):
    data: pd.DataFrame
    end_date_time: datetime = None

    def print_model(self):
        return {"symbol": self.symbol, "interval": self.interval, "limit": self.limit}

    @validator("end_date_time", pre=True, always=True)
    def get_end_date_time(cls, end_date_time, values):
        end_date_time = values.get("data").index[-1]
        return end_date_time

    class Config:
        # This is a workaround for DataFrame type
        arbitrary_types_allowed = True


class CandelBarModel(BaseModel):
    date_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SymbolModel(SymbolIdModel):
    name: str
    descr: str = ""
    status: SymbolStatus
    type: SymbolType
    trading_time: str
    # order_type: OrderType
    currency: str
    quote_precision: int
    trading_fee: float = None

    @validator("descr", pre=True, always=True)
    def concate_descr(cls, descr, values):
        descr = f'{values.get("name")} ({values.get("symbol")})'
        return descr


class SignalModel(CandelBarModel, StrategyParamModel):
    stop_loss_value: float = None
    take_profit_value: float = None
    signal: SignalType = SignalType.NONE

    def is_compatible(self, signal_types: list = []) -> bool:
        if signal_types:
            if SignalType.DEBUG_SIGNAL in signal_types or (
                self.signal and self.signal in signal_types
            ):
                return True
        else:
            if self.signal != SignalType.NONE:
                return True

        return False


class IdentifierModel(BaseModel):
    id: str = Field(alias="_id", default=None)

    @validator("id", pre=True, always=True)
    def convert_id_to_str(cls, value):
        return str(value)


class AdminModel(BaseModel):
    created_at: datetime = None
    # created_user: ObjectId = ...
    changed_at: datetime = None
    # last_changed_user: ObjectId = ...


class UserModel(IdentifierModel, AdminModel):
    email: EmailStr
    first_name: str
    second_name: str
    technical_user: bool = False

    def to_mongodb_doc(self):
        return {
            "email": self.email,
            "first_name": self.first_name,
            "second_name": self.second_name,
            "technical_user": self.technical_user,
        }


class ChannelModel(IdentifierModel, AdminModel):
    user_id: str
    name: str
    type: ChannelType
    channel: str

    def to_mongodb_doc(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type,
            "channel": self.channel,
        }


class AlertModel(IdentifierModel, AdminModel):
    user_id: str
    trader_id: str
    channel_id: str
    type: AlertType
    symbols: list = []
    intervals: list[IntervalType] = []
    strategies: list[StrategyType] = []
    signals: list[SignalType] = []

    def to_mongodb_doc(self):
        return {
            "user_id": self.user_id,
            "trader_id": self.trader_id,
            "channel_id": self.channel_id,
            "type": self.type,
            "symbols": self.symbols,
            "intervals": self.intervals,
            "strategies": self.strategies,
            "signals": self.signals,
        }


class TraderModel(IdentifierModel, AdminModel):
    user_id: str
    exchange_id: ExchangeId
    status: TraderStatus = TraderStatus.NEW
    expired_dt: datetime = datetime.now() + timedelta(days=365)
    default: bool = True
    api_key: str = ""
    api_secret: str = ""

    @validator("expired_dt")
    def check_expired_dt(cls, value_dt):
        if value_dt <= datetime.now():
            raise ValueError("The expired datetime is invalid")
        return value_dt

    def __generate_open_key(self, user_token=None):
        token = ""

        if user_token:
            token = user_token
        else:
            token = self.user_id

        open_key = config.get_env_value("ENCRYPT_OPEN_KEY")
        if not open_key:
            raise Exception(f"TraderModel: ENCRYPT_OPEN_KEY is not maintained")

        encode_token = token.encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            iterations=100000,
            salt=open_key.encode(),
            length=32,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(encode_token))
        return key

    def encrypt_key(self, key, user_token=None):
        cipher_suite = Fernet(key=self.__generate_open_key(user_token))
        encrypted_api_key = cipher_suite.encrypt(key.encode())
        return encrypted_api_key

    def decrypt_key(self, encrypted_key, user_token=None):
        cipher_suite = Fernet(key=self.__generate_open_key(user_token))
        decrypted_api_key = cipher_suite.decrypt(encrypted_key).decode()
        return decrypted_api_key

    def to_mongodb_doc(self):
        return {
            "user_id": self.user_id,
            "exchange_id": self.exchange_id,
            "status": self.status,
            "expired_dt": self.expired_dt,
            "default": self.default,
            "api_key": self.api_key,
            "api_secret": self.api_secret,
        }


class BalanceModel(AdminModel, IdentifierModel):
    session_id: str
    account_id: str = ""
    currency: str
    init_balance: float
    total_balance: float = 0
    total_profit: float = 0
    total_fee: float = 0

    @validator("total_balance", pre=True, always=True)
    def init_total_balance(cls, total_balance, values):
        total_balance = (
            values.get("init_balance") if total_balance == 0 else total_balance
        )
        return total_balance

    def to_mongodb_doc(self):
        return {
            "session_id": self.session_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "init_balance": self.init_balance,
            "total_balance": self.total_balance,
            "total_profit": self.total_profit,
            "total_fee": self.total_fee,
        }


class SessionModel(AdminModel, IdentifierModel, SymbolIntervalStrategyModel):
    # Session Details
    trader_id: str
    user_id: str
    status: SessionStatus = SessionStatus.new
    trading_type: TradingType
    session_type: SessionType

    # # Balance Details
    # account_id: str = ""
    # currency: str
    # init_balance: float
    # total_balance: float = 0
    # total_profit: float = 0
    # total_fee: float = 0

    # Trading Details
    leverage: int = 1
    take_profit_rate: float = 0
    stop_loss_rate: float = 0
    is_trailing_stop: bool = False

    # @validator("total_balance", pre=True, always=True)
    # def init_total_balance(cls, total_balance, values):
    #     total_balance = (
    #         values.get("init_balance") if total_balance == 0 else total_balance
    #     )
    #     return total_balance

    def to_mongodb_doc(self):
        return {
            "trader_id": self.trader_id,
            "user_id": self.user_id,
            "status": self.status,
            "trading_type": self.trading_type,
            "session_type": self.session_type,
            # "account_id": self.account_id,
            # "currency": self.currency,
            # "init_balance": self.init_balance,
            # "total_balance": self.total_balance,
            # "total_profit": self.total_profit,
            # "total_fee": self.total_fee,
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy": self.strategy,
            "leverage": self.leverage,
            "take_profit_rate": self.take_profit_rate,
            "stop_loss_rate": self.stop_loss_rate,
            "is_trailing_stop": self.is_trailing_stop,
        }


class OrderOpenModel(BaseModel):
    type: OrderType = OrderType.market
    side: OrderSideType
    open_price: float = 0
    open_datetime: datetime = datetime.now()
    open_reason: OrderReason = OrderReason.NONE
    open_atr: float = None
    open_stop_loss_value: float = None
    open_take_profit_value: float = None

    def to_mongodb_doc(self):
        return {
            "type": self.type,
            "side": self.side,
            "open_reason": self.open_reason,
            "open_price": self.open_price,
            "open_datetime": self.open_datetime,
        }


class OrderCloseModel(BaseModel):
    status: OrderStatus = OrderStatus.new
    close_order_id: str = ""
    close_price: float = 0
    close_datetime: datetime = datetime.now()
    close_reason: OrderReason = OrderReason.NONE
    total_profit: float = 0
    fee: float = 0

    def to_mongodb_doc(self):
        return {
            "close_order_id": self.close_order_id,
            "status": self.status,
            "close_price": self.close_price,
            "close_datetime": self.close_datetime,
            "close_reason": self.close_reason,
            "total_profit": self.total_profit,
            "fee": self.fee,
        }


class TrailingStopModel(BaseModel):
    stop_loss: float = 0
    take_profit: float = 0
    tp_increment: int = 0
    stop_loss_percent: float = 0
    take_profit_percent: float = 0

    def _calculate_delta(
        self, side: OrderSideType, current_price: float, open_price: float
    ) -> float:
        if side == OrderSideType.buy:
            return current_price - open_price
        elif side == OrderSideType.sell:
            return open_price - current_price

    def calculate_stop_loss_percent(
        self, open_price: float, side: OrderSideType
    ) -> float:
        if self.stop_loss != 0:
            delta = self._calculate_delta(
                side=side, current_price=self.stop_loss, open_price=open_price
            )
            self.stop_loss_percent = round((delta / open_price) * 100, 3)

            return self.stop_loss_percent

    def calculate_take_profit_percent(
        self, open_price: float, side: OrderSideType
    ) -> float:
        if self.take_profit != 0:
            if self.take_profit > open_price:
                delta = self.take_profit - open_price
            else:
                delta = open_price - self.take_profit

            self.take_profit_percent = round((delta / open_price) * 100, 3)
            return self.take_profit_percent

    def to_mongodb_doc(self):
        return {
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "tp_increment": self.tp_increment,
        }


class OrderAnalyticModel(BaseModel):
    high_price: float = 0
    low_price: float = 0
    percent: float = 0
    high_percent: float = 0
    low_percent: float = 0
    balance: float = 0

    def to_mongodb_doc(self):
        return {
            "high_price": self.high_price,
            "low_price": self.low_price,
        }


class OrderModel(
    AdminModel,
    IdentifierModel,
    SymbolIdModel,
    OrderOpenModel,
    TrailingStopModel,
    OrderCloseModel,
    OrderAnalyticModel,
):
    order_id: str = ""
    session_id: str
    quantity: float

    def calculate_high_price(self, price: float = 0) -> float:
        self.high_price = self.high_price if self.high_price >= price else price
        return self.high_price

    def calculate_low_price(self, price: float = 0) -> float:
        self.low_price = (
            self.low_price if self.low_price != 0 and self.low_price <= price else price
        )
        return self.low_price

    def calculate_percent(self, price: float = 0) -> float:
        price = self.close_price if self.close_price else price

        delta = self._calculate_delta(
            side=self.side, current_price=price, open_price=self.open_price
        )

        self.percent = (delta / self.open_price) * 100
        return self.percent

    def calculate_high_percent(self) -> float:
        if self.high_price != 0:
            self.high_percent = (
                (self.high_price - self.open_price) / self.open_price
            ) * 100
        else:
            self.high_percent = 0
        return self.high_percent

    def calculate_low_percent(self) -> float:
        if self.low_price != 0:
            self.low_percent = (
                (self.low_price - self.open_price) / self.open_price
            ) * 100
        else:
            self.low_percent = 0
        return self.low_percent

    def calculate_stop_loss_percent(self) -> float:
        return super().calculate_stop_loss_percent(
            open_price=self.open_price, side=self.side
        )

    def calculate_take_profit_percent(self) -> float:
        return super().calculate_take_profit_percent(
            open_price=self.open_price, side=self.side
        )

    def calculate_balance(self) -> float:
        self.balance = self.quantity * self.open_price
        return self.balance

    def to_mongodb_doc(self):
        order = {
            "order_id": self.order_id,
            "session_id": self.session_id,
            "type": self.type,
            "side": self.side,
            "status": self.status,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "fee": self.fee,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "tp_increment": self.tp_increment,
            "open_price": self.open_price,
            "open_datetime": self.open_datetime,
            "open_reason": self.open_reason,
            "close_order_id": self.close_order_id,
            "close_price": self.close_price,
            "close_datetime": self.close_datetime,
            "close_reason": self.close_reason,
            "total_profit": self.total_profit,
            "high_price": self.high_price,
            "low_price": self.low_price,
        }

        if not self.id in [None, "None", ""]:
            order["_id"] = ObjectId(self.id)

        return order


class LeverageModel(OrderModel):
    position_id: str = ""
    account_id: str
    leverage: int = 1

    def calculate_balance(self) -> float:
        self.balance = self.quantity * self.open_price / self.leverage
        return self.balance

    def to_mongodb_doc(self):
        leverage = {
            "position_id": self.position_id,
            "order_id": self.order_id,
            "session_id": self.session_id,
            "account_id": self.account_id,
            "type": self.type,
            "side": self.side,
            "status": self.status,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "fee": self.fee,
            "leverage": self.leverage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "tp_increment": self.tp_increment,
            "open_price": self.open_price,
            "open_datetime": self.open_datetime,
            "open_reason": self.open_reason,
            "close_order_id": self.close_order_id,
            "close_price": self.close_price,
            "close_datetime": self.close_datetime,
            "close_reason": self.close_reason,
            "high_price": self.high_price,
            "low_price": self.low_price,
        }

        if not self.id in [None, "None", ""]:
            leverage["_id"] = ObjectId(self.id)

        return leverage


class TransactionModel(AdminModel, IdentifierModel):
    local_order_id: str = ""
    order_id: str = ""
    session_id: str
    user_id: str
    date_time: datetime
    type: TransactionType
    data: dict

    def to_mongodb_doc(self):
        return {
            "local_order_id": self.local_order_id,
            "order_id": self.order_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "date_time": self.date_time,
            "type": self.type,
            "data": self.data,
        }


class APIException(Exception):
    pass


class RobotException(Exception):
    pass
