import os
import threading
import time
import numpy as np
import telebot
from telebot import types
from flask import Flask
from pydub import AudioSegment, effects

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_data = {}

@app.route('/')
@app.route('/ping')
def home():
    return "OK", 200

def remove_background_noise(sound):
    """Deep Spectral Noise Gate for Clean Voice Clarity"""
    samples = np.array(sound.get_array_of_samples(), dtype=np.float32)
    
    if sound.channels == 2:
        samples = samples.reshape((-1, 2))
        
    # An saita matakin threshold don goge surutun baya
    threshold = np.max(np.abs(samples)) * 0.035
    
    # Rage karfin amsawa na sauti idan ya yi kasa da threshold
    mask = np.abs(samples) > threshold
    cleaned_samples = samples * mask
    
    cleaned_samples = cleaned_samples.astype(np.int16)
    return sound._spawn(cleaned_samples.tobytes())

def process_full_master(input_path, output_path):
    # 1. Loda fayil din sauti
    sound = AudioSegment.from_file(input_path)
    
    # 2. Goge Hayaniyar Bango & Surutu (Spectral Noise Gate)
    clean_sound = remove_background_noise(sound)
    
    # 3. Yanke Low-End Noise (Air Conditioning / Mic Hum / Wind)
    clean_sound = clean_sound.high_pass_filter(150)
    
    # 4. Injin Qara Sheki da Tsarki ga Murya (Vocal Presence Boosting)
    # Wannan yana Kara haske da feshin murya (High Shelf Boost around 3kHz-6kHz)
    clean_sound = clean_sound.low_pass_filter(7500)
    
    # 5. Dynamic Compression (Yalwata Murya & Daidaita Nauyinta)
    compressed = effects.compress_dynamic_range(
        clean_sound, 
        threshold=-18.0, 
        ratio=3.5, 
        attack=3.0, 
        release=40.0
    )
    
    # 6. Smooth Studio Reverb & Spatial Echo Effect
    echo = compressed - 10
    mastered = compressed.overlay(echo, position=70)
    
    # 7. Final Loudness Normalization (Loud & Crisp Studio Audio)
    final_output = mastered.normalize()
    
    # Fitar da fayil din a ingancin Studio MP3 (320kbps)
    final_output.export(output_path, format="mp3", bitrate="320k")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    markup.add(btn_record)
    
    welcome_msg = (
        "🎧 **HAUSA AI MUSIC STUDIO** 🎧\n\n"
        "Barka da zuwa! Aiko muryarka yanzu domin gudanar da **Studio Noise Gate & Voice Enhancer**."
    )
    bot.send_message(chat_id, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📥 **Ina saukewa da sarrafa muryarka...**", parse_mode="Markdown")
    
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = f"user_{chat_id}_input.wav"
        
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        user_data[chat_id] = {
            'input_wav': input_path,
            'state': 'waiting_for_title',
            'song_title': 'Hausa AI Track'
        }
        
        bot.send_message(
            chat_id, 
            "✍️ **Rubuta Sunan Waƙar da kake so a sanya:**\n*(Ko ka danna /skip)*",
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
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        e_master = types.InlineKeyboardButton("🎛️ FULL STUDIO MASTER", callback_data="process_master")
        markup.add(e_master)
        
        title = user_data[chat_id]['song_title']
        bot.send_message(
            chat_id, 
            f"✅ **An saita sunan waƙa zuwa:** `{title}`\n\nDanna maɓallin ƙasa don gyarawa:", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
    else:
        send_welcome(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    if chat_id not in user_data or 'input_wav' not in user_data[chat_id]:
        bot.send_message(chat_id, "Da fatan za ka aiko da muryar ka tukuna!")
        return
        
    input_wav = user_data[chat_id]['input_wav']
    output_mp3 = f"user_{chat_id}_master.mp3"
    song_title = user_data[chat_id].get('song_title', 'Hausa AI Track')
    
    if call.data == "process_master" or call.data == "mode_record":
        if call.data == "mode_record":
            bot.send_message(chat_id, "🎙️ **Yi rikodin muryarka ka turo min yanzu!**", parse_mode="Markdown")
            return
            
        bot.send_message(chat_id, "🎛️ **Ina gudanar da Studio Noise Gate & Deep Enhancement...**", parse_mode="Markdown")
        try:
            process_full_master(input_wav, output_mp3)
            
            with open(output_mp3, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, 
                    audio_out, 
                    caption=f"🔥 **Gashi nan an kammala Full Studio Master!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, 
                    performer="Hausa AI Studio", 
                    parse_mode="Markdown"
                )
            
            if os.path.exists(input_wav): os.remove(input_wav)
            if os.path.exists(output_mp3): os.remove(output_mp3)

        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru wajen mastering: {str(e)}")

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.polling(none_stop=True, interval=1, timeout=15)
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
