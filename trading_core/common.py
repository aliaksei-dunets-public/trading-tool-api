from enum import Enum
from bson import ObjectId
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field, validator


class SymbolType(str, Enum):
    leverage = "LEVERAGE"
    spot = "SPOT"


class ChannelType(str, Enum):
    email = "EMAIL"
    telegram_bot = "TELEGRAM_BOT"


class SessionType(str, Enum):
    order = "ORDER"
    leverage = "LEVERAGE"


class OrderType(str, Enum):
    limit = "LIMIT"
    market = "MARKET"
    stop = "STOP"


class OrderSideType(str, Enum):
    buy = "BUY"
    sell = "SELL"


class TransactionType(str, Enum):
    open = "OPEN"
    close = "CLOSE"


class SignalType(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    STRONG_SELL = "Strong Sell"
    SELL = "Sell"
    DEBUG_SIGNAL = "Debug"
    TREND_CHANGED = "Trend Changed"


class StrategyType(str, Enum):
    CCI_14_TREND_100 = "CCI_14_TREND_100"
    CCI_14_TREND_170_165 = "CCI_14_TREND_170_165"
    CCI_20_TREND_100 = "CCI_20_TREND_100"
    CCI_50_TREND_0 = "CCI_50_TREND_0"


class SymbolStatus(str, Enum):
    open = "OPEN"
    close = "CLOSE"


class TraderStatus(str, Enum):
    new = "NEW"
    active = "ACTIVE"
    inactive = "INACTIVE"
    connected = "CONNECTED"
    failed = "FAILED"
    expired = "EXPIRED"


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


class CandelBarModel(BaseModel):
    date_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SignalModel(CandelBarModel):
    strategy: StrategyType
    signal: SignalType = ""


class SymbolIdModel(BaseModel):
    symbol: str


class SymbolModel(SymbolIdModel):
    name: str
    descr: str = ""
    status: SymbolStatus
    type: SymbolType
    trading_time: str
    # order_type: OrderType
    currency: str
    trading_fee: float = 0

    @property
    def descr(self):
        return f"{self.name} ({self.symbol})"


class IntervalIdModel(BaseModel):
    interval: str


class StrategyIdModel(BaseModel):
    strategy: str


class SymbolIntervalIdModel(SymbolIdModel, IntervalIdModel):
    pass


class SymbolIntervalStrategyModel(SymbolIntervalIdModel, StrategyIdModel):
    pass


class HistoryDataParam(SymbolIntervalIdModel):
    limit: int


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
    value: str

    def to_mongodb_doc(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "type": self.type,
            "value": self.value,
        }


class TraderModel(IdentifierModel, AdminModel):
    user_id: str
    exchange_id: ExchangeId
    status: TraderStatus = TraderStatus.new
    expired_dt: datetime = datetime.now() + timedelta(days=365)
    default: bool = True
    api_key: str = ""
    api_secret: str = ""

    @validator("expired_dt")
    def check_expired_dt(cls, value_dt):
        if value_dt <= datetime.now():
            raise ValueError("The expired datetime is invalid")
        return value_dt

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
    account_id: str
    currency: str
    init_balance: float
    total_balance: float = 0
    total_fee: float = 0

    def to_mongodb_doc(self):
        return {
            "session_id": self.session_id,
            "account_id": self.account_id,
            "currency": self.currency,
            "init_balance": self.init_balance,
            "total_balance": self.total_balance,
            "total_fee": self.total_fee,
        }


class SessionModel(AdminModel, IdentifierModel, SymbolIntervalStrategyModel):
    # Session Details
    trader_id: str
    user_id: str
    status: SessionStatus = SessionStatus.new
    type: SessionType
    is_simulation: bool = True

    # Trading Details
    leverage: int = 2
    take_profit_rate: float = 0
    stop_loss_rate: float = 0

    def to_mongodb_doc(self):
        {
            "trader_id": self.trader_id,
            "user_id": self.user_id,
            "status": self.status,
            "type": self.type,
            "is_simulation": self.is_simulation,
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy": self.strategy,
            "take_profit_rate": self.take_profit_rate,
            "stop_loss_rate": self.stop_loss_rate,
        }


class OrderModel(AdminModel, IdentifierModel, SymbolIdModel):
    session_id: str
    type: OrderType = OrderType.market
    side: OrderSideType
    status: OrderStatus = OrderStatus.new
    quantity: float
    fee: float = 0
    open_price: float
    open_datetime: datetime = datetime.now()
    close_price: float = 0
    close_datetime: datetime = datetime.now()

    def to_mongodb_doc(self):
        order = {
            "session_id": self.session_id,
            "type": self.type,
            "side": self.side,
            "status": self.status,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "fee": self.fee,
            "open_price": self.open_price,
            "open_datetime": self.open_datetime,
            "close_price": self.close_price,
            "close_datetime": self.close_datetime,
        }

        if self.id:
            order["_id"] = ObjectId(self.id)

        return order


class LeverageModel(OrderModel):
    order_id: str
    account_id: str
    leverage: int
    stop_loss: float
    take_profit: float

    def to_mongodb_doc(self):
        leverage = {
            "order_id": self.order_id,
            "session_id": self.session_id,
            "account_id": self.account_id,
            "type": self.type,
            "side": self.side,
            "status": self.status,
            "symbol": self.symbol,
            "quantity": self.quantity,
            "fee": self.fee,
            "open_price": self.open_price,
            "open_datetime": self.open_datetime,
            "close_price": self.close_price,
            "close_datetime": self.close_datetime,
            "leverage": self.leverage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
        }

        if self.id:
            leverage["_id"] = ObjectId(self.id)

        return leverage


class TransactionModel(AdminModel, IdentifierModel):
    order_id: str
    session_id: str
    type: TransactionType
    price: float
    quantity: float
    fee: float = 0

    def to_mongodb_doc(self):
        return {
            "order_id": self.order_id,
            "leverage_id": self.leverage_id,
            "session_id": self.session_id,
            "type": self.type,
            "price": self.price,
            "quantity": self.quantity,
            "fee": self.fee,
        }
