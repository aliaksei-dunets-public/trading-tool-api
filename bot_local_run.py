import bot_handler

bot_handler.register_handlers(bot_handler.bot)


if __name__ == "__main__":
    bot_handler.bot.infinity_polling()
