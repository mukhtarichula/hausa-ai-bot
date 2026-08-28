import telebot

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Barka da zuwa HAUSA AI STUDIO BOT! Bot dinka yana aiki 24/7 lami lafiya.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Na samu saqonka: {message.text}")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
