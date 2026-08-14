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

# Sizning Telegram Admin ID'ingiz
ADMIN_ID = os.getenv("ADMIN_ID", "7782825299").strip()


if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable topilmadi."
    )

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL environment variable topilmadi."
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_KEY environment variable topilmadi."
    )


# ============================================================
# TELEGRAM BOT
# ============================================================

bot = telebot.TeleBot(TOKEN)


# Admin /broadcast buyrug'idan keyin
# reklama matnini kutish holati
broadcast_waiting = set()


# ============================================================
# SUPABASE HEADERS
# ============================================================

def supabase_headers(prefer=None):

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    if prefer:
        headers["Prefer"] = prefer

    return headers


# ============================================================
# UZBEKISTAN PHONE NORMALIZATION
# ============================================================

def normalize_uz_phone(phone):

    if not phone:
        return None

    phone = str(phone).strip()

    # Bo'sh joy, -, (, ) va boshqa belgilarni olib tashlash
    phone = re.sub(r"[^\d+]", "", phone)

    # + belgisi bo'lmasa qo'shamiz
    if phone.startswith("998"):
        phone = "+" + phone

    # Faqat +998XXXXXXXXX
    if not re.fullmatch(r"\+998\d{9}", phone):
        return None

    return phone


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(message):

    if not message.from_user:
        return False

    return str(message.from_user.id) == ADMIN_ID


# ============================================================
# BROADCAST START
# ============================================================

@bot.message_handler(commands=["broadcast"])
def start_broadcast(message):

    if not is_admin(message):

        bot.send_message(
            message.chat.id,
            "❌ Sizda bu buyruqdan foydalanish huquqi yo'q."
        )

        return


    broadcast_waiting.add(
        message.from_user.id
    )


    bot.send_message(
        message.chat.id,
        "📢 Reklama xabarini yuboring.\n\n"
        "Hozircha faqat matnli xabar yuborish mumkin.\n\n"
        "Bekor qilish uchun /cancel yuboring."
    )


# ============================================================
# BROADCAST CANCEL
# ============================================================

@bot.message_handler(commands=["cancel"])
def cancel_broadcast(message):

    if not is_admin(message):
        return


    if message.from_user.id in broadcast_waiting:

        broadcast_waiting.discard(
            message.from_user.id
        )

        bot.send_message(
            message.chat.id,
            "✅ Broadcast bekor qilindi."
        )

    else:

        bot.send_message(
            message.chat.id,
            "Hozir faol broadcast yo'q."
        )


# ============================================================
# BROADCAST PROCESS
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

    broadcast_waiting.discard(
        message.from_user.id
    )


    advertisement = (
        message.text or ""
    ).strip()


    if not advertisement:

        bot.send_message(
            message.chat.id,
            "❌ Reklama matni bo'sh bo'lishi mumkin emas."
        )

        return


    # ========================================================
    # USERS FROM SUPABASE
    # ========================================================

    try:

        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            params={
                "select": "telegram_chat_id",
                "telegram_chat_id": "not.is.null",
            },
            headers=supabase_headers(),
            timeout=15,
        )


        if response.status_code != 200:

            print(
                "Broadcast users query error:",
                response.status_code,
                response.text[:1000],
            )


            bot.send_message(
                message.chat.id,
                "❌ Foydalanuvchilarni olishda xatolik yuz berdi."
            )

            return


        rows = response.json()


    except requests.RequestException as error:

        print(
            "Broadcast users connection error:",
            error
        )


        bot.send_message(
            message.chat.id,
            "❌ Server bilan bog'lanishda xatolik yuz berdi."
        )

        return


    # ========================================================
    # UNIQUE CHAT IDS
    # ========================================================

    chat_ids = []

    seen = set()


    for row in rows:

        chat_id = row.get(
            "telegram_chat_id"
        )


        if chat_id is None:
            continue


        chat_id = str(
            chat_id
        ).strip()


        if not chat_id:
            continue


        if chat_id in seen:
            continue


        seen.add(chat_id)

        chat_ids.append(
            chat_id
        )


    # ========================================================
    # SEND BROADCAST
    # ========================================================

    sent = 0
    failed = 0
    blocked = 0


    bot.send_message(
        message.chat.id,
        f"📢 Broadcast boshlandi.\n\n"
        f"👥 Jami: {len(chat_ids)} ta foydalanuvchi."
    )


    for chat_id in chat_ids:

        try:

            bot.send_message(
                chat_id,
                advertisement
            )

            sent += 1


        except Exception as error:

            failed += 1


            error_text = str(
                error
            ).lower()


            if (
                "blocked by the user" in error_text
                or "chat not found" in error_text
                or "user is deactivated" in error_text
            ):

                blocked += 1


            print(
                f"Broadcast failed "
                f"for chat_id={chat_id}: {error}"
            )


    # ========================================================
    # BROADCAST RESULT
    # ========================================================

    bot.send_message(
        message.chat.id,
        "✅ Broadcast tugadi.\n\n"
        f"📨 Yuborildi: {sent}\n"
        f"❌ Xato: {failed}\n"
        f"🚫 Bloklangan/topilmagan: {blocked}\n"
        f"👥 Jami: {len(chat_ids)}"
    )


# ============================================================
# START
# ============================================================

@bot.message_handler(
    commands=["start"]
)
def send_welcome(message):

    markup = types.ReplyKeyboardMarkup(
        one_time_keyboard=True,
        resize_keyboard=True,
    )


    button_phone = types.KeyboardButton(
        text="📞 Telefon raqamni yuborish",
        request_contact=True,
    )


    markup.add(
        button_phone
    )


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

@bot.message_handler(
    content_types=["contact"]
)
def handle_contact(message):

    if not message.contact:
        return


    # ========================================================
    # FAQAT O'ZINING KONTAKTINI QABUL QILISH
    # ========================================================

    contact_user_id = (
        message.contact.user_id
    )

    sender_user_id = (
        message.from_user.id
    )


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


    # ========================================================
    # PHONE
    # ========================================================

    raw_phone = (
        message.contact.phone_number
    )


    print(
        f"Telegram contact received: {raw_phone}"
    )


    phone = normalize_uz_phone(
        raw_phone
    )


    # ========================================================
    # NOT UZBEKISTAN NUMBER
    # ========================================================

    if not phone:

        print(
            f"Rejected phone number: {raw_phone}"
        )


        bot.send_message(
            message.chat.id,

            "❌ Bu O'zbekiston raqami emas yoki raqam noto'g'ri.\n\n"

            "🇺🇿 Faqat +998XXXXXXXXX "
            "formatidagi raqamlar qabul qilinadi.",
        )

        return


    print(
        f"Accepted Uzbekistan phone: {phone}"
    )


    chat_id = message.chat.id


    # ========================================================
    # VERIFICATION CODE
    # ========================================================

    code = str(
        random.randint(
            100000,
            999999
        )
    )


    # ========================================================
    # SUPABASE DATA
    # ========================================================

    data = {

        "phone_number":
            phone,

        "telegram_chat_id":
            chat_id,

        "verification_code":
            code,
    }


    try:

        response = requests.post(

            f"{SUPABASE_URL}/rest/v1/users",

            headers=supabase_headers(
                prefer="resolution=merge-duplicates"
            ),

            json=data,

            timeout=15,
        )


        print(
            f"Supabase response: "
            f"{response.status_code} "
            f"{response.text[:500]}"
        )


        # ====================================================
        # SUCCESS
        # ====================================================

        if response.status_code in (
            200,
            201,
            204
        ):

            bot.send_message(

                chat_id,

                f"✅ Raqamingiz qabul qilindi.\n\n"

                f"Sizning tasdiqlash kodingiz: "
                f"*{code}*\n\n"

                f"Kodning amal qilish muddati 2 daqiqa.",

                parse_mode="Markdown",

                reply_markup=(
                    types.ReplyKeyboardRemove()
                ),
            )


        # ====================================================
        # SUPABASE ERROR
        # ====================================================

        else:

            bot.send_message(

                chat_id,

                "❌ Raqam qabul qilindi, "
                "lekin bazaga yozishda xatolik yuz berdi.\n\n"

                "Iltimos, keyinroq qayta urinib ko'ring.",
            )


    except requests.RequestException as error:

        print(
            "Supabase connection error:",
            error
        )


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

    # Admin broadcast uchun matn process_broadcast
    # handleriga o'tadi.
    if (
        is_admin(message)
        and message.from_user.id in broadcast_waiting
    ):
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

print(
    "=========================================="
)

print(
    "Bot ishga tushdi..."
)

print(
    f"Admin ID: {ADMIN_ID}"
)

print(
    "=========================================="
)


bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30,
)
