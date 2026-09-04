import os
import threading
import time
import requests
import telebot
from telebot import types
from flask import Flask
from pydub import AudioSegment, effects

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
HUGGINGFACE_TOKEN = "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"

# Model na AI goge hayaniya daga Hugging Face
HF_API_URL = "https://api-inference.huggingface.co/models/JorisCos/DCCRNet_TAC_Libri1Mix_enhance"
headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_data = {}

@app.route('/')
@app.route('/ping')
def home():
    return "OK", 200

def denoise_with_ai(input_file, output_file):
    """Gudanar da AI Noise Suppression ta Hugging Face API"""
    with open(input_file, "rb") as f:
        data = f.read()
    
    response = requests.post(HF_API_URL, headers=headers, data=data)
    
    # Idan AI model din yana cikin bootup (503), za mu jira sakan kadan mu sake gwadawa
    if response.status_code == 503:
        time.sleep(8)
        response = requests.post(HF_API_URL, headers=headers, data=data)

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            f.write(response.content)
        return True
    else:
        return False

def process_full_master(input_path, output_path):
    temp_ai_clean = f"{input_path}_aiclean.wav"
    
    # 1. AI Noise Suppression (Goge tsawa da iska)
    success = denoise_with_ai(input_path, temp_ai_clean)
    
    # Idan API din bai amsa ba, za mu amfani da ainihin sound din don kar tsarin ya tsaya
    file_to_process = temp_ai_clean if (success and os.path.exists(temp_ai_clean)) else input_path
    
    sound = AudioSegment.from_file(file_to_process)
    
    # 2. Dynamic High-Pass Filter
    clean_sound = sound.high_pass_filter(100)
    
    # 3. Dynamic Compressor (Broadcast/Studio Equalization)
    compressed = effects.compress_dynamic_range(
        clean_sound, 
        threshold=-18.0, 
        ratio=3.5, 
        attack=5.0, 
        release=50.0
    )
    
    # 4. Studio Reverb & Echo
    echo = compressed - 9
    mastered = compressed.overlay(echo, position=110)
    
    # 5. Volume Normalization
    final_output = mastered.normalize()
    final_output.export(output_path, format="mp3")
    
    # Sharar fayilolin wucin gadi
    if os.path.exists(temp_ai_clean):
        os.remove(temp_ai_clean)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    markup.add(btn_record)
    
    welcome_msg = (
        "🎧 **HAUSA AI MUSIC STUDIO (AI-Powered)** 🎧\n\n"
        "Aiko muryarka yanzu domin yi mata **Full AI Studio Master** (AI Noise Suppression + Reverb + Compression)."
    )
    bot.send_message(chat_id, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📥 **Ina saukewa da adana muryarka...**", parse_mode="Markdown")
    
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
        e_master = types.InlineKeyboardButton("🎛️ FULL STUDIO MASTER (AI Enhanced)", callback_data="process_master")
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
            
        bot.send_message(chat_id, "🎛️ **Ina gudanar da AI Deep Cleaning & Studio Mastering...**", parse_mode="Markdown")
        try:
            process_full_master(input_wav, output_mp3)
            
            with open(output_mp3, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, 
                    audio_out, 
                    caption=f"🔥 **Gashi nan an kammala AI Full Master!**\n🎵 **Waƙa:** {song_title}",
                    title=song_title, 
                    performer="Hausa AI Studio", 
                    parse_mode="Markdown"
                )
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
