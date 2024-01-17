import pymongo
from bson import ObjectId
from datetime import datetime
import logging

from .constants import Const
from trading_core.core import config

mongodb_uri = config.get_env_value("MONGO_CONFIG")
client = pymongo.MongoClient(mongodb_uri)
database = client[Const.DATABASE_NAME]

# indexes:
# users -> email_asc | REGULAR | UNIQUE
# traders -> user_id_exchange_asc | REGULAR | UNIQUE/COMPOUND

# Set up logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[logging.StreamHandler()],
# )

logger = logging.getLogger("db")


class MongoBase:
    def __init__(self):
        self._collection = None

    def get_collection(self, name: str):
        return database[name]

    def insert_one(self, query: dict) -> str:
        if not query:
            raise Exception(f"DB: INSERT_ONE - Query is empty")
        else:
            query[Const.DB_CREATED_AT] = datetime.utcnow()
            query[Const.DB_CHANGED_AT] = datetime.utcnow()

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - insert_one({query})"
            )

        result = self._collection.insert_one(query)
        return str(result.inserted_id)

    def insert_many(self, entries: list) -> list:
        if not entries:
            raise Exception(f"DB: INSERT_MANY - Entries are missed")
        else:
            for entry in entries:
                entry[Const.DB_CREATED_AT] = datetime.utcnow()
                entry[Const.DB_CHANGED_AT] = datetime.utcnow()

            if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                logger.info(
                    f"{self.__class__.__name__}: {self._collection.name} - insert_many({entry})"
                )

            result = self._collection.insert_many(entries)
            return result.inserted_ids

    def update_one(self, id: str, query: dict) -> bool:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - update_one({query}) for id: {id}"
            )
        return self.__update_one(id=id, query=query)

    def upsert_one(self, id: str, query: dict) -> bool:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - upsert_one({query}) for id: {id}"
            )
        return self.__update_one(id=id, query=query, upsert=True)

    def delete_one(self, id: str) -> bool:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - delete_one({id})"
            )
        result = self._collection.delete_one({Const.DB_ID: self._convert_id(id)})
        return result.deleted_count > 0

    def delete_many(self, query: dict) -> bool:
        if not query:
            raise Exception(f"DB: delete_many - Query is empty")
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - delete_many({query})"
            )
        result = self._collection.delete_many(query)
        return result.deleted_count > 0

    def get_one(self, id: str) -> dict:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - get_one({id})"
            )
        result = self._collection.find_one({Const.DB_ID: self._convert_id(id)})
        return result

    def get_one_by_filter(self, query: dict) -> dict:
        if not query:
            raise Exception(f"DB: get_one_by_filter - Query is empty")
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - get_one_by_filter({query})"
            )
        result = self._collection.find_one(query)
        return result

    def get_many(self, query: dict = {}) -> list:
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - get_many({query})"
            )
        return list(self._collection.find(query))

    def aggregate(self, query: dict = {}) -> list:
        if not query:
            raise Exception(f"DB: aggregate - Query is empty")
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: {self._collection.name} - aggregate({query})"
            )
        return list(self._collection.aggregate(query))

    def add_param_to_query(self, query: dict, param: str, value: str) -> dict:
        if value:
            query[param] = value

        return query

    def add_multi_pram_to_query(self, query: dict, param: str, values: list) -> dict:
        if values:
            query[param] = {"$in": values}

        return query

    def __update_one(self, id: str, query: dict, upsert: bool = False) -> bool:
        if not query:
            raise Exception(f"DB: INSERT_ONE - Query is empty")
        else:
            query[Const.DB_CHANGED_AT] = datetime.utcnow()

        result = self._collection.update_one(
            {Const.DB_ID: self._convert_id(id)}, {"$set": query}, upsert
        )

        if result.modified_count == 1:
            return True
        else:
            return False

    def _convert_id(self, id: str) -> str:
        if not id:
            raise Exception(f"DB: _id is missed")

        return ObjectId(id)


class MongoJobs(MongoBase):
    def __init__(self):
        MongoBase.__init__(self)
        self._collection = self.get_collection(Const.DB_COLLECTION_JOBS)

    def get_active_jobs(self):
        return self.get_many({Const.DB_IS_ACTIVE: True})

    def create_job(self, job_type: str, interval: str, is_active: bool = True) -> str:
        query = {
            Const.DB_JOB_TYPE: job_type,
            Const.DB_INTERVAL: interval,
            Const.DB_IS_ACTIVE: is_active,
        }
        return self.insert_one(query)

    def delete_job(self, job_id: str) -> bool:
        return self.delete_one(id=job_id)

    def activate_job(self, job_id: str) -> bool:
        return self.update_one(id=job_id, query={Const.DB_IS_ACTIVE: True})

    def deactivate_job(self, job_id: str) -> bool:
        return self.update_one(id=job_id, query={Const.DB_IS_ACTIVE: False})


class MongoAlert(MongoBase):
    def __init__(self):
        MongoBase.__init__(self)
        self._collection = self.get_collection(Const.DB_COLLECTION_ALERTS)


class MongoSimulations(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_SIMULATIONS)

    def _convert_id(self, id: str) -> str:
        if not id:
            raise Exception(f"DB: _id is missed")

        return id

    def get_simulations(self, symbols: list, intervals: list, strategies: list) -> list:
        query = {}

        self.add_multi_pram_to_query(query=query, param=Const.DB_SYMBOL, values=symbols)
        self.add_multi_pram_to_query(
            query=query, param=Const.DB_INTERVAL, values=intervals
        )
        self.add_multi_pram_to_query(
            query=query, param=Const.DB_STRATEGY, values=strategies
        )

        return MongoSimulations().get_many(query)


class MongoUser(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_USERS)


class MongoChannel(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_CHANNELS)


class MongoSession(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_SESSIONS)


class MongoTrader(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_TRADERS)


class MongoBalance(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_BALANCES)


class MongoOrder(MongoBase):
    def __init__(self):
        MongoBase.__init__(self)
        self._collection = self.get_collection(Const.DB_COLLECTION_ORDERS)


class MongoLeverage(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_LEVERAGES)


class MongoTransaction(MongoBase):
    def __init__(self):
        super().__init__()
        self._collection = self.get_collection(Const.DB_COLLECTION_TRANSACTIONS)
