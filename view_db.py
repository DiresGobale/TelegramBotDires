import sqlite3
import os

DB_FILE = "fayda_bot_users.db"

def inspect_database():
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file '{DB_FILE}' አልተገኘም! መጀመሪያ ቦቱን አስነስተው መረጃ ያስመዝግቡ።")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print("\n" + "=" * 65)
    print("📋 የቦቱ ተጠቃሚዎች እና ሂሳብ (USERS & BALANCES)")
    print("=" * 65)
    c.execute("SELECT chat_id, balance FROM users")
    users = c.fetchall()

    if not users:
        print("ምንም የተመዘገበ ተጠቃሚ የለም።")
    else:
        print(f"{'Chat ID':<18} | {'ቀሪ ሂሳብ (Balance ETB)':<20}")
        print("-" * 42)
        for chat_id, balance in users:
            print(f"{str(chat_id):<18} | {balance:<20.2f}")

    print("\n" + "=" * 110)
    print("🪪 የተዘጋጁ የፋይዳ ካርዶች ሙሉ ዝርዝር (FAYDA CARDS RECORD)")
    print("=" * 110)
    c.execute("""
        SELECT id, chat_id, name_am, name_en, fan_code, phone, fin_code, theme, created_at 
        FROM card_records 
        ORDER BY id DESC
    """)
    records = c.fetchall()

    if not records:
        print("እስካሁን የወጣ ምንም የፋይዳ ካርድ የለም።")
    else:
        header = f"{'ID':<4} | {'ሙሉ ስም (አማርኛ)':<20} | {'Full Name (English)':<22} | {'FAN (16-Digit)':<18} | {'ስልክ':<12} | {'Theme':<6} | {'የተመዘገበበት ቀን'}"
        print(header)
        print("-" * len(header))
        for row in records:
            rec_id, chat_id, name_am, name_en, fan, phone, fin, theme, created_at = row
            name_am_d = (name_am[:17] + "..") if len(name_am) > 19 else name_am
            name_en_d = (name_en[:19] + "..") if len(name_en) > 21 else name_en
            print(f"{rec_id:<4} | {name_am_d:<20} | {name_en_d:<22} | {fan:<18} | {phone:<12} | {theme:<6} | {created_at}")

    print("\n" + "=" * 110)
    conn.close()

if __name__ == "__main__":
    inspect_database()