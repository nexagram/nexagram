import os
import base64
import io

print("Устанавливаем библиотеки (включая pypdf для чтения документов)...")
os.system("pip install pyTelegramBotAPI openai pypdf")

import telebot
from openai import OpenAI
from pypdf import PdfReader

# Твой токен от @BotFather
TG_TOKEN = '7986644960:AAFho5Oy4PwLe1cS0I7ZOaBSqOZQSzN7_bA'

# Твой ключ от Tooken Club
AI_KEY = 'tc_live_4e-rJE1hbDzFCn1tU1q0MfCkTtNzh44i'

# Адрес сервера
AI_URL = 'https://tooken.club/v1' 

bot = telebot.TeleBot(TG_TOKEN)

client = OpenAI(
    api_key=AI_KEY,
    base_url=AI_URL
)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я работаю 24/7. Я умею общаться текстом, рисовать по команде /img, смотреть фотографии и читать документы (PDF, TXT).")

# --- ГЕНЕРАЦИЯ КАРТИНОК ---
@bot.message_handler(commands=['img', 'image'])
def generate_image(message):
    prompt = message.text.replace('/img', '').replace('/image', '').strip()
    
    if not prompt:
        bot.reply_to(message, "Напиши, что нужно нарисовать. Например: /img киберпанк город будущего")
        return
        
    msg = bot.reply_to(message, "🎨 Рисую... Это может занять 10-20 секунд.")
    
    try:
        response = client.images.generate(
            model="gpt-image-2", 
            prompt=prompt,
            response_format="b64_json", 
            n=1
        )
        
        b64_data = response.data[0].b64_json
        image_bytes = base64.b64decode(b64_data)
        
        bot.send_photo(message.chat.id, photo=image_bytes, caption=f"Вот твоя картинка: {prompt}")
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Ошибка генерации: {e}")

# --- АНАЛИЗ ФОТОГРАФИЙ (VISION) ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    prompt = message.caption if message.caption else "Опиши подробно, что изображено на этой картинке."
    msg = bot.reply_to(message, "👀 Скачиваю и разглядываю картинку...")
    
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        image_payload = f"data:image/jpeg;base64,{base64_image}"
        
        response = client.chat.completions.create(
            model="gpt-5.6-sol",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_payload}}
                    ]
                }
            ]
        )
        
        answer = response.choices[0].message.content
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=answer)
        
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Ошибка анализа фото: {e}")

# --- НОВАЯ ФУНКЦИЯ: ЧТЕНИЕ ДОКУМЕНТОВ (PDF, TXT и др.) ---
@bot.message_handler(content_types=['document'])
def handle_document(message):
    prompt = message.caption if message.caption else "Проанализируй этот документ и кратко расскажи, о чем в нем говорится."
    msg = bot.reply_to(message, "📄 Скачиваю и читаю документ...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name.lower()
        
        extracted_text = ""
        
        # Если это текстовый файл или код
        if file_name.endswith(('.txt', '.py', '.json', '.md', '.html', '.css', '.js', '.csv')):
            extracted_text = downloaded_file.decode('utf-8', errors='ignore')
            
        # Если это PDF файл
        elif file_name.endswith('.pdf'):
            pdf_file = io.BytesIO(downloaded_file)
            reader = PdfReader(pdf_file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        else:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="Пока я умею читать только текстовые файлы (.txt, .py, .md и т.д.) и PDF (.pdf).")
            return
            
        if not extracted_text.strip():
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="Не удалось извлечь текст из документа (возможно, он пустой или состоит только из картинок без текста).")
            return
            
        # Обрезаем текст, если документ огромный (чтобы не превысить лимиты токенов за раз)
        if len(extracted_text) > 15000:
            extracted_text = extracted_text[:15000] + "\n\n[Текст был обрезан из-за большой длины...]"
            
        full_prompt = f"{prompt}\n\nСодержимое документа:\n{extracted_text}"
        
        response = client.chat.completions.create(
            model="gpt-5.6-sol",
            messages=[{"role": "user", "content": full_prompt}]
        )
        
        answer = response.choices[0].message.content
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=answer)
        
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Ошибка чтения документа: {e}")

# --- ОБРАБОТКА АУДИО/ВИДЕО ---
@bot.message_handler(content_types=['audio', 'video', 'voice'])
def handle_media(message):
    bot.reply_to(message, "Аудио и видеофайлы я пока не умею расшифровывать, отправляй текст, фото или документы (PDF).")

# --- ОБЫЧНЫЙ ТЕКСТОВЫЙ ЧАТ ---
@bot.message_handler(func=lambda message: True)
def generate_answer(message):
    msg = bot.reply_to(message, "⏳ Думаю...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.6-sol", 
            messages=[{"role": "user", "content": message.text}]
        )
        
        answer = response.choices[0].message.content
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=answer)
        
    except Exception as e:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Ошибка: {e}")

if __name__ == '__main__':
    print("Бот успешно запущен со всеми функциями!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
