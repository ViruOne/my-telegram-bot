import telebot
from telebot import types
import requests
import random

TOKEN = '8883157872:AAECAxLKnxDbMB8O-IrPgFlvDczfv5KBJNs'
bot = telebot.TeleBot(TOKEN)

SUPABASE_URL = 'https://myoghqhasjqzwnhttwdh.supabase.co' 
SUPABASE_KEY = 'sb_publishable_1mM_VX5MWU6pjf89x23tOA_A3QaP6-u'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    button_phone = types.KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)
    markup.add(button_phone)
    
    bot.send_message(
        message.chat.id, 
        "Assalomu alaykum! *Usta Express* botiga xush kelibsiz. Ro'yxatdan o'tish uchun pastdagi tugmani bosing:",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(content_types=['contact', 'text'])
def handle_contact_or_text(message):
    phone = None
    
    if message.contact is not None:
        phone = message.contact.phone_number
    elif message.text and ('+' in message.text or message.text.isdigit()):
        phone = message.text

    if phone:
        if not phone.startswith('+'):
            phone = '+' + phone

        chat_id = message.chat.id
        
        # O'ZGARTIRILDI: 4 xonali o'rniga 6 xonali tasdiqlash kodi yaratiladi
        code = str(random.randint(100000, 999999))

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }
        
        data = {
            "phone_number": phone,
            "telegram_chat_id": chat_id,
            "verification_code": code 
        }
        
        response = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=headers, json=data)

        if response.status_code in [200, 201]:
            bot.send_message(
                chat_id, 
                f"Sizning tasdiqlash kodingiz: *{code}*", 
                parse_mode='Markdown',
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(chat_id, f"Bazaga yozishda xatolik: {response.text}")
    else:
        if message.text != '/start':
            bot.send_message(message.chat.id, "Iltimos, telefon raqamingizni tugmani bosish orqali yoki to'g'ri formatda yuboring.")

print("Bot ishga tushdi...")
bot.infinity_polling()