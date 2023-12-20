import unittest

from trading_core.responser import MessageEmail


class MessageEmailTestCase(unittest.TestCase):

    def setUp(self):
        self.channel_id = "channel_001"
        self.subject = "Important Email"
        self.message_text = "Hello, World!"
        self.message_email = MessageEmail(
            self.channel_id, self.subject, self.message_text)

    def test_get_channel_id(self):
        result = self.message_email.get_channel_id()
        self.assertEqual(result, self.channel_id)

    def test_get_message_text(self):
        result = self.message_email.get_message_text()
        self.assertEqual(result, self.message_text)

    def test_set_message_text(self):
        new_text = "New message text"
        self.message_email.set_message_text(new_text)
        result = self.message_email.get_message_text()
        self.assertEqual(result, new_text)

    def test_add_message_text(self):
        additional_text = " More text"
        self.message_email.add_message_text(additional_text)
        result = self.message_email.get_message_text()
        self.assertEqual(result, self.message_text + additional_text)

    def test_get_subject(self):
        result = self.message_email.get_subject()
        self.assertEqual(result, self.subject)
