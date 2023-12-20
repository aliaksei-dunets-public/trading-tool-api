import unittest
from unittest.mock import MagicMock

from trading_core.model import Symbols
from trading_core.core import Symbol, RuntimeBufferStore


class SymbolsTestCase(unittest.TestCase):

    def setUp(self):
        self.mocked_handler = MagicMock()
        self.symbols = Symbols(from_buffer=False)
        self.symbols._Symbols__get_symbols = MagicMock(return_value={
            'BTC': Symbol('BTC', 'Bitcoin', 'active', 'crypto', '09:00-17:00'),
            'ETH': Symbol('ETH', 'Ethereum', 'active', 'crypto', '08:00-16:00'),
            'LTC': Symbol('LTC', 'Litecoin', 'inactive', 'crypto', '10:00-18:00')
        })

    def tearDown(self) -> None:
        RuntimeBufferStore().clearSymbolsBuffer()

    def test_check_symbol_existing(self):
        self.assertTrue(self.symbols.check_symbol('BTC'))

    def test_check_symbol_non_existing(self):
        self.assertFalse(self.symbols.check_symbol('XYZ'))

    def test_get_symbol_existing(self):
        symbol = self.symbols.get_symbol('ETH')
        self.assertEqual(symbol.code, 'ETH')
        self.assertEqual(symbol.name, 'Ethereum')

    def test_get_symbol_non_existing(self):
        symbol = self.symbols.get_symbol('XYZ')
        self.assertIsNone(symbol)

    def test_get_symbols_from_buffer(self):
        self.symbols._Symbols__from_buffer = True
        symbols = self.symbols.get_symbols()
        self.assertEqual(len(symbols), 3)
        self.assertIsInstance(symbols['BTC'], Symbol)
        self.assertIsInstance(symbols['ETH'], Symbol)
        self.assertIsInstance(symbols['LTC'], Symbol)

    def test_get_symbols_force_fetch(self):
        self.symbols._Symbols__from_buffer = False
        symbols = self.symbols.get_symbols()
        self.assertEqual(len(symbols), 3)
        self.assertIsInstance(symbols['BTC'], Symbol)
        self.assertIsInstance(symbols['ETH'], Symbol)
        self.assertIsInstance(symbols['LTC'], Symbol)

    def test_get_symbol_list_with_code(self):
        symbols = self.symbols.get_symbol_list('BTC', '', '', '')
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].code, 'BTC')

    def test_get_symbol_list_with_name(self):
        symbols = self.symbols.get_symbol_list('', 'Ether', '', '')
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].name, 'Ethereum')

    def test_get_symbol_list_with_status(self):
        symbols = self.symbols.get_symbol_list('', '', 'inactive', '')
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].status, 'inactive')

    def test_get_symbol_list_with_type(self):
        symbols = self.symbols.get_symbol_list('', '', '', 'crypto')
        self.assertEqual(len(symbols), 3)
        self.assertEqual(symbols[0].type, 'crypto')

    def test_get_symbol_list_json(self):
        expected_result = {
            "code": "BTC",
            "name": "Bitcoin / USD",
            "descr": "Bitcoin / USD (BTC/USD)",
            "status": "TRADING",
            "tradingTime": "UTC; Mon - 21:00, 21:05 -; Tue - 21:00, 21:05 -; Wed - 21:00, 21:05 -; Thu - 21:00, 21:05 -; Fri - 21:00, 22:01 -; Sat - 05:00, 07:00 - 21:00, 21:05 -; Sun - 21:00, 21:05 -",
            "type": "CRYPTOCURRENCY"
        }

        symbols = self.symbols.get_symbol_list_json(code='BTC')
        self.assertEqual(symbols[0]["code"], expected_result["code"])

    def test_get_symbol_code(self):
        symbols = self.symbols.get_symbol_codes()
        self.assertGreaterEqual(len(symbols), 1)
        self.assertIn('BTC', symbols)
