import os
import random
import requests
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi.")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL environment variable topilmadi.")
if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY environment variable topilmadi.")

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    button_phone = types.KeyboardButton(
        text="📞 Telefon raqamni yuborish",
        request_contact=True,
    )
    markup.add(button_phone)

    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! *Usta Express* botiga xush kelibsiz. "
        "Ro'yxatdan o'tish uchun pastdagi tugmani bosing:",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.message_handler(content_types=["contact", "text"])
def handle_contact_or_text(message):
    phone = None

    if message.contact is not None:
        phone = message.contact.phone_number
    elif message.text and ("+" in message.text or message.text.isdigit()):
        phone = message.text

    if phone:
        if not phone.startswith("+"):
            phone = "+" + phone

        chat_id = message.chat.id
        code = str(random.randint(100000, 999999))

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }

        data = {
            "phone_number": phone,
            "telegram_chat_id": chat_id,
            "verification_code": code,
        }

        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=headers,
                json=data,
                timeout=15,
            )

            if response.status_code in (200, 201, 204):
                bot.send_message(
                    chat_id,
                    f"Sizning tasdiqlash kodingiz: *{code}*",
                    parse_mode="Markdown",
                    reply_markup=types.ReplyKeyboardRemove(),
                )
            else:
                print("Supabase error:", response.status_code, response.text)
                bot.send_message(
                    chat_id,
                    "Bazaga yozishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
                )

        except requests.RequestException as error:
            print("Supabase connection error:", error)
            bot.send_message(
                chat_id,
                "Server bilan bog'lanishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            )
    else:
        if message.text != "/start":
            bot.send_message(
                message.chat.id,
                "Iltimos, telefon raqamingizni tugmani bosish orqali yoki to'g'ri formatda yuboring.",
            )


print("Bot ishga tushdi...")
bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
