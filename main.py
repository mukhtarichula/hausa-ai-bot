import os
import threading
import time
import telebot
from telebot import types
from flask import Flask
from pydub import AudioSegment, effects
from gradio_client import Client, handle_file

TELEGRAM_TOKEN = "8662812194:AAHQcaN89G9vv8uQNWpiSjgCJuAwWMwg4ns"
HUGGINGFACE_TOKEN = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_data = {}

@app.route('/')
@app.route('/ping')
def home():
    return "OK", 200

def denoise_with_gradio_ai(input_wav_path):
    """Injin AI na DeepFilterNet wanda ke wanke iska 100%"""
    try:
        client = Client("fffiloni/DeepFilterNet", hf_token=HUGGINGFACE_TOKEN)
        result = client.predict(
            audio_file_path=handle_file(input_wav_path),
            api_name="/predict"
        )
        if result and os.path.exists(result):
            return result
    except Exception as e:
        print(f"Gradio AI Error: {str(e)}")
    return None

def apply_studio_preset(sound, preset_type):
    """Sanya Custom Studio Vocal FX Presets"""
    if preset_type == "fx_amapiano":
        # Amapiano: Crisp Highs, Stereo Echo & Moderate Reverb
        clean = sound.high_pass_filter(120).low_pass_filter(8500)
        compressed = effects.compress_dynamic_range(clean, threshold=-16.0, ratio=4.0)
        echo = compressed - 6
        return compressed.overlay(echo, position=120)
        
    elif preset_type == "fx_trap":
        # Trap/Drill: Sharp Compression & Heavy Presence
        clean = sound.high_pass_filter(150)
        compressed = effects.compress_dynamic_range(clean, threshold=-22.0, ratio=5.0, attack=2.0)
        return compressed
        
    elif preset_type == "fx_acoustic":
        # Acoustic: Warm, Soft Echo & Deep Hall Reverb
        clean = sound.high_pass_filter(90)
        compressed = effects.compress_dynamic_range(clean, threshold=-14.0, ratio=2.5)
        reverb = compressed - 8
        return compressed.overlay(reverb, position=180)
        
    elif preset_type == "fx_telephone":
        # Telephone/Lo-Fi Effect: Bandpass Filter (300Hz - 3000Hz)
        return sound.high_pass_filter(300).low_pass_filter(3000)
        
    else:
        # Standard Studio Master
        clean = sound.high_pass_filter(100)
        compressed = effects.compress_dynamic_range(clean, threshold=-18.0, ratio=3.5)
        echo = compressed - 9
        return compressed.overlay(echo, position=80)

def process_full_master(input_path, output_path, preset_type="fx_standard"):
    # 1. AI Deep Cleaning
    ai_cleaned_file = denoise_with_gradio_ai(input_path)
    source_file = ai_cleaned_file if ai_cleaned_file else input_path
    
    sound = AudioSegment.from_file(source_file)
    
    # 2. Application na Selected Studio FX Preset
    mastered = apply_studio_preset(sound, preset_type)
    
    # 3. Volume Loudness Normalization
    final_output = mastered.normalize()
    final_output.export(output_path, format="mp3", bitrate="320k")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_record = types.InlineKeyboardButton("🎙️ Aiko Muryar Waka", callback_data="mode_record")
    markup.add(btn_record)
    
    welcome_msg = (
        "🎧 **HAUSA AI MUSIC STUDIO (Multi-Preset FX)** 🎧\n\n"
        "Barka da zuwa! Aiko muryarka yanzu domin yi mata **AI Deep Cleaning** da zaɓar salon **Studio Vocal Filter (FX)**."
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
        
        # Maɓallan Presets Daban-daban
        markup = types.InlineKeyboardMarkup(row_width=2)
        b1 = types.InlineKeyboardButton("🎛️ Standard Studio", callback_data="fx_standard")
        b2 = types.InlineKeyboardButton("🎹 Amapiano Vocal", callback_data="fx_amapiano")
        b3 = types.InlineKeyboardButton("🔥 Trap / Drill FX", callback_data="fx_trap")
        b4 = types.InlineKeyboardButton("🎸 Acoustic Reverb", callback_data="fx_acoustic")
        b5 = types.InlineKeyboardButton("📞 Telephone / Lo-Fi", callback_data="fx_telephone")
        
        markup.add(b1)
        markup.add(b2, b3)
        markup.add(b4, b5)
        
        title = user_data[chat_id]['song_title']
        bot.send_message(
            chat_id, 
            f"✅ **An saita sunan waƙa zuwa:** `{title}`\n\n🎛️ **Zaɓi salon Studio Vocal FX da kake so a sanya wa muryar:**", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )
    else:
        send_welcome(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    if call.data == "mode_record":
        bot.send_message(chat_id, "🎙️ **Yi rikodin muryarka ka turo min yanzu!**", parse_mode="Markdown")
        return

    if chat_id not in user_data or 'input_wav' not in user_data[chat_id]:
        bot.send_message(chat_id, "Da fatan za ka aiko da muryar ka tukuna!")
        return
        
    input_wav = user_data[chat_id]['input_wav']
    output_mp3 = f"user_{chat_id}_master.mp3"
    song_title = user_data[chat_id].get('song_title', 'Hausa AI Track')
    preset_chosen = call.data
    
    bot.send_message(chat_id, "🤖 **AI yana wanke iska da sanya Vocal FX Preset... (Minti 1-2)**", parse_mode="Markdown")
    try:
        process_full_master(input_wav, output_mp3, preset_type=preset_chosen)
        
        with open(output_mp3, 'rb') as audio_out:
            bot.send_audio(
                chat_id, 
                audio_out, 
                caption=f"🔥 **Gashi nan an kammala AI Studio Master!**\n🎵 **Waƙa:** {song_title}\n🎛️ **Preset:** `{preset_chosen.replace('fx_', '').capitalize()}`",
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
