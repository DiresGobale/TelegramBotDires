import os
import io
import time
import json
import base64
import sqlite3
import re
from io import BytesIO
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
# 1. የቴሌግራም ኤፒአይ እና ኔትወርክ ማዋቀር
# -------------------------------------------------------------------------
apihelper.CONNECT_TIMEOUT = 30
apihelper.READ_TIMEOUT = 30

TELEGRAM_BOT_TOKEN = "8732862832:AAFnHrSJHQqH4kCLkedkHCVokdgm7YRn_FI"
ADMIN_CHAT_ID = 8732862832

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=True, num_threads=25)

# -------------------------------------------------------------------------
# 2. የአማርኛ ፎንት መመዝገቢያ
# -------------------------------------------------------------------------
AMHARIC_FONT = "Helvetica"
AMHARIC_BOLD = "Helvetica-Bold"

nyala_path = "C:/Windows/Fonts/nyala.ttf"
if os.path.exists(nyala_path):
    pdfmetrics.registerFont(TTFont("Nyala", nyala_path))
    AMHARIC_FONT = "Nyala"
    AMHARIC_BOLD = "Nyala"

CARD_W = 242.6
CARD_H = 153.0

# -------------------------------------------------------------------------
# 3. አማርኛን ወደ እንግሊዝኛ መቀየሪያ (Transliteration Table)
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
# 4. የተሟላ የአድራሻ ዳታቤዝ (ጎጃም፣ ወሎ፣ ሸዋ፣ ጎንደር ወረዳዎች የተካተቱበት)
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
# 5. SQLite Database (ነባሪ ሂሳብ 0.00 ETB + ፍለጋ)
# -------------------------------------------------------------------------
DB_FILE = "fayda_bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # አዲስ ተጠቃሚ ሲመዘገብ ባላንስ 0.00 እንዲሆን ተደርጓል
    c.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)''')
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
    conn.commit()
    conn.close()

init_db()

def get_user_balance(chat_id: int) -> float:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO users (chat_id, balance) VALUES (?, 0.0)", (chat_id,))
        conn.commit()
        bal = 0.0
    else:
        bal = row[0]
    conn.close()
    return bal

def is_fan_registered(fan: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM card_records WHERE fan_code = ?", (fan,))
    row = c.fetchone()
    conn.close()
    return row is not None

def is_phone_registered(phone: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM card_records WHERE phone = ?", (phone,))
    row = c.fetchone()
    conn.close()
    return row is not None

def save_card_record(chat_id, name_am, name_en, fan, phone, fin, theme):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO card_records 
        (chat_id, name_am, name_en, fan_code, phone, fin_code, theme)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, name_am, name_en, fan, phone, fin, theme))
    conn.commit()
    conn.close()

# በስልክ ወይም በFAN ቁጥር መረጃ መፈለጊያ (ለForgot አገልግሎት)
def search_card_by_phone_or_fan(query: str):
    conn = sqlite3.connect(DB_FILE)
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

# -------------------------------------------------------------------------
# 6. 3ቱ የቀለም ቴምፕሌቶች
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

# -------------------------------------------------------------------------
# 7. ፈጣን ባርኮድ እና ይፋዊ QR ኮድ አመንጪ
# -------------------------------------------------------------------------
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
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=1
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# -------------------------------------------------------------------------
# 8. ካርዱን መሳል (ReportLab)
# -------------------------------------------------------------------------
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
# 9. የዋና ሜኑ አዝራሮች
# -------------------------------------------------------------------------
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✅ Get PDF 1", "✅ Get PDF 2", "⚠️ Get PDF 3")
    markup.row("My Balance / አሁን ያለኝ", "Add Payment / ክፍያ ጨምር")
    markup.row("🔑 Resend(forget) FAN/FIN", "🔄 Reset / እንደገና ጀምር")
    return markup

# -------------------------------------------------------------------------
# 10. የምዝገባ ደረጃዎች
# -------------------------------------------------------------------------
@bot.message_handler(commands=['start', 'reset'])
def handle_start(message):
    chat_id = message.chat.id
    user_data_store[chat_id] = {}
    get_user_balance(chat_id)

    welcome_text = (
        "👋 **እንኳን ወደ ዲጂታል መታወቂያ ማዘጋጃ ቦት በደህና መጡ!**\n\n"
        "የሚፈልጉትን የቀለም ቴምፕሌት ይምረጡ፦"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔄 Reset / እንደገና ጀምር")
def handle_reset_button(message):
    chat_id = message.chat.id
    user_data_store[chat_id] = {}
    bot.reply_to(message, "🔄 **የነበረው ሂደት ተሰርዟል!** ከአዲስ መጀመር ይችላሉ።", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text in ["✅ Get PDF 1", "✅ Get PDF 2", "⚠️ Get PDF 3"])
def handle_pdf_generation(message):
    chat_id = message.chat.id
    theme_key = message.text.replace("✅ ", "").replace("⚠️ ", "").strip()
    user_data_store[chat_id] = {"theme": theme_key}

    cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_markup.row("🔄 Reset / እንደገና ጀምር")

    msg = bot.send_message(
        chat_id,
        f"🎨 **{theme_key}** ተመርጧል!\n\n1️⃣ እባክዎ ሙሉ **ስምዎን በአማርኛ** ያስገቡ (ምሳሌ፡ ዲረስ ጎባሌ መለሰ)፦",
        reply_markup=cancel_markup
    )
    bot.register_next_step_handler(msg, step_name_am)

def step_name_am(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        msg = bot.send_message(chat_id, "⚠️ እባክዎ ትክክለኛ ስም ያስገቡ፦")
        bot.register_next_step_handler(msg, step_name_am); return

    user_data_store[chat_id]["name_am"] = text
    user_data_store[chat_id]["name_en"] = transliterate_amharic(text)

    msg = bot.send_message(
        chat_id,
        f"✅ የእንግሊዝኛ ስምዎ ተዘጋጅቷል፦ **{user_data_store[chat_id]['name_en']}**\n\n"
        "2️⃣ እባክዎ **16 አሃዝ የፋይዳ ቁጥርዎን (FAN Number)** ያስገቡ፦",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_fan_validation)

def step_fan_validation(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    text = message.text.strip().replace(" ", "").replace("-", "") if message.text else ""

    if not (text.isdigit() and len(text) == 16):
        msg = bot.send_message(chat_id, f"❌ **ስህተት! ያስገቡት FAN ቁጥር {len(text)} አሃዝ ነው።** በትክክል 16 አሃዝ ቁጥር ብቻ ያስገቡ፦")
        bot.register_next_step_handler(msg, step_fan_validation); return

    if is_fan_registered(text):
        msg = bot.send_message(chat_id, "🚫 **ይህ FAN ቁጥር ቀደም ሲል ሌላ ሰው ተጠቅሞበታል!** እባክዎ የእራስዎን FAN ያስገቡ፦")
        bot.register_next_step_handler(msg, step_fan_validation); return

    user_data_store[chat_id]["fan_code"] = text
    msg = bot.send_message(chat_id, "3️⃣ የትውልድ ቀንዎን ያስገቡ (ምሳሌ፡ 1994/10/29 | 06/06/2002)፦")
    bot.register_next_step_handler(msg, step_dob)

def step_dob(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    text = message.text.strip() if message.text else ""
    dates = text.split("|")
    user_data_store[chat_id]["dob_ec"] = dates[0].strip()
    user_data_store[chat_id]["dob_gc"] = dates[1].strip() if len(dates) > 1 else dates[0].strip()

    gender_km = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    gender_km.row("ሴት", "ወንድ")
    gender_km.row("🔄 Reset / እንደገና ጀምር")
    msg = bot.send_message(chat_id, "4️⃣ ጾታዎን ይምረጡ፦", reply_markup=gender_km)
    bot.register_next_step_handler(msg, step_gender)

def step_gender(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    txt = message.text.strip() if message.text else ""
    is_female = "ሴት" in txt
    user_data_store[chat_id]["sex_am"] = "ሴት" if is_female else "ወንድ"
    user_data_store[chat_id]["sex_en"] = "Female" if is_female else "Male"

    cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_markup.row("🔄 Reset / እንደገና ጀምር")
    msg = bot.send_message(chat_id, "5️⃣ ስልክ ቁጥርዎን ያስገቡ (ምሳሌ፡ 0912345678)፦", reply_markup=cancel_markup)
    bot.register_next_step_handler(msg, step_phone)

def step_phone(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    text = message.text.strip() if message.text else ""
    clean_phone = re.sub(r'[\s\-]', '', text)

    if not (clean_phone.isdigit() and len(clean_phone) >= 9):
        msg = bot.send_message(chat_id, "⚠️ እባክዎ ትክክለኛ ስልክ ቁጥር ያስገቡ፦")
        bot.register_next_step_handler(msg, step_phone); return

    if is_phone_registered(clean_phone):
        msg = bot.send_message(chat_id, "🚫 **ይህ ስልክ ቁጥር ቀድሞ በሌላ ካርድ ላይ ተመዝግቧል!** የእራስዎን ስልክ ያስገቡ፦")
        bot.register_next_step_handler(msg, step_phone); return

    user_data_store[chat_id]["phone"] = clean_phone

    # ክልል ምረጥ
    reg_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for r in ETHIOPIA_REGIONS.keys():
        reg_km.add(r)
    reg_km.row("🔄 Reset / እንደገና ጀምር")

    msg = bot.send_message(chat_id, "6️⃣ **ክልልዎን ይምረጡ (Select Region)፦**", reply_markup=reg_km, parse_mode="Markdown")
    bot.register_next_step_handler(msg, step_region_select)

def step_region_select(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    reg_chosen = message.text.strip()
    if reg_chosen not in ETHIOPIA_REGIONS:
        user_data_store[chat_id]["region_am"] = reg_chosen
        user_data_store[chat_id]["region_en"] = transliterate_amharic(reg_chosen)
        zones_available = []
    else:
        user_data_store[chat_id]["region_am"] = reg_chosen
        user_data_store[chat_id]["region_en"] = ETHIOPIA_REGIONS[reg_chosen]["en"]
        zones_available = list(ETHIOPIA_REGIONS[reg_chosen]["zones"].keys())

    # ዞን ምረጥ
    zone_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if zones_available:
        for i in range(0, len(zones_available), 2):
            if i + 1 < len(zones_available):
                zone_km.row(zones_available[i], zones_available[i+1])
            else:
                zone_km.add(zones_available[i])
    zone_km.row("🔄 Reset / እንደገና ጀምር")

    msg = bot.send_message(
        chat_id,
        f"✅ ክልል፦ **{reg_chosen}** ተመርጧል!\n\n7️⃣ **ዞንዎን ይምረጡ (ወይም ይጻፉ)፦**",
        reply_markup=zone_km,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_zone_select)

def step_zone_select(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    zone_chosen = message.text.strip()
    user_data_store[chat_id]["zone_am"] = zone_chosen
    user_data_store[chat_id]["zone_en"] = transliterate_amharic(zone_chosen)

    reg_am = user_data_store[chat_id].get("region_am")
    woredas_available = []
    if reg_am in ETHIOPIA_REGIONS and zone_chosen in ETHIOPIA_REGIONS[reg_am]["zones"]:
        woredas_available = ETHIOPIA_REGIONS[reg_am]["zones"][zone_chosen]

    # ወረዳ ምረጥ
    woreda_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if woredas_available:
        for i in range(0, len(woredas_available), 2):
            if i + 1 < len(woredas_available):
                woreda_km.row(woredas_available[i], woredas_available[i+1])
            else:
                woreda_km.add(woredas_available[i])
    woreda_km.row("🔄 Reset / እንደገና ጀምር")

    msg = bot.send_message(
        chat_id,
        f"✅ ዞን፦ **{zone_chosen}** ተመርጧል!\n\n8️⃣ **ወረዳዎን ይምረጡ (ወይም ይጻፉ)፦**",
        reply_markup=woreda_km,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_woreda_select)

def step_woreda_select(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    woreda_chosen = message.text.strip()
    user_data_store[chat_id]["woreda_am"] = woreda_chosen
    user_data_store[chat_id]["woreda_en"] = transliterate_amharic(woreda_chosen)

    cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_markup.row("🔄 Reset / እንደገና ጀምር")

    msg = bot.send_message(
        chat_id,
        f"✅ ወረዳ፦ **{woreda_chosen}** ተመርጧል!\n\n"
        "9️⃣ 📸 በመጨረሻም ለመታወቂያው የሚሆን ጥራት ያለው **የቁም ፎቶ** ይላኩ፦",
        reply_markup=cancel_markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_photo)

def step_photo(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message); return

    if not message.photo:
        msg = bot.reply_to(message, "⚠️ እባክዎ ፎቶ ይላኩ፦")
        bot.register_next_step_handler(msg, step_photo); return

    status_msg = bot.send_message(chat_id, "⚡ ካርዱ በቅጽበት እየተዘጋጀ ነው...")

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

    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(CARD_W, CARD_H))
    draw_card_front(c, card_data, temp_photo, theme)
    c.showPage()
    draw_card_back(c, card_data, temp_photo, theme)
    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    filename = f"Fayda_Card_{card_data['name_en'].replace(' ', '_')}.pdf"
    bot.send_document(
        chat_id,
        (filename, pdf_buffer.getvalue()),
        caption=(
            f"🎉 **እንኳን ደስ አለዎት! ካርድዎ ተዘጋጅቷል።**\n\n"
            f"👤 **ስም**: {card_data['name_am']} ({card_data['name_en']})\n"
            f"🆔 **FAN**: `{card_data['fan_code']}`\n"
            f"📍 **አድራሻ**: {card_data['region_am']} | {card_data['zone_am']} | {card_data['woreda_am']}\n"
            f"🔑 **FIN**: `{fin_number}`\n"
            f"🎨 **ቴምፕሌት**: {u.get('theme', 'PDF 1')}"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

    if os.path.exists(temp_photo):
        os.remove(temp_photo)
    bot.delete_message(chat_id, status_msg.message_id)

# -------------------------------------------------------------------------
# 11. የተሻሻለው Forgot / Resend FAN/FIN (በስልክ ወይም በFAN መፈለጊያ)
# -------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == "🔑 Resend(forget) FAN/FIN")
def handle_resend_prompt(message):
    chat_id = message.chat.id
    cancel_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel_markup.row("🔄 Reset / እንደገና ጀምር")
    
    msg = bot.send_message(
        chat_id,
        "🔍 **መረጃ መፈለጊያ (FAN / FIN Recovery)፦**\n\n"
        "እባክዎ የተመዘገቡበትን **ስልክ ቁጥር** (ምሳሌ፡ `0912345678`) ወይም ባለ **16 አሃዝ FAN ቁጥርዎን** ያስገቡ፦",
        reply_markup=cancel_markup,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, step_search_record)

def step_search_record(message):
    chat_id = message.chat.id
    if message.text == "🔄 Reset / እንደገና ጀምር":
        handle_reset_button(message)
        return

    query_text = message.text.strip() if message.text else ""
    record = search_card_by_phone_or_fan(query_text)

    if record:
        name_am, name_en, fan, phone, fin = record
        bot.send_message(
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
        bot.send_message(
            chat_id,
            f"❌ **በ `{query_text}` የተመዘገበ ምንም አይነት የካርድ መረጃ አልተገኘም!**\n\n"
            "እባክዎ ትክክለኛ ስልክ ወይም FAN ቁጥር ማስገባትዎን ያረጋግጡ ወይም ከአዲስ ካርድ ያዘጋጁ።",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

# -------------------------------------------------------------------------
# 12. ቀሪ ሂሳብ እና ክፍያ (0.00 ETB Default)
# -------------------------------------------------------------------------
@bot.message_handler(func=lambda m: m.text == "My Balance / አሁን ያለኝ")
def handle_balance(message):
    bal = get_user_balance(message.chat.id)
    bot.reply_to(
        message,
        f"💰 **የአሁኑ ቀሪ ሂሳብዎ፦** {bal:.2f} ETB\n\nካርድ ለማውጣት እባክዎ አስቀድመው ሂሳብዎን ይሙሉ (Add Payment)።",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "Add Payment / ክፍያ ጨምር")
def handle_add_payment(message):
    payment_info = (
        "💳 **የክፍያ አማራጮች፦**\n\n"
        "1. **Telebirr**: `0957625740`\n"
        "2. **CBE (የኢትዮጵያ ንግድ ባንክ)**: `1000XXXXXXXXX`\n\n"
        "ክፍያ ከፈጸሙ በኋላ የደረሰኝ ፎቶ ወይም የግብይት ቁጥር (Transaction ID) ይላኩልን።"
    )
    bot.reply_to(message, payment_info, reply_markup=get_main_keyboard(), parse_mode="Markdown")

# -------------------------------------------------------------------------
# 13. ዋና ዑደት (Resilient Polling Loop)
# -------------------------------------------------------------------------
def main():
    print("🚀 Dires Hub Bot (Phone/FAN Search + 0.00 ETB Balance + Full Zones) ዝግጁ ሆኗል...")
    while True:
        try:
            bot.polling(none_stop=True, timeout=20, long_polling_timeout=20)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    main()