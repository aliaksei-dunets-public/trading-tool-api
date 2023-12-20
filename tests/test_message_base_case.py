import unittest

from trading_core.responser import MessageBase


class MessageBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.channel_id = "channel_001"
        self.message_text = "Hello, World!"
        self.message_base = MessageBase(self.channel_id, self.message_text)

    def test_get_channel_id(self):
        result = self.message_base.get_channel_id()
        self.assertEqual(result, self.channel_id)

    def test_get_message_text(self):
        result = self.message_base.get_message_text()
        self.assertEqual(result, self.message_text)

    def test_set_message_text(self):
        new_text = "New message text"
        self.message_base.set_message_text(new_text)
        result = self.message_base.get_message_text()
        self.assertEqual(result, new_text)

    def test_add_message_text(self):
        additional_text = " More text"
        self.message_base.add_message_text(additional_text)
        result = self.message_base.get_message_text()
        self.assertEqual(result, self.message_text + additional_text)
