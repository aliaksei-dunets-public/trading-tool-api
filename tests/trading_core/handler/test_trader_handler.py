import pytest
from bson import ObjectId
from unittest.mock import patch, MagicMock
from datetime import datetime
from trading_core.handler import (
    TraderHandler,
    TraderModel,
    TraderStatus,
    Const,
    ExchangeId,
)


# Mock fixture for BufferSingleDictionary
@pytest.fixture
def mock_buffer_traders():
    buffer_mock = MagicMock()
    buffer_mock.is_data_in_buffer.return_value = False
    return buffer_mock


# Mock fixture for MongoTrader
@pytest.fixture
def mock_mongo_trader():
    mongo_mock = MagicMock()
    mongo_mock.insert_one.return_value = "123456789"
    mongo_mock.get_one.return_value = {
        "id": "123456789",
        "api_key": "mock_api_key",
        "api_secret": "mock_secret",
        "expired_dt": datetime(2099, 1, 1),
        "user_id": "user123",
        "exchange_id": ExchangeId.demo_dzengi_com,
    }
    return mongo_mock


# Mock fixture for ExchangeHandler
@pytest.fixture
def mock_exchange_handler():
    exchange_mock = MagicMock()
    exchange_mock.get_trader_model.return_value = TraderModel(
        id="123456789",
        user_id="user123",
        exchange_id=ExchangeId.demo_dzengi_com,
        api_key="mock_api_key",
        api_secret="mock_secret",
        expired_dt=datetime(2099, 1, 1),
    )
    exchange_mock.ping_server.return_value = True
    exchange_mock.get_accounts.return_value = {}
    return exchange_mock


# Mock fixture for Logger
@pytest.fixture
def mock_logger():
    with patch("trading_core.handler.logger") as logger_mock:
        yield logger_mock


# Unit tests for TraderHandler class
class TestTraderHandler:

    @pytest.fixture(autouse=True)
    def setup(self, mock_buffer_traders, mock_mongo_trader, mock_exchange_handler):
        self.handler = TraderHandler()
        self.handler._TraderHandler__buffer_traders = mock_buffer_traders
        self.mock_mongo_trader = mock_mongo_trader
        self.mock_exchange_handler = mock_exchange_handler

    def test_get_trader_from_buffer(self, mock_buffer_traders, mock_logger):
        # Arrange
        mock_buffer_traders.is_data_in_buffer.return_value = True
        mock_buffer_traders.get_buffer.return_value = TraderModel(
            _id="123456789",
            user_id="user123",
            exchange_id=ExchangeId.demo_dzengi_com,
            api_key="mock_api_key",
            api_secret="mock_secret",
            expired_dt=datetime(2099, 1, 1),
        )

        # Act
        result = self.handler.get_trader("123456789")

        # Assert
        mock_buffer_traders.get_buffer.assert_called_once_with(key="123456789")
        assert result.id == "123456789"

    # def test_get_trader_fetch_from_db(self, mock_buffer_traders, mock_mongo_trader):

    #     _id = ObjectId()
    #     str_id = str(_id)

    #     mock_buffer_traders.is_data_in_buffer.return_value = False
    #     mock_mongo_trader.get_one.return_value = {
    #         "id": _id,
    #         "api_key": "mock_api_key",
    #         "api_secret": "mock_secret",
    #         "expired_dt": datetime(2099, 1, 1),
    #         "user_id": "user123",
    #         "exchange_id": ExchangeId.demo_dzengi_com,
    #     }

    #     # Act
    #     result = self.handler.get_trader(str_id)

    #     # Assert
    #     mock_mongo_trader.get_one.assert_called_once_with(str_id)
    #     mock_buffer_traders.set_buffer.assert_called_once()
    #     assert result.id == str_id

    # def test_check_status_private_trader(self, mock_exchange_handler):
    #     # Arrange
    #     mock_exchange_handler.ping_server.return_value = True
    #     mock_exchange_handler.get_trader_model.return_value.expired_dt = datetime(
    #         2099, 1, 1
    #     )

    #     # Act
    #     result = self.handler.check_status("123456789")

    #     # Assert
    #     mock_exchange_handler.get_accounts.assert_called_once()
    #     assert result["status"] == TraderStatus.PRIVATE.value

    # def test_check_status_expired_trader(self, mock_exchange_handler):
    #     # Arrange
    #     mock_exchange_handler.get_trader_model.return_value.expired_dt = datetime(
    #         2020, 1, 1
    #     )

    #     # Act
    #     result = self.handler.check_status("123456789")

    #     # Assert
    #     assert result["status"] == TraderStatus.EXPIRED.value

    # def test_check_status_failed_ping(self, mock_exchange_handler):
    #     # Arrange
    #     mock_exchange_handler.ping_server.return_value = False

    #     # Act
    #     result = self.handler.check_status("123456789")

    #     # Assert
    #     assert result["status"] == TraderStatus.FAILED.value

    # def test_create_trader(self, mock_mongo_trader, mock_buffer_traders):
    #     # Arrange
    #     trader_model = TraderModel(
    #         id="123456789", api_key="mock_api_key", api_secret="mock_secret"
    #     )

    #     # Act
    #     result = self.handler.create_trader(trader_model)

    #     # Assert
    #     mock_mongo_trader.insert_one.assert_called_once()
    #     assert result.id == "123456789"
    #     mock_buffer_traders.set_buffer.assert_called_once()

    # def test_update_trader_with_encryption(
    #     self, mock_mongo_trader, mock_buffer_traders
    # ):
    #     # Arrange
    #     mock_buffer_traders.is_data_in_buffer.return_value = True
    #     trader_model = TraderModel(
    #         id="123456789",
    #         api_key="new_key",
    #         api_secret="new_secret",
    #         user_id="user123",
    #         exchange_id=ExchangeId.demo_dzengi_com,
    #     )
    #     mock_buffer_traders.get_buffer.return_value = trader_model
    #     query = {"api_key": "new_key", "api_secret": "new_secret"}

    #     # Act
    #     result = self.handler.update_trader("123456789", query)

    #     # Assert
    #     assert "api_key" in query
    #     assert "api_secret" in query
    #     mock_mongo_trader.update_one.assert_called_once_with(
    #         id="123456789", query=query
    #     )
    #     mock_buffer_traders.set_buffer.assert_called()

    # def test_delete_trader(self, mock_mongo_trader, mock_buffer_traders):
    #     # Act
    #     result = self.handler.delete_trader("123456789")

    #     # Assert
    #     mock_mongo_trader.delete_one.assert_called_once_with(id="123456789")
    #     mock_buffer_traders.remove_from_buffer.assert_called_once_with(key="123456789")
    #     assert result

    def test_get_default_trader_raises_exception(self, mock_mongo_trader):
        # Arrange
        mock_mongo_trader.get_many.return_value = []

        # Act / Assert
        with pytest.raises(Exception) as exc_info:
            self.handler.get_default_trader(exchange_id="exch123")
        assert str(exc_info.value) == "Exchange Id exch123 doesn't maintained"

    # def test_get_traders_by_email(self, mock_buffer_traders):
    #     # Arrange
    #     mock_user_handler = MagicMock()
    #     mock_user_handler.get_user_by_email.return_value = MagicMock(
    #         id="user123", technical_user=False
    #     )
    #     buffer_runtime_handler.get_user_handler.return_value = mock_user_handler

    #     # Act
    #     result = self.handler.get_traders_by_email(user_email="test@example.com")

    #     # Assert
    #     mock_user_handler.get_user_by_email.assert_called_once_with(
    #         email="test@example.com"
    #     )
    #     mock_buffer_traders.set_buffer.assert_called()
    #     assert isinstance(result, list)
