import os
import threading
import time
import telebot
from flask import Flask
from google import genai

# Keys
TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
GEMINI_API_KEY = "AIzaSyDwuD4RYY8mUJ1mCEWAPRItVG-bystuRVw"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

STUDIO_PROMPT = """
Kai kwararren mawaki ne kuma mai sarrafa kida (Music Producer/Lyricist) a HAUSA AI STUDIO. 
Aikin ka shine taimaka wa mutane wajen rubuta baitukan wakoki (lyrics) masu sauti da ratsa zuciya a harshen Hausa ko Turanci, da kuma tsara musu "Suno/Udio Prompt" na salon kida (Music Style) kamar Latin Pop, Reggaeton, Afrobeat, Trap, dss.

Duk lokacin da mai amfani ya aiko da ma'ana ko jigon wakar da yake so:
1. Ka tsara masa Structure na wakar: [Verse 1], [Chorus], [Verse 2], [Outro].
2. Ka ba shi Music Style Prompt (a Turanci) wanda zai kora a Suno AI ko Udio.
3. Yi magana cikin girmamawa da sigar kwararren Studio Producer a cikin Hausa.
"""

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🎵 **Barka da zuwa HAUSA AI MUSIC STUDIO BOT!** 🎵\n\n"
        "Ina taimaka muku wajen:\n"
        "✨ Rubuta baitukan waka (Lyrics) a cikin Hausa & Turanci.\n"
        "🎶 Tsara Prompts na kida (Reggaeton, Latin Pop, Afrobeat, dss.) don Suno/Udio AI.\n\n"
        "Yadda zakayi amfani dani:\n"
        "Rubuta jigon wakar da kake so ko salon kidan da kake muradi."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def generate_music_content(message):
    bot.send_chat_action(message.chat.id, 'typing')
    user_prompt = message.text

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{STUDIO_PROMPT}\n\nUser request: {user_prompt}"
        )
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "An samu matsala wajen samun amsa. Sake gwada aikawa.")
    except Exception as e:
        bot.reply_to(message, f"Matsala ta faru: {str(e)}")

def run_bot():
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
    bot.infinity_polling(skip_pending=True)

threading.Thread(target=run_bot, daemon=True).start()

app = Flask(__name__)

@app.route('/')
def home():
    return "Hausa AI Music Studio Bot Yana Aiki!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
