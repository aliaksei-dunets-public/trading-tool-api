import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pandas as pd
from trading_core.handler import (
    BufferBaseHandler,
    BufferSingleDictionary,
    BufferHistoryDataHandler,
    BufferTimeFrame,
)

from trading_core.common import HistoryDataModel, HistoryDataParamModel, IntervalType


# Mocking configuration and logging
@pytest.fixture
@patch("trading_core.core.config.get_config_value")
@patch("trading_core.handler.logger")
def mock_dependencies(mock_logger, mock_get_config_value):
    mock_get_config_value.return_value = True
    return mock_logger, mock_get_config_value


# Tests for BufferBaseHandler class
class TestBufferBaseHandler:
    @pytest.fixture
    def buffer_base_handler(self):
        return BufferBaseHandler()

    def test_get_buffer(self, buffer_base_handler, mock_dependencies):
        mock_logger, _ = mock_dependencies
        result = buffer_base_handler.get_buffer()
        assert result == {}

    def test_is_data_in_buffer(self, buffer_base_handler):
        buffer_base_handler._buffer = {"key": "value"}
        assert buffer_base_handler.is_data_in_buffer() is True

    def test_set_buffer(self, buffer_base_handler, mock_dependencies):
        mock_logger, _ = mock_dependencies
        buffer_base_handler.set_buffer({"key": "value"})
        assert buffer_base_handler._buffer == {"key": "value"}

    def test_clear_buffer(self, buffer_base_handler, mock_dependencies):
        mock_logger, _ = mock_dependencies
        buffer_base_handler._buffer = {"key": "value"}
        buffer_base_handler.clear_buffer()
        assert buffer_base_handler._buffer == {}


# Tests for BufferSingleDictionary class
class TestBufferSingleDictionary:
    @pytest.fixture
    def buffer_single_dict(self):
        return BufferSingleDictionary()

    def test_get_buffer_key_exists(self, buffer_single_dict):
        buffer_single_dict._buffer = {"key": {"data": "value"}}
        result = buffer_single_dict.get_buffer("key")
        assert result == {"data": "value"}

    def test_get_buffer_key_not_exist(self, buffer_single_dict):
        buffer_single_dict._buffer = {}
        result = buffer_single_dict.get_buffer("non_existing_key")
        assert result is None

    def test_is_data_in_buffer_key_exists(self, buffer_single_dict):
        buffer_single_dict._buffer = {"key": "value"}
        assert buffer_single_dict.is_data_in_buffer("key") is True

    def test_set_buffer(self, buffer_single_dict, mock_dependencies):
        mock_logger, _ = mock_dependencies
        buffer_single_dict.set_buffer("key", {"data": "value"})
        assert buffer_single_dict._buffer["key"] == {"data": "value"}

    def test_remove_from_buffer(self, buffer_single_dict, mock_dependencies):
        mock_logger, _ = mock_dependencies
        buffer_single_dict._buffer = {"key": "value"}
        buffer_single_dict.remove_from_buffer("key")
        assert "key" not in buffer_single_dict._buffer


# Tests for BufferHistoryDataHandler class
class TestBufferHistoryDataHandler:
    @pytest.fixture
    def buffer_history_handler(self):
        return BufferHistoryDataHandler()

    def test_get_buffer(self, buffer_history_handler, mock_dependencies):
        mock_logger, _ = mock_dependencies
        mock_param = HistoryDataParamModel(
            symbol="BTCUSD", interval=IntervalType.MIN_30, limit=1
        )
        mock_data = pd.DataFrame(
            {"price": [100, 200]}, index=pd.to_datetime(["2024-10-10", "2024-10-11"])
        )
        buffer_history_handler._buffer = {
            ("BTCUSD", IntervalType.MIN_30.value): HistoryDataModel(
                symbol="BTCUSD", interval=IntervalType.MIN_30, limit=10, data=mock_data
            )
        }

        result = buffer_history_handler.get_buffer(
            mock_param, end_datetime="2024-10-11"
        )
        assert result.symbol == "BTCUSD"
        assert len(result.data) == 1

    def test_is_data_in_buffer_key_exists(self, buffer_history_handler):
        buffer_history_handler._buffer = {
            ("BTCUSD", IntervalType.MIN_30.value): "some_data"
        }
        assert (
            buffer_history_handler.is_data_in_buffer(
                ("BTCUSD", IntervalType.MIN_30.value)
            )
            is True
        )

    def test_set_buffer(self, buffer_history_handler, mock_dependencies):
        mock_logger, _ = mock_dependencies
        mock_data = HistoryDataModel(
            symbol="BTCUSD",
            interval=IntervalType.MIN_30,
            limit=10,
            data=pd.DataFrame(
                {"price": [100, 200]},
                index=pd.to_datetime(["2024-10-10", "2024-10-11"]),
            ),
        )
        buffer_history_handler.set_buffer(mock_data)
        assert (
            buffer_history_handler._buffer[("BTCUSD", IntervalType.MIN_30.value)]
            == mock_data
        )

    def test_validate_data_in_buffer(self, buffer_history_handler):
        mock_data = pd.DataFrame({"price": [100]}, index=pd.to_datetime(["2024-10-10"]))
        buffer_history_handler._buffer = {
            ("BTCUSD", IntervalType.MIN_30.value): HistoryDataModel(
                symbol="BTCUSD",
                interval=IntervalType.MIN_30,
                limit=10,
                data=mock_data,
                end_date_time=datetime(2024, 10, 10),
            )
        }
        result = buffer_history_handler.validate_data_in_buffer(
            ("BTCUSD", IntervalType.MIN_30.value), 5, datetime(2024, 10, 10)
        )
        assert result is True

    def test_get_buffer_key(self, buffer_history_handler):
        result = buffer_history_handler.get_buffer_key("BTCUSD", IntervalType.MIN_30)
        assert result == ("BTCUSD", IntervalType.MIN_30.value)


# Tests for BufferTimeFrame class
class TestBufferTimeFrame:
    @pytest.fixture
    def buffer_time_frame(self):
        return BufferTimeFrame()

    def test_get_buffer_key_exists(self, buffer_time_frame):
        buffer_time_frame._buffer = {"10:00": {"data": "value"}}
        result = buffer_time_frame.get_buffer("10:00")
        assert result == {"data": "value"}

    def test_get_buffer_key_not_exist(self, buffer_time_frame):
        result = buffer_time_frame.get_buffer("10:00")
        assert result is None

    def test_is_data_in_buffer_key_exists(self, buffer_time_frame):
        buffer_time_frame._buffer = {"10:00": "value"}
        assert buffer_time_frame.is_data_in_buffer("10:00") is True

    def test_set_buffer(self, buffer_time_frame):
        buffer_time_frame.set_buffer("10:00", {"data": "value"})
        assert buffer_time_frame._buffer["10:00"] == {"data": "value"}
