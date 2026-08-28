import os
import threading
import telebot
from flask import Flask

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Barka da zuwa HAUSA AI STUDIO BOT! Bot dinka yana aiki 24/7 lami lafiya.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Na samu saqonka: {message.text}")

def run_bot():
    bot.infinity_polling(skip_pending=True)

# Fara bot a background thread
threading.Thread(target=run_bot, daemon=True).start()

# Flask Web Server don Render Web Service
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot yana aiki lafiya!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
