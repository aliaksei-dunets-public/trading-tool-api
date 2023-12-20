import unittest

from trading_core.core import SimulateOptions


class SimulateOptionsTestCase(unittest.TestCase):

    def setUp(self):
        self.balance = 10000
        self.limit = 10
        self.stopLossRate = 0.05
        self.takeProfitRate = 0.1
        self.feeRate = 0.01

    def test_simulate_options_creation(self):
        simulate_options = SimulateOptions(
            self.balance, self.limit, self.stopLossRate, self.takeProfitRate, self.feeRate)

        self.assertEqual(simulate_options.init_balance, self.balance)
        self.assertEqual(simulate_options.limit, self.limit)
        self.assertEqual(simulate_options.stop_loss_rate, self.stopLossRate)
        self.assertEqual(simulate_options.take_profit_rate,
                         self.takeProfitRate)
        self.assertEqual(simulate_options.fee_rate, self.feeRate)
