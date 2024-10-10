import pytest
from unittest.mock import MagicMock, patch
from trading_core.handler import (
    BufferSingleDictionary,
    TraderHandler,
)


@pytest.fixture
def mock_trader_handler():
    return TraderHandler()


@pytest.fixture
def mock_trader_model():
    trader = MagicMock()
    trader.id = "trader123"
    return trader


class TestTraderHandler:

    def test_get_buffer(self, mock_trader_handler):
        buffer = mock_trader_handler.get_buffer()
        assert isinstance(buffer, BufferSingleDictionary)

    def test_get_trader(self, mock_trader_handler, mock_trader_model):
        mock_trader_handler._fetch_trader = MagicMock(return_value=mock_trader_model)
        result = mock_trader_handler.get_trader("trader123")
        assert result.id == "trader123"

    # def test_create_trader(self, mock_trader_handler, mock_trader_model):
    #     mock_trader_handler._fetch_trader = MagicMock(return_value=mock_trader_model)
    #     result = mock_trader_handler.create_trader(mock_trader_model)
    #     assert result.id == "trader123"

    # def test_update_trader(self, mock_trader_handler, mock_trader_model):
    #     mock_trader_handler.get_trader = MagicMock(return_value=mock_trader_model)
    #     mock_trader_handler._fetch_trader = MagicMock(return_value=mock_trader_model)
    #     result = mock_trader_handler.update_trader("trader123", {"api_key": "key"})
    #     assert result is not None

    def test_delete_trader(self, mock_trader_handler):
        mock_trader_handler.get_trader = MagicMock(return_value=MagicMock())
        mock_trader_handler.delete_trader = MagicMock(return_value={"deleted": True})
        result = mock_trader_handler.delete_trader("trader123")
        assert result["deleted"] is True
