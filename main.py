import os
import threading
import time
import telebot
from telebot import types
from flask import Flask
from pydub import AudioSegment, effects
from pydub.generators import Sine
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

def create_default_studio_beat(duration_ms):
    """Irƙirar Kiɗa na Watsa Shirye-shirye (Afrobeat Rhythm) idan mai amfani ba shi da kida"""
    bpm = 110
    beat_ms = int(60000 / bpm)
    
    # Bass & Kick Sound Generator
    kick = Sine(60).to_audio_segment(duration=100).fade_out(80) + 6
    snare = Sine(250).to_audio_segment(duration=80).fade_out(60) + 2
    hat = Sine(8000).to_audio_segment(duration=30).fade_out(20) - 10
    
    measure = AudioSegment.silent(duration=beat_ms * 4)
    # Loop beats pattern
    measure = measure.overlay(kick, position=0)
    measure = measure.overlay(hat, position=int(beat_ms * 0.5))
    measure = measure.overlay(snare, position=beat_ms)
    measure = measure.overlay(hat, position=int(beat_ms * 1.5))
    measure = measure.overlay(kick, position=beat_ms * 2)
    measure = measure.overlay(hat, position=int(beat_ms * 2.5))
    measure = measure.overlay(snare, position=beat_ms * 3)
    measure = measure.overlay(hat, position=int(beat_ms * 3.5))
    
    # Repeat pattern to match vocal duration
    loops_needed = int(duration_ms / len(measure)) + 1
    full_beat = measure * loops_needed
    return full_beat[:duration_ms]

def apply_studio_preset(sound, preset_type):
    """Sanya Custom Studio Vocal FX Presets"""
    if preset_type == "fx_amapiano":
        clean = sound.high_pass_filter(120).low_pass_filter(8500)
        compressed = effects.compress_dynamic_range(clean, threshold=-16.0, ratio=4.0)
        echo = compressed - 6
        return compressed.overlay(echo, position=120)
        
    elif preset_type == "fx_trap":
        clean = sound.high_pass_filter(150)
        compressed = effects.compress_dynamic_range(clean, threshold=-22.0, ratio=5.0, attack=2.0)
        return compressed
        
    elif preset_type == "fx_acoustic":
        clean = sound.high_pass_filter(90)
        compressed = effects.compress_dynamic_range(clean, threshold=-14.0, ratio=2.5)
        reverb = compressed - 8
        return compressed.overlay(reverb, position=180)
        
    elif preset_type == "fx_telephone":
        return sound.high_pass_filter(300).low_pass_filter(3000)
        
    else:
        clean = sound.high_pass_filter(100)
        compressed = effects.compress_dynamic_range(clean, threshold=-18.0, ratio=3.5)
        echo = compressed - 9
        return compressed.overlay(echo, position=80)

def process_full_audio_mix(vocal_path, beat_path=None, output_path="output.mp3", preset_type="fx_standard"):
    # 1. AI Deep Cleaning a kan Muryar
    ai_cleaned_file = denoise_with_gradio_ai(vocal_path)
    source_vocal = ai_cleaned_file if ai_cleaned_file else vocal_path
    
    vocal_sound = AudioSegment.from_file(source_vocal)
    
    # 2. Sanya FX Preset
    processed_vocal = apply_studio_preset(vocal_sound, preset_type)
    
    # 3. Kida (Beat Mix)
    if beat_path and os.path.exists(beat_path):
        beat_sound = AudioSegment.from_file(beat_path)
    else:
        # Kirkirar Studio Beat ta atomatik idan babu fayil din kida
        beat_sound = create_default_studio_beat(len(processed_vocal))
        
    # Daidaita ƙarfin sauti (Auto-Mixing)
    beat_adjusted = beat_sound - 4
    vocal_boosted = processed_vocal + 3
    
    mixed = beat_adjusted.overlay(vocal_boosted, position=0)
    final_master = mixed.normalize()
    final_master.export(output_path, format="mp3", bitrate="320k")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'state': 'idle'}
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_record = types.InlineKeyboardButton("🎙️ Fara Aikin Waƙa / Turo Murya", callback_data="mode_record")
    markup.add(btn_record)
    
    welcome_msg = (
        "🎧 **HAUSA AI MUSIC STUDIO (Instant Song Builder)** 🎧\n\n"
        "Barka da zuwa! Zaka iya:\n"
        "1. Yi rikordin muryarka kai tsaye a Telegram.\n"
        "2. Ko turo Audio File wanda ka rigaya ka ɗauka a waya.\n\n"
        "AI zai goge hayaniya, ya sa kida da Auto-Mix ta atomatik!"
    )
    bot.send_message(chat_id, welcome_msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['voice', 'audio', 'document'])
def handle_audio(message):
    chat_id = message.chat.id
    
    # Idan mai amfani yana matakin turo Kida na kansa
    if chat_id in user_data and user_data[chat_id].get('state') == 'waiting_for_beat':
        bot.send_message(chat_id, "🎵 **Ina karɓar Fayil ɗin Kiɗan...**", parse_mode="Markdown")
        try:
            file_id = None
            if message.voice: file_id = message.voice.file_id
            elif message.audio: file_id = message.audio.file_id
            elif message.document: file_id = message.document.file_id
            
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            beat_path = f"user_{chat_id}_beat.wav"
            with open(beat_path, 'wb') as f:
                f.write(downloaded_file)
                
            user_data[chat_id]['beat_wav'] = beat_path
            user_data[chat_id]['state'] = 'choose_preset'
            show_preset_buttons(chat_id)
        except Exception as e:
            bot.send_message(chat_id, f"Matsala wajen karɓar kida: {str(e)}")
        return

    # Karɓar Murya (Voice Note, Audio File, ko Recorded Audio)
    bot.send_message(chat_id, "📥 **Ina karɓar Muryarka...**", parse_mode="Markdown")
    try:
        file_id = None
        if message.voice: file_id = message.voice.file_id
        elif message.audio: file_id = message.audio.file_id
        elif message.document: file_id = message.document.file_id

        if not file_id:
            bot.send_message(chat_id, "Don Allah turo fayil ɗin sauti (Audio/Voice Note).")
            return

        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        input_path = f"user_{chat_id}_input.wav"
        with open(input_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        user_data[chat_id] = {
            'input_wav': input_path,
            'beat_wav': None,
            'state': 'ask_beat'
        }
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        b1 = types.InlineKeyboardButton("🎵 Turo Kiɗa Na (Custom Beat)", callback_data="has_beat")
        b2 = types.InlineKeyboardButton("🪄 Yi Amfani da Auto-Beat na AI", callback_data="auto_beat")
        markup.add(b1, b2)
        
        bot.send_message(
            chat_id, 
            "✅ **An karɓi Muryarka!**\n\nZa ka turo fayil ɗin kiɗanka ne ko kuma mu haɗa ta da Kiɗan AI ta atomatik?", 
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.send_message(chat_id, f"Matsala wajen karɓar murya: {str(e)}")

def show_preset_buttons(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🎛️ Standard Studio", callback_data="fx_standard")
    b2 = types.InlineKeyboardButton("🎹 Amapiano Vocal", callback_data="fx_amapiano")
    b3 = types.InlineKeyboardButton("🔥 Trap / Drill FX", callback_data="fx_trap")
    b4 = types.InlineKeyboardButton("🎸 Acoustic Reverb", callback_data="fx_acoustic")
    b5 = types.InlineKeyboardButton("📞 Telephone / Lo-Fi", callback_data="fx_telephone")
    
    markup.add(b1)
    markup.add(b2, b3)
    markup.add(b4, b5)
    
    bot.send_message(
        chat_id, 
        "🎛️ **Zaɓi salon Studio Vocal FX da kake so a sanya a muryar:**", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    
    if call.data == "mode_record":
        bot.send_message(chat_id, "🎙️ **Yi rikodin muryarka ko ka turo fayil ɗin sauti daga wayarka!**", parse_mode="Markdown")
        return

    if call.data == "has_beat":
        user_data[chat_id]['state'] = 'waiting_for_beat'
        bot.send_message(chat_id, "🎵 **Turo fayil ɗin Kiɗanka a nan yanzu:**", parse_mode="Markdown")
        return
        
    if call.data == "auto_beat":
        user_data[chat_id]['state'] = 'choose_preset'
        show_preset_buttons(chat_id)
        return

    # Processing FX & Mixing
    if call.data.startswith("fx_"):
        if chat_id not in user_data or 'input_wav' not in user_data[chat_id]:
            bot.send_message(chat_id, "Da fatan za ka sake turo muryar ka tukuna!")
            return
            
        vocal_wav = user_data[chat_id]['input_wav']
        beat_wav = user_data[chat_id].get('beat_wav')
        preset_chosen = call.data
        output_mp3 = f"user_{chat_id}_final_song.mp3"
        
        bot.send_message(chat_id, "🎛️ **AI yana goge hayaniya, sanya kida, da Auto-Mixing... (Minti 1-2)**", parse_mode="Markdown")
        try:
            process_full_audio_mix(vocal_wav, beat_wav, output_mp3, preset_type=preset_chosen)
            
            preset_name = preset_chosen.replace('fx_', '').capitalize()
            caption_text = f"🔥 **Gashi nan an kammala Cikakkiyar Waƙa!**\n🎛️ **Preset:** `{preset_name}`"
            if beat_wav:
                caption_text += "\n🎵 **Kida:** Custom Beat"
            else:
                caption_text += "\n🪄 **Kida:** Auto-Beat Studio"

            with open(output_mp3, 'rb') as audio_out:
                bot.send_audio(
                    chat_id, 
                    audio_out, 
                    caption=caption_text,
                    title="Cikakkiyar Waka", 
                    performer="Hausa AI Studio", 
                    parse_mode="Markdown"
                )
            
            # Cleaning temporary files
            if os.path.exists(vocal_wav): os.remove(vocal_wav)
            if beat_wav and os.path.exists(beat_wav): os.remove(beat_wav)
            if os.path.exists(output_mp3): os.remove(output_mp3)

        except Exception as e:
            bot.send_message(chat_id, f"Matsala ta faru wajen sarrafa sauti: {str(e)}")

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
