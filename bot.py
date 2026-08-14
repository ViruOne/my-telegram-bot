import os
import random
import re
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
# UZBEKISTAN PHONE NORMALIZATION
# ============================================================

def normalize_uz_phone(phone):
    """
    Telegram contact quyidagi ko'rinishlarda kelishi mumkin:
      +998901234567
      998901234567
      +998 90 123 45 67
      998 90 123 45 67

    Natija doim:
      +998901234567

    Faqat O'zbekiston raqami qabul qilinadi.
    """

    if not phone:
        return None

    # Faqat raqam va + belgisini qoldiramiz
    phone = str(phone).strip()
    phone = re.sub(r"[^\d+]", "", phone)

    # Telegram ba'zan + belgisiz yuborishi mumkin
    if phone.startswith("998"):
        phone = "+" + phone

    # Aynan +998 + 9 ta raqam
    if not re.fullmatch(r"\+998\d{9}", phone):
        return None

    return phone


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
        "Assalomu alaykum! *Master Go* botiga xush kelibsiz.\n\n"
        "Ro'yxatdan o'tish uchun pastdagi "
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

    if not message.contact:
        return

    # Faqat o'zining kontaktini yuborishga ruxsat
    contact_user_id = message.contact.user_id
    sender_user_id = message.from_user.id

    if (
        contact_user_id is not None
        and contact_user_id != sender_user_id
    ):
        bot.send_message(
            message.chat.id,
            "❌ Boshqa odamning raqamini yuborish mumkin emas.\n\n"
            "Iltimos, o'zingizning raqamingizni "
            "📞 *Telefon raqamni yuborish* tugmasi orqali yuboring.",
            parse_mode="Markdown",
        )
        return

    raw_phone = message.contact.phone_number

    print(f"Telegram contact received: {raw_phone}")

    phone = normalize_uz_phone(raw_phone)

    if not phone:
        print(f"Rejected phone number: {raw_phone}")

        bot.send_message(
            message.chat.id,
            "❌ Bu O'zbekiston raqami emas yoki raqam noto'g'ri.\n\n"
            "🇺🇿 Faqat +998XXXXXXXXX formatidagi raqamlar qabul qilinadi.",
        )
        return

    print(f"Accepted Uzbekistan phone: {phone}")

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

        print(
            f"Supabase response: {response.status_code} "
            f"{response.text[:500]}"
        )

        if response.status_code in (200, 201, 204):

            bot.send_message(
                chat_id,
                f"✅ Raqamingiz qabul qilindi.\n\n"
                f"Sizning tasdiqlash kodingiz: *{code}* \n\n"
                f"Kodning amal qilish muddati 2 daqiqa",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove(),
            )

        else:

            bot.send_message(
                chat_id,
                "❌ Raqam qabul qilindi, lekin bazaga yozishda "
                "xatolik yuz berdi.\n\n"
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
# EVERYTHING ELSE IS REJECTED
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

    bot.send_message(
        message.chat.id,
        "❌ Telefon raqamini qo'lda yozib yuborish mumkin emas.\n\n"
        "📞 *Telefon raqamni yuborish* tugmasini bosing.\n"
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
