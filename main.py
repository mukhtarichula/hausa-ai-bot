import os
import threading
import time
import telebot
from telebot import types
from flask import Flask

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Dictionary don adana yanayin kowane mai amfani (User State)
user_sessions = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_sessions[chat_id] = {"mode": "idle"}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    btn_beats = types.InlineKeyboardButton("🥁 Zaɓi Salon Kiɗa", callback_data="mode_beats")
    btn_effects = types.InlineKeyboardButton("🎛️ Studio Effects", callback_data="mode_effects")
    btn_speed = types.InlineKeyboardButton("⚡ Sauri & Tempo", callback_data="mode_speed")
    btn_stem = types.InlineKeyboardButton("✂️ Raba Muryar & Kiɗa", callback_data="mode_stem")
    btn_master = types.InlineKeyboardButton("🥼 AI Mastering", callback_data="mode_master")
    
    markup.add(btn_record, btn_beats, btn_effects, btn_speed, btn_stem, btn_master)
    
    welcome_msg = (
        "🎧 **Barka da zuwa HAUSA AI MUSIC STUDIO!** 🎧\n\n"
        "Wannan bot shi ne cikakken Digital Audio Workstation (DAW) dinka na Telegram.\n\n"
        "Za ka iya:\n"
        "• Aiko muryarka a yi mata record da gyara.\n"
        "• Saka kiɗa a bayan muryar ka (Beat Integration).\n"
        "• Saka Auto-Tune, Reverb, Echo & Cire Tsawa (Noise Removal).\n"
        "• Sauya saurin waƙa da raba murya da kiɗa.\n\n"
        " Zaɓi abin da kake so ka yi a maɓallan da ke ƙasa:"
    )
    bot.reply_to(message, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == "mode_record":
        bot.answer_callback_query(call.id, "Aiko muryar ka yanzu!")
        bot.send_message(chat_id, "🎙️ **Tura muryarka (Voice Message ko Audio file):**\nBot ɗin zai karɓa ya adana don sarrafawa.")
        
    elif call.data == "mode_beats":
        markup = types.InlineKeyboardMarkup(row_width=2)
        b1 = types.InlineKeyboardButton("🔥 Afrobeat", callback_data="beat_afro")
        b2 = types.InlineKeyboardButton("🎹 Amapiano", callback_data="beat_ama")
        b3 = types.InlineKeyboardButton("🎤 Trap / Drill", callback_data="beat_trap")
        b4 = types.InlineKeyboardButton("💃 Reggaeton", callback_data="beat_reggae")
        markup.add(b1, b2, b3, b4)
        bot.edit_message_text("🥁 **Zaɓi salon kiɗan da kake so a saka wa muryarka:**", chat_id, call.message.message_id, reply_markup=markup)
        
    elif call.data == "mode_effects":
        markup = types.InlineKeyboardMarkup(row_width=2)
        e1 = types.InlineKeyboardButton("🎤 Auto-Tune", callback_data="fx_autotune")
        e2 = types.InlineKeyboardButton("🌊 Reverb & Echo", callback_data="fx_reverb")
        e3 = types.InlineKeyboardButton("🔇 Cire Tsawa (Noise Removal)", callback_data="fx_denoise")
        e4 = types.InlineKeyboardButton("🗣️ Voice Converter", callback_data="fx_voice")
        markup.add(e1, e2, e3, e4)
        bot.edit_message_text("🎛️ **Zaɓi Studio Effect ɗin da kake so ka sanya:**", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data == "mode_speed":
        bot.answer_callback_query(call.id, "Kayan aikin Sauri na zuwa!")
        bot.send_message(chat_id, "⚡ **Gudun Waƙa (Tempo & Speed):** Zai ba ka damar saurin waƙar ko rage mata sauri daidai da kiɗa.")

    elif call.data == "mode_stem":
        bot.answer_callback_query(call.id, "Stems Splitter!")
        bot.send_message(chat_id, "✂️ **Raba Waƙa:** Aiko cikakkiyar waƙa don raba muryar maƙa daban, kiɗa daban.")

    elif call.data == "mode_master":
        bot.answer_callback_query(call.id, "AI Mastering!")
        bot.send_message(chat_id, "🥼 **AI Mastering:** Tace sautin waƙarka ta koma mai ƙarfi da tsafta kamar ta Studio.")

# Karɓar fayil ɗin sauti ko murya daga mai amfani
@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📥 **An sami fayil ɗin sauti!** Ina shirin sarrafa muryar taka...")

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
