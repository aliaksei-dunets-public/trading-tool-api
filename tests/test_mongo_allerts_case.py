import unittest
from bson import ObjectId

from trading_core.constants import Const
from trading_core.mongodb import MongoAlerts


class MongoAlertsTestCase(unittest.TestCase):

    def setUp(self):
        self.mongo_alerts = MongoAlerts()

    def test_db_alerts_functionality(self):
        alert_type = Const.ALERT_TYPE_BOT
        channel_id = 689916629
        symbol = "BTC/USD"
        interval = Const.TA_INTERVAL_5M
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100,
                      Const.TA_STRATEGY_CCI_20_TREND_100]
        signals = [Const.DEBUG_SIGNAL]
        comment = "Test comments"

        self.document_id = self.mongo_alerts.create_alert(alert_type,
                                                          channel_id,
                                                          symbol,
                                                          interval,
                                                          strategies,
                                                          signals,
                                                          comment)

        self.assertTrue(ObjectId.is_valid(self.document_id))

        result = self.mongo_alerts.get_alerts(
            alert_type=alert_type, interval=interval)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        result = self.mongo_alerts.get_alerts(symbol=symbol)
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)

        self.mongo_alerts.delete_one(self.document_id)
        result_get_one = self.mongo_alerts.get_one(self.document_id)
        self.assertIsNone(result_get_one)
