import pymongo
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime

from .constants import Const

load_dotenv()

mongodb_uri = os.getenv("MONGO_CONFIG")

try:
    if not mongodb_uri:
        raise Exception(
            'Mongo Config is not maintained in the environment values')
except KeyError:
    raise Exception(
        'Mongo Config is not maintained in the environment values')

client = pymongo.MongoClient(mongodb_uri)
database = client['ClusterShared']


class MongoBase():
    def __init__(self):

        self._collection = None

    def get_collection(self, name: str):
        return database[name]

    def insert_one(self, query: dict) -> str:
        if not query:
            raise Exception(f'DB: INSERT_ONE - Query is empty')
        else:
            query[Const.DB_CREATED_AT] = datetime.utcnow()
            query[Const.DB_CHANGED_AT] = datetime.utcnow()
        result = self._collection.insert_one(query)
        return str(result.inserted_id)

    def update_one(self, id: str, query: dict) -> bool:
        if not id:
            raise Exception(f'DB: GET_ONE - ID is empty')
        elif not query:
            raise Exception(f'DB: INSERT_ONE - Query is empty')
        else:
            query[Const.DB_CHANGED_AT] = datetime.utcnow()

        result = self._collection.update_one({Const.DB_ID: ObjectId(id)},
                                             {"$set": query})
        if result.modified_count == 1:
            return True
        return False

    def delete_one(self, id: str) -> bool:
        if not id:
            raise Exception(f'DB: DELETE_ONE - ID is empty')
        result = self._collection.delete_one({Const.DB_ID: ObjectId(id)})
        return result.deleted_count > 0

    def get_one(self, id: str) -> dict:
        if not id:
            raise Exception(f'DB: GET_ONE - ID is empty')
        result = self._collection.find_one({Const.DB_ID: ObjectId(id)})
        return result

    def get_many(self, query: dict = {}) -> list:
        return list(self._collection.find(query))

    def add_param_to_query(self, query: dict, param: str, value: str) -> dict:
        if value:
            query[param] = value

        return query


class MongoJobs(MongoBase):
    def __init__(self):
        MongoBase.__init__(self)
        self._collection = self.get_collection(Const.DB_COLLECTION_JOBS)

    def get_active_jobs(self):
        return self.get_many({Const.DB_IS_ACTIVE: True})

    def create_job(self, job_type: str, interval: str, is_active: bool = True) -> str:
        query = {Const.DB_JOB_TYPE: job_type,
                 Const.DB_INTERVAL: interval,
                 Const.DB_IS_ACTIVE: is_active}
        return self.insert_one(query)

    def delete_job(self, job_id: str) -> bool:
        return self.delete_one(id=job_id)

    def activate_job(self, job_id: str) -> bool:
        return self.update_one(id=job_id, query={Const.DB_IS_ACTIVE: True})

    def deactivate_job(self, job_id: str) -> bool:
        return self.update_one(id=job_id, query={Const.DB_IS_ACTIVE: False})


class MongoAlerts(MongoBase):
    def __init__(self):
        MongoBase.__init__(self)
        self._collection = self.get_collection(Const.DB_COLLECTION_ALERTS)

    def get_alerts(self, alert_type: str = None, symbol: str = None, interval: str = None) -> list:
        query = {}
        query = self.add_param_to_query(
            query=query, param=Const.DB_ALERT_TYPE, value=alert_type)
        query = self.add_param_to_query(
            query=query, param=Const.DB_SYMBOL, value=symbol)
        query = self.add_param_to_query(
            query=query, param=Const.DB_INTERVAL, value=interval)

        return self.get_many(query)

    def create_alert(self, alert_type: str, channel_id: str, symbol: str, interval: str, strategies: list, signals: list, comment: str) -> str:
        query = {Const.DB_ALERT_TYPE: alert_type,
                 Const.DB_CHANNEL_ID: channel_id,
                 Const.DB_SYMBOL: symbol,
                 Const.DB_INTERVAL: interval,
                 Const.DB_STRATEGIES: strategies,
                 Const.DB_SIGNALS: signals,
                 Const.DB_COMMENT: comment}
        return self.insert_one(query)

    def update_alert(self, id: str, interval: str, strategies: list, signals: list, comment: str) -> bool:
        query = {Const.DB_INTERVAL: interval,
                 Const.DB_STRATEGIES: strategies,
                 Const.DB_SIGNALS: signals,
                 Const.DB_COMMENT: comment}
        return self.update_one(id=id, query=query)


class MongoOrders(MongoBase):
    def __init__(self):
        MongoBase.__init__(self)
        self._collection = self.get_collection(Const.DB_COLLECTION_ORDERS)

    def get_orders(self, symbol: str = None, interval: str = None) -> list:
        query = {}
        query = self.add_param_to_query(
            query=query, param=Const.DB_SYMBOL, value=symbol)
        query = self.add_param_to_query(
            query=query, param=Const.DB_INTERVAL, value=interval)

        return self.get_many(query)

    def create_order(self, order_type: str, open_date_time: str, symbol: str, interval: str, price: float, quantity: float, strategies: list):
        open_date_time = datetime.fromisoformat(
            open_date_time) if open_date_time else datetime.now()

        query = {Const.DB_ORDER_TYPE: order_type,
                 Const.DB_OPEN_DATE_TIME: open_date_time,
                 Const.DB_SYMBOL: symbol,
                 Const.DB_INTERVAL: interval,
                 Const.DB_PRICE: price,
                 Const.DB_QUANTITY: quantity,
                 Const.DB_STRATEGIES: strategies}
        return self.insert_one(query)
