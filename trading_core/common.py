from enum import Enum
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


class SideType(str, Enum):
    buy = "BUY"
    sell = "SELL"


class TransactionType(str, Enum):
    open = "OPEN"
    close = "CLOSE"


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


class SymbolIntervalStrategyModel(SymbolIdModel, IntervalIdModel, StrategyIdModel):
    pass


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

    # Trading Details
    take_profit_rate: float = 0
    stop_loss_rate: float = 0

    def to_mongodb_doc(self):
        return {
            "trader_id": self.trader_id,
            "user_id": self.user_id,
            "status": self.status,
            "type": self.type,
            "symbol": self.symbol,
            "interval": self.interval,
            "strategy": self.strategy,
            "take_profit_rate": self.take_profit_rate,
            "stop_loss_rate": self.stop_loss_rate,
        }


class OrderModel(AdminModel, IdentifierModel, SymbolIdModel):
    session_id: str
    type: str = OrderType.market
    side: str
    status: str = OrderStatus.new
    quantity: float
    fee: float = 0
    open_price: float
    open_datetime: datetime = datetime.now()
    close_price: float = 0
    close_datetime: datetime = datetime.now()

    def to_mongodb_doc(self):
        return {
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


class LeverageModel(OrderModel):
    order_id: str
    account_id: str
    stop_loss: float
    take_profit: float

    def to_mongodb_doc(self):
        return {
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
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
        }


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
