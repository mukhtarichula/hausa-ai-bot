import os
import threading
import time
import requests
import telebot
from flask import Flask

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

STUDIO_PROMPT = """
Kai kwararren mawaki ne kuma mai sarrafa kida (Music Producer/Lyricist) a HAUSA AI STUDIO. 
Aikin ka shine taimaka wa mutane wajen rubuta baitukan wakoki (lyrics) masu sauti da ratsa zuciya a harshen Hausa ko Turanci, da kuma tsara musu "Suno/Udio Prompt" na salon kida (Music Style) kamar Latin Pop, Reggaeton, Afrobeat, Trap, dss.

Duk lokacin da mai amfani ya aiko da ma'ana ko jigon wakar da yake so:
1. Ka tsara masa Structure na wakar: [Verse 1], [Chorus], [Verse 2], [Outro].
2. Ka ba shi Music Style Prompt (a Turanci) wanda zai kora a Suno AI ko Udio.
3. Yi magana cikin girmamawa da sigar kwararren Studio Producer a cikin Hausa.
"""

# List din komai don auto-fallback
MODELS_TO_TRY = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "gemini-2.5-flash"
]

def query_gemini(prompt_text):
    for model_name in MODELS_TO_TRY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}]
        }
        headers = {'Content-Type': 'application/json'}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            res_data = res.json()
            if "candidates" in res_data and len(res_data["candidates"]) > 0:
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            continue
    return None

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
    full_prompt = f"{STUDIO_PROMPT}\n\nUser Request: {user_prompt}"

    reply = query_gemini(full_prompt)
    if reply:
        bot.reply_to(message, reply)
    else:
        bot.reply_to(message, "An samu matsala wajen samun amsa daga Gemini API. Tabbatar API key dinka tana nan a Render Environment.")

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception:
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()

app = Flask(__name__)

@app.route('/')
def home():
    return "Hausa AI Music Studio Bot Yana Aiki!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
