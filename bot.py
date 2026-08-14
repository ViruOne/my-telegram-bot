import os
import random
import requests
import telebot
from telebot import types


# ============================================================
# ENVIRONMENT
# ============================================================

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


# ============================================================
# START
# ============================================================

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
        "Assalomu alaykum! *Usta Express* botiga xush kelibsiz.\n\n"
        "Ro'yxatdan o'tish uchun faqat pastdagi "
        "📞 *Telefon raqamni yuborish* tugmasini bosing.\n\n"
        "🇺🇿 Faqat O'zbekiston telefon raqamlari qabul qilinadi.",
        parse_mode="Markdown",
        reply_markup=markup,
    )


# ============================================================
# CONTACT ONLY
# ============================================================

@bot.message_handler(content_types=["contact"])
def handle_contact(message):
    # Faqat Telegramdagi o'z kontaktini yuborishiga ruxsat.
    # Boshqa odamning kontaktini yuborsa qabul qilinmaydi.
    if (
        message.contact.user_id is not None
        and message.contact.user_id != message.from_user.id
    ):
        bot.send_message(
            message.chat.id,
            "❌ Iltimos, o'zingizning telefon raqamingizni "
            "📞 *Telefon raqamni yuborish* tugmasi orqali yuboring.",
            parse_mode="Markdown",
        )
        return

    phone = str(message.contact.phone_number or "").strip()

    # Telegram odatda +998 formatida yuboradi.
    # Faqat O'zbekiston: +998 + 9 ta raqam.
    if not phone.startswith("+998"):
        bot.send_message(
            message.chat.id,
            "❌ Faqat 🇺🇿 O'zbekiston telefon raqamlari qabul qilinadi.\n\n"
            "Iltimos, 📞 *Telefon raqamni yuborish* tugmasini bosing.",
            parse_mode="Markdown",
        )
        return

    # +998 dan keyin aynan 9 ta raqam bo'lishi kerak.
    uz_phone_digits = phone[1:]

    if len(uz_phone_digits) != 12 or not uz_phone_digits.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ Telefon raqami noto'g'ri.\n\n"
            "Faqat 🇺🇿 O'zbekiston raqami qabul qilinadi.",
        )
        return

    # +998XXXXXXXXX
    normalized_phone = "+998" + uz_phone_digits[3:]

    chat_id = message.chat.id

    # 6 xonali tasdiqlash kodi
    code = str(random.randint(100000, 999999))

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    data = {
        "phone_number": normalized_phone,
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
            print(
                "Supabase error:",
                response.status_code,
                response.text,
            )

            bot.send_message(
                chat_id,
                "❌ Bazaga yozishda xatolik yuz berdi. "
                "Iltimos, keyinroq qayta urinib ko'ring.",
            )

    except requests.RequestException as error:
        print("Supabase connection error:", error)

        bot.send_message(
            chat_id,
            "❌ Server bilan bog'lanishda xatolik yuz berdi. "
            "Iltimos, keyinroq qayta urinib ko'ring.",
        )


# ============================================================
# ALL OTHER TEXT / CONTACT TYPES
# ============================================================

@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "video",
        "document",
        "audio",
        "voice",
        "location",
        "sticker",
        "animation",
    ]
)
def reject_manual_input(message):
    # Telefon raqamini qo'lda yozishni qabul qilmaymiz.
    # Faqat Telegram contact tugmasi ishlaydi.
    if message.text == "/start":
        return

    bot.send_message(
        message.chat.id,
        "❌ Telefon raqamini qo'lda yozib yuborish mumkin emas.\n\n"
        "Iltimos, 📞 *Telefon raqamni yuborish* tugmasini bosing.\n"
        "🇺🇿 Faqat O'zbekiston raqamlari qabul qilinadi.",
        parse_mode="Markdown",
    )


# ============================================================
# RUN
# ============================================================

print("Bot ishga tushdi...")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30,
)
