import os
import threading
import time
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

def process_full_master(input_path, output_path):
    sound = AudioSegment.from_file(input_path)
    
    # 1. High-Pass Filter (Datse Iska da Rumble)
    clean_sound = sound.high_pass_filter(120)
    
    # 2. Dynamic Compressor (Sanya Muryar ta fito kamar Rediyo/Broadcast)
    compressed = effects.compress_dynamic_range(
        clean_sound, 
        threshold=-18.0, 
        ratio=3.5, 
        attack=5.0, 
        release=50.0
    )
    
    # 3. Studio Echo / Reverb (Sanya amsawa mai zaƙi)
    echo = compressed - 9
    mastered = compressed.overlay(echo, position=100)
    
    # 4. Normalize (Daidaita Ƙarfin Sauti)
    final_output = mastered.normalize()
    final_output.export(output_path, format="mp3")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    markup.add(btn_record)
    
    welcome_msg = (
        "🎧 **HAUSA AI MUSIC STUDIO** 🎧\n\n"
        "Aiko muryarka yanzu domin yi mata **Full Studio Master** (Goge Iska + Studio Voice + Reverb)."
    )
    bot.send_message(chat_id, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "📥 **Ina saukewa da adana muryarka...**", parse_mode="Markdown")
    
    try:
        file_info = bot.get_file(message.voice.file_id if message.voice else message.audio.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = f"user_{chat_id}_input.ogg"
        
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        user_data[chat_id] = {
            'input_ogg': input_path,
            'state': 'waiting_for_title',
            'song_title': 'Hausa AI Track'
        }
        
        bot.send_message(
            chat_id, 
            "✍️ **Rubuta Sunan Waƙar dake so a sanya:**\n*(Ko ka danna /skip)*",
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
    
    if chat_id not in user_data or 'input_ogg' not in user_data[chat_id]:
        bot.send_message(chat_id, "Da fatan za ka aiko da muryar ka tukuna!")
        return
        
    input_ogg = user_data[chat_id]['input_ogg']
    output_mp3 = f"user_{chat_id}_master.mp3"
    song_title = user_data[chat_id].get('song_title', 'Hausa AI Track')
    
    if call.data == "process_master" or call.data == "mode_record":
        if call.data == "mode_record":
            bot.send_message(chat_id, "🎙️ **Yi rikodin muryarka ka turo min yanzu!**", parse_mode="Markdown")
            return
            
        bot.send_message(chat_id, "🎛️ **Ina gudanar da FULL STUDIO MASTERING...**", parse_mode="Markdown")
        try:
            process_full_master(input_ogg, output_mp3)
            
            with open(output_mp3, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, 
                    audio_out, 
                    caption=f"🔥 **Gashi nan an kammala Full Master!**\n🎵 **Waƙa:** {song_title}",
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
