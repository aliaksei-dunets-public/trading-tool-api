import unittest
from bson import ObjectId

from trading_core.constants import Const
from trading_core.mongodb import MongoBase


class MongoBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.mongo_base = MongoBase()
        collection_name = Const.DB_COLLECTION_ALERTS
        self.mongo_base._collection = self.mongo_base.get_collection(
            collection_name)

    def test_get_collection(self):
        collection_name = Const.DB_COLLECTION_ALERTS
        collection = self.mongo_base.get_collection(collection_name)
        self.assertEqual(collection.name, collection_name)

    def test_functionality(self):
        query = {Const.DB_ALERT_TYPE: Const.ALERT_TYPE_BOT,
                 Const.DB_CHANNEL_ID: 689916629,
                 Const.DB_SYMBOL: "BTC/USD",
                 Const.DB_INTERVAL: Const.TA_INTERVAL_5M,
                 Const.DB_STRATEGIES: [Const.TA_STRATEGY_CCI_14_TREND_100, Const.TA_STRATEGY_CCI_20_TREND_100],
                 Const.DB_SIGNALS: [Const.DEBUG_SIGNAL],
                 Const.DB_COMMENT: "Test comments"}
        self.document_id = self.mongo_base.insert_one(query)
        self.assertIsInstance(self.document_id, str)
        self.assertTrue(ObjectId.is_valid(self.document_id))

        result_get_one = self.mongo_base.get_one(self.document_id)
        self.assertEqual(
            result_get_one[Const.DB_ALERT_TYPE], Const.ALERT_TYPE_BOT)
        self.assertEqual(result_get_one[Const.DB_CHANNEL_ID], 689916629)
        self.assertEqual(result_get_one[Const.DB_SYMBOL], "BTC/USD")
        self.assertEqual(
            result_get_one[Const.DB_INTERVAL], Const.TA_INTERVAL_5M)
        self.assertEqual(result_get_one[Const.DB_STRATEGIES], [
            Const.TA_STRATEGY_CCI_14_TREND_100, Const.TA_STRATEGY_CCI_20_TREND_100])
        self.assertEqual(result_get_one[Const.DB_SIGNALS], [
                         Const.DEBUG_SIGNAL])
        self.assertEqual(result_get_one[Const.DB_COMMENT], "Test comments")

        query_update = {Const.DB_STRATEGIES: [Const.TA_STRATEGY_CCI_14_TREND_100],
                        Const.DB_SIGNALS: [],
                        Const.DB_COMMENT: "Test comments updated"}
        result = self.mongo_base.update_one(self.document_id, query_update)
        self.assertTrue(result)

        result_get_one = self.mongo_base.get_one(self.document_id)
        self.assertEqual(result_get_one[Const.DB_STRATEGIES], [
            Const.TA_STRATEGY_CCI_14_TREND_100])
        self.assertEqual(result_get_one[Const.DB_SIGNALS], [])
        self.assertEqual(
            result_get_one[Const.DB_COMMENT], "Test comments updated")

        query = {Const.DB_INTERVAL: Const.TA_INTERVAL_5M}
        result = self.mongo_base.get_many(query)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        result = self.mongo_base.delete_one(self.document_id)
        self.assertTrue(result)

        result_get_one = self.mongo_base.get_one(self.document_id)
        self.assertIsNone(result_get_one)
