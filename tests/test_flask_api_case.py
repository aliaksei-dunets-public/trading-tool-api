import unittest
import json
from datetime import datetime

from trading_core.constants import Const
from trading_core.model import model
from app import app


class FlaskAPITestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_get_symbols(self):
        response = self.client.get('/symbols?from_buffer=true')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertGreater(len(json_api_response), 1)

    def test_get_symbol_by_code(self):
        code = 'BTC/USD'
        response = self.client.get(f'/symbols?code={code}')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertEqual(json_api_response[0]['code'], code)

    def test_get_symbols_by_name(self):
        name = 'Bitcoin'
        expected_result = {'code': 'BTC/USD', 'name': 'Bitcoin / USD',
                           'descr': 'Bitcoin / USD (BTC/USD)', 'status': 'TRADING', 'tradingTime': 'UTC; Mon - 21:00, 21...0, 21:05 -', 'type': 'CRYPTOCURRENCY'}
        response = self.client.get(f'/symbols?name={name}&from_buffer=true')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)

        self.assertGreater(len(json_api_response), 1)
        self.assertTrue(expected_result, json_api_response)

    def test_get_intervals(self):
        expected_intervals = [{"interval": Const.TA_INTERVAL_5M,  "name": "5 minutes",  "order": 10, "importance": Const.IMPORTANCE_LOW},
                              {"interval": Const.TA_INTERVAL_15M, "name": "15 minutes",
                               "order": 20, "importance": Const.IMPORTANCE_LOW},
                              {"interval": Const.TA_INTERVAL_30M, "name": "30 minutes",
                               "order": 30, "importance": Const.IMPORTANCE_MEDIUM},
                              {"interval": Const.TA_INTERVAL_1H,  "name": "1 hour",
                               "order": 40, "importance": Const.IMPORTANCE_MEDIUM},
                              {"interval": Const.TA_INTERVAL_4H,  "name": "4 hours",
                               "order": 50, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1D,  "name": "1 day",
                               "order": 60, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1WK, "name": "1 week",     "order": 70, "importance": Const.IMPORTANCE_HIGH}]

        response = self.client.get(
            f'/intervals')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_intervals, json_api_response)

        expected_intervals = [{"interval": Const.TA_INTERVAL_4H,  "name": "4 hours",
                               "order": 50, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1D,  "name": "1 day",
                               "order": 60, "importance": Const.IMPORTANCE_HIGH},
                              {"interval": Const.TA_INTERVAL_1WK, "name": "1 week",     "order": 70, "importance": Const.IMPORTANCE_HIGH}]

        response = self.client.get(
            f'/intervals?importance={Const.IMPORTANCE_HIGH}')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_intervals, json_api_response)

    def test_get_indicators(self):
        expected_result = [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]

        response = self.client.get(
            f'/indicators')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_result, json_api_response)

    def test_get_strategies(self):
        expected_result = [
            {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14): Indicator against Trend +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_170_165,
             Const.NAME: "CCI(14): Indicator direction Trend +/- 170 | 165"},
            {Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                Const.NAME: "CCI(20): Indicator against Trend +/- 100"},
            {Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                Const.NAME: "CCI(50): Indicator direction Trend 0"}
        ]

        response = self.client.get(
            f'/strategies')
        self.assertEqual(response.status_code, 200)

        json_api_response = json.loads(response.text)
        self.assertEqual(expected_result, json_api_response)

    def test_get_history_data(self):
        interval = '4h'
        limit = 20

        response = self.client.get(
            f'/historyData?symbol=BTC/USD&interval={interval}&limit={limit}')

        json_api_response = json.loads(response.text)['data']
        latest_bar = json_api_response[-1]

        end_datetime = model.get_handler().getEndDatetime(interval)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(datetime.fromisoformat(
            latest_bar["Datetime"][:-1]), end_datetime)
        self.assertEqual(len(json_api_response), limit)

    def test_get_strategy_data(self):
        interval = '4h'
        limit = 20
        # /strategyData?code=CCI_20_TREND_100&symbol=BTC/USD&interval=4h&limit=20&closed_bars=true&from_buffer=true
        response = self.client.get(
            f'/strategyData?code=CCI_20_TREND_100&symbol=BTC/USD&interval={interval}&limit={limit}&closed_bars=true&from_buffer=true')

        json_api_response = json.loads(response.text)['data']
        latest_bar = json_api_response[-1]

        end_datetime = model.get_handler(
        ).getEndDatetime(interval=interval, closed_bars=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(datetime.fromisoformat(
            latest_bar["Datetime"][:-1]), end_datetime)
        self.assertEqual(len(json_api_response), 3)

    def test_get_signals(self):
        symbol = 'BTC/USD'
        strategy = 'CCI_20_TREND_100'
        interval_1h = Const.TA_INTERVAL_1H
        interval_4h = Const.TA_INTERVAL_4H
        closed_bars = True

        # /signals?symbol=BTC/USD&interval=4h&interval=1h&strategy=CCI_20_TREND_100&signal=Debug&closed_bars=true
        response = self.client.get(
            f'/signals?symbol={symbol}&interval={interval_1h}&interval={interval_4h}&strategy={strategy}&signal=Debug&closed_bars={closed_bars}')

        json_api_response = json.loads(response.text)

        end_datetime_1h = model.get_handler().getEndDatetime(
            interval=interval_1h, closed_bars=closed_bars)
        end_datetime_4h = model.get_handler().getEndDatetime(
            interval=interval_4h, closed_bars=closed_bars)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json_api_response), 2)
        self.assertEqual(
            json_api_response[0][Const.DATETIME], end_datetime_1h.isoformat())
        self.assertEqual(json_api_response[0][Const.PARAM_SYMBOL], symbol)
        self.assertEqual(json_api_response[0][Const.INTERVAL], interval_1h)
        self.assertEqual(json_api_response[0][Const.STRATEGY], strategy)

        self.assertEqual(
            json_api_response[1][Const.DATETIME], end_datetime_4h.isoformat())
        self.assertEqual(json_api_response[1][Const.PARAM_SYMBOL], symbol)
        self.assertEqual(json_api_response[1][Const.INTERVAL], interval_4h)
        self.assertEqual(json_api_response[1][Const.STRATEGY], strategy)

    def test_jobs_functionality(self):
        job_type = Const.JOB_TYPE_BOT
        interval = Const.TA_INTERVAL_1D

        payload = {
            Const.DB_JOB_TYPE: job_type,
            Const.DB_INTERVAL: interval
        }

        # Create job
        response = self.client.post(
            '/jobs', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_api_response = json.loads(response.text)

        job_id = json_api_response[Const.JOB_ID]
        self.assertIsNotNone(job_id)

        # Get jobs
        response = self.client.get('/jobs')
        json_api_response = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(json_api_response), 1)

        # Deactivate job
        response = self.client.post(f'/jobs/{job_id}/deactivate')
        self.assertEqual(response.status_code, 200)

        # Activate job
        response = self.client.post(f'/jobs/{job_id}/activate')
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f'/jobs/{job_id}')
        self.assertEqual(response.status_code, 200)

    def test_alerts_functionality(self):
        alert_type = Const.ALERT_TYPE_BOT
        channel_id = 1658698044
        symbol = 'BTC/USD'
        interval = Const.TA_INTERVAL_1D
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100]
        signals = [Const.STRONG_BUY]
        comment = 'Test comments'

        payload = {
            Const.DB_ALERT_TYPE: alert_type,
            Const.DB_CHANNEL_ID: channel_id,
            Const.DB_SYMBOL: symbol,
            Const.DB_INTERVAL: interval,
            Const.DB_STRATEGIES: strategies,
            Const.DB_SIGNALS: signals,
            Const.DB_COMMENT: comment
        }

        # Create
        response = self.client.post(
            '/alerts', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_api_response = json.loads(response.text)

        _id = json_api_response[Const.DB_ID]
        self.assertIsNotNone(_id)

        # Get jobs
        response = self.client.get('/alerts')
        json_api_response = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(json_api_response), 1)

        # Update
        payload = {
            Const.DB_INTERVAL: interval,
            Const.DB_STRATEGIES: strategies,
            Const.DB_SIGNALS: signals,
            Const.DB_COMMENT: 'Updated comment'
        }

        response = self.client.put(
            f'/alerts/{_id}', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f'/alerts/{_id}')
        self.assertEqual(response.status_code, 200)

    def test_orders_functionality(self):
        order_type = Const.LONG
        symbol = 'BTC/USD'
        interval = Const.TA_INTERVAL_1D
        strategies = [Const.TA_STRATEGY_CCI_14_TREND_100]
        price = 100
        quantity = 0.5

        payload = {
            Const.DB_ORDER_TYPE: order_type,
            Const.DB_SYMBOL: symbol,
            Const.DB_INTERVAL: interval,
            Const.DB_PRICE: price,
            Const.DB_QUANTITY: quantity,
            Const.DB_STRATEGIES: strategies
        }

        # Create
        response = self.client.post(
            '/orders', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        json_api_response = json.loads(response.text)

        _id = json_api_response[Const.DB_ID]
        self.assertIsNotNone(_id)

        # Get orders
        response = self.client.get('/orders')
        json_api_response = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(json_api_response), 1)

        response = self.client.delete(f'/orders/{_id}')
        self.assertEqual(response.status_code, 200)
