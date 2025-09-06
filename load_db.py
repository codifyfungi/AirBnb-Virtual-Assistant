import os
import sqlite3
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re
from dotenv import load_dotenv
load_dotenv()  
def init_db():
    conn = sqlite3.connect("airbnb.db")
    cursor = conn.cursor()

    # Create table for clients
    # Create table for messages
    # message id is email uid    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        listing_id TEXT PRIMARY KEY,
        address TEXT
    )
    """)    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id TEXT PRIMARY KEY,
        listing_id TEXT,
        guest_name TEXT,
        guest_image TEXT,
        guest_location TEXT,
        adults INT,
        children INT,
        guest_paid INT,
        host_payout INT,
        check_in_date TEXT,
        check_out_date TEXT,
        FOREIGN KEY (listing_id) REFERENCES listings (listing_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        uid INTEGER PRIMARY KEY,
        reservation_id TEXT,
        content TEXT,
        name TEXT,
        host INTEGER,
        FOREIGN KEY (reservation_id) REFERENCES listings (reservation_id)
    )
    """)

    conn.commit()
    conn.close()
def get_last_seen_uid(cursor):
    cursor.execute("SELECT MAX(uid) FROM messages")
    row = cursor.fetchone()
    return row[0] if row[0] is not None else 0
def get_body(msg):
    plain_body = ""
    html_body  = ""
    if msg.is_multipart():
        for part in msg.walk():
            # skip containers and attachments
            if part.get_content_maintype() == "multipart" or part.get("Content-Disposition"):
                continue

            ctype   = part.get_content_type()
            charset = part.get_content_charset() or "utf-8"
            if ctype == "text/plain":
                # direct concatenation
                plain_body += part.get_payload(decode=False) + "\n"
            elif ctype == "text/html":
                html_body += part.get_payload(decode=True).decode(charset, "replace") + "\n"
        else:
            # single‑part message
            ctype   = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            if ctype == "text/plain":
                plain_body = msg.get_payload(decode=False)
            elif ctype == "text/html":
                html_body = msg.get_payload(decode=True).decode(charset, "replace")        
        m = re.search(
            r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
            plain_body
        ) 
    return plain_body, html_body
def load():
    init_db()
    EM = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")
    conn = sqlite3.connect("airbnb.db")
    cursor = conn.cursor()
    last_uid = get_last_seen_uid(cursor)
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EM, PASSWORD)
    mail.select("inbox")
    #Data is a list of byte strings
    # Retrieve any new automated reservation reminders
    status, data = mail.uid(
        "search", None,
        'UID', f'{last_uid+1}:*',
        'FROM', '"automated@airbnb.com"',
        'SUBJECT', '"Reservation Reminder"'
    )
    auto_ids = b" ".join(data).split()
    #Create list of ids corresponding to an email    
    status, data = mail.uid(
        "search", None,
        'UID', f'{last_uid+1}:*',
        'FROM', '"express@airbnb.com"'
    )
    express_ids = b" ".join(data).split()
    print("IDS")
    print(last_uid+1)
    for uid in auto_ids:
        status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
        uid = int(uid.decode())
        print(uid)
        msg = email.message_from_bytes(msg_data[0][1])
        plain_body, html_body = get_body(msg)
        m = re.search(
            r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
            plain_body
        )
        reservation_id = m.group(1)
        list_m = re.search(r"https?://www\.airbnb\.com/rooms/(\d+)", plain_body)
        listing_id = list_m.group(1) if list_m else None
        loc_m = re.search(
            r"https?://www\.airbnb\.com/hosting/reservations/details/[^\s]+\S.*?\r?\n\s*([A-Za-z ]+,\s*[A-Z]{2}|US)\s*(?:\r?\n|$)",
            plain_body,
            flags=re.IGNORECASE | re.DOTALL
        )
        guest_location = loc_m.group(1).strip() if loc_m else None
        # Extract guest name from Subject line (e.g. 'Reservation reminder: Jerome is coming soon!')
        subject = msg.get('Subject', '')
        # Capture the name following 'Reservation reminder:'
        sub_m = re.search(r'Reservation reminder:\s*([A-Za-z]+)', subject, flags=re.IGNORECASE)
        guest_name = sub_m.group(1) if sub_m else None
        # Extract number of adults and children
        ad_m = re.search(r"(\d+)\s+adults", plain_body)
        adults = int(ad_m.group(1)) if ad_m else None
        ch_m = re.search(r"(\d+)\s+children", plain_body)
        children = int(ch_m.group(1)) if ch_m else None
        # Extract payment details
        paid_m = re.search(r"TOTAL \(USD\)\s*\$([\d,\.]+)", plain_body)
        total_paid = paid_m.group(1) if paid_m else None
        earn_m = re.search(r"YOU EARN\s*\$([\d,\.\-]+)", plain_body)
        host_payout = earn_m.group(1) if earn_m else None
        # Extract check-in and check-out dates based on the block with 'Check-in    Checkout' and a date line
        dates_m = re.search(
            r'Check-in[\s\S]*?^\s*([A-Za-z]{3},\s*[A-Za-z]{3}\s+\d{1,2}(?:,\s*\d{4})?)\s+([A-Za-z]{3},\s*[A-Za-z]{3}\s+\d{1,2}(?:,\s*\d{4})?)',
            plain_body,
            flags=re.IGNORECASE | re.MULTILINE
        )
        if dates_m:
            check_in_date, check_out_date = dates_m.groups()
        else:
            check_in_date = check_out_date = None
        # Override with direct muscache user image URL from either /im/pictures/user or /im/users/.../profile_pic
        img_m = re.search(
            # Match both /im/pictures/user and /im/users/.../profile_pic paths
            r'(https://a0\.muscache\.com/im/(?:pictures/user|users/[^/\s<>]+/profile_pic)/[^"\s<>]+\.(?:jpe?g)(?:\?[^"\s<>]*)?)',
            html_body,
            flags=re.IGNORECASE
        )
        try:
            guest_image = img_m.group(1)
        except AttributeError:
            guest_image = None
        soup = BeautifulSoup(html_body, "html.parser")
        ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        message = None
        if listing_id:
            cursor.execute(
                "INSERT OR IGNORE INTO listings (listing_id) VALUES (?)",
                (listing_id,)
            )
        # Upsert reservation with detailed fields
        cursor.execute(
            "INSERT OR IGNORE INTO reservations (reservation_id, listing_id, guest_name, guest_image, guest_location, adults, children, guest_paid, host_payout, check_in_date, check_out_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (reservation_id, listing_id, guest_name, guest_image, guest_location, adults, children, total_paid, host_payout, check_in_date, check_out_date)
        )
        if ptexts[5] != "Entire home/apt":
            cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, ptexts[5], guest_name, 0))
    for uid in express_ids:
        status, msg_data = mail.uid("FETCH",uid,"(RFC822)")
        uid = int(uid.decode())
        msg = email.message_from_bytes(msg_data[0][1])
        print(uid)
        print(msg["From"])
        plain_body, html_body = get_body(msg)
        m = re.search(
            r'https://www\.airbnb\.com/hosting/thread/(\d+)\?',
            plain_body
        )
        reservation_id = m.group(1)
        soup = BeautifulSoup(html_body, "html.parser")
        ptexts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        h2texts = [h2.get_text(" ", strip=True) for h2 in soup.find_all("h2")]
        image_srcs = [img["src"] for img in soup.find_all("img", src=True)]
        if ptexts[1] == "Host" or ptexts[1] == "Guest" or ptexts[1] == "Booker":
            message = ptexts[2]
            host = ptexts[1] == "Host"
            name = h2texts[0]
            cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, message, name, host))
        else:
            message = ptexts[2]
            host = image_srcs[2] == "https://a0.muscache.com/im/pictures/user/89a57bc6-3c38-435c-807d-904e2bac20c1.jpg?aki_policy=profile_medium" 
            name = ptexts[1]
            cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?)", (uid, reservation_id, message, name, host))
    conn.commit()
    conn.close()
load()