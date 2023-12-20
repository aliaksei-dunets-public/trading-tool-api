import unittest

from trading_core.core import Symbol


class SymbolTestCase(unittest.TestCase):

    def setUp(self):
        self.code = 'AAPL'
        self.name = 'Apple Inc.'
        self.status = 'Active'
        self.type = 'Stock'
        self.tradingTime = 'UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 23:01 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -'

    def test_symbol_creation(self):
        symbol = Symbol(self.code, self.name, self.status,
                        self.type, self.tradingTime)

        self.assertEqual(symbol.code, self.code)
        self.assertEqual(symbol.name, self.name)
        self.assertEqual(symbol.descr, f'{self.name} ({self.code})')
        self.assertEqual(symbol.status, self.status)
        self.assertEqual(symbol.tradingTime, self.tradingTime)
        self.assertEqual(symbol.type, self.type)