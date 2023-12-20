import unittest

from trading_core.responser import MessageBase, Messages


class MessagesTestCase(unittest.TestCase):

    def setUp(self):
        self.messages = Messages()
        self.channel_id = "channel_001"
        self.message_text = "Hello, World!"
        self.message_base = MessageBase(self.channel_id, self.message_text)

    def test_check_message(self):
        result = self.messages.check_message(self.channel_id)
        self.assertFalse(result)

        result = self.messages.get_message(self.channel_id)
        self.assertIsNone(result)

        result = self.messages.get_messages()
        self.assertEqual(result, {})

        self.messages.add_message(self.message_base)
        result = self.messages.check_message(self.channel_id)
        self.assertTrue(result)

        result = self.messages.get_message(self.channel_id)
        self.assertEqual(result, self.message_base)

        additional_text = " More text"
        result = self.messages.add_message_text(
            self.channel_id, additional_text)
        self.assertEqual(result.get_message_text(),
                         self.message_text + additional_text)

        new_text = "New message text"
        result = self.messages.set_message_text(self.channel_id, new_text)
        self.assertEqual(result.get_message_text(), new_text)

        self.channel_id = "channel_002"
        message_inst = self.messages.create_message(
            self.channel_id, self.message_text)
        self.assertIsInstance(message_inst, MessageBase)
        self.assertEqual(message_inst.get_channel_id(), self.channel_id)
        self.assertEqual(message_inst.get_message_text(), self.message_text)
        self.assertEqual(self.messages.get_message(
            self.channel_id), message_inst)

        result = self.messages.get_messages()
        self.assertIn(self.channel_id, result)
        self.assertEqual(result[self.channel_id], message_inst)
