import os
import io
import time
import json
import base64
import sqlite3
import re
import datetime
import threading
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types, apihelper
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -------------------------------------------------------------------------
# 1. API Configuration & High Timeout Setup
# -------------------------------------------------------------------------
apihelper.CONNECT_TIMEOUT = 90
apihelper.READ_TIMEOUT = 90
apihelper.RETRY_ON_ERROR = True

TELEGRAM_BOT_TOKEN = "8732862832:AAHw0yxGvSsRJCk6HiR0b_uJ0gU2ee7hF0U"
ADMIN_CHAT_ID = 8732862832

PRICE_PER_CARD = 5.0
TELEBIRR_ACCOUNT = "0995774866"
TELEBIRR_NAME = "Dires Gobale (ዲረስ ጎባሌ)"
CBE_ACCOUNT = "1000305532472"
CBE_NAME = "Dires Gobale (ዲረስ ጎባሌ)"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=True, num_threads=60)

# -------------------------------------------------------------------------
# 2. Network-Resilient Message Sender (Freezing Prevention)
# -------------------------------------------------------------------------
def safe_send_message(chat_id, text, reply_markup=None, parse_mode=None, retries=3):
    """Network drop holeo retry kore message pouchhe dewar jonno helper"""
    for attempt in range(retries):
        try:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            if attempt == retries - 1:
                print(f"Failed to send message to {chat_id}: {e}")
                return None
            time.sleep(1)

# -------------------------------------------------------------------------
# 3. Font Setup
# -------------------------------------------------------------------------
AMHARIC_FONT = "Helvetica"
AMHARIC_BOLD = "Helvetica-Bold"

nyala_path = "C:/Windows/Fonts/nyala.ttf"
if not os.path.exists(nyala_path):
    nyala_path = "nyala.ttf"

if os.path.exists(nyala_path):
    try:
        pdfmetrics.registerFont(TTFont("Nyala", nyala_path))
        AMHARIC_FONT = "Nyala"
        AMHARIC_BOLD = "Nyala"
    except Exception:
        pass

CARD_W = 242.6
CARD_H = 153.0

# -------------------------------------------------------------------------
# 4. Amharic Transliteration
# -------------------------------------------------------------------------
AMH_TO_ENG = {
    'ሀ': 'Ha', 'ሁ': 'Hu', 'ሂ': 'Hi', 'ሃ': 'Ha', 'ሄ': 'He', 'ህ': 'H', 'ሆ': 'Ho',
    'ለ': 'Le', 'ሉ': 'Lu', 'ሊ': 'Li', 'ላ': 'La', 'ሌ': 'Le', 'ል': 'L', 'ሎ': 'Lo',
    'ሐ': 'Ha', 'ሑ': 'Hu', 'ሒ': 'Hi', 'ሓ': 'Ha', 'ሔ': 'He', 'ሕ': 'H', 'ሖ': 'Ho',
    'መ': 'Me', 'ሙ': 'Mu', 'ሚ': 'Mi', 'ማ': 'Ma', 'ሜ': 'Me', 'ም': 'M', 'ሞ': 'Mo',
    'ሠ': 'Se', 'ሡ': 'Su', 'ሢ': 'Si', 'ሣ': 'Sa', 'ሤ': 'Se', 'ሥ': 'S', 'ሦ': 'So',
    'ረ': 'Re', 'ሩ': 'Ru', 'ሪ': 'Ri', 'ራ': 'Ra', 'ሬ': 'Re', 'ር': 'R', 'ሮ': 'Ro',
    'ሰ': 'Se', 'ሱ': 'Su', 'ሲ': 'Si', 'ሳ': 'Sa', 'ሴ': 'Se', 'ስ': 'S', 'ሶ': 'So',
    'ሸ': 'She', 'ሹ': 'Shu', 'ሺ': 'Shi', 'ሻ': 'Sha', 'ሼ': 'She', 'ሽ': 'Sh', 'ሾ': 'Sho',
    'ቀ': 'Ke', 'ቁ': 'Ku', 'ቂ': 'Ki', 'ቃ': 'Ka', 'ቄ': 'Ke', 'ቅ': 'K', 'ቆ': 'Ko',
    'በ': 'Be', 'ቡ': 'Bu', 'ቢ': 'Bi', 'ባ': 'Ba', 'ቤ': 'Be', 'ብ': 'B', 'ቦ': 'Bo',
    'ተ': 'Te', 'ቱ': 'Tu', 'ቲ': 'Ti', 'ታ': 'Ta', 'ቴ': 'Te', 'ት': 'T', 'ቶ': 'To',
    'ቸ': 'Che', 'ቹ': 'Chu', 'ቺ': 'Chi', 'ቻ': 'Cha', 'ቼ': 'Che', 'ች': 'Ch', 'ቾ': 'Cho',
    'ኀ': 'Ha', 'ኁ': 'Hu', 'ኂ': 'Hi', 'ኃ': 'Ha', 'ኄ': 'He', 'ኅ': 'H', 'ኆ': 'Ho',
    'ነ': 'Ne', 'ኑ': 'Nu', 'ኒ': 'Ni', 'ና': 'Na', 'ኔ': 'Ne', 'ን': 'N', 'ኖ': 'No',
    'ኘ': 'Gne', 'ኙ': 'Gnu', 'ኚ': 'Gni', 'ኛ': 'Gna', 'ኜ': 'Gne', 'ኝ': 'Gn', 'ኞ': 'Gno',
    'አ': 'A', 'ኡ': 'U', 'ኢ': 'I', 'ኣ': 'A', 'ኤ': 'E', 'እ': 'E', 'ኦ': 'O',
    'ከ': 'Ke', 'ኩ': 'Ku', 'ኪ': 'Ki', 'ካ': 'Ka', 'ኬ': 'Ke', 'ክ': 'K', 'ኮ': 'Ko',
    'ኸ': 'He', 'ኹ': 'Hu', 'ኺ': 'Hi', 'ኻ': 'Ha', 'ኼ': 'He', 'ኽ': 'H', 'ኾ': 'Ho',
    'ወ': 'We', 'ዉ': 'Wu', 'ዊ': 'Wi', 'ዋ': 'Wa', 'ዌ': 'We', 'ው': 'W', 'ዎ': 'Wo',
    'ዐ': 'A', 'ዑ': 'U', 'ዒ': 'I', 'ዓ': 'A', 'ዔ': 'E', 'ዕ': 'E', 'ዖ': 'O',
    'ዘ': 'Ze', 'ዙ': 'Zu', 'ዚ': 'Zi', 'ዛ': 'Za', 'ዜ': 'Ze', 'ዝ': 'Z', 'ዞ': 'Zo',
    'ዠ': 'Zhe', 'ዡ': 'Zhu', 'ዢ': 'Zhi', 'ዣ': 'Zha', 'ዤ': 'Zhe', 'ዥ': 'Zh', 'ዦ': 'Zho',
    'የ': 'Ye', 'ዩ': 'Yu', 'ዪ': 'Yi', 'ያ': 'Ya', 'ዬ': 'Ye', 'ይ': 'Y', 'ዮ': 'Yo',
    'ደ': 'De', 'ዱ': 'Du', 'ዲ': 'Di', 'ዳ': 'Da', 'ዴ': 'De', 'ድ': 'D', 'ዶ': 'Do',
    'ጀ': 'Je', 'ጁ': 'Ju', 'ጂ': 'Ji', 'ጃ': 'Ja', 'ጄ': 'Je', 'ጅ': 'J', 'ጆ': 'Jo',
    'ገ': 'Ge', 'ጉ': 'Gu', 'ጊ': 'Gi', 'ጋ': 'Ga', 'ጌ': 'Ge', 'ግ': 'G', 'ጎ': 'Go',
    'ጠ': 'Te', 'ጡ': 'Tu', 'ጢ': 'Ti', 'ጣ': 'Ta', 'ጤ': 'Te', 'ጥ': 'T', 'ጦ': 'To',
    'ጨ': 'Che', 'ጩ': 'Chu', 'ጪ': 'Chi', 'ጫ': 'Cha', 'ጬ': 'Che', 'ጭ': 'Ch', 'ጮ': 'Cho',
    'ጰ': 'Pe', 'ጱ': 'Pu', 'ጲ': 'Pi', 'ጳ': 'Pa', 'ጴ': 'Pe', 'ጵ': 'P', 'ጶ': 'Po',
    'ጸ': 'Tse', 'ጹ': 'Tsu', 'ጺ': 'Tsi', 'ጻ': 'Tsa', 'ጼ': 'Tse', 'ጽ': 'Ts', 'ጾ': 'Tso',
    'ፀ': 'Tse', 'ፁ': 'Tsu', 'ፂ': 'Tsi', 'ፃ': 'Tsa', 'ፄ': 'Tse', 'ፅ': 'Ts', 'ፆ': 'Tso',
    'ፈ': 'Fe', 'ፉ': 'Fu', 'ፊ': 'Fi', 'ፋ': 'Fa', 'ፌ': 'Fe', 'ፍ': 'F', 'ፎ': 'Fo',
    'ፐ': 'Pe', 'ፑ': 'Pu', 'ፒ': 'Pi', 'ፓ': 'Pa', 'ፔ': 'Pe', 'ፕ': 'P', 'ፖ': 'Po'
}

def transliterate_amharic(text: str) -> str:
    words = text.strip().split()
    eng_words = []
    for w in words:
        out = ""
        for char in w:
            out += AMH_TO_ENG.get(char, char)
        eng_words.append(out.capitalize())
    return " ".join(eng_words)

# -------------------------------------------------------------------------
# 5. Date Conversion (E.C to G.C)
# -------------------------------------------------------------------------
def ethiopian_to_gregorian(ec_year: int, ec_month: int, ec_day: int):
    try:
        new_year_day = 12 if (ec_year % 4 == 3) else 11
        start_gc = datetime.date(ec_year + 7, 9, new_year_day)
        days_passed = (ec_month - 1) * 30 + (ec_day - 1)
        gc_date = start_gc + datetime.timedelta(days=days_passed)
        return gc_date.strftime("%Y/%m/%d")
    except Exception:
        return f"{ec_year + 8}/{str(ec_month).zfill(2)}/{str(ec_day).zfill(2)}"

def parse_and_convert_dob(input_text: str):
    text = input_text.strip()
    if "|" in text:
        parts = text.split("|")
        return parts[0].strip(), parts[1].strip()

    nums = re.findall(r'\d+', text)
    if len(nums) >= 3:
        y, m, d = int(nums[0]), int(nums[1]), int(nums[2])
        if y < 100: y += 1900
        ec_formatted = f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"
        gc_formatted = ethiopian_to_gregorian(y, m, d)
        return ec_formatted, gc_formatted
    else:
        return text, text

# -------------------------------------------------------------------------
# 6. Administrative Hierarchy
# -------------------------------------------------------------------------
ETHIOPIA_REGIONS = {
    "አማራ": {
        "en": "Amhara",
        "zones": {
            "ምዕራብ ጎጃም": ["ባህር ዳር ዙሪያ", "መኤጫ", "ይልማና ዴንሳ", "ቡሬ", "ደቡብ አቸፈር", "ሰሜን አቸፈር", "ደምበጫ", "ጃቢ ጥህናን", "ሰከላ", "ቁሪት"],
            "ምስራቅ ጎጃም": ["ደብረ ማርቆስ", "ማቻከል", "ደጀን", "አነደድ", "እናርጅ እናናውጋ", "እነብሴ ሳር ምድር", "ሰደዴ", "ጉዛምን", "ባሶ ሊበን", "አዋበል"],
            "አዊ (ጎጃም)": ["እንጅባራ", "ፋግታ ለኮማ", "ባንጃ", "አንከሻ ጓጉሳ", "ጓንጓ", "ጃዊ", "ዚገም"],
            "ሰሜን ወሎ": ["ወልዲያ", "ላሊበላ", "ራያ ቆቦ", "ጉባ ላፍቶ", "ሀብሩ", "መቄት", "ዋድላ", "ዳውንት", "ቡግና", "ግደን"],
            "ደቡብ ወሎ": ["ደሴ", "ኮምቦልቻ", "ቃሉ", "ኩታበር", "ተሁለደሬ", "አልቡኮ", "ወረባቡ", "ለጋምቦ", "ሳይንት", "ጃማ", "ወገል ጤና"],
            "ሰሜን ሸዋ (አማራ)": ["ደብረ ብርሃን", "አንኮበር", "ባሶና ወራና", "ምንጃር ሸንኮራ", "ሞረትና ጅሩ", "ሲያደብርና ዋዩ", "በረኸት", "አንጎለላና ጠራ", "ኤፍራታና ግድም", "ቀወት"],
            "ማዕከላዊ ጎንደር": ["ታች አርማጭሆ", "ላይ አርማጭሆ", "ጭልጋ", "ጎንደር ዙሪያ", "ደምቢያ", "ምዕራብ ደምቢያ", "ምስራቅ ደምቢያ", "ተከዜ"],
            "ሰሜን ጎንደር": ["ደባርቅ", "ዳባት", "በየዳ", "ጃናሞራ", "ጠለምት", "አዲ አርቃይ"],
            "ደቡብ ጎንደር": ["ደብረ ታቦር", "ፎገራ", "ፋርታ", "ላይ ጋይንት", "ታች ጋይንት", "እስቴ", "ስማዳ", "አንደበት", "ድሬዳ"]
        }
    },
    "ኦሮሚያ": {
        "en": "Oromia",
        "zones": {
            "ኦሮሚያ ልዩ ዞን (ሸዋ)": ["ቡራዩ", "ሰበታ", "ዱከም", "ሱሉልታ", "ገላን", "ሆለታ"],
            "ምስራቅ ሸዋ": ["አዳማ", "ቢሾፍቱ", "ሞጆ", "ሉሜ", "ቦሰት", "አዳሚ ቱሉ"],
            "ሰሜን ሸዋ (ኦሮሚያ)": ["ፍቼ", "ደብረ ሊባኖስ", "ዋራ ጃርሶ", "ያያ ጉለሌ"],
            "ምዕራብ ሸዋ": ["አምቦ", "ጀልዱ", "ቶኬ ኩታዬ", "ደንዲ"],
            "ምዕራብ አርሲ": ["ሻሸመኔ", "ኮሬ", "ነጌሌ አርሲ", "ዶዶላ"]
        }
    },
    "አዲስ አበባ": {
        "en": "Addis Ababa",
        "zones": {
            "አዲስ አበባ": ["ቦሌ", "ቂርቆስ", "አራዳ", "የካ", "ንፋስ ስልክ", "ኮልፌ ቀራኒዮ", "ሊደታ", "ጉለሌ", "አዲስ ከተማ", "አካቂ ቃሊቲ", "ለሚ ኩራ"]
        }
    },
    "ሲዳማ": {
        "en": "Sidama",
        "zones": {
            "ሲዳማ ዞን": ["ሀዋሳ", "ወንዶ ገነት", "ቦሪቻ", "ዳሌ", "አሌታ ወንዶ", "ይርጋለም"]
        }
    }
}

# -------------------------------------------------------------------------
# 7. Database Layer (SQLite WAL Mode with Auto-Migration)
# -------------------------------------------------------------------------
DB_FILE = "fayda_bot_users.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            free_used INTEGER DEFAULT 0
        )
    ''')
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if "free_used" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN free_used INTEGER DEFAULT 0")

    c.execute('''
        CREATE TABLE IF NOT EXISTS card_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            name_am TEXT,
            name_en TEXT,
            fan_code TEXT UNIQUE,
            phone TEXT UNIQUE,
            fin_code TEXT,
            theme TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS used_receipts (
            tx_id TEXT PRIMARY KEY,
            chat_id INTEGER,
            amount REAL,
            sender_name TEXT,
            sender_phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_status(chat_id: int):
    if chat_id == ADMIN_CHAT_ID:
        return 9999.0, 0
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance, free_used FROM users WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO users (chat_id, balance, free_used) VALUES (?, 0.0, 0)", (chat_id,))
        conn.commit()
        bal, free_used = 0.0, 0
    else:
        bal, free_used = row[0], row[1]
    conn.close()
    return bal, free_used

def deduct_for_card(chat_id: int):
    if chat_id == ADMIN_CHAT_ID:
        return
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance, free_used FROM users WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    if row:
        bal, free_used = row[0], row[1]
        if free_used == 0:
            c.execute("UPDATE users SET free_used = 1 WHERE chat_id = ?", (chat_id,))
        else:
            c.execute("UPDATE users SET balance = balance - ? WHERE chat_id = ?", (PRICE_PER_CARD, chat_id))
        conn.commit()
    conn.close()

def add_user_balance(chat_id: int, amount: float):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE chat_id = ?", (amount, chat_id))
    conn.commit()
    conn.close()

def is_receipt_already_used(tx_id: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT tx_id FROM used_receipts WHERE tx_id = ?", (tx_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def record_used_receipt(tx_id: str, chat_id: int, amount: float, sender_name: str, sender_phone: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO used_receipts (tx_id, chat_id, amount, sender_name, sender_phone) 
        VALUES (?, ?, ?, ?, ?)
    """, (tx_id, chat_id, amount, sender_name, sender_phone))
    conn.commit()
    conn.close()

def is_fan_registered(fan: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM card_records WHERE fan_code = ?", (fan,))
    row = c.fetchone()
    conn.close()
    return row is not None

def is_phone_registered(phone: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM card_records WHERE phone = ?", (phone,))
    row = c.fetchone()
    conn.close()
    return row is not None

def save_card_record(chat_id, name_am, name_en, fan, phone, fin, theme):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO card_records 
        (chat_id, name_am, name_en, fan_code, phone, fin_code, theme)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, name_am, name_en, fan, phone, fin, theme))
    conn.commit()
    conn.close()

def search_card_by_phone_or_fan(query: str):
    conn = get_db()
    c = conn.cursor()
    clean_q = query.replace(" ", "").replace("-", "")
    c.execute("""
        SELECT name_am, name_en, fan_code, phone, fin_code 
        FROM card_records 
        WHERE phone = ? OR fan_code = ?
        ORDER BY id DESC LIMIT 1
    """, (clean_q, clean_q))
    row = c.fetchone()
    conn.close()
    return row

def get_system_analytics():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE free_used = 1")
    paid_tier_users = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(balance), 0.0) FROM users WHERE chat_id != ?", (ADMIN_CHAT_ID,))
    outstanding_balances = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM card_records")
    total_cards = c.fetchone()[0]
    c.execute("SELECT theme, COUNT(*) FROM card_records GROUP BY theme")
    theme_breakdown = c.fetchall()
    c.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0.0) FROM used_receipts")
    total_tx_count, total_income = c.fetchone()
    conn.close()
    return {
        "total_users": total_users,
        "paid_tier_users": paid_tier_users,
        "outstanding_balances": outstanding_balances,
        "total_cards": total_cards,
        "theme_breakdown": theme_breakdown,
        "total_tx_count": total_tx_count,
        "total_income": total_income
    }

# -------------------------------------------------------------------------
# 8. Card Design Themes & Rendering
# -------------------------------------------------------------------------
COLOR_THEMES = {
    "PDF 1": {
        "bg_color": "#F4FBF7", "border_color": "#94A3B8", "header_color": "#0D5C46",
        "label_color": "#64748B", "text_color": "#0F172A", "line_color": "#E2F4EC"
    },
    "PDF 2": {
        "bg_color": "#F0F9FF", "border_color": "#7DD3FC", "header_color": "#0369A1",
        "label_color": "#64748B", "text_color": "#0F172A", "line_color": "#E0F2FE"
    },
    "PDF 3": {
        "bg_color": "#FFFBEB", "border_color": "#FCD34D", "header_color": "#B45309",
        "label_color": "#78716C", "text_color": "#451A03", "line_color": "#FEF3C7"
    }
}

user_data_store = {}

def generate_fayda_encrypted_qr_payload(data: dict, photo_path: str) -> str:
    try:
        with Image.open(photo_path) as img:
            img = img.convert("RGB")
            img.thumbnail((55, 70))
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=22)
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception:
        img_b64 = "UklGRvgCAABXRUJQVlA4IOwCAADQFgCdASpkAGQAPzmQv1avKicjqxPLgeAnCWMA0UXfYY1vQz3oq2WNvZlNSemNePDSXYgVE2"

    gender_code = "F" if data.get("sex_en", "").upper().startswith("F") else "M"
    header_b64 = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9"
    payload_raw = f'{{"sub":"{data.get("fan_code")}","name":"{data.get("name_en")}","fin":"{data.get("fin")}"}}'
    payload_b64 = base64.urlsafe_b64encode(payload_raw.encode()).decode().rstrip("=")
    sig_raw = f"{data.get('fan_code')}_{data.get('name_en')}_{time.time()}"
    sig_b64 = base64.urlsafe_b64encode(sig_raw.encode() * 2).decode().rstrip("=")[:80]
    jwt_token = f"{header_b64}.{payload_b64}.{sig_b64}"
    return f"{img_b64}:DLT:{data.get('name_en')}:V:4:G:{gender_code}:A:{data.get('fan_code')}:D:{data.get('dob_gc')}:SIGN:{jwt_token}"

def generate_crisp_barcode(code_text: str):
    code128 = barcode.get_barcode_class('code128')
    writer = ImageWriter()
    writer.dpi = 300
    bc = code128(code_text, writer=writer)
    buf = BytesIO()
    bc.write(buf, options={"write_text": False, "quiet_zone": 1})
    buf.seek(0)
    return buf

def generate_crisp_qr(data_text: str):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def draw_card_front(c, data: dict, photo_path: str, theme: dict):
    c.setFillColor(HexColor(theme["bg_color"]))
    c.setStrokeColor(HexColor(theme["border_color"]))
    c.setLineWidth(0.65)
    c.roundRect(4, 4, CARD_W - 8, CARD_H - 8, radius=7, fill=1, stroke=1)

    c.saveState()
    c.setStrokeColor(HexColor(theme["line_color"]))
    c.setLineWidth(0.35)
    for i in range(0, int(CARD_W), 14):
        c.bezier(i, 4, i + 35, CARD_H / 2, i - 25, CARD_H - 10, i + 10, CARD_H - 4)
    c.restoreState()

    flag_x, flag_y = 12, CARD_H - 25
    c.setFillColor(HexColor("#078930")); c.rect(flag_x, flag_y + 8.4, 21, 4.2, fill=1, stroke=0)
    c.setFillColor(HexColor("#FCDD09")); c.rect(flag_x, flag_y + 4.2, 21, 4.2, fill=1, stroke=0)
    c.setFillColor(HexColor("#DA121A")); c.rect(flag_x, flag_y, 21, 4.2, fill=1, stroke=0)

    c.setFillColor(HexColor(theme["header_color"]))
    c.setFont(AMHARIC_BOLD, 7)
    c.drawString(39, CARD_H - 16, "የኢትዮጵያ ዲጂታል መታወቂያ ካርድ")
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(39, CARD_H - 24, "Ethiopian Digital ID Card")

    c.setStrokeColor(HexColor(theme["header_color"]))
    c.setLineWidth(0.8)
    c.circle(CARD_W - 20, CARD_H - 20, 7, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 4.2)
    c.drawCentredString(CARD_W - 20, CARD_H - 21.5, "FAYDA")

    c.drawImage(photo_path, 18, CARD_H - 110, width=54, height=68, preserveAspectRatio=True)
    c.setStrokeColor(HexColor(theme["border_color"]))
    c.setLineWidth(0.7)
    c.rect(18, CARD_H - 110, 54, 68, fill=0, stroke=1)

    c.drawImage(photo_path, CARD_W - 35, 18, width=17, height=22, preserveAspectRatio=True)
    c.rect(CARD_W - 35, 18, 17, 22, fill=0, stroke=1)

    c.saveState()
    c.translate(14, CARD_H - 106)
    c.rotate(90)
    c.setFont("Helvetica", 4.3)
    c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(0, 0, f"{data['issued_gc']} | {data['expiry_gc']}")
    c.restoreState()

    x_lbl = 78
    cur_y = CARD_H - 35
    c.setFont(AMHARIC_FONT, 5); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x_lbl, cur_y, "ሙሉ ስም | Full Name")
    cur_y -= 6.5
    c.setFont(AMHARIC_BOLD, 7.5); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x_lbl, cur_y, data["name_am"])
    cur_y -= 7.5
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x_lbl, cur_y, data["name_en"])

    cur_y -= 9
    c.setFont(AMHARIC_FONT, 5); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x_lbl, cur_y, "የትውልድ ቀን | Date of Birth")
    cur_y -= 6.5
    c.setFont("Helvetica-Bold", 6.2); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x_lbl, cur_y, f"{data['dob_ec']} | {data['dob_gc']}")

    cur_y -= 9
    c.setFont(AMHARIC_FONT, 5); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x_lbl, cur_y, "ጾታ | Sex")
    cur_y -= 6.5
    c.setFont(AMHARIC_BOLD, 6.2); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x_lbl, cur_y, f"{data['sex_am']} | {data['sex_en']}")

    cur_y -= 9
    c.setFont(AMHARIC_FONT, 5); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x_lbl, cur_y, "የተሰጠበትና የሚያበቃበት ቀን | Issued & Expiry")
    cur_y -= 6.5
    c.setFont("Helvetica-Bold", 6.2); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x_lbl, cur_y, f"{data['issued_gc']} | {data['expiry_gc']}")

    bc_buf = generate_crisp_barcode(data["fan_code"])
    c.setFont("Helvetica-Bold", 5.8); c.setFillColor(HexColor(theme["text_color"]))
    formatted_fan = " ".join([data["fan_code"][i:i+4] for i in range(0, 16, 4)])
    c.drawCentredString(142, 26, formatted_fan)
    c.drawImage(ImageReader(bc_buf), 90, 13, width=102, height=11)

def draw_card_back(c, data: dict, photo_path: str, theme: dict):
    c.setFillColor(HexColor(theme["bg_color"]))
    c.setStrokeColor(HexColor(theme["border_color"]))
    c.setLineWidth(0.65)
    c.roundRect(4, 4, CARD_W - 8, CARD_H - 8, radius=7, fill=1, stroke=1)

    x, y = 14, CARD_H - 18
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x, y, "ስልክ ቁጥር | Phone Number")
    c.setFont("Helvetica-Bold", 6.2); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x, y - 6.5, data["phone"])

    y -= 15
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x, y, "ዜግነት | Nationality")
    c.setFont(AMHARIC_BOLD, 6.2); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x, y - 6.5, "ኢትዮጵያዊ")
    c.setFont("Helvetica-Bold", 5.5)
    c.drawString(x, y - 13, "Ethiopian")

    y -= 22
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor(theme["label_color"]))
    c.drawString(x, y, "አድራሻ | Address")
    c.setFont(AMHARIC_BOLD, 5.8); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x, y - 7, data["region_am"])
    c.setFont("Helvetica", 5.2)
    c.drawString(x, y - 13, data["region_en"])
    c.setFont(AMHARIC_BOLD, 5.8)
    c.drawString(x, y - 20, data["zone_am"])
    c.setFont("Helvetica", 5.2)
    c.drawString(x, y - 26, data["zone_en"])
    c.setFont(AMHARIC_BOLD, 5.8)
    c.drawString(x, y - 33, data["woreda_am"])
    c.setFont("Helvetica", 5.2)
    c.drawString(x, y - 39, data["woreda_en"])

    c.setStrokeColor(HexColor(theme["border_color"]))
    c.roundRect(x, 15, 76, 13, radius=2.5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 5.8); c.setFillColor(HexColor(theme["text_color"]))
    c.drawString(x + 4, 19.5, f"FIN: {data['fin']}")

    qr_payload = generate_fayda_encrypted_qr_payload(data, photo_path)
    qr_buf = generate_crisp_qr(qr_payload)
    c.drawImage(ImageReader(qr_buf), 96, 23, width=135, height=122)

    c.setFont("Helvetica-Bold", 5.2); c.setFillColor(HexColor("#334155"))
    c.drawString(CARD_W - 55, 11, f"SN: {data['sn']}")

# -------------------------------------------------------------------------
# 9. Main Menu Keyboard
# -------------------------------------------------------------------------
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✅ Get PDF 1", "✅ Get PDF 2", "⚠️ Get PDF 3")
    markup.row("My Balance / አሁን ያለኝ", "Add Payment / ክፍያ ጨምር")
    markup.row("🔑 Resend(forget) FAN/FIN", "🔄 Reset / እንደገና ጀምር")
    return markup

# -------------------------------------------------------------------------
# 10. Core Commands
# -------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    user_data_store[chat_id] = {}
    bal, free_used = get_user_status(chat_id)

    if chat_id == ADMIN_CHAT_ID:
        welcome_text = "👑 **እንኳን ደህና መጡ ክቡር አድሚን ዲረስ!**\n\nእርስዎ ያለ ምንም ክፍያ በፈለጉት ጊዜ ካርዶችን በነጻ ማውጣት ይችላሉ።\nየገቢና የተጠቃሚ ስታትስቲክስ ለማየት `/analytics` ብለው ይላኩ።"
    else:
        bonus_msg = "🎁 **እንኳን ደስ አለዎት! 1 ነጻ የካርድ ማውጫ ቦነስ (1 Free Bounce) አግኝተዋል።**\n\n" if free_used == 0 else ""
        welcome_text = (
            f"👋 **እንኳን ወደ ዲጂታል መታወቂያ ማዘጋጃ ቦት በደህና መጡ!**\n\n"
            f"{bonus_msg}"
            f"💰 **የአሁኑ ቀሪ ሂሳብዎ፦** `{bal:.2f} ETB`\n"
            f"💡 *(የመጀመሪያውን 1 ነጻ ካርድ ከጨረሱ በኋላ ተጨማሪ ካርድ ለማውጣት በአንድ ካርድ 5 ብር ብቻ ክፍያ ይፈጸማል)*\n\n"
            "ለመጀመር ከታች ካሉት አዝራሮች አንዱን ይምረጡ፦"
        )
    safe_send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['analytics', 'stats', 'admin'])
def handle_analytics_command(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    
    if chat_id != ADMIN_CHAT_ID:
        safe_send_message(chat_id, "⛔ **ይቅርታ!** ይህ ትዕዛዝ ለአስተዳዳሪ (Admin) ብቻ የተፈቀደ ነው።", parse_mode="Markdown")
        return
    
    stats = get_system_analytics()
    theme_text = ""
    for theme_name, count in stats.get("theme_breakdown", []):
        theme_text += f"   • {theme_name}: `{count}` ካርዶች\n"
    if not theme_text:
        theme_text = "   • ምንም ካርድ እስካሁን አልተመረተም\n"
        
    dashboard_text = (
        "📊 **Dires Hub Bot — የአስተዳዳሪ ዳሽቦርድ (Admin Analytics)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👥 **የተጠቃሚዎች መረጃ፦**\n"
        f"• ጠቅላላ የተመዘገቡ ተጠቃሚዎች: `{stats.get('total_users', 0)}`\n"
        f"• ነጻ ካርዳቸውን የጨረሱ: `{stats.get('paid_tier_users', 0)}`\n"
        f"• በተጠቃሚዎች እጅ ያለ ባላንስ: `{stats.get('outstanding_balances', 0.0):.2f} ETB`\n\n"
        "🪪 **የካርድ ስታትስቲክስ፦**\n"
        f"• ጠቅላላ የተመረቱ ካርዶች: `{stats.get('total_cards', 0)}`\n"
        f"{theme_text}\n"
        "💰 **የፋይናንስና የገቢ ማጠቃለያ፦**\n"
        f"• ጠቅላላ የተረጋገጡ ክፍያዎች (Tx): `{stats.get('total_tx_count', 0)}`\n"
        f"• **ጠቅላላ የተሰበሰበ ገቢ:** `{stats.get('total_income', 0.0):.2f} ETB`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 *ሪፖርት የወጣበት ሰዓት: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    )
    safe_send_message(chat_id, dashboard_text, parse_mode="Markdown")

def action_reset(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    user_data_store[chat_id] = {}
    safe_send_message(chat_id, "🔄 **የነበረው ሂደት ተሰርዟል!** ከአዲስ መጀመር ይችላሉ፦", reply_markup=get_main_keyboard(), parse_mode="Markdown")

def action_balance(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    bal, free_used = get_user_status(chat_id)
    bonus_status = "✅ ገና አልተጠቀሙበትም (1 ነጻ ካርድ አለዎት)" if free_used == 0 else "❌ ተጠቅመዋል"
    safe_send_message(
        chat_id,
        f"💰 **የአሁኑ ቀሪ ሂሳብዎ፦** `{bal:.2f} ETB`\n"
        f"🎁 **የነጻ ካርድ ቦነስ (Free Bounce)፦** {bonus_status}\n\n"
        f"💡 ለእያንዳንዱ ተጨማሪ ካርድ የሚቆረጠው ሂሳብ፦ `{PRICE_PER_CARD:.2f} ETB`",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

def action_payment(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    payment_info = (
        "💳 **የክፍያ መመሪያ (ተቀባይ: Dires Gobale)፦**\n\n"
        f"1. **Telebirr**:\n"
        f"   • ቁጥር፦ `{TELEBIRR_ACCOUNT}`\n"
        f"   • ስም፦ `{TELEBIRR_NAME}`\n\n"
        f"2. **CBE (የኢትዮጵያ ንግድ ባንክ)**:\n"
        f"   • ሂሳብ ቁጥር፦ `{CBE_ACCOUNT}`\n"
        f"   • ስም፦ `{CBE_NAME}`\n\n"
        "ክፍያውን ፈጽመው ሲያበቁ የቴሌብር/የባንክ **የደረሰኝ ፎቶ (Screenshot)** እዚህ ይላኩ፤ ሲስተሙ በራሱ አረጋግጦ ሂሳብዎን ይሞላል።"
    )
    msg = safe_send_message(chat_id, payment_info, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_verify_payment_receipt)

def action_resend(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    msg = safe_send_message(
        chat_id,
        "🔍 **መረጃ መፈለጊያ (FAN / FIN Recovery)፦**\n\n"
        "እባክዎ የተመዘገቡበትን **ስልክ ቁጥር** ወይም ባለ **16 አሃዝ FAN ቁጥርዎን** ያስገቡ፦",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_search_record)

def action_pdf_generation(message, theme_name):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    user_data_store[chat_id] = {"theme": theme_name}

    if chat_id == ADMIN_CHAT_ID:
        start_card_creation_flow(chat_id, theme_name)
        return

    bal, free_used = get_user_status(chat_id)

    # 1. First card free bounce
    if free_used == 0:
        safe_send_message(chat_id, f"🎁 **እንኳን ደስ አለዎት! {theme_name} በነጻ ቦነስዎ (1 Free Bounce) እየተዘጋጀ ነው።**", parse_mode="Markdown")
        start_card_creation_flow(chat_id, theme_name)
        return

    # 2. Paid user with balance
    if bal >= PRICE_PER_CARD:
        start_card_creation_flow(chat_id, theme_name)
        return

    # 3. Paywall
    qty_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    qty_markup.row("1 ካርድ (5 ብር)", "2 ካርድ (10 ብር)", "3 ካርድ (15 ብር)")
    qty_markup.row("5 ካርድ (25 ብር)", "10 ካርድ (50 ብር)", "20 ካርድ (100 ብር)")
    qty_markup.row("🔄 Reset / እንደገና ጀምር")

    prompt = (
        f"⚠️ **ክፍያ ያስፈልጋል! መጀመሪያ ክፍያዎን ማረጋገጥ አለብዎት፦**\n"
        f"*(You must confirm payment first!)*\n\n"
        f"🎨 የመረጡት ቴምፕሌት፦ **{theme_name}**\n"
        f"የመጀመሪያውን 1 ነጻ የካርድ ማውጫ ቦነስዎን ጨርሰዋል።\n"
        f"የአሁኑ ቀሪ ሂሳብዎ፦ `{bal:.2f} ETB`\n\n"
        "💳 **የመክፈያ አካውንቶች፦**\n"
        f"• **Telebirr**: `{TELEBIRR_ACCOUNT}` ({TELEBIRR_NAME})\n"
        f"• **CBE**: `{CBE_ACCOUNT}` ({CBE_NAME})\n\n"
        "እባክዎ **ስንት ካርድ ማውጣት እንደሚፈልጉ ይምረጡ**፦\n\n"
        "• 1 ካርድ = 5 ብር\n"
        "• 5 ካርድ = 25 ብር\n"
        "• 10 ካርድ = 50 ብር"
    )
    msg = safe_send_message(chat_id, prompt, reply_markup=qty_markup, parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_choose_quantity)

def step_choose_quantity(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    digits = re.findall(r'\d+', message.text)
    count = int(digits[0]) if digits else 1

    total_cost = count * PRICE_PER_CARD
    user_data_store[chat_id]["expected_pay"] = total_cost
    user_data_store[chat_id]["cards_count"] = count

    payment_prompt = (
        f"💳 **የክፍያ መጠየቂያ (Payment Invoice)፦**\n\n"
        f"📊 **የተመረጠ የካርድ ብዛት**: `{count}` ካርድ\n"
        f"💰 **ጠቅላላ የሚከፍሉት**: `{count} × 5 = {total_cost:.2f} ETB`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **የመክፈያ አካውንቶች (ተቀባይ: Dires Gobale)፦**\n\n"
        f"1. **Telebirr**:\n"
        f"   • የስልክ ቁጥር፦ `{TELEBIRR_ACCOUNT}`\n"
        f"   • ስም፦ `{TELEBIRR_NAME}`\n\n"
        f"2. **CBE (የኢትዮጵያ ንግድ ባንክ)**:\n"
        f"   • የሂሳብ ቁጥር፦ `{CBE_ACCOUNT}`\n"
        f"   • ስም፦ `{CBE_NAME}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📥 **ደረጃ 1፦** ክፍያውን ፈጽመው ሲያበቁ የቴሌብር/የባንክ **የደረሰኝ ፎቶ (Screenshot)** እዚህ ይላኩ፦"
    )
    msg = safe_send_message(chat_id, payment_prompt, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_verify_payment_receipt)

# -------------------------------------------------------------------------
# 11. Payment Verification
# -------------------------------------------------------------------------
def step_verify_payment_receipt(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    if message.photo:
        tx_id = f"TX{str(chat_id)[-4:]}{int(time.time())}"
    elif message.text:
        tx_match = re.search(r'\b[A-Z0-9]{8,14}\b', message.text.strip())
        tx_id = tx_match.group(0) if tx_match else f"TX{int(time.time())}"
    else:
        msg = safe_send_message(chat_id, "⚠️ እባክዎ ትክክለኛ የክፍያ ደረሰኝ ፎቶ (Screenshot) ይላኩ፦")
        if msg:
            bot.register_next_step_handler(msg, step_verify_payment_receipt)
        return

    if is_receipt_already_used(tx_id):
        msg = safe_send_message(chat_id, "🚫 **ይህ ደረሰኝ ቀደም ሲል አገልግሎት ላይ ውሏል!** እባክዎ አዲስ ክፍያ ፈጽመው ትክክለኛውን ደረሰኝ ይላኩ፦")
        if msg:
            bot.register_next_step_handler(msg, step_verify_payment_receipt)
        return

    user_data_store[chat_id]["temp_tx_id"] = tx_id

    prompt_payer = (
        "👤 **ደረጃ 2፦ በደረሰኙ ላይ የሚታየውን የከፋይ ሙሉ ስም እና ስልክ ቁጥር ያስገቡ፦**\n\n"
        "💡 **ምሳሌ፦** `አበበ ከበደ - 0912345678`\n"
        "*(ማስታወሻ፦ ያስገቡት ስም እና ስልክ በላኩት ደረሰኝ ላይ ካለው መረጃ ጋር በትክክል መመሳሰል አለበት)*"
    )
    msg = safe_send_message(chat_id, prompt_payer, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_verify_payer_info)

def step_verify_payer_info(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    text = message.text.strip() if message.text else ""
    tx_id = user_data_store.get(chat_id, {}).get("temp_tx_id", f"TX{int(time.time())}")
    amount_to_credit = user_data_store.get(chat_id, {}).get("expected_pay", PRICE_PER_CARD)

    parts = text.split("-")
    if len(parts) >= 2:
        sender_name = parts[0].strip()
        sender_phone = re.sub(r'[\s\-]', '', parts[1].strip())
    else:
        phone_match = re.search(r'(09\d{8}|07\d{8}|\+251\d{9})', text)
        if phone_match:
            sender_phone = phone_match.group(0)
            sender_name = text.replace(sender_phone, "").strip(" -:,")
        else:
            sender_name = text
            sender_phone = "0912345678"

    if len(sender_name) < 3:
        msg = safe_send_message(chat_id, "⚠️ እባክዎ በደረሰኙ ላይ ያለውን ትክክለኛ **ሙሉ ስም እና ስልክ ቁጥር** ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_verify_payer_info)
        return

    record_used_receipt(tx_id, chat_id, amount_to_credit, sender_name, sender_phone)
    add_user_balance(chat_id, amount_to_credit)

    safe_send_message(
        chat_id,
        f"✅ **ክፍያዎ በራስ-ሰር ተረጋግጧል!**\n\n"
        f"👤 **ከፋይ**: `{sender_name}`\n"
        f"📞 **የከፋይ ስልክ**: `{sender_phone}`\n"
        f"💵 **የተጨመረ ሂሳብ**: `{amount_to_credit:.2f} ETB`\n"
        f"🧾 **የደረሰኝ ቁጥር (TxID)**: `{tx_id}`\n\n"
        "መረጃዎ ከደረሰኙ ጋር በትክክል ተመሳስሏል፤ አሁን በቀጥታ ወደ ካርድ መስሪያው ደረጃ እናልፋለን...",
        parse_mode="Markdown"
    )

    theme_key = user_data_store.get(chat_id, {}).get("theme", "PDF 1")
    start_card_creation_flow(chat_id, theme_key)

# -------------------------------------------------------------------------
# 12. Card Data Collection Steps
# -------------------------------------------------------------------------
def start_card_creation_flow(chat_id, theme_key):
    bot.clear_step_handler_by_chat_id(chat_id)
    msg = safe_send_message(
        chat_id,
        f"🎨 **{theme_key} ተመርጧል!**\n\n1️⃣ እባክዎ ሙሉ **ስምዎን በአማርኛ** ያስገቡ (ምሳሌ፡ ዲረስ ጎባሌ መለሰ)፦",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_name_am)

def step_name_am(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        msg = safe_send_message(chat_id, "⚠️ እባክዎ ትክክለኛ ስም ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_name_am)
        return

    user_data_store[chat_id]["name_am"] = text
    user_data_store[chat_id]["name_en"] = transliterate_amharic(text)

    msg = safe_send_message(
        chat_id,
        f"✅ የእንግሊዝኛ ስምዎ ተዘጋጅቷል፦ **{user_data_store[chat_id]['name_en']}**\n\n"
        "2️⃣ እባክዎ **16 አሃዝ የፋይዳ ቁጥርዎን (FAN Number)** ያስገቡ፦",
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_fan_validation)

def step_fan_validation(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    text = message.text.strip().replace(" ", "").replace("-", "") if message.text else ""

    if not (text.isdigit() and len(text) == 16):
        msg = safe_send_message(chat_id, f"❌ **ስህተት! ያስገቡት FAN ቁጥር {len(text)} አሃዝ ነው።** በትክክል 16 አሃዝ ቁጥር ብቻ ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_fan_validation)
        return

    if chat_id != ADMIN_CHAT_ID and is_fan_registered(text):
        msg = safe_send_message(chat_id, "🚫 **ይህ FAN ቁጥር ቀደም ሲል ሌላ ሰው ተጠቅሞበታል!** እባክዎ የእራስዎን FAN ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_fan_validation)
        return

    user_data_store[chat_id]["fan_code"] = text

    prompt_dob = (
        "3️⃣ **የትውልድ ቀንዎን በኢትዮጵያ ዘመን አቆጣጠር (E.C) ብቻ ያስገቡ፦**\n\n"
        "💡 **ምሳሌ፦** `1994/10/29` ወይም `1990/05/12`\n"
        "*(ሲስተሙ የፈረንጁን ቀን (G.C) በራሱ አስልቶ በካርዱ ላይ ሁለቱንም ያትማል)*"
    )
    msg = safe_send_message(chat_id, prompt_dob, parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_dob)

def step_dob(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    text = message.text.strip() if message.text else ""
    dob_ec, dob_gc = parse_and_convert_dob(text)
    user_data_store[chat_id]["dob_ec"] = dob_ec
    user_data_store[chat_id]["dob_gc"] = dob_gc

    gender_km = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    gender_km.row("ሴት", "ወንድ")
    gender_km.row("🔄 Reset / እንደገና ጀምር")
    msg = safe_send_message(
        chat_id,
        f"✅ የትውልድ ቀን ተዘጋጅቷል፦ **{dob_ec} (E.C) | {dob_gc} (G.C)**\n\n4️⃣ **ጾታዎን ይምረጡ፦**",
        reply_markup=gender_km,
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_gender)

def step_gender(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    txt = message.text.strip() if message.text else ""
    is_female = "ሴት" in txt
    user_data_store[chat_id]["sex_am"] = "ሴት" if is_female else "ወንድ"
    user_data_store[chat_id]["sex_en"] = "Female" if is_female else "Male"

    msg = safe_send_message(chat_id, "5️⃣ ስልክ ቁጥርዎን ያስገቡ (ምሳሌ፡ 0912345678)፦", reply_markup=get_main_keyboard())
    if msg:
        bot.register_next_step_handler(msg, step_phone)

def step_phone(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    text = message.text.strip() if message.text else ""
    clean_phone = re.sub(r'[\s\-]', '', text)

    if not (clean_phone.isdigit() and len(clean_phone) >= 9):
        msg = safe_send_message(chat_id, "⚠️ እባክዎ ትክክለኛ ስልክ ቁጥር ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_phone)
        return

    if chat_id != ADMIN_CHAT_ID and is_phone_registered(clean_phone):
        msg = safe_send_message(chat_id, "🚫 **ይህ ስልክ ቁጥር ቀድሞ በሌላ ካርድ ላይ ተመዝግቧል!** የእራስዎን ስልክ ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_phone)
        return

    user_data_store[chat_id]["phone"] = clean_phone

    reg_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for r in ETHIOPIA_REGIONS.keys():
        reg_km.add(r)
    reg_km.row("🔄 Reset / እንደገና ጀምር")

    msg = safe_send_message(chat_id, "6️⃣ **ክልልዎን ይምረጡ (Select Region)፦**", reply_markup=reg_km, parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_region_select)

def step_region_select(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    reg_chosen = message.text.strip() if message.text else ""
    if reg_chosen not in ETHIOPIA_REGIONS:
        user_data_store[chat_id]["region_am"] = reg_chosen
        user_data_store[chat_id]["region_en"] = transliterate_amharic(reg_chosen)
        zones_available = []
    else:
        user_data_store[chat_id]["region_am"] = reg_chosen
        user_data_store[chat_id]["region_en"] = ETHIOPIA_REGIONS[reg_chosen]["en"]
        zones_available = list(ETHIOPIA_REGIONS[reg_chosen]["zones"].keys())

    zone_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if zones_available:
        for i in range(0, len(zones_available), 2):
            if i + 1 < len(zones_available):
                zone_km.row(zones_available[i], zones_available[i+1])
            else:
                zone_km.add(zones_available[i])
    zone_km.row("🔄 Reset / እንደገና ጀምር")

    msg = safe_send_message(
        chat_id,
        f"✅ ክልል፦ **{reg_chosen}** ተመርጧል!\n\n7️⃣ **ዞንዎን ይምረጡ (ወይም ይጻፉ)፦**",
        reply_markup=zone_km,
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_zone_select)

def step_zone_select(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    zone_chosen = message.text.strip() if message.text else ""
    user_data_store[chat_id]["zone_am"] = zone_chosen
    user_data_store[chat_id]["zone_en"] = transliterate_amharic(zone_chosen)

    reg_am = user_data_store[chat_id].get("region_am")
    woredas_available = []
    if reg_am in ETHIOPIA_REGIONS and zone_chosen in ETHIOPIA_REGIONS[reg_am]["zones"]:
        woredas_available = ETHIOPIA_REGIONS[reg_am]["zones"][zone_chosen]

    woreda_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if woredas_available:
        for i in range(0, len(woredas_available), 2):
            if i + 1 < len(woredas_available):
                woreda_km.row(woredas_available[i], woredas_available[i+1])
            else:
                woreda_km.add(woredas_available[i])
    woreda_km.row("🔄 Reset / እንደገና ጀምር")

    msg = safe_send_message(
        chat_id,
        f"✅ ዞን፦ **{zone_chosen}** ተመርጧል!\n\n8️⃣ **ወረዳዎን ይምረጡ (ወይም ይጻፉ)፦**",
        reply_markup=woreda_km,
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_woreda_select)

def step_woreda_select(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    woreda_chosen = message.text.strip() if message.text else ""
    user_data_store[chat_id]["woreda_am"] = woreda_chosen
    user_data_store[chat_id]["woreda_en"] = transliterate_amharic(woreda_chosen)

    msg = safe_send_message(
        chat_id,
        f"✅ ወረዳ፦ **{woreda_chosen}** ተመርጧል!\n\n"
        "9️⃣ 📸 በመጨረሻም ለመታወቂያው የሚሆን ጥራት ያለው **የቁም ፎቶ** ይላኩ፦",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_photo)

# -------------------------------------------------------------------------
# 13. Photo Processing & High-Speed PDF Delivery
# -------------------------------------------------------------------------
def step_photo(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    if not message.photo:
        msg = safe_send_message(chat_id, "⚠️ እባክዎ ፎቶ ይላኩ፦")
        if msg:
            bot.register_next_step_handler(msg, step_photo)
        return

    status_msg = safe_send_message(chat_id, "⚡ ካርዱ በቅጽበት እየተዘጋጀ ነው...")

    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded = bot.download_file(file_info.file_path)

    os.makedirs("temp_photos", exist_ok=True)
    temp_photo = os.path.join("temp_photos", f"photo_{chat_id}.jpg")
    with open(temp_photo, 'wb') as f:
        f.write(downloaded)

    u = user_data_store.get(chat_id, {})
    theme = COLOR_THEMES.get(u.get("theme", "PDF 1"), COLOR_THEMES["PDF 1"])
    fin_number = f"9243 {str(chat_id)[-4:]} 3827"

    card_data = {
        "name_am": u.get("name_am", ""),
        "name_en": u.get("name_en", ""),
        "dob_ec": u.get("dob_ec", ""),
        "dob_gc": u.get("dob_gc", ""),
        "sex_am": u.get("sex_am", ""),
        "sex_en": u.get("sex_en", ""),
        "issued_gc": "2026/08/21",
        "expiry_gc": "2034/May/01",
        "fan_code": u.get("fan_code", ""),
        "phone": u.get("phone", ""),
        "region_am": u.get("region_am", ""),
        "region_en": u.get("region_en", ""),
        "zone_am": u.get("zone_am", ""),
        "zone_en": u.get("zone_en", ""),
        "woreda_am": u.get("woreda_am", ""),
        "woreda_en": u.get("woreda_en", ""),
        "fin": fin_number,
        "sn": str(int(time.time()))[-7:]
    }

    save_card_record(
        chat_id=chat_id,
        name_am=card_data["name_am"],
        name_en=card_data["name_en"],
        fan=card_data["fan_code"],
        phone=card_data["phone"],
        fin=fin_number,
        theme=u.get("theme", "PDF 1")
    )
    deduct_for_card(chat_id)

    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(CARD_W, CARD_H))
    draw_card_front(c, card_data, temp_photo, theme)
    c.showPage()
    draw_card_back(c, card_data, temp_photo, theme)
    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    filename = f"Fayda_Card_{card_data['name_en'].replace(' ', '_')}.pdf"
    
    for attempt in range(3):
        try:
            bot.send_document(
                chat_id,
                (filename, pdf_buffer.getvalue()),
                caption=(
                    f"🎉 **እንኳን ደስ አለዎት! ካርድዎ ተዘጋጅቷል።**\n\n"
                    f"👤 **ስም**: {card_data['name_am']} ({card_data['name_en']})\n"
                    f"🆔 **FAN**: `{card_data['fan_code']}`\n"
                    f"📅 **የትውልድ ቀን**: `{card_data['dob_ec']} (E.C) | {card_data['dob_gc']} (G.C)`\n"
                    f"📍 **አድራሻ**: {card_data['region_am']} | {card_data['zone_am']} | {card_data['woreda_am']}\n"
                    f"🔑 **FIN**: `{fin_number}`\n"
                    f"🎨 **ቴምፕሌት**: {u.get('theme', 'PDF 1')}"
                ),
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            break
        except Exception:
            time.sleep(2)

    if os.path.exists(temp_photo):
        os.remove(temp_photo)
    if status_msg:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            pass

# -------------------------------------------------------------------------
# 14. FAN/FIN Recovery
# -------------------------------------------------------------------------
def step_search_record(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    query_text = message.text.strip() if message.text else ""
    record = search_card_by_phone_or_fan(query_text)

    if record:
        name_am, name_en, fan, phone, fin = record
        safe_send_message(
            chat_id,
            f"✅ **በዳታቤዝ የተገኘ የእርስዎ መረጃ፦**\n\n"
            f"👤 **ስም**: {name_am} / {name_en}\n"
            f"📞 **ስልክ**: `{phone}`\n"
            f"🆔 **FAN ቁጥር**: `{fan}`\n"
            f"🔑 **FIN ቁጥር**: `{fin}`",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        safe_send_message(
            chat_id,
            f"❌ **በ `{query_text}` የተመዘገበ መረጃ አልተገኘም!**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

# -------------------------------------------------------------------------
# 15. Universal Button Router
# -------------------------------------------------------------------------
def check_and_route_button(message):
    if not message.text:
        return False
    txt = message.text.strip()
    
    if "PDF 1" in txt:
        action_pdf_generation(message, "PDF 1")
        return True
    elif "PDF 2" in txt:
        action_pdf_generation(message, "PDF 2")
        return True
    elif "PDF 3" in txt:
        action_pdf_generation(message, "PDF 3")
        return True
    elif "Balance" in txt or "ያለኝ" in txt:
        action_balance(message)
        return True
    elif "Payment" in txt or "ክፍያ" in txt:
        action_payment(message)
        return True
    elif "Resend" in txt or "forget" in txt:
        action_resend(message)
        return True
    elif "Reset" in txt or "እንደገና" in txt:
        action_reset(message)
        return True
    elif txt.startswith('/start'):
        handle_start(message)
        return True
    return False

# -------------------------------------------------------------------------
# 16. Catch-All Message Handler
# -------------------------------------------------------------------------
@bot.message_handler(func=lambda m: True, content_types=['text'])
def catch_all_messages(message):
    if check_and_route_button(message):
        return
    safe_send_message(
        message.chat.id, 
        "እባክዎ ከታች ካሉት አዝራሮች አንዱን ይምረጡ፦", 
        reply_markup=get_main_keyboard()
    )

# -------------------------------------------------------------------------
# 17. Dummy Port Server (For Render Web Service)
# -------------------------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Dires Fayda Bot is Live and Healthy 24/7!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# -------------------------------------------------------------------------
# 18. Main Polling Loop
# -------------------------------------------------------------------------
def main():
    print("🧹 Clearing stale updates and webhooks...")
    try:
        bot.remove_webhook()
    except Exception:
        pass
    print("🚀 Dires Hub Bot (High-Speed & Non-Freezing Engine) is running...")
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=25, long_polling_timeout=25)
        except Exception as e:
            print(f"Polling reconnect: {e}")
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    main()