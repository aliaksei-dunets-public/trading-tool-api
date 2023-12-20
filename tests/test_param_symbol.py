import unittest

from trading_core.model import ParamSymbol


class TestParamSymbol(unittest.TestCase):

    def test_init(self):
        # Test initializing ParamSymbol with consistency_check=True
        symbol = "BABA"
        param_symbol = ParamSymbol(symbol)

        # Check if the symbol attribute is set correctly
        self.assertEqual(param_symbol.symbol, symbol)

    def test_get_symbol_config(self):
        # Test get_symbol_config when symbol config exists
        symbol = "BABA"
        param_symbol = ParamSymbol(symbol, consistency_check=False)

        # Manually set the symbol_config for testing
        param_symbol._ParamSymbol__symbol_config = "MockSymbolConfig"

        symbol_config = param_symbol.get_symbol_config()

        # Check, if get_symbol_config returns the correct symbol config
        self.assertEqual(symbol_config, "MockSymbolConfig")

    def test_get_symbol_config_exception(self):
        # Test get_symbol_config when symbol config doesn't exist
        symbol = "INVALID_SYMBOL"
        param_symbol = ParamSymbol(symbol, consistency_check=False)

        # Ensure that symbol_config is None (not set manually)
        self.assertIsNone(param_symbol._ParamSymbol__symbol_config)

        # Attempt to get the symbol config and expect an exception
        with self.assertRaises(Exception):
            param_symbol.get_symbol_config()
