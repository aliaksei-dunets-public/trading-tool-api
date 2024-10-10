import pytest
from unittest.mock import MagicMock, patch
from trading_core.handler import (
    BufferSingleDictionary,
    UserHandler,
    UserModel,
)


@pytest.fixture
def mock_user_model():
    """Fixture to provide a mock user model."""
    return UserModel(email="test@example.com", first_name="John", second_name="Doe")


@pytest.fixture
def mock_user_handler():
    """Fixture to provide a UserHandler instance with a mocked buffer."""
    handler = UserHandler()
    handler._UserHandler__buffer_users = MagicMock(BufferSingleDictionary())
    return handler


@pytest.fixture
def mock_mongo_user():
    """Fixture to mock MongoUser."""
    with patch("trading_core.handler.MongoUser") as mock:
        yield mock


@pytest.fixture
def mock_logger():
    """Fixture to mock logger."""
    with patch("trading_core.handler.logger") as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Fixture to mock config."""
    with patch("trading_core.core.config") as mock:
        yield mock


class TestUserHandler:

    def test_get_buffer(self, mock_user_handler):
        """Test get_buffer returns the buffer instance."""
        buffer = mock_user_handler.get_buffer()
        assert isinstance(buffer, BufferSingleDictionary)

    def test_get_user_by_email_from_buffer(
        self, mock_user_handler, mock_config, mock_logger
    ):
        """Test get_user_by_email when the user is already in the buffer."""
        mock_user_handler._UserHandler__buffer_users.is_data_in_buffer.return_value = (
            True
        )
        mock_user_handler._UserHandler__buffer_users.get_buffer.return_value = (
            "mock_user"
        )

        result = mock_user_handler.get_user_by_email("test@example.com")

        mock_user_handler._UserHandler__buffer_users.is_data_in_buffer.assert_called_once_with(
            "test@example.com"
        )
        mock_user_handler._UserHandler__buffer_users.get_buffer.assert_called_once_with(
            "test@example.com"
        )
        assert result == "mock_user"

    def test_get_user_by_email_not_in_buffer(
        self, mock_user_handler, mock_mongo_user, mock_user_model
    ):
        """Test get_user_by_email when the user is not in the buffer."""
        mock_user_handler._UserHandler__buffer_users.is_data_in_buffer.return_value = (
            False
        )
        mock_mongo_user().get_one_by_filter.return_value = {
            "email": "test@example.com",
            "first_name": "John",
            "second_name": "Doe",
        }

        result = mock_user_handler.get_user_by_email("test@example.com")

        assert result == mock_user_model

    def test_create_user_success(self, mock_mongo_user, mock_user_model):
        """Test create_user successful creation."""
        mock_mongo_user().insert_one.return_value = "mock_id"
        with patch.object(UserHandler, "get_user_by_id", return_value=mock_user_model):
            result = UserHandler.create_user(mock_user_model)

        mock_mongo_user().insert_one.assert_called_once()
        assert result == mock_user_model

    def test_create_user_failure(self, mock_mongo_user, mock_user_model, mock_logger):
        """Test create_user when insertion raises an exception."""
        mock_mongo_user().insert_one.side_effect = Exception("User already exists")
        with pytest.raises(Exception, match="User test@example.com already exists"):
            UserHandler.create_user(mock_user_model)

    def test_delete_user(self, mock_user_handler, mock_mongo_user):
        """Test delete_user functionality."""
        mock_mongo_user().delete_one.return_value = "deleted"
        mock_user_handler.get_buffer().clear_buffer = MagicMock()

        result = mock_user_handler.delete_user("test_user_id")

        mock_mongo_user().delete_one.assert_called_once_with(id="test_user_id")
        assert result == "deleted"

    def test_update_user(self, mock_mongo_user):
        """Test update_user method."""
        mock_mongo_user().update_one.return_value = "updated"

        result = UserHandler.update_user(
            id="test_id", query={"email": "newemail@example.com"}
        )

        mock_mongo_user().update_one.assert_called_once_with(
            id="test_id", query={"email": "newemail@example.com"}
        )
        assert result == "updated"

    def test_get_user_by_id(self, mock_mongo_user, mock_user_model):
        """Test get_user_by_id when user exists."""
        mock_mongo_user().get_one.return_value = {
            "email": "test@example.com",
            "first_name": "1",
            "second_name": "b",
            "technical_user": True,
        }

        result = UserHandler.get_user_by_id("test_id")

        assert result.email == "test@example.com"

    def test_get_user_by_id_user_does_not_exist(self, mock_mongo_user):
        """Test get_user_by_id when user doesn't exist."""
        mock_mongo_user().get_one.return_value = None

        with pytest.raises(Exception, match=f"User test_id doesn't exists"):
            UserHandler.get_user_by_id("test_id")

    def test_get_technical_user(self, mock_mongo_user, mock_user_model):
        """Test get_technical_user when a technical user exists."""
        mock_mongo_user().get_many.return_value = [
            {
                "email": "test@example.com",
                "first_name": "1",
                "second_name": "b",
                "technical_user": True,
            }
        ]

        result = UserHandler.get_technical_user()

        assert result.email == "test@example.com"

    def test_get_technical_user_no_technical_user(self, mock_mongo_user):
        """Test get_technical_user when no technical user exists."""
        mock_mongo_user().get_many.return_value = []

        with pytest.raises(Exception, match=f"Technical User isn't maintained"):
            UserHandler.get_technical_user()
