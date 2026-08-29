import os
import time
import threading

import telebot
from flask import Flask
from google import genai


# ======================
# ENV VARIABLES
# ======================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN")

if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY")


# ======================
# GEMINI SETUP
# ======================

client = genai.Client(
    api_key=GEMINI_API_KEY
)


model_name = "gemini-2.5-flash"


# ======================
# TELEGRAM SETUP
# ======================

bot = telebot.TeleBot(
    TELEGRAM_TOKEN,
    parse_mode="HTML"
)


# ======================
# AI ROLE
# ======================

STUDIO_PROMPT = """

Kai ne HAUSA AI MUSIC STUDIO,
kwararren Music Producer, Song Writer da Lyricist.

Aikinka:
- Rubuta lyrics masu zurfi a Hausa ko Turanci.
- Ka tsara wakar da structure:
[Verse 1]
[Chorus]
[Verse 2]
[Bridge]
[Outro]

- Ka samar da Suno AI / Udio music prompt a Turanci.
- Ka bada shawarar:
  * Genre
  * Mood
  * Instruments
  * Vocal style

Yi magana da Hausa cikin salon professional studio producer.

"""


# ======================
# COMMANDS
# ======================

@bot.message_handler(commands=["start", "help"])
def welcome(message):

    text = """
🎵 <b>HAUSA AI MUSIC STUDIO BOT</b> 🎵


Ni ina taimaka maka wajen:

🎤 Rubuta Lyrics
🎶 Kirkirar Music Style Prompt
🔥 Suno AI / Udio Prompt
🌍 Hausa & English songs


Aiko min da:
- Jigon wakarka
- Sunan artist style
- Salon kida da kake so


Misali:
"Rubuta min waka ta soyayya irin Afrobeat"
"""

    bot.reply_to(message, text)



# ======================
# AI GENERATION
# ======================

@bot.message_handler(func=lambda m: True)
def generate(message):

    bot.send_chat_action(
        message.chat.id,
        "typing"
    )

    user_text = message.text


    try:

        prompt = f"""
{STUDIO_PROMPT}


User request:

{user_text}

"""


        result = client.models.generate_content(
            model=model_name,
            contents=prompt
        )


        if result.text:

            bot.reply_to(
                message,
                result.text
            )

        else:

            bot.reply_to(
                message,
                "Ban samu amsa ba. Ka sake gwadawa."
            )


    except Exception as e:

        print(e)

        bot.reply_to(
            message,
            "An samu matsala wajen hada AI. Ka sake gwadawa."
        )



# ======================
# BOT THREAD
# ======================

def start_bot():

    while True:

        try:

            print("Bot yana aiki...")

            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60
            )


        except Exception as e:

            print(
                "Bot error:",
                e
            )

            time.sleep(5)



threading.Thread(
    target=start_bot,
    daemon=True
).start()



# ======================
# FLASK SERVER
# ======================

app = Flask(__name__)


@app.route("/")
def home():

    return "HAUSA AI MUSIC STUDIO BOT ONLINE"



if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
