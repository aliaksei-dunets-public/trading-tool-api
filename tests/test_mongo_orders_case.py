import unittest

from trading_core.constants import Const
from trading_core.mongodb import MongoOrders


class MongoOrdersTestCase(unittest.TestCase):

    def setUp(self):
        self.mongo_orders = MongoOrders()

    def test_db_orders_functionality(self):
        order_type = Const.LONG
        open_date_time = ''
        symbol = "BTC/USD"
        interval = Const.TA_INTERVAL_5M
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100,
                      Const.TA_STRATEGY_CCI_20_TREND_100]

        self.document_id = self.mongo_orders.create_order(
            order_type, open_date_time, symbol, interval, 100, 1.1, strategies)

        result = self.mongo_orders.get_orders(interval=interval)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        result = self.mongo_orders.get_orders(symbol=symbol)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        self.mongo_orders.delete_one(self.document_id)
        result_get_one = self.mongo_orders.get_one(self.document_id)
        self.assertIsNone(result_get_one)
