import unittest


from trading_core.model import ParamBase


class TestParamBase(unittest.TestCase):

    def test_copy_instance(self):
        # Create an instance of ParamBase
        param_base = ParamBase()

        # Copy the instance using copy_instance
        copied_param_base = ParamBase.copy_instance(param_base)

        # Check if the original and copied instances are not the same object
        self.assertIsNot(param_base, copied_param_base)
