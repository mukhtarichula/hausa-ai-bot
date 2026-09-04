import os
import threading
import time
import telebot
from telebot import types
from flask import Flask
from pydub import AudioSegment
import noisereduce as nr
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import butter, lfilter

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

app = Flask(__name__)
user_data = {}

def highpass_filter(data, cutoff=80, fs=44100, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    y = lfilter(b, a, data)
    return y

@app.route('/')
def home():
    return "Hausa AI Music Studio Bot Yana Aiki!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    btn_effects = types.InlineKeyboardButton("🎛️ Studio Effects", callback_data="mode_effects")
    btn_beats = types.InlineKeyboardButton("🥁 Zaɓi Beat", callback_data="mode_beats")
    markup.add(btn_record, btn_effects, btn_beats)
    
    welcome_msg = (
        "🎧 **Barka da zuwa HAUSA AI MUSIC STUDIO!** 🎧\n\n"
        "Za ka iya aiko muryarka don gogewa tsaf, saka Reverb, cire tsawa & iska, ko sanya sunan waƙa da kanka.\n\n"
        "Zaɓi abin da kake so ka yi a maɓallan ƙasa:"
    )
    bot.reply_to(message, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📥 **Ina saukewa da adana muryarka...**", parse_mode="Markdown")
    
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = f"user_{chat_id}_input.ogg"
        wav_path = f"user_{chat_id}_input.wav"
        
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        sound = AudioSegment.from_file(input_path)
        sound.export(wav_path, format="wav")
        
        user_data[chat_id] = {
            'input_wav': wav_path,
            'state': 'waiting_for_title',
            'song_title': 'Hausa AI Track'
        }
        
        bot.send_message(
            chat_id, 
            "✍️ **Rubuta Sunan Waƙar da kake so a sanya:**\n*(Ko ka danna /skip idan baka so)*",
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.send_message(chat_id, f"Matsala wajen karɓar murya: {str(e)}")

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    chat_id = message.chat.id
    
    if chat_id in user_data and user_data[chat_id].get('state') == 'waiting_for_title':
        if message.text and message.text != "/skip":
            user_data[chat_id]['song_title'] = message.text
            
        user_data[chat_id]['state'] = 'ready'
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        e1 = types.InlineKeyboardButton("🔇 Cire Iska & Tsawa", callback_data="process_denoise")
        e2 = types.InlineKeyboardButton("🌊 Echo / Reverb", callback_data="process_reverb")
        e3 = types.InlineKeyboardButton("🔊 Normalize Volume", callback_data="process_normalize")
        markup.add(e1, e2, e3)
        
        title = user_data[chat_id]['song_title']
        bot.send_message(
            chat_id, 
            f"✅ **An saita sunan waƙa zuwa:** `{title}`\n\nYanzu zaɓi abin da kake so a yi wa muryar:", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
    else:
        send_welcome(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if chat_id not in user_data or 'input_wav' not in user_data[chat_id]:
        bot.answer_callback_query(call.id, "Da fatan za ka aiko da muryar ka tukuna!")
        return
        
    input_wav = user_data[chat_id]['input_wav']
    output_wav = f"user_{chat_id}_output.wav"
    song_title = user_data[chat_id].get('song_title', 'Hausa AI Track')
    
    if call.data == "process_denoise":
        bot.send_message(chat_id, "⚙️ **Ina goge iska da tsawar baya...**", parse_mode="Markdown")
        try:
            rate, data = wavfile.read(input_wav)
            if len(data.shape) > 1:
                filtered_data = np.zeros_like(data)
                for i in range(data.shape[1]):
                    filtered_data[:, i] = highpass_filter(data[:, i], cutoff=80, fs=rate)
            else:
                filtered_data = highpass_filter(data, cutoff=80, fs=rate)
            
            reduced_noise = nr.reduce_noise(y=filtered_data, sr=rate, prop_decrease=0.95, stationary=False)
            wavfile.write(output_wav, rate, np.int16(reduced_noise))
            
            sound = AudioSegment.from_wav(output_wav)
            normalized_sound = sound.normalize()
            normalized_sound.export(output_wav, format="wav")
            
            with open(output_wav, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, audio_out, 
                    caption=f"✨ **Gashi nan an goge iska da tsawa!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, performer="Hausa AI Studio", parse_mode="Markdown"
                )
        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru: {str(e)}")

    elif call.data == "process_reverb":
        bot.send_message(chat_id, "🌊 **Ina sanya Reverb & Echo...**", parse_mode="Markdown")
        try:
            sound = AudioSegment.from_wav(input_wav)
            echo_delay = 150
            echo = sound - 6
            combined = sound.overlay(echo, position=echo_delay)
            combined.export(output_wav, format="wav")
            
            with open(output_wav, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, audio_out, 
                    caption=f"✨ **Gashi nan an sanya Reverb!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, performer="Hausa AI Studio", parse_mode="Markdown"
                )
        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru: {str(e)}")

    elif call.data == "process_normalize":
        bot.send_message(chat_id, "🔊 **Ina daidaita ƙarfin sauti...**", parse_mode="Markdown")
        try:
            sound = AudioSegment.from_wav(input_wav)
            normalized_sound = sound.normalize()
            normalized_sound.export(output_wav, format="wav")
            
            with open(output_wav, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, audio_out, 
                    caption=f"🔊 **Gashi nan an daidaita ƙarfin sauti!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, performer="Hausa AI Studio", parse_mode="Markdown"
                )
        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru: {str(e)}")

def run_bot():
    time.sleep(3)
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
