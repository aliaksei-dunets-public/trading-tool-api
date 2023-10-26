import os
from dotenv import load_dotenv

import logging
import telebot

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logging.error('Bot token is not maintained in the environment values')

HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')

# webhook settings
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=["start"])
def start(message: telebot.types.Message):
    logger.info(f'Get message from: {message.from_user.id}')
    bot.send_message(message.from_user.id, f'Hello {message.chat.username}')

def set_webhook():
    result = bot.set_webhook(url=WEBHOOK_URL)
    if result:
        logging.info(f'{WEBHOOK_URL} is succesfully activated')
        return f'{WEBHOOK_URL} is succesfully activated'
    else:
        logging.error(f'Activation of the webhook: {WEBHOOK_URL} is failed')
        return f'{WEBHOOK_URL} is failed'

def remove_webhook():
    result = bot.remove_webhook()
    if result:
        logging.info(f'{WEBHOOK_URL} is succesfully removed')
        return f'{WEBHOOK_URL} is succesfully activated'
    else:
        logging.error(f'Removing of the webhook: {WEBHOOK_URL} is failed')
        return f'{WEBHOOK_URL} is failed'

def get_webhook_info():
    return bot.get_webhook_info()

if __name__ == "__main__":
    bot.infinity_polling()
