import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from bson import ObjectId

from trading_core.mongodb import (
    MongoBase,
    MongoJobs,
    MongoSimulations,
    MongoUser,
    Const,
)


@pytest.fixture
@patch("trading_core.mongodb.pymongo.MongoClient")  # Patch pymongo MongoClient
@patch("trading_core.core.config.get_env_value")  # Patch the config environment
def mock_mongo_base(mock_get_env_value, mock_mongo_client):
    # Mock environment variable for MongoDB URI
    mock_get_env_value.return_value = "mongodb://test_uri"
    mock_db = MagicMock()  # Mock MongoDB database
    mock_mongo_client.return_value = mock_db

    mongo_base = MongoBase()  # Create an instance of MongoBase with mocks
    mongo_base._collection = MagicMock()  # Mock the collection
    return mongo_base, mock_db  # Return the base instance and mock_db for further use


# # Fixture to mock datetime.utcnow
# @pytest.fixture
# @patch("trading_core.mongodb.datetime")  # Patch datetime at the correct module
# def mock_datetime(mock_datetime):
#     mock_datetime.utcnow.return_value = datetime(2024, 10, 10)  # Mock datetime.utcnow
#     return mock_datetime


class TestMongoBase:
    def test_get_collection(self, mock_mongo_base):
        mongo_base, mock_db = mock_mongo_base
        collection = mongo_base.get_collection("test_collection")
        assert collection.name == "test_collection"

    def test_insert_one_success(self, mock_mongo_base, mock_datetime):
        mongo_base, _ = mock_mongo_base
        mongo_base._collection.insert_one.return_value.inserted_id = (
            ObjectId()
        )  # Mock insert_one result

        mock_query = {"key": "value"}
        result_id = mongo_base.insert_one(mock_query)

        assert result_id is not None
        assert mongo_base._collection.insert_one.called

        # Check that timestamps were added
        mock_query[Const.DB_CREATED_AT] = mock_datetime.utcnow.return_value
        mock_query[Const.DB_CHANGED_AT] = mock_datetime.utcnow.return_value
        mongo_base._collection.insert_one.assert_called_with(mock_query)

    def test_insert_one_empty_query(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        with pytest.raises(Exception, match="DB: INSERT_ONE - Query is empty"):
            mongo_base.insert_one({})

    def test_insert_many_success(self, mock_mongo_base, mock_datetime):
        mongo_base, _ = mock_mongo_base
        entries = [{"key": "value"}, {"key2": "value2"}]

        mongo_base.insert_many(entries)

        assert mongo_base._collection.insert_many.called
        for entry in entries:
            assert Const.DB_CREATED_AT in entry
            assert Const.DB_CHANGED_AT in entry

    def test_insert_many_empty_entries(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        with pytest.raises(Exception, match="DB: INSERT_MANY - Entries are missed"):
            mongo_base.insert_many([])

    def test_update_one(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        id = str(ObjectId())
        query = {"key": "new_value"}

        mongo_base.update_one(id, query)
        assert mongo_base._collection.update_one.called

    def test_delete_one(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        mongo_base._collection.delete_one.return_value.deleted_count = 1
        id = str(ObjectId())

        assert mongo_base.delete_one(id)
        assert mongo_base._collection.delete_one.called

    def test_delete_many(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        mongo_base._collection.delete_many.return_value.deleted_count = 2
        query = {"key": "value"}

        assert mongo_base.delete_many(query)
        assert mongo_base._collection.delete_many.called

    def test_get_one(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        id = str(ObjectId())
        mongo_base.get_one(id)

        assert mongo_base._collection.find_one.called

    def test_get_one_by_filter(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        query = {"key": "value"}
        mongo_base.get_one_by_filter(query)

        assert mongo_base._collection.find_one.called

    def test_get_many(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        mongo_base.get_many()

        assert mongo_base._collection.find.called

    def test_get_count(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        mongo_base.get_count()

        assert mongo_base._collection.count_documents.called

    def test_aggregate(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        query = [{"$match": {"key": "value"}}]

        mongo_base.aggregate(query)
        assert mongo_base._collection.aggregate.called

    def test_add_param_to_query(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        query = {}
        param = "key"
        value = "value"
        result = mongo_base.add_param_to_query(query, param, value)

        assert result == {param: value}

    def test_add_multi_param_to_query(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        query = {}
        param = "key"
        values = ["value1", "value2"]
        result = mongo_base.add_multi_pram_to_query(query, param, values)

        assert result == {param: {"$in": values}}

    def test_convert_id(self, mock_mongo_base):
        mongo_base, _ = mock_mongo_base
        with pytest.raises(Exception, match="DB: _id is missed"):
            mongo_base._convert_id(None)

        assert isinstance(mongo_base._convert_id(str(ObjectId())), ObjectId)


# class TestMongoJobs:
#     @patch("module_where_code_is_located.MongoBase.insert_one")
#     def test_create_job(self, mock_insert_one):
#         mock_insert_one.return_value = str(ObjectId())
#         mongo_jobs = MongoJobs()
#         job_id = mongo_jobs.create_job("test_job", "daily")

#         assert job_id is not None
#         mock_insert_one.assert_called_once()

#     def test_get_active_jobs(self):
#         mongo_jobs = MongoJobs()
#         mongo_jobs.get_many = MagicMock(return_value=[{"job": "active"}])
#         jobs = mongo_jobs.get_active_jobs()

#         assert jobs == [{"job": "active"}]

#     @patch("module_where_code_is_located.MongoBase.delete_one")
#     def test_delete_job(self, mock_delete_one):
#         mock_delete_one.return_value = True
#         mongo_jobs = MongoJobs()
#         result = mongo_jobs.delete_job(str(ObjectId()))

#         assert result
#         mock_delete_one.assert_called_once()
