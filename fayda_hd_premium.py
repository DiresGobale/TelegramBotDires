import os
import time
import math
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import Image, ImageDraw
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Amharic Font Configuration
AMHARIC_FONT = "Helvetica"
AMHARIC_BOLD = "Helvetica-Bold"

nyala_path = "C:/Windows/Fonts/nyala.ttf"
if os.path.exists(nyala_path):
    pdfmetrics.registerFont(TTFont("Nyala", nyala_path))
    AMHARIC_FONT = "Nyala"
    AMHARIC_BOLD = "Nyala"

# Standard CR80 Card Dimensions (in points)
CARD_W = 242.6
CARD_H = 153.0

def generate_sample_avatar(filename="user_photo.jpg"):
    """High quality avatar image generate karta hai agar file na ho"""
    if not os.path.exists(filename):
        img = Image.new("RGB", (400, 520), color="#E2E8F0")
        draw = ImageDraw.Draw(img)
        draw.ellipse([130, 90, 270, 230], fill="#64748B")
        draw.chord([60, 250, 340, 530], start=180, end=360, fill="#475569")
        img.save(filename, quality=100)
    return filename

def generate_crisp_barcode(code_text: str):
    """Ultra crisp 300+ DPI Code128 barcode"""
    code128 = barcode.get_barcode_class('code128')
    writer = ImageWriter()
    writer.dpi = 350
    bc = code128(code_text, writer=writer)
    buf = BytesIO()
    bc.write(buf, options={"write_text": False, "quiet_zone": 1})
    buf.seek(0)
    return buf

def generate_crisp_qr(data_text: str):
    """High resolution crisp QR Code"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=1,
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG", quality=100)
    buf.seek(0)
    return buf

def draw_security_pattern(c):
    """Card background me authentic fine security curves draw karta hai"""
    c.saveState()
    c.setStrokeColor(HexColor("#E2F4EC"))
    c.setLineWidth(0.35)
    for i in range(0, int(CARD_W), 14):
        c.bezier(i, 4, i + 35, CARD_H / 2, i - 25, CARD_H - 10, i + 10, CARD_H - 4)
    c.restoreState()

def draw_front_side(c, data: dict, photo_path: str):
    # Base background and outer border
    c.setFillColor(HexColor("#F6FCF9"))
    c.setStrokeColor(HexColor("#94A3B8"))
    c.setLineWidth(0.65)
    c.roundRect(4, 4, CARD_W - 8, CARD_H - 8, radius=7, fill=1, stroke=1)

    # Security waves background
    draw_security_pattern(c)

    # 1. Header Section
    flag_x, flag_y = 12, CARD_H - 25
    c.setFillColor(HexColor("#078930")); c.rect(flag_x, flag_y + 8.4, 21, 4.2, fill=1, stroke=0)
    c.setFillColor(HexColor("#FCDD09")); c.rect(flag_x, flag_y + 4.2, 21, 4.2, fill=1, stroke=0)
    c.setFillColor(HexColor("#DA121A")); c.rect(flag_x, flag_y, 21, 4.2, fill=1, stroke=0)

    # Header Titles
    c.setFillColor(HexColor("#0D5C46"))
    c.setFont(AMHARIC_BOLD, 7)
    c.drawString(39, CARD_H - 16, "የኢትዮጵያ ዲጂታል መታወቂያ ካርድ")
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(39, CARD_H - 24, "Ethiopian Digital ID Card")

    # National ID Emblem / Logo icon in top right
    c.setStrokeColor(HexColor("#0D5C46"))
    c.setLineWidth(0.8)
    c.circle(CARD_W - 20, CARD_H - 20, 7, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 4.2)
    c.drawCentredString(CARD_W - 20, CARD_H - 21.5, "FAYDA")

    # 2. Main Photo and Secondary Ghost Photo
    photo = generate_sample_avatar(photo_path)
    c.drawImage(photo, 18, CARD_H - 110, width=54, height=68, preserveAspectRatio=True)
    c.setStrokeColor(HexColor("#64748B"))
    c.setLineWidth(0.7)
    c.rect(18, CARD_H - 110, 54, 68, fill=0, stroke=1)

    # Secondary Photo (Right Bottom)
    c.drawImage(photo, CARD_W - 35, 18, width=17, height=22, preserveAspectRatio=True)
    c.rect(CARD_W - 35, 18, 17, 22, fill=0, stroke=1)

    # Vertical Date Text (Left side of photo)
    c.saveState()
    c.translate(14, CARD_H - 106)
    c.rotate(90)
    c.setFont("Helvetica", 4.3)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(0, 0, f"{data['issued_gc']} | {data['expiry_gc']}")
    c.restoreState()

    # 3. User Details
    x_lbl = 78
    cur_y = CARD_H - 35

    # Full Name
    c.setFont(AMHARIC_FONT, 5)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(x_lbl, cur_y, "ሙሉ ስም | Full Name")
    cur_y -= 6.5
    c.setFont(AMHARIC_BOLD, 7.5)
    c.setFillColor(HexColor("#0F172A"))
    c.drawString(x_lbl, cur_y, data["name_am"])
    cur_y -= 7.5
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x_lbl, cur_y, data["name_en"])

    # Date of Birth
    cur_y -= 9
    c.setFont(AMHARIC_FONT, 5)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(x_lbl, cur_y, "የትውልድ ቀን | Date of Birth")
    cur_y -= 6.5
    c.setFont("Helvetica-Bold", 6.2)
    c.setFillColor(HexColor("#0F172A"))
    c.drawString(x_lbl, cur_y, f"{data['dob_ec']} | {data['dob_gc']}")

    # Gender
    cur_y -= 9
    c.setFont(AMHARIC_FONT, 5)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(x_lbl, cur_y, "ጾታ | Sex")
    cur_y -= 6.5
    c.setFont(AMHARIC_BOLD, 6.2)
    c.setFillColor(HexColor("#0F172A"))
    c.drawString(x_lbl, cur_y, f"{data['sex_am']} | {data['sex_en']}")

    # Issue and Expiry
    cur_y -= 9
    c.setFont(AMHARIC_FONT, 5)
    c.setFillColor(HexColor("#64748B"))
    c.drawString(x_lbl, cur_y, "የተሰጠበትና የሚያበቃበት ቀን | Issued & Expiry")
    cur_y -= 6.5
    c.setFont("Helvetica-Bold", 6.2)
    c.setFillColor(HexColor("#0F172A"))
    c.drawString(x_lbl, cur_y, f"{data['issued_gc']} | {data['expiry_gc']}")

    # 4. Barcode and Identification Number
    bc_buf = generate_crisp_barcode(data["fan_code"])
    c.setFont("Helvetica-Bold", 5.8)
    c.setFillColor(HexColor("#0F172A"))
    c.drawCentredString(142, 26, data["fan_code"])
    c.drawImage(ImageReader(bc_buf), 90, 13, width=102, height=11)

def draw_back_side(c, data: dict):
    # Base background and outer border
    c.setFillColor(HexColor("#F6FCF9"))
    c.setStrokeColor(HexColor("#94A3B8"))
    c.setLineWidth(0.65)
    c.roundRect(4, 4, CARD_W - 8, CARD_H - 8, radius=7, fill=1, stroke=1)

    draw_security_pattern(c)

    # 1. Left Information Details
    x = 14
    y = CARD_H - 18

    # Phone Number
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor("#64748B"))
    c.drawString(x, y, "ስልክ ቁጥር | Phone Number")
    c.setFont("Helvetica-Bold", 6.2); c.setFillColor(HexColor("#0F172A"))
    c.drawString(x, y - 6.5, data["phone"])

    # Nationality
    y -= 15
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor("#64748B"))
    c.drawString(x, y, "ዜግነት | Nationality")
    c.setFont(AMHARIC_BOLD, 6.2); c.setFillColor(HexColor("#0F172A"))
    c.drawString(x, y - 6.5, "ኢትዮጵያዊ")
    c.setFont("Helvetica-Bold", 5.5)
    c.drawString(x, y - 13, "Ethiopian")

    # Address
    y -= 22
    c.setFont(AMHARIC_FONT, 4.8); c.setFillColor(HexColor("#64748B"))
    c.drawString(x, y, "አድራሻ | Address")

    # Region
    c.setFont(AMHARIC_BOLD, 5.8); c.setFillColor(HexColor("#0F172A"))
    c.drawString(x, y - 7, data["region_am"])
    c.setFont("Helvetica", 5.2)
    c.drawString(x, y - 13, data["region_en"])

    # Zone
    c.setFont(AMHARIC_BOLD, 5.8)
    c.drawString(x, y - 20, data["zone_am"])
    c.setFont("Helvetica", 5.2)
    c.drawString(x, y - 26, data["zone_en"])

    # Woreda (Tach Armachiho)
    c.setFont(AMHARIC_BOLD, 5.8)
    c.drawString(x, y - 33, data["woreda_am"])
    c.setFont("Helvetica", 5.2)
    c.drawString(x, y - 39, data["woreda_en"])

    # FIN Box
    c.setStrokeColor(HexColor("#64748B"))
    c.roundRect(x, 15, 76, 13, radius=2.5, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 5.8)
    c.setFillColor(HexColor("#0F172A"))
    c.drawString(x + 4, 19.5, f"FIN: {data['fin']}")

    # 2. Large High-Density QR Code
    qr_payload = f"FIN:{data['fin']};NAME:{data['name_en']};DOB:{data['dob_gc']};PHONE:{data['phone']}"
    qr_buf = generate_crisp_qr(qr_payload)
    c.drawImage(ImageReader(qr_buf), 96, 23, width=135, height=122)

    # Serial Number (SN)
    c.setFont("Helvetica-Bold", 5.2)
    c.setFillColor(HexColor("#334155"))
    c.drawString(CARD_W - 55, 11, f"SN: {data['sn']}")

def create_fayda_card_pdf(output_pdf="official_fayda_id.pdf"):
    c = canvas.Canvas(output_pdf, pagesize=(CARD_W, CARD_H))

    card_data = {
        "name_am": "መቅደስ ዋጋው መለሰ",
        "name_en": "Mekides Wagnaw Melese",
        "dob_ec": "2009/04/03",
        "dob_gc": "25/07/2001",
        "sex_am": "ሴት",
        "sex_en": "Female",
        "issued_gc": "2026/08/21",
        "expiry_gc": "2034/May/01",
        "fan_code": "3186142308743784",
        "phone": "0957625740",
        "region_am": "አማራ",
        "region_en": "Amhara",
        "zone_am": "ማዕከላዊ ጎንደር",
        "zone_en": "Central Gonder",
        "woreda_am": "ታች አርማጭሆ",
        "woreda_en": "Tach Armachiho",
        "fin": "9243 1046 3827",
        "sn": "8116635"
    }

    # Front Page
    draw_front_side(c, card_data, "user_photo.jpg")
    c.showPage()

    # Back Page
    draw_back_side(c, card_data)
    c.showPage()

    c.save()
    print(f"File create ho gayi hai: {output_pdf}")

if __name__ == "__main__":
    file_name = f"official_fayda_hd_{int(time.time())}.pdf"
    create_fayda_card_pdf(file_name)