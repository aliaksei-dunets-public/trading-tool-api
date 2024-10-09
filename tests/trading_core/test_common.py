import pytest
import os
import configparser
from unittest import mock
from pydantic import ValidationError
from datetime import datetime, timedelta
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64
from cryptography.fernet import Fernet
from trading_core.common import (
    IntervalType,
    IndicatorType,
    StrategyType,
    Importance,
    SymbolType,
    PriceType,
    ChannelType,
    AlertType,
    TradingType,
    SessionType,
    OrderType,
    OrderSideType,
    OrderReason,
    TransactionType,
    SignalType,
    TrendDirectionType,
    RiskType,
    SymbolStatus,
    TraderStatus,
    SessionStatus,
    OrderStatus,
    ExchangeId,
    TraderIdModel,
    SymbolIdModel,
    IntervalIdModel,
    StrategyIdModel,
    SymbolIntervalModel,
    SymbolIntervalStrategyModel,
    SymbolIntervalLimitModel,
    SymbolIntervalStrategyLimitModel,
    TraderSymbolIntervalLimitModel,
    TraderSymbolIntervalStrategyLimitModel,
    HistoryDataOptionsModel,
    StrategyParamModel,
    SignalParamModel,
    IndicatorParamModel,
    HistoryDataParamModel,
    IntervalModel,
    StrategyModel,
    StrategyConfigModel,
    HistoryDataModel,
    CandelBarModel,
    SymbolModel,
    SignalModel,
    IdentifierModel,
    AdminModel,
    UserModel,
    ChannelModel,
    AlertModel,
    TraderModel,
    SignalType,
    IntervalType,
    StrategyType,
    SymbolType,
    SymbolStatus,
    Importance,
    RiskType,
    ChannelType,
    AlertType,
    TraderStatus,
    ExchangeId,
    BalanceModel,
    SessionModel,
    OrderOpenModel,
    OrderCloseModel,
    TrailingStopModel,
    LeverageModel,
    TransactionModel,
)
from trading_core.core import Config
from trading_core.constants import Const


@pytest.fixture
def mock_env():
    with mock.patch.dict(
        os.environ,
        {
            "LOGGER_FORMAT": "%(message)s",
            "SOME_ENV_VAR": "value",
            "ENCRYPT_OPEN_KEY": "",
        },
    ):
        yield


################## Enum Tests ##################
def test_enum_values():
    # Test every enum case for full coverage
    assert IntervalType.MIN_1 == "1m"
    assert IntervalType.MIN_3 == "3m"
    assert IntervalType.MIN_5 == "5m"
    assert IntervalType.MIN_15 == "15m"
    assert IntervalType.MIN_30 == "30m"
    assert IntervalType.HOUR_1 == "1h"
    assert IntervalType.HOUR_2 == "2h"
    assert IntervalType.HOUR_4 == "4h"
    assert IntervalType.HOUR_6 == "6h"
    assert IntervalType.HOUR_12 == "12h"
    assert IntervalType.DAY_1 == "1d"
    assert IntervalType.WEEK_1 == "1w"
    assert IntervalType.MONTH_1 == "1month"

    assert IndicatorType.ATR == "ATR"
    assert IndicatorType.CCI == "CCI"
    assert IndicatorType.CCI_ATR == "CCI_ATR"

    assert StrategyType.CCI_14_CROSS_100 == "CCI_14_CROSS_100"
    assert StrategyType.CCI_20_CROSS_100 == "CCI_20_CROSS_100"
    assert StrategyType.CCI_50_CROSS_0 == "CCI_50_CROSS_0"
    assert StrategyType.EMA_30_CROSS_EMA_100 == "EMA_30_CROSS_EMA_100"
    assert (
        StrategyType.EMA_8_CROSS_EMA_30_FILTER_CCI_14
        == "EMA_8_CROSS_EMA_30_FILTER_CCI_14"
    )
    assert (
        StrategyType.EMA_8_CROSS_EMA_30_FILTER_EMA_100
        == "EMA_8_CROSS_EMA_30_FILTER_EMA_100"
    )
    assert (
        StrategyType.EMA_30_CROSS_EMA_100_FILTER_CCI_50
        == "EMA_30_CROSS_EMA_100_FILTER_CCI_50"
    )
    assert (
        StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND
        == "EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND"
    )
    assert (
        StrategyType.EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP
        == "EMA_50_CROSS_EMA_100_FILTER_UP_LEVEL_TREND_TP"
    )

    assert Importance.LOW == "Low"
    assert Importance.MEDIUM == "Medium"
    assert Importance.HIGH == "High"

    assert SymbolType.spot == "SPOT"
    assert SymbolType.leverage == "LEVERAGE"

    assert PriceType.ASK == "ask"
    assert PriceType.BID == "bid"

    assert ChannelType.TELEGRAM_BOT == "Telegram"
    assert ChannelType.EMAIL == "Email"

    assert AlertType.TRADING == "Trading"
    assert AlertType.ERROR == "Error"
    assert AlertType.SIGNAL == "Signal"

    assert TradingType.SPOT == "SPOT"
    assert TradingType.LEVERAGE == "LEVERAGE"

    assert SessionType.SIMULATION == "Real Simulation"
    assert SessionType.HISTORY == "History Simulation"
    assert SessionType.TRADING == "Trading"

    assert OrderType.market == "MARKET"
    assert OrderType.stop == "STOP"
    assert OrderType.limit == "LIMIT"

    assert OrderSideType.sell == "SELL"
    assert OrderSideType.buy == "BUY"

    assert OrderReason.STOP_LOSS == "Stop Loss"
    assert OrderReason.TAKE_PROFIT == "Take Profit"
    assert OrderReason.SIGNAL == "Signal"
    assert OrderReason.MANUAL == "Manual"
    assert OrderReason.CANCEL == "Cancel"
    assert OrderReason.TRADER == "Trader"
    assert OrderReason.NONE == ""

    assert TransactionType.DB_CREATE_POSITION == "DB: Position Create"
    assert TransactionType.DB_UPDATE_POSITION == "DB: Position Update"
    assert TransactionType.DB_SYNC_POSITION == "DB: Position Synchronize"
    assert TransactionType.DB_CLOSE_POSITION == "DB: Position Close"
    assert TransactionType.DB_UPDATE_BALANCE == "DB: Balance Update"
    assert TransactionType.API_CREATE_POSITION == "API: Position Create"
    assert TransactionType.API_UPDATE_POSITION == "API: Position Update"
    assert TransactionType.API_CLOSE_POSITION == "API: Position Close"

    assert SignalType.STRONG_BUY == "Strong Buy"
    assert SignalType.BUY == "Buy"
    assert SignalType.STRONG_SELL == "Strong Sell"
    assert SignalType.SELL == "Sell"
    assert SignalType.DEBUG_SIGNAL == "Debug"
    assert SignalType.NONE == ""

    assert TrendDirectionType.TREND_UP == "UpTrend"
    assert TrendDirectionType.TREND_DOWN == "DownTrend"
    assert TrendDirectionType.STRONG_TREND_UP == "StrongUpTrend"
    assert TrendDirectionType.STRONG_TREND_DOWN == "StrongDownTrend"

    assert RiskType.DEFAULT == "Default"
    assert RiskType.SL_BOUND_TO_TP == "SL_BOUND_TO_TP"

    assert SymbolStatus.open == "OPEN"
    assert SymbolStatus.close == "CLOSE"

    assert TraderStatus.NEW == 0
    assert TraderStatus.PUBLIC == 1
    assert TraderStatus.PRIVATE == 2
    assert TraderStatus.EXPIRED == -1
    assert TraderStatus.FAILED == -2

    assert SessionStatus.new == "NEW"
    assert SessionStatus.active == "ACTIVE"
    assert SessionStatus.closed == "CLOSED"
    assert SessionStatus.failed == "FAILED"

    assert OrderStatus.new == "NEW"
    assert OrderStatus.opened == "OPENED"
    assert OrderStatus.canceled == "CANCELED"
    assert OrderStatus.closed == "CLOSED"

    assert ExchangeId.demo_dzengi_com == "DEMO_DZENGI_COM"
    assert ExchangeId.dzengi_com == "DZENGI_COM"
    assert ExchangeId.demo_bybit_com == "DEMO_BYBIT_COM"
    assert ExchangeId.bybit_com == "BYBIT_COM"


def test_enum_docstrings():
    # Test the docstrings for ExchangeId Enum
    assert ExchangeId.demo_dzengi_com.__doc__ == "Demo: Dzengi.com"
    assert ExchangeId.dzengi_com.__doc__ == "Dzengi.com"


################## Pydantic Model Tests ##################


def test_trader_id_model():
    # Test the TraderIdModel creation
    model = TraderIdModel(trader_id="12345")
    assert model.trader_id == "12345"


def test_symbol_id_model_valid():
    # Test the SymbolIdModel creation with valid input
    model = SymbolIdModel(symbol="BTCUSDT")
    assert model.symbol == "BTCUSDT"


def test_symbol_id_model_invalid():
    # Test SymbolIdModel creation with invalid input
    with pytest.raises(ValidationError) as excinfo:
        SymbolIdModel(symbol="null")
    assert "The symbol is missed" in str(excinfo.value)


def test_symbol_id_model_missing_symbol():
    # Test SymbolIdModel creation with missing symbol (None)
    with pytest.raises(ValidationError) as excinfo:
        SymbolIdModel(symbol="")
    assert "The symbol is missed" in str(excinfo.value)


def test_interval_id_model():
    # Test IntervalIdModel creation
    model = IntervalIdModel(interval=IntervalType.MIN_1)
    assert model.interval == IntervalType.MIN_1


def test_strategy_id_model():
    # Test StrategyIdModel creation
    model = StrategyIdModel(strategy=StrategyType.CCI_14_CROSS_100)
    assert model.strategy == StrategyType.CCI_14_CROSS_100


def test_trader_id_model_invalid():
    # Test TraderIdModel creation with invalid input (None)
    with pytest.raises(ValidationError):
        TraderIdModel(trader_id=None)


################## Negative Tests ##################


def test_invalid_interval_type():
    # Test IntervalIdModel with an invalid interval type
    with pytest.raises(ValidationError):
        IntervalIdModel(interval="invalid_interval")


def test_invalid_strategy_type():
    # Test StrategyIdModel with an invalid strategy type
    with pytest.raises(ValidationError):
        StrategyIdModel(strategy="invalid_strategy")


############################
# Parameter Model Tests
############################


def test_symbol_interval_model():
    model = SymbolIntervalModel(symbol="BTCUSDT", interval=IntervalType.MIN_1)
    assert model.symbol == "BTCUSDT"
    assert model.interval == IntervalType.MIN_1


def test_symbol_interval_strategy_model():
    model = SymbolIntervalStrategyModel(
        symbol="BTCUSDT",
        interval=IntervalType.MIN_1,
        strategy=StrategyType.CCI_14_CROSS_100,
    )
    assert model.symbol == "BTCUSDT"
    assert model.interval == IntervalType.MIN_1
    assert model.strategy == StrategyType.CCI_14_CROSS_100


def test_symbol_interval_limit_model():
    model = SymbolIntervalLimitModel(
        symbol="BTCUSDT", interval=IntervalType.MIN_1, limit=100
    )
    assert model.symbol == "BTCUSDT"
    assert model.limit == 100
    model.set_limit(200)
    assert model.limit == 200


def test_trader_symbol_interval_limit_model():
    model = TraderSymbolIntervalLimitModel(
        trader_id="12345", symbol="BTCUSDT", interval=IntervalType.MIN_1, limit=50
    )
    assert model.trader_id == "12345"
    assert model.symbol == "BTCUSDT"
    assert model.limit == 50


def test_trader_symbol_interval_strategy_limit_model():
    model = TraderSymbolIntervalStrategyLimitModel(
        trader_id="12345",
        symbol="BTCUSDT",
        interval=IntervalType.MIN_1,
        strategy=StrategyType.CCI_14_CROSS_100,
        limit=50,
    )
    assert model.trader_id == "12345"
    assert model.symbol == "BTCUSDT"
    assert model.strategy == StrategyType.CCI_14_CROSS_100
    assert model.limit == 50


############################
# History Data Options Model
############################


def test_history_data_options_model():
    model = HistoryDataOptionsModel(from_buffer="true", closed_bars="false")
    assert model.from_buffer == True
    assert model.closed_bars == False

    model = HistoryDataOptionsModel(from_buffer=False, closed_bars=True)
    assert model.from_buffer == False
    assert model.closed_bars == True


############################
# Strategy Param Model
############################


def test_strategy_param_model():
    model = StrategyParamModel(
        trader_id="12345",
        symbol="BTCUSDT",
        interval=IntervalType.MIN_1,
        strategy=StrategyType.CCI_14_CROSS_100,
        limit=100,
        from_buffer=True,
        closed_bars=False,
    )
    assert model.trader_id == "12345"
    assert model.symbol == "BTCUSDT"
    assert model.interval == IntervalType.MIN_1
    assert model.strategy == StrategyType.CCI_14_CROSS_100
    assert model.limit == 100
    assert model.from_buffer == True
    assert model.closed_bars == False


############################
# Signal Model
############################


def test_signal_model():
    model = SignalModel(
        date_time=datetime.now(),
        open=10000,
        high=10500,
        low=9500,
        close=10200,
        volume=1.5,
        trader_id="12345",
        symbol="BTCUSDT",
        interval=IntervalType.MIN_1,
        strategy=StrategyType.CCI_14_CROSS_100,
        limit=100,
        from_buffer=True,
        closed_bars=False,
        signal=SignalType.BUY,
    )
    assert model.signal == SignalType.BUY
    assert model.is_compatible([SignalType.BUY]) == True
    assert model.is_compatible([SignalType.SELL]) == False
    assert model.is_compatible([SignalType.STRONG_BUY]) == False

    model.signal == SignalType.NONE
    assert model.is_compatible([]) == True


############################
# History Data Model
############################


def test_history_data_model():
    df = pd.DataFrame(
        {"close": [100, 200, 300]}, index=pd.date_range("2020-01-01", periods=3)
    )
    model = HistoryDataModel(
        symbol="BTCUSDT", interval=IntervalType.MIN_1, limit=100, data=df
    )
    assert model.data is not None
    assert model.end_date_time == df.index[-1]


############################
# User Model
############################


def test_user_model():
    model = UserModel(
        email="user@example.com",
        first_name="John",
        second_name="Doe",
        technical_user=True,
    )
    doc = model.to_mongodb_doc()
    assert doc["email"] == "user@example.com"
    assert doc["first_name"] == "John"
    assert doc["technical_user"] == True


############################
# Channel Model
############################


def test_channel_model():
    model = ChannelModel(
        user_id="user123",
        name="Test Channel",
        type=ChannelType.TELEGRAM_BOT,
        channel="telegram",
    )
    doc = model.to_mongodb_doc()
    assert doc["user_id"] == "user123"
    assert doc["type"] == ChannelType.TELEGRAM_BOT


############################
# Alert Model
############################


def test_alert_model():
    model = AlertModel(
        user_id="user123",
        trader_id="trader123",
        channel_id="channel123",
        type=AlertType.SIGNAL,
        symbols=["BTCUSDT"],
        intervals=[IntervalType.MIN_1],
        strategies=[StrategyType.CCI_14_CROSS_100],
        signals=[SignalType.BUY],
    )
    doc = model.to_mongodb_doc()
    assert doc["user_id"] == "user123"
    assert doc["symbols"] == ["BTCUSDT"]


############################
# Trader Model
############################


class TestTraderModel:

    def test_generate_open_key_env_missing(self, mock_env):
        # Mock get_env_value to return None (which simulates a missing env variable)

        trader = TraderModel(
            user_id="test_user",
            exchange_id=ExchangeId.demo_dzengi_com,
            api_key="dummy_key",
            api_secret="dummy_secret",
        )

        # Check that exception is raised when ENCRYPT_OPEN_KEY is not present
        with pytest.raises(Exception) as exc_info:
            trader._TraderModel__generate_open_key()

        assert str(exc_info.value) == "TraderModel: ENCRYPT_OPEN_KEY is not maintained"

    def test_generate_open_key_env_exists(self):
        trader = TraderModel(
            user_id="test_user",
            exchange_id=ExchangeId.demo_dzengi_com,
            api_key="dummy_key",
            api_secret="dummy_secret",
        )

        # Ensure the open key generation works correctly without raising exceptions
        key = trader._TraderModel__generate_open_key()

        assert key is not None
        assert isinstance(key, bytes)  # The generated key should be in bytes format

    def test_to_mongodb_doc(self):
        trader = TraderModel(
            user_id="test_user",
            exchange_id=ExchangeId.demo_dzengi_com,
            status=TraderStatus.PRIVATE,
            expired_dt=datetime.now() + timedelta(days=365),
            default=True,
            api_key="dummy_api_key",
            api_secret="dummy_api_secret",
        )

        expected_doc = {
            "user_id": "test_user",
            "exchange_id": ExchangeId.demo_dzengi_com,
            "status": TraderStatus.PRIVATE,
            "expired_dt": trader.expired_dt,
            "default": True,
            "api_key": "dummy_api_key",
            "api_secret": "dummy_api_secret",
        }

        assert trader.to_mongodb_doc() == expected_doc


def test_trader_model_encrypt_decrypt():
    trader = TraderModel(
        user_id="user123",
        exchange_id=ExchangeId.demo_dzengi_com,
        api_key="test_api_key",
        api_secret="test_api_secret",
    )
    encrypted_key = trader.encrypt_key(trader.api_key)
    decrypted_key = trader.decrypt_key(encrypted_key)
    assert decrypted_key == "test_api_key"

    encrypted_key = trader.encrypt_key(key=trader.api_key, user_token="12345")
    decrypted_key = trader.decrypt_key(encrypted_key=encrypted_key, user_token="12345")
    assert decrypted_key == "test_api_key"


def test_trader_model_expired_dt_validator():
    dt = datetime.now() + timedelta(days=1)
    trader_model = TraderModel(
        user_id="user123",
        exchange_id=ExchangeId.demo_dzengi_com,
        expired_dt=dt,
    )

    assert trader_model.expired_dt == dt

    with pytest.raises(ValueError, match="The expired datetime is invalid"):
        TraderModel(
            user_id="user123",
            exchange_id=ExchangeId.demo_dzengi_com,
            expired_dt=datetime.now() - timedelta(days=1),  # Past date
        )


############################
# Identifier Model
############################


def test_identifier_model():
    model = IdentifierModel(_id="abc123")
    assert model.id == "abc123"


############################
# Admin Model
############################


def test_admin_model():
    model = AdminModel(created_at=datetime.now(), changed_at=datetime.now())
    assert model.created_at is not None


# Unit tests for BalanceModel
class TestBalanceModel:
    def test_balance_model_initialization(self):
        balance = BalanceModel(
            session_id="sess_123",
            account_id="acc_123",
            currency="USD",
            init_balance=1000,
        )
        assert balance.session_id == "sess_123"
        assert balance.account_id == "acc_123"
        assert balance.currency == "USD"
        assert balance.init_balance == 1000
        assert balance.total_balance == 1000  # initialized by validator
        assert balance.total_profit == 0
        assert balance.total_fee == 0

    def test_balance_model_to_mongodb_doc(self):
        balance = BalanceModel(
            session_id="sess_123",
            account_id="acc_123",
            currency="USD",
            init_balance=1000,
            total_balance=1200,
            total_profit=200,
            total_fee=20,
        )
        doc = balance.to_mongodb_doc()
        assert doc["session_id"] == "sess_123"
        assert doc["account_id"] == "acc_123"
        assert doc["currency"] == "USD"
        assert doc["init_balance"] == 1000
        assert doc["total_balance"] == 1200
        assert doc["total_profit"] == 200
        assert doc["total_fee"] == 20


# Unit tests for SessionModel
class TestSessionModel:
    def test_session_model_initialization(self):
        session = SessionModel(
            trader_id="trader_123",
            user_id="user_123",
            status=SessionStatus.new,
            trading_type=TradingType.LEVERAGE,
            session_type=SessionType.TRADING,
            symbol="BTCUSD",
            interval="1h",
            strategy=StrategyType.CCI_14_CROSS_100,
            leverage=10,
            take_profit_rate=0.05,
            stop_loss_rate=0.02,
            is_trailing_stop=True,
        )
        assert session.trader_id == "trader_123"
        assert session.user_id == "user_123"
        assert session.status == SessionStatus.new
        assert session.trading_type == TradingType.LEVERAGE
        assert session.session_type == SessionType.TRADING
        assert session.leverage == 10
        assert session.take_profit_rate == 0.05
        assert session.stop_loss_rate == 0.02
        assert session.is_trailing_stop is True
        assert session.strategy == StrategyType.CCI_14_CROSS_100

    def test_session_model_to_mongodb_doc(self):
        session = SessionModel(
            trader_id="trader_123",
            user_id="user_123",
            status=SessionStatus.new,
            trading_type=TradingType.SPOT,
            session_type=SessionType.HISTORY,
            symbol="BTCUSD",
            interval="1h",
            strategy=StrategyType.CCI_50_CROSS_0,
            leverage=10,
            take_profit_rate=0.05,
            stop_loss_rate=0.02,
            is_trailing_stop=True,
        )
        doc = session.to_mongodb_doc()
        assert doc["trader_id"] == "trader_123"
        assert doc["user_id"] == "user_123"
        assert doc["trading_type"] == TradingType.SPOT
        assert doc["session_type"] == SessionType.HISTORY
        assert doc["leverage"] == 10
        assert doc["strategy"] == StrategyType.CCI_50_CROSS_0


# Unit tests for OrderOpenModel
class TestOrderOpenModel:
    def test_order_open_model_initialization(self):
        order_open = OrderOpenModel(
            type=OrderType.market,
            side=OrderSideType.buy,
            open_price=10000,
            open_reason=OrderReason.MANUAL,
        )
        assert order_open.type == OrderType.market
        assert order_open.side == OrderSideType.buy
        assert order_open.open_price == 10000
        assert order_open.open_reason == OrderReason.MANUAL

    def test_order_open_model_to_mongodb_doc(self):
        order_open = OrderOpenModel(
            type=OrderType.market,
            side=OrderSideType.buy,
            open_price=10000,
            open_reason=OrderReason.SIGNAL,
        )
        doc = order_open.to_mongodb_doc()
        assert doc["type"] == OrderType.market
        assert doc["side"] == OrderSideType.buy
        assert doc["open_price"] == 10000


# Unit tests for OrderCloseModel
class TestOrderCloseModel:
    def test_order_close_model_initialization(self):
        order_close = OrderCloseModel(
            status=OrderStatus.closed,
            close_order_id="close_123",
            close_price=11000,
            total_profit=1000,
            fee=50,
        )
        assert order_close.status == OrderStatus.closed
        assert order_close.close_order_id == "close_123"
        assert order_close.close_price == 11000
        assert order_close.total_profit == 1000
        assert order_close.fee == 50

    def test_order_close_model_to_mongodb_doc(self):
        order_close = OrderCloseModel(
            status=OrderStatus.closed,
            close_order_id="close_123",
            close_price=11000,
            total_profit=1000,
            fee=50,
        )
        doc = order_close.to_mongodb_doc()
        assert doc["status"] == OrderStatus.closed
        assert doc["close_order_id"] == "close_123"
        assert doc["close_price"] == 11000
        assert doc["total_profit"] == 1000
        assert doc["fee"] == 50


# Unit tests for TrailingStopModel
class TestTrailingStopModel:
    def test_trailing_stop_model_calculate_stop_loss_percent(self):
        trailing_stop = TrailingStopModel(stop_loss=9500)
        stop_loss_percent = trailing_stop.calculate_stop_loss_percent(
            open_price=10000, side=OrderSideType.buy
        )
        assert stop_loss_percent == -5.0

        stop_loss_percent = trailing_stop.calculate_stop_loss_percent(
            open_price=10000, side=OrderSideType.sell
        )
        assert stop_loss_percent == 5.0

    def test_trailing_stop_model_calculate_take_profit_percent(self):
        trailing_stop = TrailingStopModel(take_profit=10500)
        take_profit_percent = trailing_stop.calculate_take_profit_percent(
            open_price=10000, side=OrderSideType.buy
        )
        assert take_profit_percent == 5.0

        take_profit_percent = trailing_stop.calculate_take_profit_percent(
            open_price=11000, side=OrderSideType.buy
        )
        assert take_profit_percent == 4.762

    def test_trailing_stop_model_to_mongodb_doc(self):
        trailing_stop = TrailingStopModel(
            stop_loss=9500, take_profit=10500, tp_increment=2
        )
        doc = trailing_stop.to_mongodb_doc()
        assert doc["stop_loss"] == 9500
        assert doc["take_profit"] == 10500
        assert doc["tp_increment"] == 2


# Unit tests for LeverageModel
class TestLeverageModel:
    def test_leverage_model_calculate_balance(self):
        leverage = LeverageModel(
            order_id="ord_123",
            session_id="sess_123",
            account_id="acc_123",
            symbol="BTCUSD",
            quantity=2,
            leverage=10,
            open_price=10000,
            side=OrderSideType.buy,
        )
        balance = leverage.calculate_balance()
        assert balance == 2000

    def test_leverage_model_to_mongodb_doc(self):
        leverage = LeverageModel(
            order_id="ord_123",
            session_id="sess_123",
            account_id="acc_123",
            symbol="BTCUSD",
            quantity=2,
            leverage=10,
            open_price=10000,
            side=OrderSideType.sell,
        )
        doc = leverage.to_mongodb_doc()
        assert doc["leverage"] == 10
        assert doc["quantity"] == 2
        assert doc["open_price"] == 10000
        assert doc["side"] == OrderSideType.sell


# Unit tests for TransactionModel
class TestTransactionModel:
    def test_transaction_model_to_mongodb_doc(self):
        transaction = TransactionModel(
            local_order_id="local_123",
            order_id="ord_123",
            session_id="sess_123",
            user_id="user_123",
            date_time=datetime.now(),
            type=TransactionType.API_CLOSE_POSITION,
            data={"price": 10000},
        )
        doc = transaction.to_mongodb_doc()
        assert doc["local_order_id"] == "local_123"
        assert doc["order_id"] == "ord_123"
        assert doc["session_id"] == "sess_123"
        assert doc["user_id"] == "user_123"
        assert doc["type"] == TransactionType.API_CLOSE_POSITION
        assert doc["data"] == {"price": 10000}


import pytest
from pydantic import ValidationError

# Assuming SymbolModel, SymbolStatus, and SymbolType are already imported


class TestSymbolModel:
    def test_symbol_model_initialization(self):
        symbol = SymbolModel(
            symbol="BTCUSD",
            name="Bitcoin",
            status=SymbolStatus.open,
            type=SymbolType.leverage,
            trading_time="24/7",
            currency="USD",
            quote_precision=2,
        )

        assert symbol.symbol == "BTCUSD"
        assert symbol.name == "Bitcoin"
        assert symbol.descr == "Bitcoin (BTCUSD)"  # description generated by validator
        assert symbol.status == SymbolStatus.open
        assert symbol.type == SymbolType.leverage
        assert symbol.trading_time == "24/7"
        assert symbol.currency == "USD"
        assert symbol.quote_precision == 2
        assert symbol.trading_fee is None

    def test_symbol_model_with_custom_description(self):
        symbol = SymbolModel(
            symbol="ETHUSD",
            name="ETHUSD",
            descr="Ethereum/US Dollar",
            status=SymbolStatus.open,
            type=SymbolType.leverage,
            trading_time="24/7",
            currency="USD",
            quote_precision=2,
        )
        # `descr` should still be overridden by the validator
        assert symbol.descr == "ETHUSD (ETHUSD)"

    def test_symbol_model_to_mongodb_doc(self):
        symbol = SymbolModel(
            symbol="BTCUSD",
            name="BTCUSD",
            status=SymbolStatus.open,
            type=SymbolType.spot,
            trading_time="24/7",
            currency="USD",
            quote_precision=2,
            trading_fee=0.1,
        )

        assert symbol.trading_fee == 0.1
