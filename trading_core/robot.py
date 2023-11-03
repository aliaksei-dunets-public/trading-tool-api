from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

# from bson import ObjectId
from datetime import datetime, timedelta


class ChannelType(str, Enum):
    email = "EMAIL"
    telegram_bot = "TELEGRAM_BOT"


class TraderStatus(str, Enum):
    new = "NEW"
    active = "ACTIVE"
    inactive = "INACTIVE"
    connected = "CONNECTED"
    failed = "FAILED"
    expired = "EXPIRED"


class SessionStatus(str, Enum):
    active = "ACTIVE"
    closed = "CLOSED"
    failed = "FAILED"


class SessionType(str, Enum):
    order = "ORDER"
    leverage = "LEVERAGE"


class Exchange(str, Enum):
    demo_dzengi_com = "DEMO_DZENGI_COM"
    dzengi_com = "DZENGI_COM"


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

    def to_mongodb_doc(self):
        return {"first_name": self.first_name, "second_name": self.second_name}


class ChannelModel(IdentifierModel, AdminModel):
    user_id: UserModel.id
    name: str
    type: ChannelType
    value: str


class Trader(IdentifierModel, AdminModel):
    user_id: UserModel.id
    exchange: Exchange
    status: TraderStatus = TraderStatus.new
    expired_dt: datetime = datetime.now + timedelta(days=365)
    api_key: str = None
    api_secret: str = None

    @validator("expired_dt")
    def format_first_name(cls, value_dt):
        if value_dt <= datetime.now:
            raise ValueError("The expired datetime is invalid")
        return value_dt


# class Symbol(BaseModel):
#     symbol: str


# class Interval(BaseModel):
#     interval: str


# class Strategy(BaseModel):
#     strategy: str


# class SymbolInterval(Symbol, Interval):
#     pass


# class SymbolIntervalStrategy(Symbol, Interval, Strategy):
#     pass


# class Session(AdminData, SymbolIntervalStrategy):
#     _id: ObjectId = ...
#     trader_id = Trader._id
#     user_id: User._id
#     status: SessionStatus
#     type: SessionType
#     balance: float

#     # Trading Details
#     account_id: str
#     currency: str
#     init_balance: float
#     take_profit_rate: float = ...
#     stop_loss_rate: float = ...

#     # @property
#     # def name(self):
#     #     return self._name

#     # @name.setter
#     # def name(self, value):
#     #     # You can add custom logic here
#     #     if not value.isalpha():
#     #         raise ValueError("Name must contain only alphabetic characters")
#     #     self._name = value
