import os
import random
import re
import time

import requests
import telebot
from telebot import types


# ============================================================
# ENVIRONMENT
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi.")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL environment variable topilmadi.")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY environment variable topilmadi.")

if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID environment variable topilmadi.")

ADMIN_ID = str(ADMIN_ID).strip()

bot = telebot.TeleBot(TOKEN)

# Admin broadcast xabarini kutayotgan bo'lsa shu yerda saqlanadi.
broadcast_waiting = set()


# ============================================================
# SUPABASE HEADERS
# ============================================================

def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


# ============================================================
# ADMIN
# ============================================================

def is_admin(message):
    if not message.from_user:
        return False
    return str(message.from_user.id) == ADMIN_ID


# ============================================================
# UZBEKISTAN PHONE NORMALIZATION
# ============================================================

def normalize_uz_phone(phone):
    """
    Faqat O'zbekiston telefon raqamini qabul qiladi.

    Qabul qilinadigan ko'rinishlar:
        +998901234567
        998901234567
        +998 90 123 45 67
        998 90 123 45 67

    Natija:
        +998901234567
    """

    if not phone:
        return None

    phone = str(phone).strip()
    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("998"):
        phone = "+" + phone

    if not re.fullmatch(r"\+998\d{9}", phone):
        return None

    return phone


# ============================================================
# GET REGISTERED USERS
# ============================================================

def get_registered_chat_ids():
    """
    Supabase users jadvalidan telegram_chat_id larni oladi.
    Takroriy chat_id larni bitta foydalanuvchi deb hisoblaydi.
    """

    url = (
        f"{SUPABASE_URL}/rest/v1/users"
        "?select=telegram_chat_id"
        "&telegram_chat_id=not.is.null"
    )

    response = requests.get(
        url,
        headers=supabase_headers(),
        timeout=20,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Supabase users query xatosi: "
            f"{response.status_code} {response.text[:500]}"
        )

    rows = response.json()

    chat_ids = []
    seen = set()

    for row in rows:
        chat_id = row.get("telegram_chat_id")

        if chat_id is None:
            continue

        chat_id = str(chat_id).strip()

        if not chat_id or chat_id in seen:
            continue

        seen.add(chat_id)
        chat_ids.append(chat_id)

    return chat_ids


# ============================================================
# /USERS
# ============================================================

@bot.message_handler(commands=["users"])
def users_count(message):
    """
    Faqat admin foydalanuvchilar sonini ko'ra oladi.
    """

    if not is_admin(message):
        bot.send_message(
            message.chat.id,
            "❌ Bu buyruq faqat admin uchun.",
        )
        return

    try:
        chat_ids = get_registered_chat_ids()

        bot.send_message(
            message.chat.id,
            "👥 *Foydalanuvchilar statistikasi*\n\n"
            f"👤 Jami ro'yxatdan o'tgan foydalanuvchilar: "
            f"*{len(chat_ids)} ta*\n\n"
            "Bu hisob telegram_chat_id bo'yicha takrorlanmaydigan "
            "foydalanuvchilar asosida chiqarildi.",
            parse_mode="Markdown",
        )

    except Exception as error:
        print("Users count error:", error)

        bot.send_message(
            message.chat.id,
            "❌ Foydalanuvchilar sonini olishda xatolik yuz berdi.",
        )


# ============================================================
# /STATS
# ============================================================

@bot.message_handler(commands=["stats"])
def stats(message):
    """
    /stats ham foydalanuvchilar sonini ko'rsatadi.
    """

    if not is_admin(message):
        bot.send_message(
            message.chat.id,
            "❌ Bu buyruq faqat admin uchun.",
        )
        return

    try:
        chat_ids = get_registered_chat_ids()

        bot.send_message(
            message.chat.id,
            "📊 *Bot statistikasi*\n\n"
            f"👥 Foydalanuvchilar: *{len(chat_ids)} ta*\n"
            f"🤖 Bot ishlayapti: *ha*",
            parse_mode="Markdown",
        )

    except Exception as error:
        print("Stats error:", error)

        bot.send_message(
            message.chat.id,
            "❌ Statistikani olishda xatolik yuz berdi.",
        )


# ============================================================
# /BROADCAST
# ============================================================

@bot.message_handler(commands=["broadcast"])
def start_broadcast(message):

    if not is_admin(message):
        bot.send_message(
            message.chat.id,
            "❌ Sizda bu buyruqdan foydalanish huquqi yo'q.",
        )
        return

    broadcast_waiting.add(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "📢 *Broadcast rejimi yoqildi.*\n\n"
        "Endi yubormoqchi bo'lgan reklama matningizni yuboring.\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode="Markdown",
    )


# ============================================================
# /CANCEL
# ============================================================

@bot.message_handler(commands=["cancel"])
def cancel_broadcast(message):

    if not is_admin(message):
        return

    if message.from_user.id in broadcast_waiting:
        broadcast_waiting.discard(message.from_user.id)

        bot.send_message(
            message.chat.id,
            "✅ Broadcast bekor qilindi.",
        )
    else:
        bot.send_message(
            message.chat.id,
            "Hozir faol broadcast yo'q.",
        )


# ============================================================
# PROCESS BROADCAST TEXT
# ============================================================

@bot.message_handler(
    func=lambda message: (
        message.from_user is not None
        and str(message.from_user.id) == ADMIN_ID
        and message.from_user.id in broadcast_waiting
        and message.content_type == "text"
        and not (message.text or "").startswith("/")
    )
)
def process_broadcast(message):

    broadcast_waiting.discard(message.from_user.id)

    advertisement = (message.text or "").strip()

    if not advertisement:
        bot.send_message(
            message.chat.id,
            "❌ Reklama matni bo'sh bo'lishi mumkin emas.",
        )
        return

    try:
        chat_ids = get_registered_chat_ids()
    except Exception as error:
        print("Broadcast users query error:", error)

        bot.send_message(
            message.chat.id,
            "❌ Foydalanuvchilarni olishda xatolik yuz berdi.",
        )
        return

    total = len(chat_ids)

    bot.send_message(
        message.chat.id,
        "📢 *Broadcast boshlandi.*\n\n"
        f"👥 Jami: *{total} ta* foydalanuvchi.",
        parse_mode="Markdown",
    )

    sent = 0
    failed = 0
    blocked = 0

    for index, chat_id in enumerate(chat_ids, start=1):

        try:
            bot.send_message(
                chat_id,
                advertisement,
            )

            sent += 1

        except Exception as error:

            failed += 1

            error_text = str(error).lower()

            if (
                "blocked by the user" in error_text
                or "chat not found" in error_text
                or "user is deactivated" in error_text
                or "bot was blocked" in error_text
            ):
                blocked += 1

            print(
                f"Broadcast failed for chat_id={chat_id}: {error}"
            )

        # Telegram rate limitiga urilmaslik uchun kichik pauza.
        if index % 25 == 0:
            time.sleep(1)

    bot.send_message(
        message.chat.id,
        "✅ *Broadcast tugadi.*\n\n"
        f"👥 Jami: *{total}*\n"
        f"📨 Yuborildi: *{sent}*\n"
        f"❌ Xato: *{failed}*\n"
        f"🚫 Bloklangan/topilmagan: *{blocked}*",
        parse_mode="Markdown",
    )


# ============================================================
# /HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    if is_admin(message):
        bot.send_message(
            message.chat.id,
            "🤖 *Admin buyruqlari*\n\n"
            "/users — foydalanuvchilar soni\n"
            "/stats — bot statistikasi\n"
            "/broadcast — hammaga reklama yuborish\n"
            "/cancel — broadcastni bekor qilish\n"
            "/help — yordam",
            parse_mode="Markdown",
        )
    else:
        bot.send_message(
            message.chat.id,
            "ℹ️ Ro'yxatdan o'tish uchun "
            "📞 *Telefon raqamni yuborish* tugmasidan foydalaning.",
            parse_mode="Markdown",
        )


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

    # Faqat foydalanuvchining o'z kontaktini qabul qilamiz.
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
            "🇺🇿 Faqat O'zbekiston raqamlari qabul qilinadi.",
        )
        return

    print(f"Accepted Uzbekistan phone: {phone}")

    chat_id = message.chat.id

    # 6 xonali tasdiqlash kodi.
    code = str(random.randint(100000, 999999))

    data = {
        "phone_number": phone,
        "telegram_chat_id": chat_id,
        "verification_code": code,
    }

    try:

        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers={
                **supabase_headers(),
                "Prefer": "resolution=merge-duplicates",
            },
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
                f"Sizning tasdiqlash kodingiz: *{code}*\n\n"
                f"Kodning amal qilish muddati 2 daqiqa.",
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
            "❌ Server bilan bog'lanishda xatolik yuz berdi.\n"
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

    # Admin broadcast kutish holatida bo'lsa, bu handler aralashmaydi.
    if is_admin(message) and message.from_user.id in broadcast_waiting:
        return

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
