import os
import threading
import time
import telebot
from telebot import types
from flask import Flask
from pydub import AudioSegment, effects
import noisereduce as nr
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import butter, lfilter

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

app = Flask(__name__)
user_data = {}

def apply_highpass(data, rate, cutoff=100):
    nyq = 0.5 * rate
    normal_cutoff = cutoff / nyq
    b, a = butter(5, normal_cutoff, btype='high', analog=False)
    if len(data.shape) > 1:
        y = np.zeros_like(data)
        for i in range(data.shape[1]):
            y[:, i] = lfilter(b, a, data[:, i])
        return y
    return lfilter(b, a, data)

def clean_audio_data(input_wav, output_wav):
    rate, data = wavfile.read(input_wav)
    hp_data = apply_highpass(data, rate, cutoff=100)
    denoised_data = nr.reduce_noise(
        y=hp_data, 
        sr=rate, 
        prop_decrease=0.85, 
        stationary=True,
        n_fft=1024
    )
    wavfile.write(output_wav, rate, np.int16(denoised_data))

def apply_studio_effects(input_wav, output_wav, add_reverb=True):
    temp_clean = f"{output_wav}_temp.wav"
    clean_audio_data(input_wav, temp_clean)
    
    sound = AudioSegment.from_wav(temp_clean)
    sound = effects.compress_dynamic_range(sound, threshold=-20.0, ratio=4.0)
    
    if add_reverb:
        echo = sound - 8
        sound = sound.overlay(echo, position=120)
    
    final_sound = sound.normalize()
    final_sound.export(output_wav, format="wav")
    
    if os.path.exists(temp_clean):
        os.remove(temp_clean)

@app.route('/')
@app.route('/ping')
def home():
    return "OK", 200

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    markup.add(btn_record)
    
    welcome_msg = (
        "🎧 **Barka da zuwa HAUSA AI MUSIC STUDIO!** 🎧\n\n"
        "Aiko muryarka yanzu domin yi mata **Mastering** na kwararru (Cire Iska + Reverb + Daidaita Ƙarfi) lokaci guda."
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
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        e_master = types.InlineKeyboardButton("🎛️ FULL STUDIO MASTER (Gaba Ɗaya)", callback_data="process_master")
        e_denoise = types.InlineKeyboardButton("🔇 Cire Iska & Tsawa Kawai", callback_data="process_denoise")
        e_reverb = types.InlineKeyboardButton("🌊 Echo / Reverb Kawai", callback_data="process_reverb")
        markup.add(e_master, e_denoise, e_reverb)
        
        title = user_data[chat_id]['song_title']
        bot.send_message(
            chat_id, 
            f"✅ **An saita sunan waƙa zuwa:** `{title}`\n\nZaɓi tsarin gyaran da kake so:", 
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
    
    if call.data == "process_master":
        bot.send_message(chat_id, "🎛️ **Ina gudanar da FULL MASTERING...**", parse_mode="Markdown")
        try:
            apply_studio_effects(input_wav, output_wav, add_reverb=True)
            with open(output_wav, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, audio_out, 
                    caption=f"🔥 **Gashi nan an kammala Full Studio Master!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, performer="Hausa AI Studio", parse_mode="Markdown"
                )
        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru: {str(e)}")

    elif call.data == "process_denoise":
        bot.send_message(chat_id, "⚙️ **Ina goge iska da tsawar baya...**", parse_mode="Markdown")
        try:
            clean_audio_data(input_wav, output_wav)
            sound = AudioSegment.from_wav(output_wav).normalize()
            sound.export(output_wav, format="wav")
            
            with open(output_wav, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, audio_out, 
                    caption=f"✨ **Gashi nan an cire iska da tsawa!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, performer="Hausa AI Studio", parse_mode="Markdown"
                )
        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru: {str(e)}")

    elif call.data == "process_reverb":
        bot.send_message(chat_id, "🌊 **Ina sanya Reverb & Echo...**", parse_mode="Markdown")
        try:
            sound = AudioSegment.from_wav(input_wav)
            echo = sound - 8
            combined = sound.overlay(echo, position=120).normalize()
            combined.export(output_wav, format="wav")
            
            with open(output_wav, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, audio_out, 
                    caption=f"✨ **Gashi nan an sanya Reverb!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, performer="Hausa AI Studio", parse_mode="Markdown"
                )
        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru: {str(e)}")

def start_bot():
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    t = threading.Thread(target=start_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
