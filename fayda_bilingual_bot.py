import os
import io
import time
import json
import base64
import sqlite3
import re
import datetime
import threading
import urllib.request
import math
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types, apihelper
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageOps, ImageDraw
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# -------------------------------------------------------------------------
# 1. API Configuration & Admin Settings
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
# 2. የአማርኛ ፎንት አወራረድና ምዝገባ
# -------------------------------------------------------------------------
AMHARIC_FONT = "Helvetica"
AMHARIC_BOLD = "Helvetica-Bold"

def setup_amharic_font():
    global AMHARIC_FONT, AMHARIC_BOLD
    font_filename = "NotoSansEthiopic-Regular.ttf"
    font_bold_filename = "NotoSansEthiopic-Bold.ttf"
    
    regular_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansEthiopic/NotoSansEthiopic-Regular.ttf"
    bold_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansEthiopic/NotoSansEthiopic-Bold.ttf"

    try:
        if not os.path.exists(font_filename):
            urllib.request.urlretrieve(regular_url, font_filename)
        if not os.path.exists(font_bold_filename):
            urllib.request.urlretrieve(bold_url, font_bold_filename)

        pdfmetrics.registerFont(TTFont("AmharicFont", font_filename))
        pdfmetrics.registerFont(TTFont("AmharicBold", font_bold_filename))
        AMHARIC_FONT = "AmharicFont"
        AMHARIC_BOLD = "AmharicBold"
    except Exception as e:
        if os.path.exists("C:/Windows/Fonts/nyala.ttf"):
            try:
                pdfmetrics.registerFont(TTFont("Nyala", "C:/Windows/Fonts/nyala.ttf"))
                AMHARIC_FONT = "Nyala"
                AMHARIC_BOLD = "Nyala"
            except Exception:
                pass

setup_amharic_font()

CARD_W = 242.6
CARD_H = 153.0

# -------------------------------------------------------------------------
# 3. የአድሚን ማሳወቂያ እና መልእክት መላኪያ
# -------------------------------------------------------------------------
def notify_admin(text: str):
    def _send():
        try:
            bot.send_message(ADMIN_CHAT_ID, text, parse_mode="Markdown")
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

def safe_send_message(chat_id, text, reply_markup=None, parse_mode=None, retries=2):
    for attempt in range(retries):
        try:
            return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(0.5)

# -------------------------------------------------------------------------
# 4. ፊደላት መተርጎሚያ
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

def transliterate_text(text: str) -> str:
    words = text.strip().split()
    eng_words = []
    for w in words:
        out = ""
        for char in w:
            out += AMH_TO_ENG.get(char, char)
        eng_words.append(out.capitalize())
    return " ".join(eng_words)

# -------------------------------------------------------------------------
# 5. የቀን ስሌት
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
# 6. የኢትዮጵያ ክልሎች ዳታቤዝ
# -------------------------------------------------------------------------
ETHIOPIA_REGIONS = {
    "አማራ (Amhara)": {
        "local": "አማራ",
        "en": "Amhara",
        "zones": {
            "ምዕራብ ጎጃም": {"en": "West Gojjam", "woredas": ["ባህር ዳር ዙሪያ", "መኤጫ", "ይልማና ዴንሳ", "ቡሬ", "ደቡብ አቸፈር", "ሰሜን አቸፈር", "ደምበጫ", "ጃቢ ጥህናን", "ሰከላ", "ቁሪት"]},
            "ምስራቅ ጎጃም": {"en": "East Gojjam", "woredas": ["ደብረ ማርቆስ", "ማቻከል", "ደጀን", "አነደድ", "እናርጅ እናናውጋ", "እነብሴ ሳር ምድር", "ሰደዴ", "ጉዛምን", "ባሶ ሊበን", "አዋበል"]},
            "አዊ (ጎጃም)": {"en": "Awi (Gojjam)", "woredas": ["እንጅባራ", "ፋግታ ለኮማ", "ባንጃ", "አንከሻ ጓጉሳ", "ጓንጓ", "ጃዊ", "ዚገም"]},
            "ሰሜን ወሎ": {"en": "North Wollo", "woredas": ["ወልዲያ", "ላሊበላ", "ራያ ቆቦ", "ጉባ ላፍቶ", "ሀብሩ", "መቄት", "ዋድላ", "ዳውንት", "ቡግና", "ግደን"]},
            "ደቡብ ወሎ": {"en": "South Wollo", "woredas": ["ደሴ", "ኮምቦልቻ", "ቃሉ", "ኩታበር", "ተሁለደሬ", "አልቡኮ", "ወረባቡ", "ለጋምቦ", "ሳይንት", "ጃማ", "ወገል ጤና"]},
            "ሰሜን ሸዋ (አማራ)": {"en": "North Shewa", "woredas": ["ደብረ ብርሃን", "አንኮበር", "ባሶና ወራና", "ምንጃር ሸንኮራ", "ሞረትና ጅሩ", "ሲያደብርና ዋዩ", "በረኸት", "አንጎለላና ጠራ", "ኤፍራታና ግድም", "ቀወት"]},
            "ማዕከላዊ ጎንደር": {"en": "Central Gondar", "woredas": ["ታች አርማጭሆ", "ላይ አርማጭሆ", "ጭልጋ", "ጎንደር ዙሪያ", "ደምቢያ", "ምዕራብ ደምቢያ", "ምስራቅ ደምቢያ", "ተከዜ"]},
            "ሰሜን ጎንደር": {"en": "North Gondar", "woredas": ["ደባርቅ", "ዳባት", "በየዳ", "ጃናሞራ", "ጠለምት", "አዲ አርቃይ"]},
            "ደቡብ ጎንደር": {"en": "South Gondar", "woredas": ["ደብረ ታቦር", "ፎገራ", "ፋርታ", "ላይ ጋይንት", "ታች ጋይንት", "እስቴ", "ስማዳ", "አንደበት", "ድሬዳ"]},
            "ዋግ ኽምራ": {"en": "Wag Hemra", "woredas": ["ሰቆጣ", "ዝቋላ", "ሳህላ", "ደሃና", "ገዘብላ"]}
        }
    },
    "Oromiyaa (ኦሮሚያ)": {
        "local": "Oromiyaa",
        "en": "Oromia",
        "zones": {
            "Godina Addaa Oromiyaa": {"en": "Oromia Special Zone", "woredas": ["Buraayyuu", "Sabbataa", "Dukam", "Sulultaa", "Galaan", "Hoolota"]},
            "Shawaa Bahaa": {"en": "East Shewa", "woredas": ["Adaamaa", "Bishooftuu", "Mojo", "Luume", "Bosat", "Adaamii Tulluu"]},
            "Shawaa Kaabaa": {"en": "North Shewa", "woredas": ["Fiichee", "Dabra Libaanos", "Waara Jaarsoo", "Yaayaa Gullallee"]},
            "Shawaa Dhihaa": {"en": "West Shewa", "woredas": ["Amboo", "Jaldu", "Tookkee Kuttaaye", "Dandi"]},
            "Arsii Dhihaa": {"en": "West Arsi", "woredas": ["Shaashamannee", "Kofalee", "Nageellee Arsi", "Doddola"]},
            "Arsii": {"en": "Arsi", "woredas": ["Asallaa", "Ticho", "Diksiis", "Siree", "Zuwaay Dugda"]},
            "Jimma": {"en": "Jimma Zone", "woredas": ["Jimma", "Aggaaroo", "Manna", "Gommaa", "Limmuu Saqqa"]},
            "Harargee Bahaa": {"en": "East Hararghe", "woredas": ["Awadaay", "Haramaya", "Kombolcha", "Babile", "Fedis"]},
            "Wallagga Dhihaa": {"en": "West Wollega", "woredas": ["Gimbi", "Nedjo", "Boji Dirmeji", "Ayira"]}
        }
    },
    "ትግራይ (Tigray)": {
        "local": "ትግራይ",
        "en": "Tigray",
        "zones": {
            "ዞባ መቐለ": {"en": "Mekelle Zone", "woredas": ["ሓወልቲ", "ዓዲ ሓቂ", "ቀዳማይ ወያነ", "ሰሜን", "ደቡብ"]},
            "ምብራቕ ትግራይ": {"en": "Eastern Tigray", "woredas": ["ዓዲግራት", "ውቅሮ", "ጉሎ መኸዳ", "ኢሮብ", "ሳዕሲዕ ጻዕዳእምባ"]},
            "ማእኸላይ ትግራይ": {"en": "Central Tigray", "woredas": ["ዓድዋ", "ኣኽሱም", "ታሕታይ ማይጨው", "ወርዒ ለኸ", "ናዕዴር ዓዴት"]},
            "ደቡብ ትግራይ": {"en": "Southern Tigray", "woredas": ["ማይጨው", "ራያ ዓዘቦ", "እንዳመኾኒ", "ኦፍላ", "ራያ ጨርጨር"]},
            "ሰሜን ምዕራብ ትግራይ": {"en": "North Western Tigray", "woredas": ["ሽረ እንዳስላሴ", "ታሕታይ ቆራሮ", "መድበይ ዛና", "ኣስገደ ጽምብላ"]}
        }
    },
    "አዲስ አበባ (Addis Ababa)": {
        "local": "አዲስ አበባ",
        "en": "Addis Ababa",
        "zones": {
            "ክፍለ ከተማ": {"en": "Sub-City", "woredas": ["ቦሌ", "ቂርቆስ", "አራዳ", "የካ", "ንፋስ ስልክ ላፍቶ", "ኮልፌ ቀራኒዮ", "ሊደታ", "ጉለሌ", "አዲስ ከተማ", "አካቂ ቃሊቲ", "ለሚ ኩራ"]}
        }
    },
    "Soomaali (ሶማሌ)": {
        "local": "Dowlad Degaanka Soomaalida",
        "en": "Somali",
        "zones": {
            "Shabeele": {"en": "Shabelle Zone", "woredas": ["Godey", "Qalaafe", "Mustaxiil", "Feerfeer", "Beer-caano"]},
            "Faafan": {"en": "Fafan Zone", "woredas": ["Jigjiga", "Wajaale", "Awbare", "Babili", "Gursum", "Tuliguuleed"]},
            "Siti": {"en": "Siti Zone", "woredas": ["Shinile", "Ayesha", "Dembel", "Erer", "Mieso"]},
            "Doollo": {"en": "Dollo Zone", "woredas": ["Wardheer", "Boh", "Danood", "Galadi", "Daratoole"]},
            "Jarar": {"en": "Jarar Zone", "woredas": ["Degehabur", "Birkod", "Bilcil Bur", "Gunagado"]}
        }
    },
    "Qafar (አፋር)": {
        "local": "Qafar Rakaakay",
        "en": "Afar",
        "zones": {
            "Awsi Rasu (Zone 1)": {"en": "Awsi Rasu", "woredas": ["Asaita", "Dubti", "Afambo", "Chifra", "Mille"]},
            "Kilbet Rasu (Zone 2)": {"en": "Kilbet Rasu", "woredas": ["Abala", "Berhale", "Dalol", "Koneba"]},
            "Gabi Rasu (Zone 3)": {"en": "Gabi Rasu", "woredas": ["Awash Fentale", "Amibara", "Bure Mudaytu", "Geweane"]},
            "Fanti Rasu (Zone 4)": {"en": "Fanti Rasu", "woredas": ["Ewa", "Golina", "Yalo", "Teru"]}
        }
    },
    "Sidaama (ሲዳማ)": {
        "local": "Sidaamu Dagoomi Gedo",
        "en": "Sidama",
        "zones": {
            "Hawassa": {"en": "Hawassa City Admin", "woredas": ["Menehariya", "Tabor", "Hayk Dar", "Misraq", "Mehal"]},
            "Sidama Zooni": {"en": "Sidama Zone", "woredas": ["Wondo Genet", "Aleta Wondo", "Borecha", "Daale", "Yirgalem", "Chuko", "Hula"]}
        }
    },
    "ደቡብ ኢትዮጵያ (South Ethiopia)": {
        "local": "ደቡብ ኢትዮጵያ",
        "en": "South Ethiopia",
        "zones": {
            "ዎላይታ": {"en": "Wolayita Zone", "woredas": ["ሶዶ", "ቦዲቲ", "አረካ", "ዳሞት ጋሌ", "ዳሞት ወይዴ", "ሁምቦ", "ኦፋ"]},
            "ጋሞ": {"en": "Gamo Zone", "woredas": ["አርባ ምንጭ", "ጨንቻ", "ዲታ", "ቦንኬ", "ሚርአብ አባያ", "ቁቻ"]},
            "ጎፋ": {"en": "Gofa Zone", "woredas": ["ሳውላ", "ደሜ ጎፋ", "ዛላ", "ኡባ ደብረ ፀሐይ"]},
            "ጌዴኦ": {"en": "Gedeo Zone", "woredas": ["ዲላ", "ይርጋጨፌ", "ወናጎ", "ቡሌ", "ኮቾሬ"]}
        }
    },
    "ማዕከላዊ ኢትዮጵያ (Central Ethiopia)": {
        "local": "ማዕከላዊ ኢትዮጵያ",
        "en": "Central Ethiopia",
        "zones": {
            "ጉራጌ": {"en": "Gurage Zone", "woredas": ["ወልቂጤ", "እምድብር", "ቡታጅራ", "ጉመር", "እዣ", "ቸሃ", "አበሽጌ"]},
            "ስልጤ": {"en": "Siltie Zone", "woredas": ["ወራቤ", "ዳሎቻ", "ሳንኩራ", "ሁልባራግ", "ላንፍሮ"]},
            "ሀዲያ": {"en": "Hadiya Zone", "woredas": ["ሆሳዕና", "ሌሞ", "ሻሾጎ", "ሶሮ", "ሚሻ", "አናሌሞ"]},
            "ከምባታ": {"en": "Kembata Zone", "woredas": ["ዱራሜ", "አንጋቻ", "ቃዲዳ ጋሚላ", "ዶዮገና"]}
        }
    },
    "ደቡብ ምዕራብ ኢትዮጵያ (SW Ethiopia)": {
        "local": "ደቡብ ምዕራብ ኢትዮጵያ",
        "en": "South West Ethiopia",
        "zones": {
            "ካፋ": {"en": "Keffa Zone", "woredas": ["ቦንጋ", "ጊምቦ", "ዴቻ", "ጨና", "ገሻ", "ቴሎ"]},
            "ቤንች ሸኮ": {"en": "Bench Sheko Zone", "woredas": ["ሚዛን አማን", "ደቡብ ቤንች", "ሰሜን ቤንች", "ሸኮ", "ጉራፈርዳ"]},
            "ዳውሮ": {"en": "Dawro Zone", "woredas": ["ተርጫ", "ማሪቃ", "ሎማ", "ገነ ቦሳ", "ቶጫ"]}
        }
    },
    "ቤንሻንጉል ጉሙዝ (Benishangul Gumuz)": {
        "local": "ቤንሻንጉል ጉሙዝ",
        "en": "Benishangul Gumuz",
        "zones": {
            "አሶሳ": {"en": "Assosa Zone", "woredas": ["አሶሳ", "ባምባሲ", "ሆሞሻ", "መንጌ", "ኩርሙክ", "ኦዳ ቡልዲግሉ"]},
            "መተከል": {"en": "Metekel Zone", "woredas": ["ጊልገል በለስ", "ዳንጉር", "ጉባ", "ማንዱራ", "ዲባጤ", "ቡለን"]}
        }
    },
    "ጋምቤላ (Gambella)": {
        "local": "ጋምቤላ",
        "en": "Gambella",
        "zones": {
            "አኙዋክ": {"en": "Anuak Zone", "woredas": ["ጋምቤላ ከተማ", "አቦቦ", "ጎግ", "ጆር"]},
            "ኑዌር": {"en": "Nuer Zone", "woredas": ["ላሬ", "ጂካዎ", "ዋንቱዋ", "አኮቦ"]}
        }
    },
    "ሐረሪ (Harari)": {
        "local": "ሐረሪ",
        "en": "Harari",
        "zones": {
            "ሐረር": {"en": "Harar City", "woredas": ["አሚር ኑር", "አባድር", "ሸንኮር", "ጂንኤላ", "ሶፊ", "ኤረር"]}
        }
    },
    "ድሬዳዋ (Dire Dawa)": {
        "local": "ድሬዳዋ",
        "en": "Dire Dawa",
        "zones": {
            "አስተዳደር": {"en": "Administration", "woredas": ["ቀበሌ 01-09", "ገደይስ", "ዋሂል", "ለገሀሬ"]}
        }
    }
}

# -------------------------------------------------------------------------
# 7. Database Layer (Strict Unique Phone and FAN)
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
        return 999999.0, 0
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
# 8. ራስ-ሰር የፎቶ ማስተካከያ (Smart Crop: Full Body to Passport Headshot)
# -------------------------------------------------------------------------
_FACE_CASCADES = None

def _get_face_cascades():
    global _FACE_CASCADES
    if _FACE_CASCADES is not None:
        return _FACE_CASCADES
    cascades = []
    try:
        import cv2
        cascade_names = [
            "haarcascade_frontalface_default.xml",
            "haarcascade_frontalface_alt2.xml",
            "haarcascade_profileface.xml"
        ]
        for name in cascade_names:
            cpath = os.path.join(cv2.data.haarcascades, name)
            if os.path.exists(cpath):
                clf = cv2.CascadeClassifier(cpath)
                if not clf.empty():
                    cascades.append(clf)
    except Exception:
        pass
    _FACE_CASCADES = cascades
    return _FACE_CASCADES

def prepare_portrait_photo(photo_bytes: bytes, target_width=320, target_height=420):
    """ተጠቃሚው ሙሉ ቁመት (Full Body) ወይም ማንኛውንም ፎቶ ቢልክ ልክ እንደ ስታንዳርድ ፓስፖርት (ጭንቅላትና ደረቱ ጎልቶ) እንዲወጣ ያደርገዋል"""
    img = Image.open(BytesIO(photo_bytes)).convert("RGB")
    img = ImageOps.exif_transpose(img)
    w, h = img.size

    target_ratio = target_width / target_height

    found_face = False
    fx, fy, fw, fh = 0, 0, 0, 0

    try:
        cascades = _get_face_cascades()
        if cascades:
            import cv2
            import numpy as np
            arr = np.array(img)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            all_faces = []
            for casc in cascades:
                faces = casc.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=4,
                    minSize=(max(30, int(w * 0.05)), max(30, int(h * 0.03)))
                )
                if len(faces) > 0:
                    all_faces.extend(faces)
            if len(all_faces) > 0:
                fx, fy, fw, fh = max(all_faces, key=lambda b: b[2] * b[3])
                found_face = True
    except Exception:
        found_face = False

    if found_face:
        cx = fx + fw // 2
        cy = fy + fh // 2

        # ፓስፖርት ቅርጽ፦ ፊቱ ~37%-38% የፎቶውን ቁመት እንዲይዝ፣ ከጭንቅላት በላይ ተገቢ ቦታ፣ ከታች ደረትና ትከሻ እንዲወጣ
        crop_h = int(fh * 2.65)
        crop_w = int(crop_h * target_ratio)

        if crop_w < int(fw * 1.85):
            crop_w = int(fw * 1.85)
            crop_h = int(crop_w / target_ratio)

        if crop_w > w:
            crop_w = w
            crop_h = int(crop_w / target_ratio)
        if crop_h > h:
            crop_h = h
            crop_w = int(crop_h * target_ratio)

        x1 = int(cx - crop_w / 2)
        y1 = int(cy - crop_h * 0.40)

        if x1 < 0:
            x1 = 0
        elif x1 + crop_w > w:
            x1 = max(0, w - crop_w)

        if y1 < 0:
            y1 = 0
        elif y1 + crop_h > h:
            y1 = max(0, h - crop_h)

        crop_box = (x1, y1, min(w, x1 + crop_w), min(h, y1 + crop_h))
    else:
        # ሙሉ ቁመት (Full Body) ፎቶ ሆኖ ፊቱ በግልጽ ካልታወቀ የላይኛውን ክፍል (ጭንቅላትና ደረት) ይወስዳል
        if h > w * 1.40:
            crop_h = int(h * 0.40)
            crop_w = int(crop_h * target_ratio)
            if crop_w > w:
                crop_w = w
                crop_h = int(crop_w / target_ratio)
            x1 = max(0, (w - crop_w) // 2)
            y1 = int(h * 0.02)
            if y1 + crop_h > h:
                y1 = 0
            crop_box = (x1, y1, x1 + crop_w, y1 + crop_h)
        else:
            current_ratio = w / h
            if current_ratio > target_ratio:
                new_w = int(h * target_ratio)
                offset = (w - new_w) // 2
                crop_box = (offset, 0, offset + new_w, h)
            else:
                new_h = int(w / target_ratio)
                crop_box = (0, 0, w, new_h)

    img = img.crop(crop_box).resize((target_width, target_height), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf

# -------------------------------------------------------------------------
# 9. የካርዱ ትክክለኛ የሁለት ቀለም ዳራ ማመንጫ (Mint Green + Warm Sunny Yellow)
# -------------------------------------------------------------------------
CARD_BG_CACHE = None

def get_dual_tone_card_background():
    """በግራ በኩል ደማቅ ሚንት አረንጓዴ፣ በቀኝ በኩል ደግሞ ወርቃማ ቢጫ ቀለም ያለው ድንቅ ዳራ ያዘጋጃል"""
    global CARD_BG_CACHE
    if CARD_BG_CACHE:
        CARD_BG_CACHE.seek(0)
        return CARD_BG_CACHE

    width, height = 1000, 630
    img = Image.new("RGB", (width, height), "#FFFFFF")
    pixels = img.load()

    # የሁለቱ ቀለሞች ቅንብር
    # Mint Green: (134, 239, 196) / (110, 231, 183)
    # Warm Sunny Yellow: (254, 240, 138) / (253, 224, 71)
    for y in range(height):
        for x in range(width):
            # በግራ እና በቀኝ መካከል የሚደረግ የከለር ውህደት
            fx = x / float(width)
            fy = (height - y) / float(height)

            # በቀኝ በኩል እና መሃል ላይ የቢጫው ክብደት ይጨምራል
            yellow_weight = math.pow(fx, 0.9) * 0.75 + math.pow(fy, 1.2) * 0.25
            yellow_weight = min(1.0, max(0.0, yellow_weight))

            # አረንጓዴ (Mint) እና ቢጫ (Warm Yellow) ውህደት
            r = int((140 * (1 - yellow_weight)) + (254 * yellow_weight))
            g = int((240 * (1 - yellow_weight)) + (235 * yellow_weight))
            b = int((205 * (1 - yellow_weight)) + (130 * yellow_weight))

            pixels[x, y] = (r, g, b)

    draw = ImageDraw.Draw(img)

    # የሞገድ መስመሮች (Guilloche Wave Lines)
    for i in range(-200, width + 200, 45):
        points = []
        for step_x in range(0, width + 10, 20):
            step_y = int(math.sin((step_x + i) * 0.015) * 45 + (step_x * 0.2) + (i * 0.5))
            points.append((step_x, step_y % height))
        draw.line(points, fill=(160, 245, 215), width=2)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    CARD_BG_CACHE = buf
    return CARD_BG_CACHE

user_data_store = {}

def draw_ethiopian_flag(c, x, y, width=22, height=14):
    """የኢትዮጵያ ባንዲራ ከነ ሰማያዊው አርማ እና ቢጫ ኮከብ"""
    stripe_h = height / 3.0
    c.setFillColor(HexColor("#078930")); c.rect(x, y + stripe_h * 2, width, stripe_h, fill=1, stroke=0)
    c.setFillColor(HexColor("#FCDD09")); c.rect(x, y + stripe_h, width, stripe_h, fill=1, stroke=0)
    c.setFillColor(HexColor("#DA121A")); c.rect(x, y, width, stripe_h, fill=1, stroke=0)

    cx, cy = x + width / 2.0, y + height / 2.0
    radius = height * 0.38
    c.setFillColor(HexColor("#0F47AF"))
    c.circle(cx, cy, radius, fill=1, stroke=0)

    c.setFillColor(HexColor("#FCDD09"))
    c.setStrokeColor(HexColor("#FCDD09"))
    c.setLineWidth(0.35)
    p = c.beginPath()
    for i in range(10):
        ang = i * math.pi / 5 - math.pi / 2
        r = radius * 0.75 if i % 2 == 0 else radius * 0.32
        px = cx + r * math.cos(ang)
        py = cy + r * math.sin(ang)
        if i == 0:
            p.moveTo(px, py)
        else:
            p.lineTo(px, py)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

def draw_exact_national_id_logo(c, x, y):
    """በቀኝ ራስጌ ላይ ያለውን ኦሪጅናል የብሔራዊ መታወቂያ ክብ አርማ ይስላል"""
    c.saveState()
    # ሰማያዊ ክብ ዳራ
    c.setFillColor(HexColor("#0284C7"))
    c.circle(x, y, 9, fill=1, stroke=0)
    
    # በክቡ ውስጥ ነጭ የዲጂታል ኖዶች እና መስመሮች
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(HexColor("#FFFFFF"))
    c.setLineWidth(0.65)
    c.circle(x - 3.5, y + 2.5, 1.3, fill=1, stroke=0)
    c.circle(x + 3.5, y + 2.5, 1.3, fill=1, stroke=0)
    c.circle(x, y - 4, 1.3, fill=1, stroke=0)
    c.circle(x, y + 0.5, 1.6, fill=1, stroke=0)
    c.line(x - 3.5, y + 2.5, x, y + 0.5)
    c.line(x + 3.5, y + 2.5, x, y + 0.5)
    c.line(x, y - 4, x, y + 0.5)

    # በጎኑ ያለ ጽሑፍ
    c.setFillColor(HexColor("#044E72"))
    c.setFont(AMHARIC_BOLD, 4.2)
    c.drawString(x + 12, y + 2, "ብሔራዊ መታወቂያ")
    c.setFont("Helvetica-Bold", 4.8)
    c.drawString(x + 12, y - 4, "National ID")
    c.restoreState()

def draw_fayda_amharic_center_logo(c, x, y):
    """መሃል ላይ የሚታየውን ኦሪጅናል 'ፋይዳ' ምልክት ይስላል"""
    c.saveState()
    c.setFillColor(HexColor("#34A87C"))
    c.setFont(AMHARIC_BOLD, 17)
    c.drawString(x, y, "ፋይዳ")
    c.restoreState()

def generate_fayda_encrypted_qr_payload(data: dict, photo_bytes: bytes) -> str:
    try:
        with Image.open(BytesIO(photo_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((50, 60))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=30)
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
    writer.dpi = 150
    bc = code128(code_text, writer=writer)
    buf = BytesIO()
    bc.write(buf, options={"write_text": False, "quiet_zone": 1})
    buf.seek(0)
    return buf

def generate_crisp_qr(data_text: str):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=3, border=1)
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# -------------------------------------------------------------------------
# 10. Front Side Rendering
# -------------------------------------------------------------------------
def draw_card_front(c, data: dict, photo_reader, ghost_reader):
    # ሁለቱንም ቀለሞች (Mint Green & Warm Yellow) የያዘውን ዳራ መሳል
    bg_buf = get_dual_tone_card_background()
    c.drawImage(ImageReader(bg_buf), 0, 0, width=CARD_W, height=CARD_H)

    # የካርዱ ዙሪያ ድንበር
    c.setStrokeColor(HexColor("#86EFAC"))
    c.setLineWidth(0.65)
    c.roundRect(3, 3, CARD_W - 6, CARD_H - 6, radius=6, fill=0, stroke=1)

    # በማዕከሉ ደብዛዛ የኢትዮጵያ ኮከብ አርማ (Watermark Star)
    cx, cy = CARD_W * 0.58, CARD_H * 0.45
    c.setStrokeColor(HexColor("#C8F5E2"))
    c.setFillColor(HexColor("#D4F7E7"))
    c.setLineWidth(0.6)
    p = c.beginPath()
    for i in range(10):
        ang = i * math.pi / 5 - math.pi / 2
        r = 26 if i % 2 == 0 else 10
        px = cx + r * math.cos(ang)
        py = cy + r * math.sin(ang)
        if i == 0:
            p.moveTo(px, py)
        else:
            p.lineTo(px, py)
    p.close()
    c.drawPath(p, fill=1, stroke=1)

    # 1. ባንዲራ
    draw_ethiopian_flag(c, 12, CARD_H - 24, width=22, height=13)

    # 2. ርዕስ (Title)
    c.setFillColor(HexColor("#084534"))
    c.setFont(AMHARIC_BOLD, 7.5)
    c.drawString(38, CARD_H - 16, "የኢትዮጵያ ዲጂታል መታወቂያ ካርድ")
    c.setFont("Helvetica-Bold", 7.0)
    c.drawString(38, CARD_H - 24, "Ethiopian Digital ID Card")

    # 3. ብሔራዊ መታወቂያ አርማ (National ID Logo)
    draw_exact_national_id_logo(c, CARD_W - 55, CARD_H - 18)

    # 4. ዋና የቁም ፎቶ (Smart Portrait Headshot)
    photo_w, photo_h = 56, 73
    photo_x, photo_y = 12, CARD_H - 110
    c.drawImage(photo_reader, photo_x, photo_y, width=photo_w, height=photo_h, preserveAspectRatio=True)
    c.setStrokeColor(HexColor("#6EE7B7"))
    c.setLineWidth(0.65)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)

    # 5. ትንሽ የደህንነት ፎቶ (Ghost Portrait)
    ghost_w, ghost_h = 19, 25
    ghost_x, ghost_y = CARD_W - 44, 15
    c.drawImage(ghost_reader, ghost_x, ghost_y, width=ghost_w, height=ghost_h, preserveAspectRatio=True)
    c.setStrokeColor(HexColor("#6EE7B7"))
    c.setLineWidth(0.5)
    c.rect(ghost_x, ghost_y, ghost_w, ghost_h, fill=0, stroke=1)

    # 6. የጎን ጽሑፍ (Date of Issue & Date)
    c.saveState()
    c.translate(8.5, CARD_H - 105)
    c.rotate(90)
    c.setFont(AMHARIC_FONT, 3.8)
    c.setFillColor(HexColor("#4B8B70"))
    c.drawString(0, 0, f"የተሰጠበት ቀን  15/02/2019 Date of Issue       {data['issued_gc']}")
    c.restoreState()

    # 7. የካርዱ ዝርዝር መረጃዎች (በወርቃማ-ቡኒ ርዕሶች)
    x_lbl = 76
    cur_y = CARD_H - 35
    
    # ሙሉ ስም
    c.setFont(AMHARIC_FONT, 4.6); c.setFillColor(HexColor("#92400E"))
    c.drawString(x_lbl, cur_y, "ሙሉ ስም | Full Name")
    cur_y -= 6.2
    c.setFont(AMHARIC_BOLD, 7.5); c.setFillColor(HexColor("#06281D"))
    c.drawString(x_lbl, cur_y, data["name_am"])
    cur_y -= 7.2
    c.setFont("Helvetica-Bold", 6.8); c.setFillColor(HexColor("#06281D"))
    c.drawString(x_lbl, cur_y, data["name_en"])

    cur_y -= 8.5
    # የትውልድ ቀን
    c.setFont(AMHARIC_FONT, 4.6); c.setFillColor(HexColor("#92400E"))
    c.drawString(x_lbl, cur_y, "የትውልድ ቀን | Date of Birth")
    cur_y -= 6.2
    c.setFont("Helvetica-Bold", 6.5); c.setFillColor(HexColor("#06281D"))
    c.drawString(x_lbl, cur_y, f"{data['dob_ec']}  |  {data['dob_gc']}")

    cur_y -= 8.5
    # ጾታ
    c.setFont(AMHARIC_FONT, 4.6); c.setFillColor(HexColor("#92400E"))
    c.drawString(x_lbl, cur_y, "ጾታ | Sex")
    cur_y -= 6.2
    c.setFont(AMHARIC_BOLD, 6.5); c.setFillColor(HexColor("#06281D"))
    c.drawString(x_lbl, cur_y, data["sex_am"])
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x_lbl + 22, cur_y, f"|  {data['sex_en']}")

    cur_y -= 8.5
    # የሚያበቃበት ቀን
    c.setFont(AMHARIC_FONT, 4.6); c.setFillColor(HexColor("#92400E"))
    c.drawString(x_lbl, cur_y, "የሚያበቃበት ቀን | Date of Expiry")
    cur_y -= 6.2
    c.setFont("Helvetica-Bold", 6.5); c.setFillColor(HexColor("#06281D"))
    c.drawString(x_lbl, cur_y, f"{data['expiry_ec']} | {data['expiry_gc']}")

    # 8. 'ፋይዳ' መሃል ላይ
    draw_fayda_amharic_center_logo(c, CARD_W - 95, 52)

    # 9. ባርኮድ እና FAN
    c.setFont(AMHARIC_FONT, 4.2); c.setFillColor(HexColor("#4B8B70"))
    c.drawString(76, 32, "ካርድ")
    c.drawString(76, 26, "ቁጥር")
    c.setFont("Helvetica-Bold", 4.2)
    c.drawString(76, 20, "FAN")

    bc_buf = generate_crisp_barcode(data["fan_code"])
    c.setFont("Helvetica-Bold", 5.8); c.setFillColor(HexColor("#06281D"))
    c.drawCentredString(142, 33, data["fan_code"])
    c.drawImage(ImageReader(bc_buf), 90, 18, width=105, height=13)

# -------------------------------------------------------------------------
# 11. Back Side Rendering (ከነ ሙሉ የታችኛው Disclaimer ጽሑፍ)
# -------------------------------------------------------------------------
def draw_card_back(c, data: dict, photo_bytes: bytes):
    bg_buf = get_dual_tone_card_background()
    c.drawImage(ImageReader(bg_buf), 0, 0, width=CARD_W, height=CARD_H)

    c.setStrokeColor(HexColor("#86EFAC"))
    c.setLineWidth(0.65)
    c.roundRect(3, 3, CARD_W - 6, CARD_H - 6, radius=6, fill=0, stroke=1)

    x, y = 14, CARD_H - 18
    # ስልክ
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor("#92400E"))
    c.drawString(x, y, "ስልክ | Phone Number")
    c.setFont("Helvetica-Bold", 6.8); c.setFillColor(HexColor("#06281D"))
    c.drawString(x, y - 7.5, data["phone"])

    y -= 17
    # ዜግነት
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor("#92400E"))
    c.drawString(x, y, "ዜግነት | Nationality")
    c.setFont(AMHARIC_FONT, 3.5); c.setFillColor(HexColor("#B45309"))
    c.drawString(x, y - 4.5, "(በራስ የተገለጸ/በውል የተሰጠ | Self Declared)")
    c.setFont(AMHARIC_BOLD, 6.8); c.setFillColor(HexColor("#06281D"))
    c.drawString(x, y - 12, "ኢትዮጵያዊ  |  Ethiopian")

    y -= 23
    # አድራሻ
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor("#92400E"))
    c.drawString(x, y, "አድራሻ | Address")
    c.setFont(AMHARIC_BOLD, 6.5); c.setFillColor(HexColor("#06281D"))
    c.drawString(x, y - 7.5, data["region_local"])
    c.setFont("Helvetica-Bold", 5.8)
    c.drawString(x, y - 13.5, data["region_en"])
    c.setFont(AMHARIC_BOLD, 6.5)
    c.drawString(x, y - 21, data["zone_local"])
    c.setFont("Helvetica-Bold", 5.8)
    c.drawString(x, y - 27, data["zone_en"])
    c.setFont(AMHARIC_BOLD, 6.5)
    c.drawString(x, y - 34.5, data["woreda_local"])
    c.setFont("Helvetica-Bold", 5.8)
    c.drawString(x, y - 40.5, data["woreda_en"])

    # FIN Box
    c.setFont(AMHARIC_FONT, 3.8); c.setFillColor(HexColor("#4B8B70"))
    c.drawString(x, 24, "ፋይዳ")
    c.drawString(x, 19, "መለያ ቁጥር")
    c.setStrokeColor(HexColor("#6EE7B7"))
    c.roundRect(x + 18, 16.5, 76, 12, radius=1.5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 6.2); c.setFillColor(HexColor("#06281D"))
    c.drawString(x + 22, 20, f"FIN {data['fin']}")

    # Crisp QR Code
    qr_payload = generate_fayda_encrypted_qr_payload(data, photo_bytes)
    qr_buf = generate_crisp_qr(qr_payload)
    c.drawImage(ImageReader(qr_buf), 115, 26, width=118, height=118)

    # የታችኛው ሙሉ Disclaimer ጽሑፍ (በአማርኛ እና በእንግሊዝኛ)
    c.saveState()
    c.setFont(AMHARIC_FONT, 3.2); c.setFillColor(HexColor("#1A3A2F"))
    c.drawString(10, 10, "ይህ መታወቂያ የጠፋበት ካገኘ በአቅራቢያው ላለ ፖሊስ ጣቢያ ወይም ለተቋሙ ያስረክቡ። ለተጨማሪ 9779 ላይ ይደውሉ ወይም id.et/cardprint ይጎብኙ።")
    c.setFont("Helvetica", 3.2)
    c.drawString(10, 5.5, "If lost and found, please return to nearby police station or to the institution. Call 9779 or visit id.et/cardprint for more")

    # SN ቁጥር በስተቀኝ
    c.setFont("Helvetica-Bold", 4.8); c.setFillColor(HexColor("#06281D"))
    c.drawRightString(CARD_W - 10, 7.5, f"SN: {data['sn']}")
    c.restoreState()

# -------------------------------------------------------------------------
# 12. Main Menu Keyboard
# -------------------------------------------------------------------------
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✅ Get PDF 1")
    markup.row("My Balance / አሁን ያለኝ", "Add Payment / ክፍያ ጨምር")
    markup.row("🔑 Resend(forget) FAN/FIN", "🔄 Reset / እንደገና ጀምር")
    return markup

# -------------------------------------------------------------------------
# 13. Handlers & Flow Management
# -------------------------------------------------------------------------
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name or "User"
    username = f"@{message.from_user.username}" if message.from_user.username else "No username"

    bot.clear_step_handler_by_chat_id(chat_id)
    user_data_store[chat_id] = {}
    bal, free_used = get_user_status(chat_id)

    if chat_id != ADMIN_CHAT_ID:
        notify_admin(
            f"🔔 **አዲስ ተጠቃሚ ቦቱን ከፍቷል!**\n\n"
            f"👤 **ስም:** {user_name}\n"
            f"🔗 **Username:** {username}\n"
            f"🆔 **Chat ID:** `{chat_id}`\n"
            f"💰 **ባላንስ:** `{bal:.2f} ETB`"
        )

    if chat_id == ADMIN_CHAT_ID:
        welcome_text = (
            "👑 **እንኳን ደህና መጡ ክቡር አድሚን ዲረስ!**\n\n"
            "እርስዎ ያለ ምንም ክፍያ ያልተገደበ (Unlimited) ካርዶችን በነጻ ማውጣት ይችላሉ።\n\n"
            "📌 **የአድሚን ትዕዛዝ፦** `/analytics`"
        )
    else:
        bonus_msg = "🎁 **እንኳን ደስ አለዎት! 1 ነጻ የካርድ ማውጫ ቦነስ አግኝተዋል።**\n\n" if free_used == 0 else ""
        welcome_text = (
            f"👋 **እንኳን ወደ ዲጂታል መታወቂያ ማዘጋጃ ቦት በደህና መጡ!**\n\n"
            f"{bonus_msg}"
            f"💰 **የአሁኑ ቀሪ ሂሳብዎ፦** `{bal:.2f} ETB`\n\n"
            "ለመጀመር ከታች **«✅ Get PDF 1»** የሚለውን ይጫኑ፦"
        )
    safe_send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['analytics', 'stats', 'admin'])
def handle_analytics_command(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_CHAT_ID:
        safe_send_message(chat_id, "⛔ ይህ ትዕዛዝ ለአስተዳዳሪ ብቻ የተፈቀደ ነው።")
        return

    stats = get_system_analytics()
    dashboard_text = (
        "📊 **Dires Hub Bot — የአስተዳዳሪ ዳሽቦርድ (Admin Analytics)**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• ጠቅላላ የተመዘገቡ ተጠቃሚዎች: `{stats.get('total_users', 0)}`\n"
        f"• ነጻ ካርድ የተጠቀሙ: `{stats.get('paid_tier_users', 0)}`\n"
        f"• በተጠቃሚዎች እጅ ያለ ባላንስ: `{stats.get('outstanding_balances', 0.0):.2f} ETB`\n"
        f"• ጠቅላላ የተመረቱ ካርዶች: `{stats.get('total_cards', 0)}`\n"
        f"• የተረጋገጡ ክፍያዎች (Tx): `{stats.get('total_tx_count', 0)}`\n"
        f"• **ጠቅላላ የተሰበሰበ ገቢ:** `{stats.get('total_income', 0.0):.2f} ETB`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
    if chat_id == ADMIN_CHAT_ID:
        safe_send_message(chat_id, "👑 **ክቡር አድሚን ዲረስ፦** እርስዎ ያልተገደበ (Unlimited) ነጻ መዳረሻ አለዎት።", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return
    bonus_status = "✅ ገና አልተጠቀሙበትም" if free_used == 0 else "❌ ተጠቅመዋል"
    safe_send_message(
        chat_id,
        f"💰 **የአሁኑ ቀሪ ሂሳብዎ፦** `{bal:.2f} ETB`\n"
        f"🎁 **የነጻ ካርድ ቦነስ፦** {bonus_status}\n\n"
        f"💡 ለእያንዳንዱ ተጨማሪ ካርድ፦ `{PRICE_PER_CARD:.2f} ETB`",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

def action_payment(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    payment_info = (
        "💳 **የክፍያ መመሪያ (ተቀባይ: Dires Gobale)፦**\n\n"
        f"1. **Telebirr**: `{TELEBIRR_ACCOUNT}` ({TELEBIRR_NAME})\n"
        f"2. **CBE**: `{CBE_ACCOUNT}` ({CBE_NAME})\n\n"
        "ክፍያውን ፈጽመው ሲያበቁ የቴሌብር/የባንክ **የደረሰኝ ፎቶ (Screenshot)** እዚህ ይላኩ።"
    )
    msg = safe_send_message(chat_id, payment_info, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_verify_payment_receipt)

def action_resend(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    msg = safe_send_message(
        chat_id,
        "🔍 **መረጃ መፈለጊያ (FAN / FIN Recovery)፦**\n\nየተመዘገቡበትን **ስልክ ቁጥር** ወይም **16 አሃዝ FAN ቁጥርዎን** ያስገቡ፦",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_search_record)

def action_pdf_generation(message):
    chat_id = message.chat.id
    bot.clear_step_handler_by_chat_id(chat_id)
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {}

    if chat_id == ADMIN_CHAT_ID:
        start_card_creation_flow(chat_id)
        return

    bal, free_used = get_user_status(chat_id)

    if free_used == 0:
        safe_send_message(chat_id, "🎁 **እንኳን ደስ አለዎት! በነጻ ቦነስዎ ካርድዎ እየተዘጋጀ ነው።**", parse_mode="Markdown")
        start_card_creation_flow(chat_id)
        return

    if bal >= PRICE_PER_CARD:
        start_card_creation_flow(chat_id)
        return

    qty_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    qty_markup.row("1 ካርድ (5 ብር)", "2 ካርድ (10 ብር)", "3 ካርድ (15 ብር)")
    qty_markup.row("5 ካርድ (25 ብር)", "10 ካርድ (50 ብር)", "20 ካርድ (100 ብር)")
    qty_markup.row("🔄 Reset / እንደገና ጀምር")

    prompt = (
        f"⚠️ **ክፍያ ያስፈልጋል!**\n\n"
        f"የአሁኑ ቀሪ ሂሳብዎ፦ `{bal:.2f} ETB`\n\n"
        f"• **Telebirr**: `{TELEBIRR_ACCOUNT}`\n"
        f"• **CBE**: `{CBE_ACCOUNT}`\n\n"
        "እባክዎ **ስንት ካርድ ማውጣት እንደሚፈልጉ ይምረጡ**፦"
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
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {}
    user_data_store[chat_id]["expected_pay"] = total_cost
    user_data_store[chat_id]["cards_count"] = count

    payment_prompt = (
        f"💳 **የክፍያ መጠየቂያ፦**\n\n"
        f"📊 የተመረጠ: `{count}` ካርድ\n"
        f"💰 ጠቅላላ ዋጋ: `{total_cost:.2f} ETB`\n\n"
        f"• Telebirr: `{TELEBIRR_ACCOUNT}` ({TELEBIRR_NAME})\n"
        f"• CBE: `{CBE_ACCOUNT}` ({CBE_NAME})\n\n"
        "ክፍያውን ፈጽመው ሲያበቁ የደረሰኙን **ፎቶ (Screenshot)** እዚህ ይላኩ፦"
    )
    msg = safe_send_message(chat_id, payment_prompt, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_verify_payment_receipt)

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
        msg = safe_send_message(chat_id, "🚫 ይህ ደረሰኝ ቀደም ሲል ጥቅም ላይ ውሏል! እባክዎ አዲስ ደረሰኝ ይላኩ፦")
        if msg:
            bot.register_next_step_handler(msg, step_verify_payment_receipt)
        return

    if chat_id not in user_data_store:
        user_data_store[chat_id] = {}
    user_data_store[chat_id]["temp_tx_id"] = tx_id
    prompt_payer = "👤 **በደረሰኙ ላይ የሚታየውን የከፋይ ሙሉ ስም እና ስልክ ቁጥር ያስገቡ፦**\n\n(ምሳሌ፡ አበበ ከበደ - 0912345678)"
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
        msg = safe_send_message(chat_id, "⚠️ እባክዎ ትክክለኛ ሙሉ ስም እና ስልክ ቁጥር ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_verify_payer_info)
        return

    record_used_receipt(tx_id, chat_id, amount_to_credit, sender_name, sender_phone)
    add_user_balance(chat_id, amount_to_credit)

    notify_admin(
        f"💵 **አዲስ ክፍያ ተረጋግጧል!**\n\n"
        f"👤 ከፋይ: `{sender_name}`\n"
        f"📞 ስልክ: `{sender_phone}`\n"
        f"💰 መጠን: `{amount_to_credit:.2f} ETB`\n"
        f"🧾 TxID: `{tx_id}`\n"
        f"🆔 Chat ID: `{chat_id}`"
    )

    safe_send_message(chat_id, f"✅ **ክፍያዎ ተረጋግጧል!** `{amount_to_credit:.2f} ETB` ተጨምሯል።\n\nወዲያውኑ ወደ ካርድ መስሪያው ደረጃ እናልፋለን...")
    start_card_creation_flow(chat_id)

# -------------------------------------------------------------------------
# 14. የመረጃ መቀበያ ደረጃዎች
# -------------------------------------------------------------------------
def start_card_creation_flow(chat_id):
    bot.clear_step_handler_by_chat_id(chat_id)
    if chat_id not in user_data_store:
        user_data_store[chat_id] = {}

    msg = safe_send_message(
        chat_id,
        "🎨 **ዲጂታል መታወቂያ ካርድ ዝግጅት፦**\n\n1️⃣ እባክዎ ሙሉ **ስምዎን በአማርኛ** ያስገቡ (ምሳሌ፡ ዲረስ ጎባሌ መለሰ)፦",
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
    user_data_store[chat_id]["name_en"] = transliterate_text(text)

    msg = safe_send_message(
        chat_id,
        f"✅ የእንግሊዝኛ ስምዎ፦ **{user_data_store[chat_id]['name_en']}**\n\n"
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
        msg = safe_send_message(chat_id, f"❌ ስህተት! ያስገቡት FAN ቁጥር {len(text)} አሃዝ ነው። በትክክል 16 አሃዝ ቁጥር ብቻ ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_fan_validation)
        return

    if chat_id != ADMIN_CHAT_ID and is_fan_registered(text):
        msg = safe_send_message(chat_id, "🚫 **ይህ FAN ቁጥር ቀደም ሲል ሌላ ሰው ተጠቅሞበታል!** እባክዎ የእራስዎን FAN ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_fan_validation)
        return

    user_data_store[chat_id]["fan_code"] = text
    prompt_dob = "3️⃣ **የትውልድ ቀንዎን በኢትዮጵያ ዘመን አቆጣጠር (E.C) ብቻ ያስገቡ፦**\n\n(ምሳሌ፡ 1994/09/29)"
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
        f"✅ የትውልድ ቀን፦ **{dob_ec} (E.C) | {dob_gc} (G.C)**\n\n4️⃣ **ጾታዎን ይምረጡ፦**",
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
        msg = safe_send_message(chat_id, "🚫 **ይህ ስልክ ቁጥር ቀድሞ በሌላ ካርድ ላይ ተመዝግቧል!** እባክዎ ያልተመዘገበ የራስዎን ስልክ ያስገቡ፦")
        if msg:
            bot.register_next_step_handler(msg, step_phone)
        return

    user_data_store[chat_id]["phone"] = clean_phone

    reg_km = types.ReplyKeyboardMarkup(resize_keyboard=True)
    reg_keys = list(ETHIOPIA_REGIONS.keys())
    for i in range(0, len(reg_keys), 2):
        if i + 1 < len(reg_keys):
            reg_km.row(reg_keys[i], reg_keys[i+1])
        else:
            reg_km.add(reg_keys[i])
    reg_km.row("🔄 Reset / እንደገና ጀምር")

    msg = safe_send_message(chat_id, "6️⃣ **ክልልዎን ይምረጡ (Select Region)፦**", reply_markup=reg_km, parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, step_region_select)

def step_region_select(message):
    chat_id = message.chat.id
    if check_and_route_button(message):
        return

    reg_chosen = message.text.strip() if message.text else ""
    selected_reg_data = None
    for k, v in ETHIOPIA_REGIONS.items():
        if reg_chosen == k or reg_chosen == v["local"] or reg_chosen == v["en"]:
            selected_reg_data = (k, v)
            break

    if not selected_reg_data:
        user_data_store[chat_id]["region_local"] = reg_chosen
        user_data_store[chat_id]["region_en"] = transliterate_text(reg_chosen)
        user_data_store[chat_id]["selected_region_key"] = None
        zones_available = []
    else:
        k, v = selected_reg_data
        user_data_store[chat_id]["region_local"] = v["local"]
        user_data_store[chat_id]["region_en"] = v["en"]
        user_data_store[chat_id]["selected_region_key"] = k
        zones_available = list(v["zones"].keys())

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
        f"✅ ክልል፦ **{user_data_store[chat_id]['region_local']} ({user_data_store[chat_id]['region_en']})** ተመርጧል!\n\n7️⃣ **ዞንዎን ይምረጡ (ወይም ይጻፉ)፦**",
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
    reg_key = user_data_store[chat_id].get("selected_region_key")

    woredas_available = []
    if reg_key and reg_key in ETHIOPIA_REGIONS and zone_chosen in ETHIOPIA_REGIONS[reg_key]["zones"]:
        z_info = ETHIOPIA_REGIONS[reg_key]["zones"][zone_chosen]
        user_data_store[chat_id]["zone_local"] = zone_chosen
        user_data_store[chat_id]["zone_en"] = z_info["en"]
        woredas_available = z_info["woredas"]
    else:
        user_data_store[chat_id]["zone_local"] = zone_chosen
        user_data_store[chat_id]["zone_en"] = transliterate_text(zone_chosen)

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
        f"✅ ዞን፦ **{user_data_store[chat_id]['zone_local']} ({user_data_store[chat_id]['zone_en']})** ተመርጧል!\n\n8️⃣ **ወረዳዎን ይምረጡ (ወይም ይጻፉ)፦**",
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
    user_data_store[chat_id]["woreda_local"] = woreda_chosen
    user_data_store[chat_id]["woreda_en"] = transliterate_text(woreda_chosen)

    msg = safe_send_message(
        chat_id,
        f"✅ ወረዳ፦ **{woreda_chosen}** ተመርጧል!\n\n"
        "9️⃣ 📸 በመጨረሻም ለመታወቂያው የሚሆን ማንኛውንም **የቁም ፎቶ** ይላኩ (ሙሉ ቁመት ፎቶ ቢሆን እንኳን ሲስተሙ ፊቱን በራሱ ቆርጦ ፓስፖርት ያደርገዋል)፦",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    if msg:
        bot.register_next_step_handler(msg, step_photo)

# -------------------------------------------------------------------------
# 15. ፎቶ ተቀብሎ በቅጽበት ፒዲኤፍ ማመንጨት
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
    raw_photo_bytes = bot.download_file(file_info.file_path)

    # ራስ-ሰር ፊቱንና ደረቱን አጉልቶ የሚቆርጥ ስማርት አሰራር (Smart Portrait Crop)
    processed_photo_buf = prepare_portrait_photo(raw_photo_bytes)
    photo_reader = ImageReader(processed_photo_buf)
    ghost_reader = ImageReader(processed_photo_buf)

    u = user_data_store.get(chat_id, {})
    fin_number = f"4391 {str(chat_id)[-4:]} 4128"

    card_data = {
        "name_am": u.get("name_am", ""),
        "name_en": u.get("name_en", ""),
        "dob_ec": u.get("dob_ec", ""),
        "dob_gc": u.get("dob_gc", ""),
        "sex_am": u.get("sex_am", ""),
        "sex_en": u.get("sex_en", ""),
        "issued_gc": "25/Oct/2026",
        "expiry_ec": "13/02/2027",
        "expiry_gc": "2034/Oct/23",
        "fan_code": u.get("fan_code", ""),
        "phone": u.get("phone", ""),
        "region_local": u.get("region_local", ""),
        "region_en": u.get("region_en", ""),
        "zone_local": u.get("zone_local", ""),
        "zone_en": u.get("zone_en", ""),
        "woreda_local": u.get("woreda_local", ""),
        "woreda_en": u.get("woreda_en", ""),
        "fin": fin_number,
        "sn": str(int(time.time()))[-7:]
    }

    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(CARD_W, CARD_H))
    draw_card_front(c, card_data, photo_reader, ghost_reader)
    c.showPage()
    draw_card_back(c, card_data, raw_photo_bytes)
    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    filename = f"Fayda_Card_{card_data['name_en'].replace(' ', '_')}.pdf"
    
    try:
        bot.send_document(
            chat_id,
            (filename, pdf_buffer.getvalue()),
            caption=(
                f"🎉 **የኢትዮጵያ ዲጂታል መታወቂያ ካርድዎ ተዘጋጅቷል!**\n\n"
                f"👤 **ስም**: {card_data['name_am']} ({card_data['name_en']})\n"
                f"🆔 **FAN**: `{card_data['fan_code']}`\n"
                f"📅 **የትውልድ ቀን**: `{card_data['dob_ec']} (E.C) | {card_data['dob_gc']} (G.C)`\n"
                f"📍 **አድራሻ**: {card_data['region_local']} | {card_data['zone_local']}\n"
                f"🔑 **FIN**: `{fin_number}`"
            ),
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Send document error: {e}")

    def _background_save_and_notify():
        try:
            save_card_record(
                chat_id=chat_id,
                name_am=card_data["name_am"],
                name_en=card_data["name_en"],
                fan=card_data["fan_code"],
                phone=card_data["phone"],
                fin=fin_number,
                theme="PDF 1"
            )
            deduct_for_card(chat_id)
            notify_admin(
                f"🪪 **አዲስ ካርድ ወጥቷል!**\n\n"
                f"👤 ስም: {card_data['name_am']} ({card_data['name_en']})\n"
                f"🆔 FAN: `{card_data['fan_code']}`\n"
                f"📞 ስልክ: `{card_data['phone']}`\n"
                f"📍 አድራሻ: {card_data['region_en']}, {card_data['zone_en']}\n"
                f"🆔 Chat ID: `{chat_id}`"
            )
        except Exception:
            pass

    threading.Thread(target=_background_save_and_notify, daemon=True).start()

    if status_msg:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            pass

# -------------------------------------------------------------------------
# 16. FAN/FIN መፈለጊያ
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
            f"✅ **የተገኘ መረጃ፦**\n\n"
            f"👤 **ስም**: {name_am} / {name_en}\n"
            f"📞 **ስልክ**: `{phone}`\n"
            f"🆔 **FAN ቁጥር**: `{fan}`\n"
            f"🔑 **FIN ቁጥር**: `{fin}`",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        safe_send_message(chat_id, f"❌ በ `{query_text}` የተመዘገበ መረጃ አልተገኘም!", reply_markup=get_main_keyboard(), parse_mode="Markdown")

# -------------------------------------------------------------------------
# 17. Universal Button Router
# -------------------------------------------------------------------------
def check_and_route_button(message):
    if not message.text:
        return False
    txt = message.text.strip()
    
    if "PDF" in txt:
        action_pdf_generation(message)
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

@bot.message_handler(func=lambda m: True, content_types=['text'])
def catch_all_messages(message):
    if check_and_route_button(message):
        return
    safe_send_message(message.chat.id, "እባክዎ ከታች ካሉት አዝራሮች አንዱን ይምረጡ፦", reply_markup=get_main_keyboard())

# -------------------------------------------------------------------------
# 18. Dummy Port Server (ለ Render)
# -------------------------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Dires Fayda Bot is Live and Authentic!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

# -------------------------------------------------------------------------
# 19. Polling Loop
# -------------------------------------------------------------------------
def main():
    try:
        bot.remove_webhook()
    except Exception:
        pass
    print("🚀 Dires Hub Bot (Vibrant Mint-Green & Yellow Dual-Tone Engine) is running...")
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=25, long_polling_timeout=25)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    main()