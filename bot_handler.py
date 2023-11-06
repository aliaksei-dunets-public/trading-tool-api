import os
from dotenv import load_dotenv
import telebot
import logging


load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logging.error('Bot token is not maintained in the environment values')


logger = telebot.logger
telebot.logger.setLevel(logging.INFO)


bot = telebot.TeleBot(BOT_TOKEN)


def register_handlers(bot):
    @bot.message_handler(commands=["start"])
    def start(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'Hello {message.chat.username}')

    @bot.message_handler(commands=["help"])
    def helper(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'''{message.chat.username}, select the available functions\n
/chat_id view the chat id
    
/user_id view your id
    
/simulate <SYMBOL> <INTERVAL> <STOP_LOSS> <TAKE_PROFIT>
    <SYMBOL>: EPAM, BABA and so on
    <INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w
    <STOP_LOSS>: OPTIONAL. 0% by default and stop loss isn't accepted during calculation
    <TAKE_PROFIT>: OPTIONAL. 0% by default and take profit isn't accepted during calculation
    
/analize <SYMBOL> <LIMIT>
    <SYMBOL>: EPAM, BABA and so on
    <LIMIT>: OPTIONAL. How many timeframes analize
    
/signal <SYMBOL> <INTERVAL>
    <SYMBOL>: EPAM, BABA and so on
    <INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w
    
/search <SYMBOL_NAME>
    
/subscribe <SYMBOL> <INTERVAL>
    <SYMBOL>: EPAM, BABA and so on
    <INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w
    
/subscriptions
    
/unsubscribe <SYMBOL> <INTERVAL>
    <SYMBOL>: EPAM, BABA and so on
    <INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w - OPTIONAL. If value is empty the bot removes all subscription for this symbol
    
/unsubscribe_all
        ''')

    @bot.message_handler(commands=["chat_id"])
    def chat_id(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'Chat id {message.chat.id}')

    @bot.message_handler(commands=["user_id"])
    def chat_id(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'Your id {message.from_user.id}')

    @bot.message_handler(commands=["simulate"])
    def simulate(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function of simulate')

    @bot.message_handler(commands=["analize"])
    def analyze(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function of data analysis')

    @bot.message_handler(commands=["signal"])
    def signal(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function of receiving a signal')

    @bot.message_handler(commands=["search"])
    def search(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function '
                                               f'of search for information about the selected symbol')

    @bot.message_handler(commands=["subscribe"])
    def subscribe(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function'
                                               f' of subscribing to the signal of the selected symbol')

    @bot.message_handler(commands=["subscriptions"])
    def subscriptions(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function '
                                               f'of viewing all subscriptions')

    @bot.message_handler(commands=["unsubscribe"])
    def unsubscribe(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function '
                                               f'of unsubscribing to the signal of the selected symbol')

    @bot.message_handler(commands=["unsubscribe_all"])
    def unsubscribe_all(message: telebot.types.Message):
        telebot.logger.info(f'Get message from: {message.from_user.id}')
        bot.send_message(message.from_user.id, f'{message.chat.username} this is a function '
                                               f'of unsubscribing from all signals')
